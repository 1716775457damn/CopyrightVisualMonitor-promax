@echo off
echo [*] Removing stagnant Git lock files...
del /F /A .git\index.lock 2>nul
del /F /A .git\HEAD.lock 2>nul
del /F /A .git\refs\heads\main.lock 2>nul
del /F /A .git\refs\heads\master.lock 2>nul
echo [*] Lock files cleared! You can now commit in GitHub Desktop!
pause
