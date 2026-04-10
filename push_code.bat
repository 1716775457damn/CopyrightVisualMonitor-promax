@echo off
setlocal enabledelayedexpansion

echo [*] Parsing credentials from .env safely...
for /f "tokens=1,2 delims==" %%A in (.env) do (
    if "%%A"=="GITHUB_TOKEN" set TOKEN=%%B
)

if not exist ".git" (
    echo [*] Not a git repo, initializing base...
    git init
)

echo [*] Bootstrapping Git environment config...
git config user.email "auto@github.com"
git config user.name "AI-Automated"

echo [*] Adding all changes to Git...
git rm -r --cached edge_profile/ 2>nul
git rm --cached .env app.log *.log debug_*.png 2>nul
git add .
echo [*] Committing changes...
git commit -m "feat: complete slider captcha visual refactor using Airtest, implement dynamic elastic scaling box, and fix dashboard recognition amnesia"
echo [*] Pushing HEAD directly to remote 'main' branch fully automated...
git push https://1716775457damn:%TOKEN%@github.com/1716775457damn/CopyrightVisualMonitor-promax.git HEAD:main --force
echo [*] Done!
pause
