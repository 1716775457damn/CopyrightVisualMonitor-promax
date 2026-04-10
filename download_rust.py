import urllib.request
import os
import subprocess

print("Downloading official Rustup via USTC Mirror (binary safe mode)...")
url = "https://mirrors.ustc.edu.cn/rust-static/rustup/dist/x86_64-pc-windows-gnu/rustup-init.exe"

try:
    urllib.request.urlretrieve(url, "rustup-init.exe")
    print("Download complete. Installing Rust (GNU toolchain)...")
    
    env = os.environ.copy()
    env["RUSTUP_DIST_SERVER"] = "https://mirrors.ustc.edu.cn/rust-static"
    env["RUSTUP_UPDATE_ROOT"] = "https://mirrors.ustc.edu.cn/rust-static/rustup"
    
    subprocess.run(["rustup-init.exe", "-y", "--default-host", "x86_64-pc-windows-gnu", "--profile", "default"], env=env, check=True)
    print("Rust Installation Setup triggered successfully!")
    
    os.remove("rustup-init.exe")
except Exception as e:
    print(f"Failed: {e}")
