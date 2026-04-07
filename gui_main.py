"""
CopyrightVisualMonitor v3.0 - 统一双模式 UI
支持两种功能模式：① 软著申请状态监控 ② 软著文件自动上传提交
保留统一的账号密码配置和控制台日志。
"""
import tkinter as tk
import ttkbootstrap as ttkb
from ttkbootstrap.constants import *
from tkinter import messagebox, scrolledtext
import threading
import os
import sys

import config_manager

# 模式常量
MODE_MONITOR = "monitor"
MODE_UPLOAD = "upload"
MODE_AMEND = "amend"


class MainGUI:
    def __init__(self, root, monitor_callback, upload_callback, amend_callback=None, amend_resume_callback=None):
        self.root = root
        self.monitor_callback = monitor_callback
        self.upload_callback = upload_callback
        self.amend_callback = amend_callback
        self.amend_resume_callback = amend_resume_callback
        
        self.root.title("CopyrightVisualMonitor v3.0")
        self.root.geometry("1080x820")
        self.root.minsize(960, 780)
        
        # 字体系统
        self.font_header = ("Microsoft YaHei UI", 22, "bold")
        self.font_title = ("Microsoft YaHei UI", 12, "bold")
        self.font_body = ("Microsoft YaHei UI", 10)
        self.font_small = ("Microsoft YaHei UI", 9)
        self.font_log = ("Consolas", 10)
        
        # 加载配置
        self._config = config_manager.load_config()
        
        # 当前模式
        self.var_mode = tk.StringVar(value=MODE_MONITOR)
        
        self.create_widgets()
        
    def create_widgets(self):
        # --- 全局背景 ---
        self.root.configure(bg="#0f172a")  # 暗夜蓝主题色
        
        # --- 顶部高亮装饰条 ---
        top_accent = ttkb.Frame(self.root, bootstyle="info", height=5)
        top_accent.pack(fill=X)
        
        # --- 头部 (Header) ---
        header_frame = ttkb.Frame(self.root, padding=(40, 35, 40, 15))
        header_frame.pack(fill=X)
        
        lbl_brand = ttkb.Label(header_frame, text="CCNU Copyright Hub", 
                               font=("Microsoft YaHei UI", 24, "bold"), bootstyle="inverse-primary")
        lbl_brand.pack(side=LEFT)
        
        lbl_sub = ttkb.Label(header_frame, text="软著全流程自动化工作站", 
                             font=("Microsoft YaHei UI", 11), bootstyle="secondary")
        lbl_sub.pack(side=LEFT, padx=25, pady=(12, 0))
        
        # --- 模式选择区域 ---
        mode_frame = ttkb.Frame(self.root, padding=(40, 10, 40, 20))
        mode_frame.pack(fill=X)
        
        ttkb.Label(mode_frame, text="⚙️ 选择工作流：", font=("Microsoft YaHei UI", 11, "bold"), 
                  bootstyle="light").pack(side=LEFT, padx=(0, 20))
        
        btn_style_options = {'padding': (15, 8)}
        
        rb_monitor = ttkb.Radiobutton(
            mode_frame, text="📊 状态监控", 
            variable=self.var_mode, value=MODE_MONITOR,
            bootstyle="info-toolbutton", command=self._on_mode_change,
            **btn_style_options
        )
        rb_monitor.pack(side=LEFT, padx=(0, 15))
        
        rb_upload = ttkb.Radiobutton(
            mode_frame, text="📤 自动上传提交",
            variable=self.var_mode, value=MODE_UPLOAD,
            bootstyle="warning-toolbutton", command=self._on_mode_change,
            **btn_style_options
        )
        rb_upload.pack(side=LEFT, padx=(0, 15))
        
        rb_amend = ttkb.Radiobutton(
            mode_frame, text="🛠️ 自动补正",
            variable=self.var_mode, value=MODE_AMEND,
            bootstyle="danger-toolbutton", command=self._on_mode_change,
            **btn_style_options
        )
        rb_amend.pack(side=LEFT)
        
        # 分隔线
        sep_frame = ttkb.Frame(self.root, padding=(40, 0))
        sep_frame.pack(fill=X)
        ttkb.Separator(sep_frame, bootstyle="secondary").pack(fill=X)
        
        # --- 主容器 ---
        main_container = ttkb.Frame(self.root, padding=(40, 20, 40, 40))
        main_container.pack(fill=BOTH, expand=YES)
        
        # 使用网格布局分配空间 3.5 : 6.5
        main_container.columnconfigure(0, weight=35)
        main_container.columnconfigure(1, weight=65)
        main_container.rowconfigure(0, weight=1)
        
        # =============== 左侧：设置面板 ===============
        left_panel = ttkb.Frame(main_container)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 30))
        
        # 1. 通行证卡片
        user_card = ttkb.Labelframe(left_panel, text=" 🔐 身份凭据 ", padding=20, bootstyle="info")
        user_card.pack(fill=X, pady=(0, 15))
        
        ttkb.Label(user_card, text="账号 (手机号)", font=("Microsoft YaHei UI", 10, "bold"), bootstyle="light").pack(anchor=W, pady=(0, 6))
        self.var_account = tk.StringVar(value=self._config.get("account", ""))
        entry_acct = ttkb.Entry(user_card, textvariable=self.var_account, font=("Consolas", 11))
        entry_acct.pack(fill=X, pady=(0, 12))
        
        ttkb.Label(user_card, text="账号密码", font=("Microsoft YaHei UI", 10, "bold"), bootstyle="light").pack(anchor=W, pady=(0, 4))
        
        # 密码行布局
        pwd_line = ttkb.Frame(user_card)
        pwd_line.pack(fill=X, pady=(0, 12))
        
        self.var_password = tk.StringVar(value=self._config.get("password", ""))
        self.entry_pwd = ttkb.Entry(pwd_line, textvariable=self.var_password, font=("Consolas", 11), show="●")
        self.entry_pwd.pack(side=LEFT, fill=X, expand=YES, padx=(0, 10))
        
        self.var_show_pwd = tk.BooleanVar(value=False)
        chk_pwd = ttkb.Checkbutton(pwd_line, text="👁", variable=self.var_show_pwd, 
                                   command=self._on_toggle_pwd, bootstyle="info-toolbutton")
        chk_pwd.pack(side=RIGHT)
        
        btn_save = ttkb.Button(user_card, text="持久化保存凭据", bootstyle="info-outline", 
                               command=self._save_account_config, padding=(10, 6))
        btn_save.pack(anchor=E)
        
        # 2. 调优卡片
        tuning_card = ttkb.Labelframe(left_panel, text=" ⚙️ 引擎性能控制 ", padding=15, bootstyle="secondary")
        tuning_card.pack(fill=X, pady=(0, 10))
        
        ttkb.Label(tuning_card, text="自适应延迟倍率", font=self.font_body).pack(anchor=W, pady=(0, 5))
        
        self.var_conf = tk.DoubleVar(value=self._config.get("delay_rate", 1.0))
        scale = ttkb.Scale(tuning_card, from_=0.5, to_=3.0, variable=self.var_conf, bootstyle="success")
        scale.pack(fill=X)
        
        scale_txt = ttkb.Frame(tuning_card)
        scale_txt.pack(fill=X, pady=(5, 0))
        ttkb.Label(scale_txt, text="高速", font=("Microsoft YaHei UI", 8), bootstyle="secondary").pack(side=LEFT)
        ttkb.Label(scale_txt, textvariable=self.var_conf, font=("Consolas", 10, "bold"), bootstyle="success").pack(side=LEFT, expand=YES)
        ttkb.Label(scale_txt, text="稳定", font=("Microsoft YaHei UI", 8), bootstyle="secondary").pack(side=RIGHT)
        
        # 3. 补正附加选项卡 (默认隐藏，仅在补正模式显示)
        self.amend_card = ttkb.Labelframe(left_panel, text=" 📝 申请类型选项 ", padding=15, bootstyle="danger")
        self.var_applicant_type = tk.StringVar(value="self")
        
        rb_self = ttkb.Radiobutton(self.amend_card, text="👤 自己申请 (默认)", variable=self.var_applicant_type, value="self", bootstyle="danger-toolbutton")
        rb_self.pack(fill=X, pady=(0, 6))
        
        rb_proxy = ttkb.Radiobutton(self.amend_card, text="💼 代理申请", variable=self.var_applicant_type, value="proxy", bootstyle="danger-toolbutton")
        rb_proxy.pack(fill=X, pady=(0, 2))
        
        # 分隔空间
        spacer = ttkb.Frame(left_panel, height=20)
        spacer.pack(fill=X)
        
        # 4. 操作按钮组
        self.btn_start = ttkb.Button(left_panel, text="▶ 启动全自动监测流水线", 
                                     bootstyle="success", command=self.on_start, padding=18)
        self.btn_start.pack(fill=X, pady=(15, 8))
        
        self.btn_resume_amend = ttkb.Button(left_panel, text="⏩ 跳过登录直接接管执行补正", 
                                     bootstyle="warning-outline", command=self.on_resume_amend, padding=16)
        
        self.btn_continue = ttkb.Button(left_panel, text="⏭️ 已手动上传，继续完成提交", 
                                     bootstyle="info", command=self.on_continue, padding=16)
        # 默认不显示 btn_continue，直到等待人工操作时再 pack
        
        # 4. 实时状态回显
        self.status_box = ttkb.Frame(left_panel, bootstyle="dark", padding=15)
        self.status_box.pack(fill=X)
        
        self.var_status_text = tk.StringVar(value="准备就绪 — 状态监控模式")
        lbl_status = ttkb.Label(self.status_box, textvariable=self.var_status_text, 
                                font=self.font_title, bootstyle="inverse-dark",
                                wraplength=280)
        lbl_status.pack(anchor=CENTER)
        
        self.progress_bar = ttkb.Progressbar(self.status_box, bootstyle="success-striped", 
                                            mode='indeterminate')
        
        # =============== 右侧：控制台面板 ===============
        right_panel = ttkb.Frame(main_container)
        right_panel.grid(row=0, column=1, sticky="nsew")
        
        # 终端阴影效果框
        term_frame = ttkb.Frame(right_panel, bootstyle="dark", padding=3)
        term_frame.pack(fill=BOTH, expand=YES)
        
        term_header = ttkb.Frame(term_frame, bootstyle="secondary", padding=(15, 10))
        term_header.pack(fill=X)
        
        ttkb.Label(term_header, text="● ● ●", font=("Consolas", 14), bootstyle="inverse-secondary").pack(side=LEFT, padx=(0, 15))
        ttkb.Label(term_header, text="TERMINAL OUTPUT", font=("Consolas", 10, "bold"), 
                  bootstyle="inverse-secondary").pack(side=LEFT)
        
        self.txt_log = scrolledtext.ScrolledText(term_frame, wrap=tk.WORD, font=("Consolas", 11),
                                                 bg="#050505", fg="#00ff41", insertbackground="white",
                                                 padx=20, pady=20, borderwidth=0, highlightthickness=0)
        self.txt_log.pack(fill=BOTH, expand=YES)
    
    # --- 模式切换回调 ---
    def _on_mode_change(self):
        mode = self.var_mode.get()
        if mode == MODE_MONITOR:
            self.amend_card.pack_forget()
            if hasattr(self, 'btn_resume_amend'):
                self.btn_resume_amend.pack_forget()
            self.btn_start.config(text="▶ 启动全自动监测流水线", bootstyle="success")
            self.var_status_text.set("准备就绪 — 状态监控模式")
        elif mode == MODE_UPLOAD:
            self.amend_card.pack_forget()
            if hasattr(self, 'btn_resume_amend'):
                self.btn_resume_amend.pack_forget()
            self.btn_start.config(text="📤 启动自动上传提交流程", bootstyle="warning")
            self.var_status_text.set("准备就绪 — 自动上传模式")
        else:
            self.amend_card.pack(fill=X, pady=(0, 10), before=self.btn_start)
            if hasattr(self, 'btn_resume_amend'):
                self.btn_resume_amend.pack(fill=X, pady=(0, 10), after=self.btn_start)
            self.btn_start.config(text="🛠️ 启动自动补正流程", bootstyle="danger")
            self.var_status_text.set("准备就绪 — 自动补正模式")
        
    def _on_toggle_pwd(self):
        show = "" if self.var_show_pwd.get() else "●"
        self.entry_pwd.config(show=show)
        
    def _save_account_config(self):
        account = self.var_account.get().strip()
        password = self.var_password.get()
        if not account:
            messagebox.showwarning("提示", "账号字段不能为空。")
            return
        new_config = {
            "account": account, 
            "password": password,
            "delay_rate": self.var_conf.get()
        }
        if config_manager.save_config(new_config):
            self._config = new_config
            self.log("[CONFIG] 配置已安全同步至本地磁盘。")
            messagebox.showinfo("成功", "身份凭据已持久化保存。")
            
    def get_current_credentials(self):
        return self.var_account.get().strip(), self.var_password.get()
    
    def get_current_mode(self) -> str:
        return self.var_mode.get()
        
    def get_applicant_type(self) -> str:
        return self.var_applicant_type.get()

    def log(self, text):
        def append():
            self.txt_log.insert(tk.END, f"> {text}\n")
            self.txt_log.see(tk.END)
            self.root.update_idletasks()
        self.root.after(0, append)
        
    def update_status(self, text, start_progress=False, stop_progress=False):
        def update():
            self.var_status_text.set(text)
            if start_progress:
                self.progress_bar.pack(fill=X, pady=(15, 0))
                self.progress_bar.start(15)
            if stop_progress:
                self.progress_bar.stop()
                self.progress_bar.pack_forget()
        self.root.after(0, update)
        
    def set_button_state(self, is_running):
        def update():
            mode = self.var_mode.get()
            if is_running:
                self.btn_start.config(state=tk.DISABLED, text="⚡ 正在执行任务...")
                if hasattr(self, 'btn_resume_amend'):
                    self.btn_resume_amend.config(state=tk.DISABLED)
            else:
                if hasattr(self, 'btn_resume_amend'):
                    self.btn_resume_amend.config(state=tk.NORMAL)
                if mode == MODE_MONITOR:
                    self.btn_start.config(state=tk.NORMAL, text="▶ 启动全自动监测流水线")
                elif mode == MODE_UPLOAD:
                    self.btn_start.config(state=tk.NORMAL, text="📤 启动自动上传提交流程")
                else:
                    self.btn_start.config(state=tk.NORMAL, text="🛠️ 启动自动补正流程")
        self.root.after(0, update)

    def on_continue(self):
        if hasattr(self, 'continue_event') and self.continue_event:
            self.continue_event.set()

    def wait_for_continue(self, msg=None):
        if msg is None:
            msg = "请在网页上完成需要手动上传的文档，完成后点击本界面上的【已手动上传，继续完成提交】按钮。"
        self.continue_event = threading.Event()
        
        # Show the continue button above status_box
        def show():
            self.btn_continue.pack(fill=X, pady=(0, 15), before=self.status_box)
            self.root.update_idletasks()
            self.log(f"⏸ 引流暂停: {msg}")
            messagebox.showinfo("请操作", msg)
            
        self.root.after(0, show)
        
        # Block the calling thread (the playwright automation thread)
        self.continue_event.wait()
        
        # Once continue is clicked, hide the button
        self.root.after(0, self.btn_continue.pack_forget)

    def wait_for_captcha(self):
        msg = "💡 检测到短信验证需求。请直接在网页上输入验证码，程序将【自动感应】您的输入并代劳最终提交。"
        
        def show_status():
            self.log(f"🔍 自动监听模式: {msg}")
            self.update_status("正在监听验证码输入...", start_progress=True)
            
        self.root.after(0, show_status)
        # 注意：此处不再使用 messagebox.showinfo 以实现“无手”操作
        # 但是主逻辑线程（navigator_amend）仍然会通过其内部循环等待

    def ask_for_login(self, blocking_event):
        def show():
            # 只有在确需人工介入时才弹窗，如果是全自动则这一步可跳过
            self.log("⚠️ 自动识别滑块遇到阻碍，请在浏览器中协助滑动或登录。完成后请点击【我已登录】按钮。")
            self.btn_continue.config(text="✅ 我已完成验证/登录")
            self.btn_continue.pack(fill=X, pady=(0, 15), before=self.status_box)
            self.continue_event = blocking_event
            
        self.root.after(0, show)

    def show_alert_changes(self, data):
        def alert():
            msg = f"检测到重要状态变动！\n说明: {data.get('变化说明')}"
            messagebox.showwarning("状态通知", msg)
        self.root.after(0, alert)
        
    def on_start(self):
        # 启动时保存配置
        account = self.var_account.get().strip()
        password = self.var_password.get()
        delay_rate = self.var_conf.get()
        if account:
            new_config = {"account": account, "password": password, "delay_rate": delay_rate}
            config_manager.save_config(new_config)
            self._config = new_config

        self.set_button_state(True)
        self.update_status("正在自检...", start_progress=True)
        self.txt_log.delete(1.0, tk.END)
        
        mode = self.var_mode.get()
        if mode == MODE_MONITOR:
            self.log(f"ENGINE STARTING... [状态监控模式]")
            self.log(f"STRATEGY: COMPUTER VISION (LATENCY {delay_rate}x)")
            self.log(f"IDENTITY: {account}")
            self.log("-" * 30)
            threading.Thread(target=self.monitor_callback, daemon=True).start()
        elif mode == MODE_UPLOAD:
            self.log(f"ENGINE STARTING... [自动上传模式]")
            self.log(f"STRATEGY: PLAYWRIGHT + COMPUTER VISION (LATENCY {delay_rate}x)")
            self.log(f"IDENTITY: {account}")
            self.log("-" * 30)
            threading.Thread(target=self.upload_callback, daemon=True).start()
        else:
            self.log(f"ENGINE STARTING... [自动补正模式]")
            self.log(f"STRATEGY: PLAYWRIGHT + COMPUTER VISION (LATENCY {delay_rate}x)")
            self.log(f"IDENTITY: {account}")
            self.log("-" * 30)
            if self.amend_callback:
                threading.Thread(target=self.amend_callback, daemon=True).start()

    def on_resume_amend(self):
        # 启动时保存配置
        account = self.var_account.get().strip()
        password = self.var_password.get()
        delay_rate = self.var_conf.get()
        if account:
            new_config = {"account": account, "password": password, "delay_rate": delay_rate}
            config_manager.save_config(new_config)
            self._config = new_config

        self.set_button_state(True)
        self.update_status("正在自检...", start_progress=True)
        self.txt_log.delete(1.0, tk.END)
        
        self.log(f"ENGINE STARTING... [跳过登录直接补正模式]")
        self.log(f"STRATEGY: PLAYWRIGHT (LATENCY {delay_rate}x)")
        self.log(f"IDENTITY: {account}")
        self.log("-" * 30)
        if self.amend_resume_callback:
            threading.Thread(target=self.amend_resume_callback, daemon=True).start()
