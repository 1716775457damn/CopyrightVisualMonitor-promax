"""
浏览器控制模块
利用 subprocess 启动本机 Edge 浏览器，并通过指定 user-data-dir 实现持久化免密登录
"""
import subprocess
import time
import os
import winreg

def get_edge_path():
    """读取注册表获取系统的 Node Edge 绝对路径"""
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
        path, _ = winreg.QueryValueEx(key, "")
        return path
    except Exception:
        # Fallback 常见路径
        for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", 
                  r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]:
            if os.path.exists(p):
                return p
        raise FileNotFoundError("未找到 Edge 浏览器，请确认已安装。")

def start_edge(url):
    """启动本地 Edge 并导航到指定URL"""
    import sys
    edge_path = get_edge_path()
    
    # 获取程序运行的根目录 (兼容源码运行和打包后的 exe 运行)
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 模式，sys.executable 是 exe 路径，其父目录是安装目录
        base_dir = os.path.dirname(sys.executable)
    else:
        # 源码运行模式
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    profile_dir = os.path.join(base_dir, "edge_profile")
    
    # 强制清理环境，防止 PyInstaller 注入的 DLL 路径影响 msedge 子进程
    app_env = os.environ.copy()
    if getattr(sys, 'frozen', False):
        # PyInstaller 会将程序目录（onedir）或临时目录（onefile）添加到 PATH 开头，
        # 这会导致 msedge 错误地加载打包版本附带的（可能版本不匹配）DLL（如 libssl, zlib 等）。
        # 我们需要从 PATH 中移除包含程序目录的项目。
        meipass = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
        path_list = app_env.get('PATH', '').split(os.pathsep)
        # 移除包含 meipass 路径的项（通常是第一项）
        cleaned_path = os.pathsep.join([p for p in path_list if meipass.lower() not in p.lower()])
        app_env['PATH'] = cleaned_path
        # 彻底移除 Python 路径，防止 msedge 误解析
        app_env.pop('PYTHONPATH', None)
        app_env.pop('PYTHONHOME', None)
        # 有时还需要清理 TK_LIBRARY 和 TCL_LIBRARY
        app_env.pop('TK_LIBRARY', None)
        app_env.pop('TCL_LIBRARY', None)
    
    cmd = [
        edge_path,
        f"--user-data-dir={profile_dir}",
        "--remote-debugging-port=9222",
        "--start-maximized",
        "--inprivate",
        "--force-device-scale-factor=1",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-restore-session-state",
        "--hide-crash-restore-bubble",
        "--disable-session-crashed-bubble",
        "--disable-features=SessionCrashedBubble,RestoreSessionCrashedBubble,PrintCompositorLP", # 特别禁用导致21错误的功能
        "--edge-skip-compat-layer-relaunch", # 跳过可能导致 session not created 的层
        url
    ]
    
    # 确保用户数据目录存在
    if not os.path.exists(profile_dir):
        try:
            os.makedirs(profile_dir, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"无法创建浏览器配置文件目录: {profile_dir}, 错误: {e}")
        
    try:
        # 启动前清理残留的 Edge 进程，更彻底地解决目录锁定问题
        taskkill_path = r"C:\Windows\System32\taskkill.exe"
        try:
            if os.path.exists(taskkill_path):
                # 尝试强制关闭，但不捕获错误，因为可能由于权限原因无法干掉用户正在开着的其他 Edge
                subprocess.run([taskkill_path, "/F", "/IM", "msedge.exe", "/T"], 
                               capture_output=True, creationflags=0x08000000) 
                time.sleep(2) # 留出文件释放时间
        except Exception:
            pass
            
        # 使用 Popen 启动，并传入干净的环境
        process = subprocess.Popen(cmd, env=app_env)
        
        # 校验进程状态
        time.sleep(3) # 再多等一会儿
        exit_code = process.poll()
        if exit_code is not None and exit_code != 0:
             raise RuntimeError(f"浏览器启动失败并退出，返回码: {exit_code} (请确认是否有其他浏览器实例占用了端口或目录)")
             
        return process
    except Exception as e:
        raise RuntimeError(f"Edge 启动连接链路异常: {e}")
