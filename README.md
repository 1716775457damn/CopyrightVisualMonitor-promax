# CCNU Copyright Hub (CopyrightVisualMonitor v3.0)

华中师范大学软件著作权申请全流程自动化工作站

基于 **纯视觉 AI (Tesseract OCR) + OpenCV + Playwright** 构建的完全离线、自动化 Edge 浏览器操作工具。
无需任何网络训练数据上传，即开即用，一站式解决软著申请的繁琐流程。

---

## 🚀 项目架构与原理

本项目在 v3.0 版本进行了重大重构，**彻底移除了对 YOLO 等复杂深度学习目标检测模型的依赖**。

- **核心路线：** `纯视觉 OCR + Playwright 流程控制`
- **视觉引擎：** `pytesseract` 进行全屏中英文本坐标定位，`OpenCV` 处理图像二值化与验证码缺口计算。
- **动作执行：** `pyautogui` 实现拟人化鼠标轨迹移动与点击，防御平台风控；`Playwright` 用于深度的自动化表格填写。
- **数据输出：** `pandas` 与 `openpyxl` 负责数据的清洗降噪与比对纠错。

## 📁 目录结构

```text
CCNU_Copyright_Hub/
├── main.py                # 核心程序入口，串联监控与上传模式
├── gui_main.py            # Tkinter 构建的统一控制台界面
├── config_manager.py      # 用户凭据持久化与超参配置加载
├── page_judger.py         # 基于 OCR 的纯视觉页面解析逻辑（滑动验证码处理核心）
├── browser_utils.py       # 本地 Edge 浏览器调用与 Cookie 缓存管理
├── exporter.py            # Excel 报表生成及本地快照记录
├── navigator_r11.py       # (Playwright) 软著 R11 登记表自动上传流
├── navigator_amend.py     # (Playwright) 软著问题自动补正流
├── requirements.txt       # Python 包依赖
├── build_exe.bat          # PyInstaller 一键打包构建脚本
├── models/                # [保留目录] 预留给未来可能扩展的小模型
├── tessdata/              # [必须配置] Tesseract 识别库 (chi_sim, eng, osd)
├── build_assets/          # Pyinstaller `.spec` 构建配置存档
└── tests/                 # 视觉特征与 OpenCV 几何识别测试脚本 
```

---

## 🛠 开发与部署环境搭建

1. **安装依赖**
   ```cmd
   pip install -r requirements.txt
   ```
   *注意：Playwright 需在初次运行前安装浏览器内核 `playwright install chromium`*

2. **准备 Tesseract (必备)**
   - 从 [Tesseract 官方发布页](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装。
   - 提取 `tessdata` 文件夹（必须包含 `chi_sim.traineddata` 和 `eng.traineddata`），放入本项目根目录！
   - **核心坑点**：如果缺少完整的中文字库，或者没放在主目录下，Pyinstaller 打包后的程序 OCR 将陷入假死或闪退！

---

## 🤖 核心功能模块

启动项目：
```cmd
python main.py
```

### 模式一：📊 状态监控流水线

**适用场景：** 每日批量刷新名下所有软著的审核状态，自动提取发放通知，生成 Excel 比对报告。
**特性：**
- **自适应强防抖算法**：避免人工误触导致的坐标系紊乱。
- **拟人化滑块破解**：利用 OpenCV Canny 算子自动寻踪阴影边界，实现 3 段式贝塞尔曲线阻尼拖动验证。
- **增量式 Excel 路由**：新旧状态纵向对比，弹窗高频提示“待补正”或“已发证”等突变词组。

### 模式二：📤 自动上传提交流

**适用场景：** 基于标准的 TXT 模板和 PDF 文件，实现“一键全自动填表登记”。
**特性：**
- **材料自解析**：自动读取业务文件夹下的 `xxx软件信息.txt` 及对应 PDF。
- **Playwright DOM 接管**：绕过视觉抖动，直接对 input 和上传 input 接口注水，10秒内完成两页超级大表单填报。
- **自动截取凭证**：关键锚点步骤自动保留截图至本地留存。

### 模式三：🛠️ 自动补正响应流

**适用场景：** 针对被版权中心要求补正的存量单据进行材料纠错覆盖重传。

---

## ❓ 常见问题 FAQ

**Q1：为何抛弃 YOLO 而转用纯 OCR？**
✅ 国版中心的前端 UI 及徽标颜色改版频率较高。YOLO 必须经历漫长痛苦的重新标注和算力训练才能适应。基于 Tesseract 中文 OCR 的 `page_judger` 能够免疫按钮颜色和方位的改变，只要文字词根存在，就能锁定坐标中点。

**Q2：运行中鼠标乱飘，或者点击老是偏几公分？**
✅ Windows 缩放补偿问题。在 4K 屏幕下，请右键 python.exe 或打包后的程序，勾选“高 DPI 缩放替代”。在代码中我们已经写入了 `ctypes.windll.user32.SetProcessDPIAware()`，正常情况下已自动修正偏差。

**Q3：验证码拼图无法滑动到位？**
✅ 可在 GUI 界面将 **自适应延迟倍率** 调高（向右拉至“稳定”侧），放缓拖动速度；OpenCV 因浏览器字体发光特效有时会导致 15 像素以内的计算偏差，程序会在 4 次失败后自适应拉大边界偏移量。如果连续多次失败，请在弹窗时手动接管并辅助划动这一下。
