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

def find_text_on_screen(img, target_text, lang='chi_sim', binarize=False):
    """使用 Tesseract OCR 查找指定文本在屏幕上的坐标中心"""
    # 预处理：灰度化以提高识别率
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    scale = 1.0
    if binarize:
        # 针对浅色/浅蓝色分页器文字，放大两倍并进行反相二值化提取，极大提高识别率
        scale = 2.0
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        _, gray = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY_INV)
    
    # 获取详细的检测数据，包括坐标
    # --psm 11 适合寻找稀疏零散的文本段落
    data = pytesseract.image_to_data(gray, lang=lang, config='--psm 11', output_type=pytesseract.Output.DICT)
    
    all_texts = []
    # 重组所有的text并记录每个字符的包围盒，保证字符串索引和坐标数组索引绝对一对一映射
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
    
    # 用滑动窗口的形式在合成的字符串里寻找 target_text
    idx = full_ocr_str.find(target_text)
    if idx != -1:
        # 找到了，计算联合Bounding Box
        # 提取相关字符的box
        match_boxes = valid_boxes[idx:idx+len(target_text)]
        min_x = min(b['x'] for b in match_boxes)
        min_y = min(b['y'] for b in match_boxes)
        max_x = max(b['x'] + b['w'] for b in match_boxes)
        max_y = max(b['y'] + b['h'] for b in match_boxes)
        
        cx = min_x + (max_x - min_x) // 2
        cy = min_y + (max_y - min_y) // 2
        return (cx, cy), (min_x, min_y, max_x - min_x, max_y - min_y), all_texts

    return None, None, all_texts

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
        self.log("分析页面当前状态...")
        for attempt in range(4):
            time.sleep(2.5) # 渲染缓冲时间
            img = capture_screen()
            
            # 状态1：核心提取页
            center, _, _ = find_text_on_screen(img, "全部", lang='chi_sim') # 去除eng，增强纯中文识别
            if center:
                # 为了保险，同时找 "软件登记"
                soft_center, _, _ = find_text_on_screen(img, "软件登记", lang='chi_sim')
                if soft_center:
                    self.log("成功定位到核心软件登记列表页。")
                    return True

            # 状态2：在首页但未进入系统
            top_login_center, _, _ = find_text_on_screen(img, "登录", lang='chi_sim')
            # 尝试区分这到底是顶部小登录按钮，还是登录大面板。通常右上角的按钮 y 坐标较小(< 150)
            if top_login_center and top_login_center[1] < 150:
                self.log("在首页且未登录，点击头部登录按钮...")
                self.interruptible_servo_move(top_login_center[0], top_login_center[1])
                time.sleep(2)
                continue
                
            # 状态3：在系统内但未点击软件登记
            soft_nav_center, _, _ = find_text_on_screen(img, "软件登记", lang='chi_sim')
            if soft_nav_center:
                self.log("登录成功，点击左侧【软件登记】菜单...")
                self.interruptible_servo_move(soft_nav_center[0], soft_nav_center[1])
                continue
                
            # 状态4：未登录，并位于登录面板页 (需要自动输入账号密码)
            login_panel_center, _, all_texts = find_text_on_screen(img, "账号登录", lang='chi_sim')
            pwd_login_center, _, _ = find_text_on_screen(img, "密码登录", lang='chi_sim')
            
            # 增强宽松匹配：只要屏幕上有 登录 或者 密码 的字眼且不在顶部，也认为是登录面板
            if login_panel_center or pwd_login_center or (top_login_center and top_login_center[1] >= 150):
                self.log("检测到登录面板，准备先行自动输入账号密码...")
                
                # 寻找输入框提示词定位输入框
                user_hint_center, _, _ = find_text_on_screen(img, "用户名", lang='chi_sim')
                
                if user_hint_center:
                    target_cx = user_hint_center[0]
                    target_cy = user_hint_center[1]
                    
                    # 先将鼠标移动到“请输入用户名”并在那里点击
                    reached = self.interruptible_servo_move(target_cx, target_cy, click=True)
                    if reached:
                        self.log("瞄准账号框，开始输入账号...")
                        pyautogui.typewrite(self.account, interval=0.03)
                        time.sleep(0.3)
                        
                        # 再移动并点击密码框
                        # 搜索“入密码”而不是“密码”，避免匹配到登录类型选择栏的“密码登录”
                        pwd_hint_center, _, _ = find_text_on_screen(img, "入密码", lang='chi_sim')
                        if not pwd_hint_center:
                            pwd_hint_center, _, _ = find_text_on_screen(img, "请密码", lang='chi_sim')
                        if pwd_hint_center:
                            self.log("移动至密码框，准备输入密码...")
                            self.interruptible_servo_move(pwd_hint_center[0], pwd_hint_center[1], click=True)
                            pyautogui.typewrite(self.password, interval=0.03)
                            time.sleep(0.3)
                            
                    # 最后移动到立即登录按钮并点击！
                    login_btn_center, _, _ = find_text_on_screen(img, "即登录", lang='chi_sim')
                    if login_btn_center:
                        self.log("将鼠标移动至【立即登录】并点击...")
                        self.interruptible_servo_move(login_btn_center[0], login_btn_center[1], click=True)
                        time.sleep(2)  # 等待验证码弹出
                        
                        # 【重要优化】检测并尝试自动处理滑块验证码
                        # 此处如果检测到验证码，将尝试最多 5 次自动处理，不再直接弹窗拦截
                        if self.solve_slider_captcha():
                            self.log("滑块验证码处理完毕，等待页面跳转...")
                            time.sleep(3)
                            continue  # 进入下一轮状态判断

                    self.log("账号和密码均已顺畅输入完毕！")
            
            self.log("已暂停视觉控制！此时您可以移动鼠标接管并进行滑动拼图验证...")
            require_login_callback()
            # 等待用户点确定后，由于已登录，下一轮重试将落入状态3
            continue
        else:
            if attempt == 3:
                 self.log("最后一次重试，保存调试截图和OCR日志...")
                 cv2.imwrite("debug_last_screen.png", img)
                 with open("debug_ocr_texts.txt", "w", encoding="utf-8") as f:
                     f.write("\n".join(all_texts))
                 self.log("识别到的文本已保存到 debug_ocr_texts.txt。请查看提取内容是否准确。")

        self.log("多次重试仍未能定位到有效页面。")
        return False

    def solve_slider_captcha(self):
        """
        自动检测屏幕上的滑块验证码并通过 OpenCV 计算缺口距离进行拟人滑动
        """
        self.log("正在扫描屏幕，等待滑动验证码加载...")
        
        bbox = None
        img = None
        all_texts = []
        for wait_i in range(5):
            img = capture_screen()
            
            # 使用更广泛的关键词组合
            # 由于 OCR 偶尔会将“安全验证”识别为“安全验证码”或“完成验证”等，我们尝试多个子串
            for keyword in ["安全验证", "安全测试", "完成验证", "请完成", "完成安全", "验证码"]:
                _, bbox, all_texts = find_text_on_screen(img, keyword, lang='chi_sim')
                if bbox:
                    self.log(f"✅ 发现验证码特征 [{keyword}]！启动几何锁定与 OpenCV 计算引擎...")
                    break
            
            if bbox:
                break
                
            self.log(f"  ...未看到验证码，继续等待加载 ({wait_i+1}/5)")
            time.sleep(2)
            
        if not bbox:
            # 帮助调试：如果没找到，在日志里输出前5个识别到的词，看看 Tesseract 到底看成了什么
            debug_sample = " | ".join(all_texts[:5]) if all_texts else "空"
            self.log(f"当前屏幕未检测到验证码标题特征 (这可能意味着验证码尚未弹出，或已被自动关闭)。提取摘要: {debug_sample}")
            return False
            
        # 增加总尝试轮数到 10 轮 (5次尝试 + 自动重置后的5次尝试)
        for captcha_attempt in range(10):
            self.log(f"✅ 第 {captcha_attempt + 1} 次获取滑块验证码特征...")
            if captcha_attempt > 0:
                img = capture_screen()
                title_hint, bbox, _ = find_text_on_screen(img, "安全验证", lang='chi_sim')
                if not title_hint:
                    title_hint, bbox, _ = find_text_on_screen(img, "请完成", lang='chi_sim')
                
                if not title_hint:
                    self.log("滑块验证码已消失，判定为验证成功！")
                    return True
            
            sx, sy, sw, sh = bbox
            
            # 基于“请完成安全验证”标题的严格几何定位
            # 拼图图片通常定死在标题框正下方约 15 像素处，尺寸绝大多数约为 340x212
            img_top = sy + sh + 15
            img_bottom = img_top + 212
            img_left = sx - 20
            img_right = img_left + 340
            
            # 边界安全保护
            h, w = img.shape[:2]
            img_top, img_bottom = max(0, img_top), min(h, img_bottom)
            img_left, img_right = max(0, img_left), min(w, img_right)
            
            captcha_img = img[img_top:img_bottom, img_left:img_right]
            
            gray = cv2.cvtColor(captcha_img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 100, 200)
            ch, cw = edges.shape
            
            # 假设拼图块在左侧 65 像素内（标准滑块拼图块大小约为 50-60px）
            slider_width_estimate = 65
            slider_template = edges[:, :slider_width_estimate]
            search_area = edges[:, slider_width_estimate:]
            
            # 纯粹的结构化匹配，无视背景分数噪音
            res = cv2.matchTemplate(search_area, slider_template, cv2.TM_CCOEFF)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            
            cv2.imwrite(f"debug_captcha_edges_{captcha_attempt}.png", edges)
            
            target_x_offset = max_loc[0] + slider_width_estimate
            self.log(f"🎯 OpenCV 原生计算缺口距离: {target_x_offset} 像素。")
            
            # 往往由于拼图块自身带有外发光/透明边框，或者网页 CSS 缩放等原因
            # [自适应策略]：如果是第一轮失败，后续尝试微调偏移量
            CALIBRATION_OFFSET = 13 
            if captcha_attempt > 3:
                 CALIBRATION_OFFSET = 11 # 稍微减小，防止由于惯性冲过头
            elif captcha_attempt > 6:
                 CALIBRATION_OFFSET = 15 # 稍微加大
                 
            target_x_offset += CALIBRATION_OFFSET
            self.log(f"🔧 [精度微调] 为了防止滑动不足，增加边框偏移量 {CALIBRATION_OFFSET}，最终物理滑动: {target_x_offset} 像素。")
            
            # 定位实际的滑块按钮，按钮固定在图片左下角的随动轨道最左侧
            # 按钮也是固定大小的圆框或者方框（宽高约40），因此中心点在图片左下边角往右往下各偏移 20-25 像素
            start_x = img_left + 22
            start_y = img_bottom + 22
            
            self.log("开始拟人化拖动滑块...")
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
        
        self.log("滑动验证码连续多次均未能成功，请手动介入！")
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
            
            # 截图找下一页的标识（裁剪屏幕：30% 到 95% 之间，防止页面太短导致分页器悬在屏幕中间以上的地方）
            img_bottom = capture_screen()
            h, w = img_bottom.shape[:2]
            crop_y_start = int(h * 0.30)
            crop_y_end = int(h * 0.95)
            img_bottom_cropped = img_bottom[crop_y_start:crop_y_end, :]
            
            # ======================== 终极强化二值化定位方案 ========================
            # 使用二值化强化（能过滤掉周围淡蓝色/浅灰色的背景干扰，让细小的图标现形）
            next_btn_center, _, _ = find_text_on_screen(img_bottom_cropped, ">", lang='eng+chi_sim', binarize=True)
            
            if next_btn_center:
                self.log("精准锁定 '>' 下一页图标锚定翻页区域...")
            else:
                # 降级：如果识别不出箭头，直接找数字页码（如 '2'）
                next_btn_center, _, _ = find_text_on_screen(img_bottom_cropped, next_page_num, lang='eng+chi_sim', binarize=True)
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
        
        # 先清空剪贴板
        try:
            pyperclip.copy("")
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
        time.sleep(0.7)  # 等待剪贴板写入（页面内容较多时需要更多时间）
        
        raw_text = ""
        try:
            raw_text = pyperclip.paste()
        except Exception as e:
            self.log(f"  剪贴板读取失败: {e}")
            
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


