@echo off
setlocal enabledelayedexpansion

echo [1/4] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist\CopyrightVisualMonitor rmdir /s /q dist\CopyrightVisualMonitor

echo [2/4] 正在安装/更新依赖库...
pip install -r requirements.txt

echo [3/4] 正在开始 PyInstaller 打包流程...
pyinstaller --noconfirm build_pro.spec

echo [4/4] 正在准备 Playwright 运行时环境...
echo 注意：打包后的软件需要 Playwright 浏览器。
echo 正在尝试自动安装 chromium 到配套目录...
set PLAYWRIGHT_BROWSERS_PATH=dist\CopyrightVisualMonitor\playwright_browsers
playwright install chromium

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo 打包成功！
    echo 生成目录: dist\CopyrightVisualMonitor
    echo 可执行文件: CopyrightVisualMonitor.exe
    echo ==========================================
) else (
    echo.
    echo 打包过程中出现错误，请检查日志。
)

pause
