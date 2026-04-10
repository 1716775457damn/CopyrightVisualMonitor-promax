"""
页面逻辑调度器 (OpenCV + PyTesseract + PyAutoGUI 纯视觉版本)
通过全屏截图、OCR识别文本坐标来实现页面导航，并加入自动输入账号密码逻辑。
"""
import mss
import cv2
import numpy as np
import time
import pyautogui
import os
import pytesseract
import ctypes
import platform

if platform.system() == "Windows":
    try:
        # 修复高分屏下绝对坐标系与mss截图物理坐标系不匹配的问题，这是之前位移误差过大的根本原因
        ctypes.windll.user32.SetProcessDPIAware()  
    except Exception:
        pass

# 显式配置 tesseract.exe 路径，避免环境变量未生效的问题
import sys

# 【务实平替版新增】初始化 Airtest 网易视觉引擎内核
try:
    from airtest.core.api import auto_setup, connect_device, exists, touch, Template
    auto_setup(__file__)
    # 强制劫持全量 Windows 桌面绘图层
    connect_device("Windows:///")
except ImportError:
    print("[ERROR] Airtest 未正确安装，请检查环境！")

# 获取程序运行的根目录 (兼容源码运行和打包后的 exe 运行)
if getattr(sys, 'frozen', False):
    # 打包后的系统路径 (PyInstaller 运行时路径)
    _BASE_DIR = sys._MEIPASS
    # 优先搜索 exe 同级目录下的 tesseract
    _EXE_DIR = os.path.dirname(sys.executable)
    _TESS_EXE_POSSIBLE_PATHS = [
        os.path.join(_EXE_DIR, 'Tesseract-OCR', 'tesseract.exe'),
        os.path.join(_EXE_DIR, 'tesseract.exe'),
        r'C:\Tesseract-OCR\tesseract.exe'
    ]
else:
    # 源码运行模式
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    _TESS_EXE_POSSIBLE_PATHS = [
        r'C:\Tesseract-OCR\tesseract.exe'
    ]

# 自动寻找存在的 tesseract.exe
pytesseract.pytesseract.tesseract_cmd = next((p for p in _TESS_EXE_POSSIBLE_PATHS if os.path.exists(p)), _TESS_EXE_POSSIBLE_PATHS[-1])

# 显式配置 tessdata 路径，避免语言包缺失或默认路径找不到
_TESSDATA_PATH = os.path.join(_BASE_DIR, 'tessdata')
os.environ['TESSDATA_PREFIX'] = _TESSDATA_PATH
def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1] # 截取主显示器
        img = np.array(sct.grab(monitor))
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR) # OpenCV标准的BGR格式

def extract_ocr_data(img, lang='chi_sim', binarize=False):
    """一次性读取全屏图，生成带坐标的字符块列表，构建并返回一套 OCR Data 对象。"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    scale = 1.0
    if binarize:
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        _, gray = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    data = pytesseract.image_to_data(gray, lang=lang, config='--psm 11', output_type=pytesseract.Output.DICT)
    
    all_texts = []
    valid_boxes = []
    for i in range(len(data['text'])):
        text = str(data['text'][i]).replace(' ', '').strip()
        if text:
            all_texts.append(text)
            for char in text:
                valid_boxes.append({
                    'char': char,
                    'x': int(data['left'][i] / scale),
                    'y': int(data['top'][i] / scale),
                    'w': int(data['width'][i] / scale),
                    'h': int(data['height'][i] / scale)
                })
            
    full_ocr_str = "".join(b['char'] for b in valid_boxes)
    
    return {
        'valid_boxes': valid_boxes,
        'full_ocr_str': full_ocr_str,
        'all_texts': all_texts
    }


def find_target_in_ocr(ocr_data, target_text, fuzzy=False):
    """在提取好的 OCR 缓存数据中寻找目标文字"""
    valid_boxes = ocr_data['valid_boxes']
    full_ocr_str = ocr_data['full_ocr_str']
    all_texts = ocr_data['all_texts']
    
    target_text = target_text.replace(" ", "")
    idx = -1
    
    if fuzzy and len(target_text) >= 3:
        import difflib
        best_ratio = 0
        best_idx = -1
        # 滑动窗口查找最相似的部分
        for i in range(len(full_ocr_str) - len(target_text) + 1):
            window = full_ocr_str[i:i+len(target_text)]
            ratio = difflib.SequenceMatcher(None, target_text, window).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
        if best_ratio >= 0.8:  # 允许大约错1个字
            idx = best_idx
    else:
        idx = full_ocr_str.find(target_text)
        
    if idx != -1:
        match_boxes = valid_boxes[idx:idx+len(target_text)]
        min_x = min(b['x'] for b in match_boxes)
        min_y = min(b['y'] for b in match_boxes)
        max_x = max(b['x'] + b['w'] for b in match_boxes)
        max_y = max(b['y'] + b['h'] for b in match_boxes)
        
        cx = min_x + (max_x - min_x) // 2
        cy = min_y + (max_y - min_y) // 2
        return (cx, cy), (min_x, min_y, max_x - min_x, max_y - min_y), all_texts

    return None, None, all_texts

def find_all_targets_in_ocr(ocr_data, target_text):
    """返回 OCR 结果中所有匹配 target_text 的目标中心坐标列表"""
    valid_boxes = ocr_data['valid_boxes']
    full_ocr_str = ocr_data['full_ocr_str']
    target_text = target_text.replace(" ", "")
    results = []
    start = 0
    while True:
        idx = full_ocr_str.find(target_text, start)
        if idx == -1:
            break
        match_boxes = valid_boxes[idx:idx+len(target_text)]
        min_x = min(b['x'] for b in match_boxes)
        min_y = min(b['y'] for b in match_boxes)
        max_x = max(b['x'] + b['w'] for b in match_boxes)
        max_y = max(b['y'] + b['h'] for b in match_boxes)
        cx = min_x + (max_x - min_x) // 2
        cy = min_y + (max_y - min_y) // 2
        results.append((cx, cy))
        start = idx + 1
    return results


def find_text_on_screen(img, target_text, lang='chi_sim', binarize=False, fuzzy=False):
    """向下兼容的包裹函数，支持外部直接传入截图并检索"""
    ocr_data = extract_ocr_data(img, lang=lang, binarize=binarize)
    return find_target_in_ocr(ocr_data, target_text, fuzzy=fuzzy)

class PageJudger:
    def __init__(self, logger_callback=print, account="", password=""):
        self.log = logger_callback
        self.account = account
        self.password = password

    def interruptible_servo_move(self, target_cx, target_cy, click=True):
        """
        持续纠正鼠标位置，渐渐逼近目标坐标（基于绝对坐标系）。
        如果期间检测到用户人为移动了鼠标(发生位置偏移)，则抛出中断信号返回 False。
        """
        self.log(f"启动辅助随动，引导鼠标至 ({target_cx}, {target_cy})...")
        last_mx, last_my = pyautogui.position()
        
        for _ in range(50):
            mx, my = pyautogui.position()
            
            # 检测人为干预 (欧氏距离>15视为用户外部介入)
            dist_user = ((mx - last_mx)**2 + (my - last_my)**2)**0.5
            if dist_user > 15:
                self.log("【中断】检测到防抖阈值以上的外部动作，系统中止接管交还给您！")
                return False
                
            dx = target_cx - mx
            dy = target_cy - my
            dist_target = (dx**2 + dy**2)**0.5
            
            if dist_target <= 5:
                # 已经足够靠近，执行到达点击
                if click: 
                    pyautogui.click()
                time.sleep(0.1)
                return True
                
            # 计算步长（比例控制系统，逐渐逼近减速防止冲过头）
            move_x = int(dx * 0.35)
            move_y = int(dy * 0.35)
            if move_x == 0 and dx != 0: move_x = 1 if dx > 0 else -1
            if move_y == 0 and dy != 0: move_y = 1 if dy > 0 else -1
                
            pyautogui.move(move_x, move_y, duration=0.01)
            last_mx, last_my = pyautogui.position()
            
        return False

    def process_flow(self, require_login_callback):
        self.log("启动纯正 Airtest 视觉监控引擎...")
        for attempt in range(4):
            time.sleep(2.5) # 渲染缓冲时间
            
            # 状态1：如果在系统内（判断是否滑块已经通过并成功登录！）
            try:
                # 方案 A：工业级 Airtest 定位（如果您截图了 button/quanbu.png）
                if os.path.exists("button/quanbu.png") and exists(Template(r"button/quanbu.png", threshold=0.7)):
                    self.log("✅ [Airtest] 识别到后台专属元素 [全部] 标签，判定为：已核心系统。")
                    return True
            except Exception as e:
                pass
                
            try:
                # 方案 B：传统低准确率 OCR 备胎
                img = capture_screen()
                ocr_data = extract_ocr_data(img, lang='chi_sim')
                center, _, _ = find_target_in_ocr(ocr_data, "全部")
                if center:
                    soft_center, _, _ = find_target_in_ocr(ocr_data, "软件登记")
                    if soft_center:
                        self.log("✅ [OCR识别] 模糊识别到控制台字样，判定为：已双重进入核心页。")
                        return True
            except Exception as e:
                self.log(f"后台检测出现轻微异常: {e}")

            # 状态2：在首页但未进入系统（头部登录按钮）
            try:
                top_login_center, _, _ = find_target_in_ocr(ocr_data, "登录")
                if top_login_center and top_login_center[1] < 150:
                    self.log("在首页且未登录，点击头部登录按钮...")
                    self.interruptible_servo_move(top_login_center[0], top_login_center[1])
                    time.sleep(2)
                    continue
            except:
                pass

            # 状态4：原拓扑视觉抽取 -> 现已升级为 Airtest 工业级特征制导
            try:
                # 利用 Airtest 极度鲁棒的特征匹配无视灰度和分辨率
                is_login_page = False
                try:
                    if exists(Template(r"button/zhanghao.png", threshold=0.7)):
                        is_login_page = True
                except:
                    pass

                if is_login_page:
                    self.log("【Airtest 视觉引擎】成功解构面积极度恶劣的[账号输入框]轮廓！准备暴力注入...")
                    
                    touch(Template(r"button/zhanghao.png", threshold=0.7))
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    pyautogui.press('backspace')
                    pyautogui.typewrite(self.account, interval=0.03)
                    time.sleep(0.3)
                    
                    self.log("【Airtest 视觉引擎】锁定[密码输入框]轮廓...")
                    touch(Template(r"button/mima.png", threshold=0.7))
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    pyautogui.press('backspace')
                    pyautogui.typewrite(self.password, interval=0.03)
                    time.sleep(0.3)
                    
                    self.log("【Airtest 视觉引擎】精准制导[登录按钮]！发射！")
                    touch(Template(r"button/denglu.png", threshold=0.7))
                    time.sleep(2.5)
                    
                    if hasattr(self, 'solve_slider_captcha') and self.solve_slider_captcha():
                        self.log("【联动模块】智能滑块验证码突围成功，登录已直达，强制向主放行...")
                        time.sleep(3)
                        return True # 直接跨过验证，直接宣告胜利！

                    self.log("主登录动作发射完毕，暂时交回鼠标权！如果有残留验证码请手动推一下～")
                    require_login_callback()
                    return True # 人工确认后也直接宣告胜利！
            except Exception as e:
                self.log(f"【降维打击异常】Airtest 执行流被干扰: {e}")
            
            # 由于可能处于任何未知页或读取错误，等待下一次循环重试
            self.log(f"第 {attempt + 1} 次制导尝试似乎未遇上熟知界面，准备重试...")

        self.log("多次重试仍未能定位到有效页面，制导引擎挂起。")
        return False

    def solve_slider_captcha(self):
        """
        自动检测屏幕上的滑块验证码并通过 OpenCV 计算缺口距离进行拟人滑动，
        纯正支持 Airtest 锚点动态分辨率适应 (1080p, 4K 通杀)
        """
        self.log("正在扫描屏幕，等待滑动验证码加载...")
        time.sleep(2) # 等待动画
        
        # 增加总尝试轮数到 10 轮
        for captcha_attempt in range(10):
            self.log(f"✅ 第 {captcha_attempt + 1} 次弹性捕获滑块验证码特征...")
            
            try:
                # [核心改造] 放弃 OCR 搜字，转为使用 Airtest 获取绝对锚点
                pos_title = exists(Template(r"button/captcha_title.png", threshold=0.7))
                pos_btn = exists(Template(r"button/slider_btn.png", threshold=0.7))
                
                if (not pos_title) or (not pos_btn):
                    if captcha_attempt > 0:
                        self.log("屏幕上的验证码核心组件已消失，判定为验证码被消灭！")
                        # --- 新增的特殊流程后续点击 ---
                        try:
                            # 预判可能会弹出的“跳过”按钮（比如防沉迷、绑定手机或者纯系提示弹窗）
                            if exists(Template(r"button/tiaoguo.png", threshold=0.7)):
                                self.log(">> 捕捉到附属弹窗，点按 [tiaoguo/跳过] 按钮！")
                                touch(Template(r"button/tiaoguo.png", threshold=0.7))
                                time.sleep(1)
                        except Exception as e:
                            pass
                            
                        return True
                    else:
                        self.log("尚未全量检测到[验证码标题]与[底层拖动滑块]，如果验证码没弹出来请忽略，继续等待加载...")
                        time.sleep(2)
                        continue
            except Exception as e:
                self.log(f"Airtest 锚点探测异常，防抱死处理: {e}")
                time.sleep(2)
                continue
            
            # 【核心弹性算法】基于头尾坐标动态开辟搜索空间！完全摆脱传统分辨率 340*212 的死定宽高
            y_t = pos_title[1]
            y_b = pos_btn[1]
            x_b = pos_btn[0]
            
            img = capture_screen()
            h, w = img.shape[:2]
            
            # 拼图区域垂直方向一定在标题和按钮这两者之间，各向内收紧一点点像素剔除外框
            img_top = max(0, int(y_t + 20))
            img_bottom = min(h, int(y_b - 20))
            
            # 拼图水平距离大概是从滑块按钮中心点稍左侧，向右延伸至适当长度 (大约1.6倍高宽比或固定400)
            img_left = max(0, int(x_b - 30))
            elastic_width = max(380, int(abs(y_b - y_t) * 1.5))
            img_right = min(w, int(img_left + elastic_width))
            
            captcha_img = img[img_top:img_bottom, img_left:img_right]
            
            # 如果截成了负数或极小图像说明获取极其异常
            if captcha_img.shape[0] < 50 or captcha_img.shape[1] < 50:
                self.log("动态框选失败，高度/宽度异常，等待重试...")
                time.sleep(2)
                continue
                
            gray = cv2.cvtColor(captcha_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            ch, cw = edges.shape
            
            # --- 【优化】动态抓取拼图轮廓作为匹配模版 ---
            # 提取左侧最多80像素（或者大概四分之一宽）的区域寻找拼图的闭合轮廓
            search_bound = min(cw, max(80, int(cw * 0.2)))
            edges_left = edges[:, :search_bound]
            contours, _ = cv2.findContours(edges_left, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            slider_template = edges[:, :search_bound] # 兜底模版
            slider_x = 0
            slider_w = search_bound
            y_start = 0
            y_end = ch
            
            if contours:
                valid_contours = [c for c in contours if cv2.contourArea(c) > max(40, ch * 0.15)]
                if valid_contours:
                    # 找到最大面积的闭合轮廓作为拼图块
                    c = max(valid_contours, key=cv2.contourArea)
                    x, y, bw, bh = cv2.boundingRect(c)
                    pad = 3
                    y_start = max(0, y - pad)
                    y_end = min(ch, y + bh + pad)
                    x_start = max(0, x - pad)
                    x_end = min(search_bound, x + bw + pad)
                    
                    slider_template = edges[y_start:y_end, x_start:x_end]
                    slider_x = x_start
                    slider_w = x_end - x_start
            
            # 从拼图块右侧的其余部分中寻找坑位
            search_area_x_start = slider_x + slider_w
            # 限制在相同高度条带内寻找，极大地排除了其它位置的垂直噪点干扰
            search_area = edges[y_start:y_end, search_area_x_start:]
            
            if search_area.shape[1] < slider_template.shape[1]:
                self.log("截区空间不足以构成匹配，忽略本次")
                time.sleep(1)
                continue
            
            # 纯粹的结构化匹配，无视背景分数噪音
            res = cv2.matchTemplate(search_area, slider_template, cv2.TM_CCOEFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            try:
                cv2.imwrite(f"debug_captcha_edges_{captcha_attempt}.png", edges)
            except:
                pass
            
            # 滑动距离 = 匹配结果X偏移 + 搜索区起始X - 原拼图所在X
            target_x_offset = max_loc[0] + search_area_x_start - slider_x
            self.log(f"🎯 OpenCV 弹性引擎计算缺口距离: {target_x_offset} 像素。")
            
            # 往往由于拼图块自身带有外发光/透明边框，或者网页 CSS 缩放等原因
            # [自适应策略]：如果是第一轮失败，后续尝试微调偏移量
            CALIBRATION_OFFSET = 12 
            if captcha_attempt > 3:
                 CALIBRATION_OFFSET = 10 # 稍微减小，防止由于惯性冲过头
            elif captcha_attempt > 6:
                 CALIBRATION_OFFSET = 15 # 稍微加大
                 
            target_x_offset += CALIBRATION_OFFSET
            self.log(f"🔧 [精度微调] 为了防止滑动不足，增加边框偏移量 {CALIBRATION_OFFSET}，最终物理滑动: {target_x_offset} 像素。")
            
            # 以 Airtest 给出的滑块准心作为起点
            start_x = int(pos_btn[0])
            start_y = int(pos_btn[1])
            
            self.log(f"开始拟人化拖动滑块，起步坐标: ({start_x}, {start_y})...")
            # 移动到滑块
            pyautogui.moveTo(start_x, start_y, duration=0.5, tween=pyautogui.easeInOutQuad)
            pyautogui.mouseDown()
            
            # 分段拟人拖动
            import random
            current_x = start_x
            remaining_dist = target_x_offset
            
            # 起步：快速滑动 60%
            first_step = int(remaining_dist * 0.6)
            current_x += first_step
            pyautogui.moveTo(current_x, start_y + random.randint(-2, 2), duration=random.uniform(0.2, 0.4), tween=pyautogui.easeOutQuad)
            
            # 中段：平缓滑动 30%
            remaining_dist -= first_step
            second_step = int(remaining_dist * 0.8)
            current_x += second_step
            pyautogui.moveTo(current_x, start_y + random.randint(-1, 1), duration=random.uniform(0.3, 0.6), tween=pyautogui.easeInOutSine)
            
            # 末段：微调对齐剩余像素
            remaining_dist -= second_step
            current_x += remaining_dist
            pyautogui.moveTo(current_x, start_y, duration=random.uniform(0.4, 0.8), tween=pyautogui.easeOutBounce)
            
            # 保持一下再松开
            time.sleep(random.uniform(0.3, 0.5))
            pyautogui.mouseUp()
            
            self.log("拖动完成！等待判断结果...")
            time.sleep(3) # 留时间刷新等待验证码重置或成功跳转
        
        self.log("滑动验证码连续多次均未能成功，可能被风控阻拦，请手动滑一下！")
        return False

    def read_core_data(self):
        """关键节点：在【全部】标签页，翻页提取所有软件记录并去重，根据记录状态分类统计数目"""
        self.log("开始在【全部】标签页提取所有连续页的软件登记信息...")
        time.sleep(2)
        
        tab_names = ["待受理", "待审查", "待补正", "待发放", "已发放"]
        summary = {k: 0 for k in tab_names}
        all_parsed_records = []
        
        img = capture_screen()
        
        self.log("点击标签页：全部...")
        tab_center, _, _ = find_text_on_screen(img, "全部", lang='chi_sim')
        if tab_center:
            self.interruptible_servo_move(tab_center[0], tab_center[1], click=True)
            time.sleep(1.5)  # 缩短等待时间提速
            img = capture_screen()
        else:
            self.log("  未找到标签 [全部]，尝试直接读取当前页面。")
            
        current_page = 1
        last_page_records = []
        # ======================== 终极提取与去重主循环 ========================
        # 定义一个变量保存上一页提取出的原始字符串，用于绝对防重
        last_page_raw_text = ""
        
        while True:
            self.log(f"--- 正在提取第 {current_page} 页 ---")
            records, current_raw_text = self._extract_records_from_screen(img, f"全部_页{current_page}", return_raw=True)
            self.log(f"  第 {current_page} 页提取到 {len(records)} 条记录")
            
            # 【终极防死锁机制】：直接对比剪贴板原始文本
            # 如果当前页复制出来的长文本，连一个标点符号都没变，绝对说明页面完全没动！
            if current_page > 1 and current_raw_text and current_raw_text == last_page_raw_text:
                self.log("【终极查重】当前页面的提取文本与上一页一字不差，确认已到达最后一页，结束翻页。")
                break
                
            last_page_raw_text = current_raw_text
            
            # 存入本页提取到的有效记录
            if records:
                all_parsed_records.extend(records)
                    
            # 安全防死锁机制 2：全局重复判定（最强托底）
            # 如果本页提取到的所有记录，在之前都已经提取过了，说明一直停在老页面没动
            if current_page > 1 and records:
                existing_serials = set(r.get('serial') for r in all_parsed_records if r.get('serial'))
                current_serials = set(r.get('serial') for r in records if r.get('serial'))
                # 如果当前页的所有非空流水号，都是以前见过的
                if current_serials and current_serials.issubset(existing_serials):
                    self.log("【全局查重】检测到本页所有数据均已提取过，判定翻页无效或到达末尾，结束循环。")
                    break
            
            next_page_num = str(current_page + 1)
            self.log(f"尝试按 OCR 强化提取寻找第 {next_page_num} 页或下一页按钮...")
            
            # 滚动到底部以显示分页器（增加滚动次数，确保在任何分辨率和缩放比例下都能彻底触底）
            pyautogui.click(pyautogui.size()[0]//2, pyautogui.size()[1]//2)  # 确保焦点
            for _ in range(4):
                pyautogui.press('pagedown')
                time.sleep(0.1)
            time.sleep(0.5)  # 缩短滚动底部的总体等待时间
            
            # 截图找下一页的标识（裁剪屏幕：15% 到 95% 之间，防止页面太短导致分页器悬在屏幕中间以上的地方）
            img_bottom = capture_screen()
            h, w = img_bottom.shape[:2]
            crop_y_start = int(h * 0.15)
            crop_y_end = int(h * 0.95)
            img_bottom_cropped = img_bottom[crop_y_start:crop_y_end, :]
            
            # ======================== 终极强化二值化定位方案 ========================
            # 使用二值化强化（能过滤掉周围淡蓝色/浅灰色的背景干扰，让细小的图标现形）
            bottom_ocr_data = extract_ocr_data(img_bottom_cropped, lang='eng+chi_sim', binarize=True)
            
            # 辅助函数：在数据中寻找所有匹配，并返回最下方（y最大）的那一个
            def get_bottom_most_center(ocr_data, target):
                target_stripped = target.replace(' ', '')
                full_str = ocr_data['full_ocr_str']
                boxes = ocr_data['valid_boxes']
                
                best_center = None
                max_y = -1
                
                # 寻找所有出现的子串
                idx = full_str.find(target_stripped)
                while idx != -1:
                    match_boxes = boxes[idx:idx+len(target_stripped)]
                    min_x = min(b['x'] for b in match_boxes)
                    min_y = min(b['y'] for b in match_boxes)
                    max_x = max(b['x'] + b['w'] for b in match_boxes)
                    max_y_box = max(b['y'] + b['h'] for b in match_boxes)
                    
                    if min_y > max_y:
                        max_y = min_y
                        cx = min_x + (max_x - min_x) // 2
                        cy = min_y + (max_y_box - min_y) // 2
                        best_center = (cx, cy)
                        
                    idx = full_str.find(target_stripped, idx + 1)
                    
                return best_center
            
            next_btn_center = get_bottom_most_center(bottom_ocr_data, ">")
            
            if next_btn_center:
                self.log("精准锁定 '>' 下一页图标锚定翻页区域...")
            else:
                # 降级：如果识别不出箭头，直接找数字页码（如 '2'）
                next_btn_center = get_bottom_most_center(bottom_ocr_data, next_page_num)
                if next_btn_center:
                    self.log(f"精准锁定页码 '{next_page_num}' 锚定翻页区域...")
            
            if next_btn_center:
                # 坐标还原到全屏系
                real_x = next_btn_center[0]
                real_y = next_btn_center[1] + crop_y_start
                
                self.log(f"在屏幕下半部找到翻页触发区 '>'，准备点击...")
                success = self.interruptible_servo_move(real_x, real_y, click=True)
                
                # ★ 增加人工接管暂停功能：如果人为移动了鼠标，中断原操作并等待用户手动确认
                if not success:
                    import win32api
                    self.log("【动作中断】工作流已暂停运行！")
                    self.log("👉 如果识别的按钮不准，请您自行将鼠标移动到真实的“下一页”并单击一次左键。程序检测到点击后将自动恢复并读取下一页...")
                    
                    # 循环死等，直到用户单击左键
                    while True:
                        if win32api.GetAsyncKeyState(0x01) < 0:
                            self.log("【恢复】已接收到您的点击确认，工作流继续提取...")
                            # 防止重复触发，等待鼠标松开
                            while win32api.GetAsyncKeyState(0x01) < 0:
                                time.sleep(0.05)
                            break
                        time.sleep(0.1)
                
                time.sleep(1.5)  # 缩短新页面加载等待时间
                img = capture_screen()
                current_page += 1
            else:
                self.log("未在屏幕底部找到'页'或'共'字，判定为已到达最后一页，结束翻页。")
                break
        
        # 对全部记录进行去重：同一软件名称只保留最新申请日期的一条
        unique_records_dict = {}
        from datetime import datetime
        
        for r in all_parsed_records:
            name = r.get("软件名称")
            if not name:
                continue
                
            date_str = r.get("申请日期", "")
            try:
                # 尝试解析为 datetime 对象以便严谨比较 (格式如 "2025-08-21")
                current_date = datetime.strptime(date_str, "%Y-%m-%d")
            except Exception:
                # 解析失败赋予极小值，作为保底
                current_date = datetime.min
                
            if name not in unique_records_dict:
                unique_records_dict[name] = {"record": r, "date": current_date}
            else:
                # 如果已经存在同名软件，比较申请日期，只保留最新的
                existing_date = unique_records_dict[name]["date"]
                if current_date > existing_date:
                    unique_records_dict[name] = {"record": r, "date": current_date}
                
        final_records = [item["record"] for item in unique_records_dict.values()]
        self.log(f"去重后共获得 {len(final_records)} 个独立软件项目的最新状态。")
        
        # 根据去重后的项目列表，动态计算每个状态对应的项目数量
        for r in final_records:
            st = r.get("状态")
            if st:
                if st in summary:
                    summary[st] += 1
                else:
                    summary[st] = 1  # 记录其他未知状态（如“不予办理”）
            
        return summary, final_records, img

    def _extract_records_from_screen(self, img, tab_filter="全部", return_raw=False):
        """使用 Ctrl+A + Ctrl+C 复制页面所有文字，再从剪贴板解析记录行"""
        import pyperclip
        
        # 先清空剪贴板，填入防并发哨兵标志
        try:
            pyperclip.copy("[COPY_IN_PROGRESS]")
        except Exception:
            pass
        
        # ★ 关键修复：先点击页面正文区域，确保焦点在浏览器内容区而非其他窗口
        # 取屏幕中心偏下的安全位置（避开顶部工具栏和标签栏），然后再操作键盘
        screen_w, screen_h = pyautogui.size()
        safe_x = screen_w // 2
        safe_y = int(screen_h * 0.55)  # 页面内容区中部，避免点到导航元素
        pyautogui.click(safe_x, safe_y)
        time.sleep(0.4)  # 等待焦点切换完成
        
        # Ctrl+Home 滚动到页面顶部，确保全选能读完整页面
        pyautogui.hotkey('ctrl', 'home')
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'a')   # 在浏览器中全选
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'c')   # 复制
        
        # 【强健性架构优化】：取代死等 0.7 秒，使用剪贴板轮询锁保障庞大表格数据的完整提取
        raw_text = ""
        wait_loops = 20 # 最长等待两秒
        try:
            while wait_loops > 0:
                raw_text = pyperclip.paste()
                if raw_text != "[COPY_IN_PROGRESS]":
                    break
                time.sleep(0.1)
                wait_loops -= 1
        except Exception as e:
            self.log(f"  剪贴板读取异常: {e}")
            
        # 取消选中，恢复正常
        pyautogui.press('escape')
        time.sleep(0.1)
        
        # 保存调试日志，便于排查剪贴板内容是否正确
        try:
            safe_tab = tab_filter.replace('/', '_')
            debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f'debug_clip_{safe_tab}.txt')
            with open(debug_path, 'w', encoding='utf-8') as df:
                df.write(raw_text)
        except Exception:
            pass
        
        if not raw_text or len(raw_text) < 50:
            self.log(f"  剪贴板内容异常（长度={len(raw_text)}），跳过本标签解析")
            if return_raw:
                return [], ""
            return []
        
        self.log(f"  剪贴板读取成功，共 {len(raw_text)} 字符，开始解析...")
        records = self._parse_clipboard_text(raw_text, tab_filter)
        if return_raw:
            return records, raw_text
        return records
    
    def _parse_clipboard_text(self, raw_text: str, tab_filter: str) -> list:
        """从剪贴板复制的页面文字中解析软件记录"""
        import re
        
        records = []
        lines = [l.strip() for l in raw_text.replace('\r', '').split('\n') if l.strip()]
        
        STATUS_KEYWORDS = ["待受理", "待审查", "待补正", "待发放", "已发放", "不予办理", "撤回", "已通过"]
        SKIP_KEYWORDS = ["流水号", "登记详情", "申请确认签页", "状态", "操作", "高级筛选", "查询",
                         "软件登记", "作品登记", "我的登记", "我的查询", "我的历史", "历史记录",
                         "历史查询", "软件查询", "作品查询", "撤回申请", "查看详情"]
        
        current_serial = None
        current_name = None
        current_date = None
        current_status = None
        
        for line in lines:
            # 跳过导航菜单项
            if any(k == line or k in line for k in SKIP_KEYWORDS):
                if len(line) < 15:  # 短导航行，跳过
                    continue
            
            # 识别流水号 (如 2025R11L3667971)，使用允许内部空格的正则，并且不用 replace(' ', '') 把日期黏在一起
            serial_m = re.search(r'(20\d{2}\s*[A-Z]\s*\d{2}\s*[A-Z]\s*\d{6,10})(?!\d)', line)
            if serial_m:
                # 保存上一条（如果齐全）
                if current_serial and current_name and current_status:
                    records.append({
                        "流水号": current_serial,
                        "软件名称": current_name,
                        "申请日期": current_date or "",
                        "状态": current_status,
                        "标签页": tab_filter
                    })
                # 开始新的记录
                current_serial = serial_m.group(1).replace(' ', '')
                current_name = None
                current_status = None
                current_date = None
                # 同行可能有日期
                date_m = re.search(r'(\d{4}-\d{2}-\d{2})', line)
                if date_m:
                    current_date = date_m.group(1)
                continue
            
            # 识别日期行
            date_m = re.search(r'^(\d{4}-\d{2}-\d{2})$', line)
            if date_m and current_serial:
                current_date = date_m.group(1)
                continue
            
            # 识别状态（识别到后立即跳过，避免同行被误当作软件名称）
            status_found = False
            for status in STATUS_KEYWORDS:
                if status in line:
                    current_status = status
                    status_found = True
                    break
            if status_found:
                continue
            
            # 识别软件名称（中文为主，长度适中，非导航噪音，上限50字防止抓到长句子）
            if (current_serial and not current_name
                    and 4 <= len(line) <= 50
                    and any('\u4e00' <= c <= '\u9fff' for c in line)
                    and not any(k in line for k in STATUS_KEYWORDS + SKIP_KEYWORDS)
                    and not re.match(r'^\d', line)):
                current_name = line
        
        # 保存最后一条
        if current_serial and current_name and current_status:
            records.append({
                "流水号": current_serial,
                "软件名称": current_name,
                "申请日期": current_date or "",
                "状态": current_status,
                "标签页": tab_filter
            })
            
        return records


