@echo off
chcp 65001 >nul
title 软著视觉自检助手 - CopyrightVisualMonitor

echo ========================================
echo    正在进入 CopyrightVisualMonitor 环境...
echo ========================================

:: 切换到你指定的 Anaconda
set PATH=F:\yolov11\anaconda\Scripts;F:\yolov11\anaconda;%PATH%

:: 激活项目专用环境
call conda activate copyright_monitor

echo ✅ 环境激活成功！
python --version
echo 当前环境: %CONDA_DEFAULT_ENV%
echo.

echo 正在启动程序...
python main.py

pause