# CopyrightVisualMonitor v2.0
中国版权局软件著作权申请状态视觉自检助手

基于纯视觉 AI (YOLO) + 传统 OCR 构建的完全离线、自动化 Edge 浏览器操作工具。
无需任何网络连接，即开即用直接监控软件著作权登记各个阶段的变化情况。

---

## 🚀 项目目录结构建议
```text
CopyrightVisualMonitor/
├── main.py                # 核心程序入口
├── gui_main.py            # Tkinter 桌面端界面
├── yolo_detector.py       # YOLOv12n/v11n 推理层 (cv2.dnn)
├── ocr_engine.py          # Tesseract 传统字符提取 (pytesseract)
├── page_judger.py         # 业务页面动作流、数据拾取
├── browser_utils.py       # 本地 Edge 调度管理器
├── exporter.py            # 数据对比及 Excel 导出
├── requirements.txt       # Python 包依赖
├── build_exe.bat          # PyInstaller 一键打包脚本
├── README.md              # 部署及使用文档
├── models/
│   └── best.onnx          # 训练好的 YOLO 模型文件存放处
└── tessdata/
    ├── chi_sim.traineddata# Tesseract 中文语言包
    ├── eng.traineddata    # 必须的英文字符支持包
    └── osd.traineddata    # Tesseract 数据包
```

---

## 🛠 开发与部署环境搭建

1. **安装依赖**
   ```cmd
   pip install -r requirements.txt
   ```

2. **准备 Tesseract (必备)**
   - 从 [Tesseract 官方预编译版或 GitHub 发行](https://github.com/UB-Mannheim/tesseract/wiki) 下载安装
   - 提取 `tessdata` 文件夹包含 `chi_sim.traineddata` 等文件，放进本项目的根目录下 (如上方结构图所示)。
   - **坑点防御**：如果没放对目录，Pyinstaller打包后 OCR 会闪退！

3. **准备 YOLO 模型**
   将训练好的 YOLOv12n 或 YOLOv11n 权重导出为 ONNX，放入 `models` 目录下。
   命名必须是：`models/best.onnx`

---

## 🎯 YOLO 标注与训练指南

按要求标注 **15个具体类别**：
1. `logo_ccp` (中国版权保护中心圆形logo)
2. `btn_login_top` (首页右上角“登录”按钮)
3. `btn_login_submit` (登录页蓝色“立即登录”按钮)
4. `field_username` (登录页用户名输入框)
5. `field_password` (登录页密码输入框)
6. `nav_my_register` (左侧导航“我的登记”)
7. `nav_software_register` (左侧“软件登记”—高亮时也用此)
8. `tab_all` (顶部Tab) / `tab_draft` / `tab_to_submit` / `tab_wait_accept` / `tab_wait_review` / `tab_wait_correct` / `tab_to_issue` / `tab_issued` (这几类Tab，重点圈出文字+角标覆盖区域)
9. `badge_red_number` (所有红色数字角标，圆形红色背景+白色数字，极度关键)
10. `status_text` (表格中每一行的特定状态文字区域)
11. `list_row` (表格中的每一行记录区域)
12. `btn_view_detail` (每行“查看详情”蓝色链接)
13. `btn_refresh` (页面右上角刷新图标)

**如何标注 (以 20-60张图为例)：**
1. 运行 `pip install labelImg` (或使用在线工具如 Roboflow)。
2. 将浏览器分别处于这几张页面的多种状态。
3. 把所有的红点数字标记为 `badge_red_number`，每个Tab区域框好对应名。
4. 确保在标注格式中选择 YOLO，这会生成对应的 `classes.txt`。

**推荐的训练命令：**
```bash
yolo task=detect mode=train model=yolo11n.pt data=dataset.yaml epochs=100 imgsz=640 batch=16
```
*(注：YOLOv12n目前在2026-02可能仍在早期体验版阶段，如果你使用的是 v12 的 pt 文件可以直接替换。在不确定的情况下，v11n 是完全稳定且效果极佳的退路。两者导出的 ONNX 结构相似，直接放入即可兼容。)*

**导出 ONNX 命令：**
```bash
yolo export model=runs/detect/train/weights/best.pt format=onnx opset=12 simplify=True
```
导出后将对应的 `best.onnx` 放入本项目 `models/` 文件夹即可。

---

## 🤖 首次使用流程

1. **配置本地账户数据目录**
   程序默认运行会调用本地 Edge 并在同级产生一个 `edge_profile` 文件夹作为独立浏览器状态档案。
   
2. **首次手动免密登录赋权**
   点击界面“🚀 立即开始视觉自检”。系统会拉起浏览器。
   第一次看到登录页时，如果模型检测到了登录框（并弹出提示框阻塞），请手动在弹出的 Edge 页面完成账号、密码输入，并处理可能的滑块、短信等风控验证！
   勾选任意“X天内免密登录”。登录成功后，返回小工具点击对话框“确定”让流程继续。
   
3. **日常无人值守执行**
   后续由于 `edge_profile` 的持久化 cookie 缓存，打开就会直达登录状态，实现完全的全自动纯净运行。

---

## ⏰ 定时任务自动化参考 (Windows)

如果不希望手动去点，可以结合 Windows 任务计划程序：
1. 按下 `Win+R`，输入 `taskschd.msc` 打开。
2. 创建基本任务 -> 名称 "软著自动查询"。
3. 触发器选每天 12:00 或其他时间。
4. 操作选“启动程序”，选中打包好的 `CopyrightVisualMonitor_v2.exe`。
5. （如果希望纯后台静默，可在后续二次开发中为 `main.py` 增加静默启动参数并在 GUI 中 bypass 掉窗口弹出。）

---

## ❓ 常见问题 FAQ

**Q1：打包后程序突然闪退？**
✅ 检查是不是忘了把 `models` 和 `tessdata` 里的文件复制全。`build_exe.bat` 已包含相关命令。

**Q2：OCR读出来的全是乱码，或识别不出数字？**
✅ `ocr_engine.py` 针对性使用了图像放缩和反色算法增强 `tesseract` 的识别率。如果效果依旧不好，请检查 `tessdata` 英语和数字库文件是否完备。

**Q3：YOLO 一直框不准某个红色角标？**
✅ YOLO推理存在置信度问题，可利用桌面窗口左侧的拉条将“置信度”降低到 **0.4** 或更低进行尝试；并且确保你训练时这部分有足够多样性的截图。
