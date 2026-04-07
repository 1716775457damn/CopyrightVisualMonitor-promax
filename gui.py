import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.scrolledtext as st
import threading
from datetime import datetime

class AppGUI:
    def __init__(self, start_callback):
        self.root = tk.Tk()
        self.root.title("软著自检助手 (Copyright Visual Monitor)")
        self.root.geometry("500x550")
        self.root.resizable(False, False)
        
        self.start_callback = start_callback
        
        self._build_ui()
        
    def _build_ui(self):
        # 标题
        title_lbl = tk.Label(self.root, text="中国版权保护中心软著状态自检", font=("微软雅黑", 14, "bold"))
        title_lbl.pack(pady=10)
        
        # 按钮区
        self.start_btn = tk.Button(self.root, text="▶ 开始自检", font=("微软雅黑", 12), bg="#4CAF50", fg="white", 
                                   command=self.on_start_click, width=15, height=2)
        self.start_btn.pack(pady=5)
        
        # 状态提示
        self.status_var = tk.StringVar(value="状态：等待操作...")
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var, font=("微软雅黑", 10), fg="#666666")
        self.status_lbl.pack(pady=2)
        
        # 进度条
        self.progress = ttk.Progressbar(self.root, orient=tk.HORIZONTAL, length=460, mode='determinate')
        self.progress.pack(pady=5)
        
        # 结果表格
        columns = ("状态", "数量")
        self.tree = ttk.Treeview(self.root, columns=columns, show="headings", height=4)
        self.tree.heading("状态", text="软著状态")
        self.tree.heading("数量", text="数量 (件)")
        self.tree.column("状态", anchor="center")
        self.tree.column("数量", anchor="center")
        self.tree.pack(pady=5, fill=tk.X, padx=20)
        
        # 日志区
        log_lbl = tk.Label(self.root, text="执行日志:", font=("微软雅黑", 9))
        log_lbl.pack(anchor="w", padx=20)
        self.log_text = st.ScrolledText(self.root, height=10, width=60, font=("Consolas", 9), bg="#F5F5F5")
        self.log_text.pack(padx=20, pady=5, fill=tk.BOTH, expand=True)

    def log(self, msg):
        """添加日志记录到文本框"""
        now = datetime.now().strftime("%H:%M:%S")
        def _append():
            self.log_text.insert(tk.END, f"[{now}] {msg}\n")
            self.log_text.see(tk.END)
        self.root.after(0, _append)
        print(f"[{now}] {msg}")
        
    def on_start_click(self):
        self.start_btn.config(state=tk.DISABLED, text="正在运行...")
        self.progress["value"] = 0
        self.update_status("正在启动浏览器...")
        self.log_text.delete(1.0, tk.END)
        self.log("开始新的自检任务...")
        
        # 开启新线程运行长任务防止阻塞 GUI
        threading.Thread(target=self._run_task, daemon=True).start()
        
    def _run_task(self):
        try:
            results = self.start_callback(self)
            self.update_results(results)
            self.update_status("自检完成！")
            self.progress["value"] = 100
            self.log("自检任务全部完成。")
        except Exception as e:
            self.update_status(f"出现错误: {str(e)}")
            self.log(f"任务错误: {str(e)}")
            messagebox.showerror("错误", f"自检过程中发生错误:\n{str(e)}")
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL, text="▶ 开始自检"))
            
    def update_status(self, msg, progress_val=None):
        self.root.after(0, lambda: self.status_var.set(f"状态：{msg}"))
        if progress_val is not None:
            self.root.after(0, lambda: self.progress.config(value=progress_val))
            
    def update_results(self, data: dict):
        def _update():
            # 清空旧数据
            for item in self.tree.get_children():
                self.tree.delete(item)
            # 插入新数据
            for k, v in data.items():
                self.tree.insert("", tk.END, values=(k, v))
        self.root.after(0, _update)

    def run(self):
        self.root.mainloop()

