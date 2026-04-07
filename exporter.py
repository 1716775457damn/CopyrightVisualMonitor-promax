"""
数据导出与通知模块
负责将解析的结果与上一轮历史进行比对，若有变化触发系统通知，同时保存Excel表格及全量截图
"""
import pandas as pd
import json
import os
import cv2
import datetime
from win10toast import ToastNotifier

DESKTOP_PATH = os.path.join(os.path.expanduser("~"), "Desktop")

class Exporter:
    def __init__(self, excel_path=None, last_result_path="result.json"):
        # 默认将 Excel 直接保存到桌面
        if excel_path is None:
            self.excel_path = os.path.join(DESKTOP_PATH, "软著登记状态追踪.xlsx")
        else:
            self.excel_path = excel_path
        self.last_result_path = last_result_path
        self.toaster = ToastNotifier()
        
    def check_changes_and_notify(self, current_data: dict):
        """对比上一次运行结果，检测变化"""
        last_data = {}
        if os.path.exists(self.last_result_path):
            try:
                with open(self.last_result_path, 'r', encoding='utf-8') as f:
                    last_data = json.load(f)
            except Exception:
                pass
                
        changes = []
        for stage, count in current_data.items():
            if stage in ['待受理', '待审查', '待补正', '待发放', '已发放']:
                old_count = last_data.get(stage, 0)
                if count != old_count:
                    diff = count - old_count
                    sign = "新增" if diff > 0 else "减少"
                    changes.append(f"{stage}{sign}{abs(diff)}个")
                    
        change_desc = "、".join(changes) if changes else "无变化"
        current_data["变化说明"] = change_desc
        
        # 覆写最新的json以便下次对比
        with open(self.last_result_path, 'w', encoding='utf-8') as f:
            json.dump(current_data, f, ensure_ascii=False, indent=4)
            
        # 若有实质变化，弹窗通知
        if changes:
            msg = f"版权局审核状态出现变动: {change_desc}\n待受理:{current_data.get('待受理',0)} 待审查:{current_data.get('待审查',0)} 待补正:{current_data.get('待补正',0)}"
            import threading
            threading.Thread(target=self.toaster.show_toast, args=("版权状态更新", msg), kwargs={'duration': 10, 'threaded': True}).start()
            
        return current_data
        
    def save_excel(self, current_data: dict, records: list = None):
        """将包含时间戳的汇总结果+详细记录存入桌面 Excel，两个 Sheet"""
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Sheet1: 状态汇总（追加模式，保留历史）
        summary_row = {
            "读取时间": now_str,
            "待受理": current_data.get("待受理", 0),
            "待审查": current_data.get("待审查", 0),
            "待补正": current_data.get("待补正", 0),
            "待发放": current_data.get("待发放", 0),
            "已发放": current_data.get("已发放", 0),
            "变化说明": current_data.get("变化说明", "无")
        }
        
        df_new_summary = pd.DataFrame([summary_row])
        
        # Sheet2: 本次提取到的详细记录
        if records:
            df_records = pd.DataFrame(records)
            df_records.insert(0, "记录时间", now_str)
        else:
            df_records = pd.DataFrame(columns=["记录时间", "流水号", "软件名称", "申请日期", "状态", "标签页"])
        
        # 如果已有文件，读取并追加汇总数据
        if os.path.exists(self.excel_path):
            try:
                df_old_summary = pd.read_excel(self.excel_path, sheet_name="状态汇总")
                df_summary = pd.concat([df_old_summary, df_new_summary], ignore_index=True)
            except Exception:
                df_summary = df_new_summary
        else:
            df_summary = df_new_summary
            
        # 写入双 Sheet
        with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
            df_summary.to_excel(writer, sheet_name="状态汇总", index=False)
            df_records.to_excel(writer, sheet_name="详细记录", index=False)
        
        return self.excel_path
        
    def save_screenshot(self, img_cv):
        """保存全量证据截图（OpenCV ndarray 或 None）"""
        screenshots_dir = os.path.join(DESKTOP_PATH, "软著截图")
        os.makedirs(screenshots_dir, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(screenshots_dir, f"proof_{now_str}.png")
        if img_cv is not None:
            cv2.imwrite(path, img_cv)
        return path
