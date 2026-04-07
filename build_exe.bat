@echo off
chcp 65001 >nul
echo ================================================================
echo   CopyrightVisualMonitor v3.0 - 打包工具
echo   软著全流程自动化工作站（状态监控 + 自动上传提交）
echo ================================================================
echo.

REM 检查 PyInstaller 是否安装
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] 未检测到 PyInstaller，正在自动安装...
    pip install pyinstaller
)

echo [1/2] 正在执行 PyInstaller 打包...
echo.

pyinstaller ^
    --noconfirm ^
    --onedir ^
    --windowed ^
    --name "CopyrightHub_v3" ^
    --add-data "tessdata;tessdata" ^
    --add-data "templates;templates" ^
    --add-data "config.json;." ^
    --hidden-import=ttkbootstrap ^
    --hidden-import=win10toast ^
    --hidden-import=PIL ^
    --hidden-import=cv2 ^
    --hidden-import=mss ^
    --hidden-import=pyautogui ^
    --hidden-import=pytesseract ^
    --hidden-import=pandas ^
    --hidden-import=openpyxl ^
    --hidden-import=playwright ^
    --hidden-import=playwright.sync_api ^
    --collect-all ttkbootstrap ^
    main.py

if errorlevel 1 (
    echo.
    echo [ERROR] 打包失败，请检查上方错误信息。
    pause
    exit /b 1
)

echo.
echo [2/2] 复制运行时必需的额外文件...

REM 复制 edge_profile 目录（如果存在）用于浏览器持久化登录
if exist "edge_profile" (
    xcopy /E /I /Y "edge_profile" "dist\CopyrightHub_v3\edge_profile" >nul
    echo   - edge_profile 已复制
)

REM 确保 config.json 存在
if not exist "dist\CopyrightHub_v3\config.json" (
    copy "config.json" "dist\CopyrightHub_v3\config.json" >nul
    echo   - config.json 已复制
)

echo.
echo ================================================================
echo   打包完毕！
echo   输出目录: dist\CopyrightHub_v3\
echo   主程序:   dist\CopyrightHub_v3\CopyrightHub_v3.exe
echo.
echo   注意事项:
echo   1. 首次运行前请将 exe 加入杀毒软件白名单
echo   2. 使用"自动上传"模式前需安装 Playwright 浏览器:
echo      playwright install chromium
echo   3. 系统需安装 Tesseract-OCR 到 C:\Tesseract-OCR\
echo ================================================================
pause
