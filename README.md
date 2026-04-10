# CCNU Copyright Hub (CopyrightVisualMonitor v4.0 Promax)

华中师范大学软件著作权申请全流程自动化工作站

基于 **纯视觉 AI (Airtest) + OpenCV边缘检测 + Playwright** 构建的完全离线、环境免疫的极客自动化工具。
全面兼容各种 1080P、2K、4K 分辨率及高系统 DPI 缩放，即开即用，无需妥协环境。

---

## 🚀 项目架构与引擎重塑

本项目在 v4.0 Promax 版本进行了底层颠覆式的自适应重构，**全面接入游戏工业界大热的网易 Airtest 自动图像制导引擎**，结合 OpenCV，打造了目前最鲁棒的登录防封锁与滑块突围模块。

- **核心路线：** `Airtest 锚点制导 + OpenCV 弹性计算 + Playwright 流程控制`
- **重构视觉面：** 针对“环境稍微改变导致截取失败”的顽疾，开发出无极缩放弹性的“捕鼠网”。目前只要能看到【标题】和【底座】，计算网格大小和拖动距离就能实现自适应。
- **降维打击控制：** 鼠标轨迹应用随机偏振和仿生贝塞尔曲线。

## 📁 主要底层结构

```text
CCNU_Copyright_Hub/
├── main.py                # 核心程序交互入口，串联监控与上传多模式流
├── gui_main.py            # Tkinter 构建的赛博极简控制台界面
├── config_manager.py      # .env / config 文件读取优先级处理器
├── page_judger.py         # [核心] Airtest视觉引挚封装与滑块动态验证
├── browser_utils.py       # Popen调用本地Edge与Profile沙盒持久化隔离
├── push_code.bat          # 集成版 Git-Token 免密推云工具
└── button/                # [绝对核心]存放运行时抓取的特征指纹图(切勿随意更改!)
```

---

## 🛠 开发与部署环境搭建

1. **核心依赖链**
   ```cmd
   pip install airtest opencv-python pyautogui pandas
   pip install playwright
   ```
   *注意：初次运行后需执行 `playwright install chromium` 以预装沙盒内核。*

2. **环境变量安全存放阵列 (.env)**
   如果希望全自动免交互登录以及后续使用快速推包功能，建议在同级目录下新建 `.env`：
   ```env
   ACCOUNT=您的账号
   PASSWORD=您的长密码
   GITHUB_TOKEN=您的专属 Github Token
   ```

3. **视觉锚点准备 (Airtest)**
   需要在 `button` 文件夹内配备最新截取的登录页元素，程序完全根据您的这几张截图产生相对坐标：
   - `zhanghao.png`、`mima.png`、`denglu.png`
   - **(验证码必备)**：`captcha_title.png` 和 `slider_btn.png`。

---

## 🤖 核心机制 - 极速体验

### 🛡️ 智能滑块弹性突破 (Cyber Slider Breaker)
**痛点**：传统 RPA 在经过分辨率转换或 125% 缩放后，原本写死的 340*212 的坐标框必定错位截图失败，导致 OpenCV 当场报错。
**破绽**：本次升级后，程序利用 Airtest 首先扫描出 `验证码标题` 和 `滑块按钮` 两道水平阈值，随即像拉皮筋一样动态生成一块纯净裁剪布。无视环境分辨率！提取原图后无缝交给 Canny 生成边缘并找到凹槽，自动触发拟人拖放。

### 🎭 后台多线程协同防卡死
彻底解构了原来因为异步任务卡死在验证码上的超时逻辑。加入 **Tesseract OCR 兜底检测探针**，只要一滑入系统内部（识别出“全部”字段），马上截断循环直达提效端。

---

## ❓ 常见问题 FAQ

**Q1：为何抛弃 YOLO 和部分 PyTesseract 转用 Airtest？**
✅ 国版中心前端的色彩饱和度调整过于频繁。YOLO 在不补全算力的情况难以迅速响应新环境；传统的 Tesseract 虽然能找文字但成功率随图片缩放比例极度不稳。引入工业级手游测试标杆的 Airtest，让这套系统彻底实现了“只认形体，无视光影和放缩”。

**Q2：运行中看到大量关于 `edge_profile` 的报错或 GitHub 拥堵？**
✅ `edge_profile/` 是本程序独家模拟人类运行、存储极度敏感个人登录态和 Cookie 以及十万碎片的绝密暗房！它已被底层封印加入 `.gitignore` 且有缓存清除脚卫。**绝不可以手动将它推送至 Github 任意公共库！**

**Q3：验证码拼图连刷好几次失败？**
✅ 有些滑块因浏览器硬件发光特效，可能在缺口边缘产生了干扰伪影。不用急，代码里自带校准功能，如果失败 3 次它会自动增加 `CALIBRATION_OFFSET`，失败 6 次再加距。要是全军覆没那就人工用手滑一下帮忙过门即可。
