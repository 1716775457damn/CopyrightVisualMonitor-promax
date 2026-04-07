@echo off
echo 开始打包软著自检助手...
pyinstaller --noconfirm --onedir --windowed --add-data "templates;templates/" --add-data "tessdata/chi_sim.traineddata;tessdata/" --hidden-import=win10toast main.py
echo 打包完成！
pause
