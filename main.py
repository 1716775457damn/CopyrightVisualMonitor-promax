"""
核心入口 main.py
统一调度两种功能模式：
  ① 软著申请状态监控 (Monitor)
  ② 软著文件自动上传提交 (Upload)
"""
import threading
import sys
import os
import tkinter as tk
from tkinter import filedialog
import glob
import re

from page_judger import PageJudger
from exporter import Exporter
from browser_utils import start_edge
from gui_main import MainGUI
import config_manager


# ============== 材料解析工具函数 (上传模式) ==============

def discover_material_files(folder_path):
    """自动发现材料文件夹中的 TXT 信息文件和 PDF 文档"""
    txt_files = glob.glob(os.path.join(folder_path, "*软件信息*.txt"))
    code_pdfs = glob.glob(os.path.join(folder_path, "*源代码文档*.pdf"))
    doc_pdfs = glob.glob(os.path.join(folder_path, "*软件著作权*.pdf"))
    if not doc_pdfs:
        doc_pdfs = glob.glob(os.path.join(folder_path, "*文档*.pdf"))
    
    if not txt_files:
        raise FileNotFoundError("未找到包含'软件信息'的 TXT 文件")
    if not code_pdfs:
        raise FileNotFoundError("未找到包含'源代码文档'的 PDF 文件")
    if not doc_pdfs:
        raise FileNotFoundError("未找到包含'软件著作权文档'或'文档'的 PDF 文件")
        
    return txt_files[0], code_pdfs[0], doc_pdfs[0]


def parse_software_info(txt_path):
    """从 TXT 信息文件中解析结构化软件信息"""
    data = {}
    key_mapping = {
        "软件全称": "software_name",
        "版本号": "version",
        "开发的硬件环境": "dev_hardware",
        "运行的硬件环境": "run_hardware",
        "开发该软件的操作系统": "dev_os",
        "软件开发环境 / 开发工具": "dev_tools",
        "该软件的运行平台 / 操作系统": "run_platform",
        "软件运行支撑环境 / 支持软件": "support_software",
        "编程语言": "language",
        "源程序量": "source_lines",
        "开发目的": "dev_purpose",
        "面向领域 / 行业": "target_domain",
        "软件的主要功能": "main_functions",
        "技术特点": "tech_features"
    }
    
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(txt_path, 'r', encoding='gbk') as f:
            content = f.read()
            
    matches = re.finditer(r'【(.+?)】[：:]?\s*([^\n]+)', content)
    for match in matches:
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key in key_mapping:
            data[key_mapping[key]] = value
            
    time_match = re.search(r'生成时间[：:]\s*([0-9/]+)', content)
    if time_match:
        time_str = time_match.group(1).replace('/', '-')
        data['dev_finish_date'] = time_str
            
    return data


# ============== 核心应用类 ==============

class AppCore:
    def __init__(self, gui: MainGUI):
        self.gui = gui
        
        self.exporter = Exporter()
        self.page_judger = None
        self.process = None
        
    def init_browser(self):
        """通用浏览器初始化（两种模式共用）"""
        # 记录账号密码刷新
        account, password = self.gui.get_current_credentials()
        self.page_judger = PageJudger(
            logger_callback=self.gui.log,
            account=account,
            password=password
        )

        # 检查浏览器进程是否存活
        is_alive = self.process and self.process.poll() is None
        
        if not is_alive:
            if self.process:
                self.gui.log("检测到浏览器已关闭，正在重新启动...")
            else:
                self.gui.log("正在启动本地 Edge 浏览器环境...")
            
            self.process = None # 重置
            target_url = "https://register.ccopyright.com.cn/account.html?current=soft_register"
            self.process = start_edge(target_url)
            self.gui.log(f"浏览器已就绪，使用账号: {account} 执行任务")
        else:
            self.gui.log(f"检测到已有浏览器运行中，直接激活任务账号: {account}")
        
    def require_login(self):
        """由 Judger 回调请求登录验证阻塞"""
        event = threading.Event()
        self.gui.ask_for_login(event)
        self.gui.log(">>> 请在弹出的浏览器中手动完成图形验证...")
        event.wait()
        self.gui.log("用户已确认验证完成，继续读取。")
    
    # ---------- 模式 1：状态监控流程 ----------
    def run_monitor_flow(self):
        try:
            self.init_browser()
            
            self.gui.log("开始进行页面图像 OCR 状态扫描...")
            is_ready = self.page_judger.process_flow(require_login_callback=self.require_login)
            
            if not is_ready:
                self.gui.log("未能进入待检测列表页面，请检查网络或重试。")
                return
                
            self.gui.update_status("正在提取角标与表格数据...")
            
            data_res, records, img_cv = self.page_judger.read_core_data()
            self.gui.log(f"各状态统计: {data_res}")
            self.gui.log(f"共提取到 {len(records)} 条软件登记记录")
            
            self.gui.update_status("数据归档中...")
            final_data = self.exporter.check_changes_and_notify(data_res)
            
            self.gui.log(f"变化核对结果: {final_data.get('变化说明')}")
            if final_data.get('变化说明') != '无变化':
                self.gui.show_alert_changes(final_data)
                
            excel_dst = self.exporter.save_excel(final_data, records)
            self.gui.log(f"数据已追加保存至 -> {excel_dst}")
            
            img_dst = self.exporter.save_screenshot(img_cv)
            self.gui.log(f"证据截图已保存至 -> {img_dst}")
            
            self.gui.log("本次监控任务圆满成功！")
            self.gui.update_status("自检空闲中 (任务完成)", stop_progress=True)
            
            try:
                self.gui.log("正在尝试自动打开 Excel...")
                os.startfile(excel_dst)
            except Exception as e:
                self.gui.log(f"自动打开 Excel 失败: {e}")
                
        except Exception as e:
            self.gui.log(f"执行异常发生: {e}")
            self.gui.update_status("自检失败退回", stop_progress=True)
        finally:
            self.gui.set_button_state(False)
    
    # ---------- 模式 2：自动上传提交流程 ----------
    def run_upload_flow(self):
        try:
            # 0. 请求用户选择材料文件夹
            self.gui.log("等待用户选择软著申请材料文件夹...")
            materials_dir = filedialog.askdirectory(title="请选择包含TXT和PDF的软著材料文件夹")
            if not materials_dir:
                self.gui.log("用户取消了文件夹选择，中止任务。")
                self.gui.set_button_state(False)
                self.gui.update_status("任务已取消", stop_progress=True)
                return
                
            self.gui.log(f"已选择材料文件夹: {materials_dir}")

            # 1. 初始化浏览器
            self.init_browser()
            
            # 2. 页面状态确认流转
            self.gui.log("开始进行页面图像 OCR 状态扫描...")
            is_ready = self.page_judger.process_flow(require_login_callback=self.require_login)
            
            if not is_ready:
                self.gui.log("未能进入系统页面，请检查网络或重试。")
                return
                
            self.gui.update_status("执行自动登记申请流程...")
            
            # 3. 解析材料
            try:
                txt_path, code_pdf_path, doc_pdf_path = discover_material_files(materials_dir)
                parsed_data = parse_software_info(txt_path)
                self.gui.log(f"成功解析信息: {parsed_data.get('software_name', '')} {parsed_data.get('version', '')}")
            except Exception as e:
                self.gui.log(f"解析材料失败：{e}")
                self.gui.update_status("材料解析失败退回", stop_progress=True)
                return
            
            # 4. 使用 Playwright 执行 R11 登记表单自动化
            from navigator_r11 import execute_r11_registration
            success = execute_r11_registration(parsed_data, code_pdf_path, doc_pdf_path, logger=self.gui.log)
            
            if success:
                self.gui.log("本次自动化登记提交任务成功！请继续后续操作...")
                self.gui.update_status("已进入发证表单", stop_progress=True)
            else:
                self.gui.log("R11登记入口进入失败。")
                self.gui.update_status("自检失败退回", stop_progress=True)
            
        except Exception as e:
            self.gui.log(f"执行异常发生: {e}")
            self.gui.update_status("自检失败退回", stop_progress=True)
        finally:
            self.gui.set_button_state(False)

    # ---------- 模式 3：自动补正流程 ----------
    def run_amend_flow(self, skip_login=False):
        try:
            self.gui.log("等待用户选择对应的软著材料文件夹...")
            materials_dir = filedialog.askdirectory(title="请选择进行补正的软著材料文件夹")
            if not materials_dir:
                self.gui.log("用户取消了文件夹选择，中止任务。")
                self.gui.set_button_state(False)
                self.gui.update_status("任务已取消", stop_progress=True)
                return
                
            software_name = os.path.basename(materials_dir)
            self.gui.log(f"已选择补正目标: {materials_dir}")
            self.gui.log(f"提取的目标软件名称: {software_name}")

            self.init_browser()
            
            if not skip_login:
                self.gui.log("正在登录系统...")
                is_ready = self.page_judger.process_flow(require_login_callback=self.require_login)
                if not is_ready:
                    self.gui.log("未能进入系统页面，请检查网络或重试。")
                    return
            else:
                self.gui.log("跳过登录验证阶段，直接接管浏览器执行后续操作...")
                
            self.gui.update_status("执行自动补正流程...")
            
            applicant_type = self.gui.get_applicant_type()
            
            from navigator_amend import execute_amend_flow
            success = execute_amend_flow(
                software_name, 
                applicant_type, 
                wait_callback=self.gui.wait_for_continue,
                captcha_callback=self.gui.wait_for_captcha,
                page_judger=self.page_judger,
                logger=self.gui.log
            )
            
            if success:
                self.gui.log("本次补正任务成功到达最终确认步！")
                self.gui.update_status("自检空闲中 (任务完成)", stop_progress=True)
            else:
                self.gui.log("自动补正流程失败。")
                self.gui.update_status("自检失败退回", stop_progress=True)
            
        except Exception as e:
            self.gui.log(f"执行异常发生: {e}")
            self.gui.update_status("自检失败退回", stop_progress=True)
        finally:
            self.gui.set_button_state(False)

    def run_amend_flow_resume(self):
        """直接跳过登录验证流程的方法入口"""
        self.run_amend_flow(skip_login=True)


def main():
    import ttkbootstrap as ttkb
    
    root = ttkb.Window(themename="superhero")
    
    app = AppCore(None)
    
    gui = MainGUI(root, 
                  monitor_callback=app.run_monitor_flow, 
                  upload_callback=app.run_upload_flow,
                  amend_callback=app.run_amend_flow,
                  amend_resume_callback=app.run_amend_flow_resume)
    app.gui = gui
    
    root.mainloop()

if __name__ == "__main__":
    main()
