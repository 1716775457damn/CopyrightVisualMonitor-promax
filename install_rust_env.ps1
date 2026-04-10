# 捕获异常
$ErrorActionPreference = "Stop"

Write-Host "[1/3] Fetching Microsoft Visual Studio Build Tools..."
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile "vs_buildtools.exe"

Write-Host "[2/3] Installing MSVC Build Tools silently (this may take 5 ~ 15 minutes, please wait!)..."
$process = Start-Process -FilePath ".\vs_buildtools.exe" -ArgumentList "--quiet --wait --norestart --nocache --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended" -Wait -PassThru -NoNewWindow
if ($process.ExitCode -ne 0 -and $process.ExitCode -ne 3010) {
    Write-Warning "MSVC Installer exited with code $($process.ExitCode). Continuing anyway..."
}

Write-Host "[3/3] Fetching and installing Rust Toolchain..."
Invoke-WebRequest -Uri "https://win.rustup.rs/" -OutFile "rustup-init.exe"
$rustupProcess = Start-Process -FilePath ".\rustup-init.exe" -ArgumentList "-y --profile default --default-toolchain stable" -Wait -PassThru -NoNewWindow
if ($rustupProcess.ExitCode -ne 0) {
    Write-Warning "Rustup installer exited with code $($rustupProcess.ExitCode)."
}

Write-Host "Cleaning up..."
Remove-Item -Force ".\vs_buildtools.exe" -ErrorAction SilentlyContinue
Remove-Item -Force ".\rustup-init.exe" -ErrorAction SilentlyContinue

Write-Host "Installation workflow completed!"
