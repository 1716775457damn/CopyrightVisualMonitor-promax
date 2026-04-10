"""
配置管理器 config_manager.py
负责从 config.json 读取和写入用户账号配置信息。
若配置文件不存在，则自动创建并使用内置的默认值。
"""
import json
import os

import sys

# 获取程序运行的根目录 (兼容源码运行和打包后的 exe 运行)
if getattr(sys, 'frozen', False):
    # 打包后的 exe 模式
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    # 源码运行模式
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 配置文件路径
CONFIG_FILE = os.path.join(_BASE_DIR, "config.json")
ENV_FILE = os.path.join(_BASE_DIR, ".env")

# 默认配置（与原始硬编码值保持一致）
DEFAULT_CONFIG = {
    "account": "YOUR_PHONE_NUMBER",
    "password": "YOUR_PASSWORD",
    "delay_rate": 1.0
}


def load_config() -> dict:
    """
    加载 config.json 中的配置项。
    若文件不存在，自动创建并返回默认配置。
    """
    try:
        data = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
        # 补充可能缺失的键（兼容旧版本配置文件）
        for key, value in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = value
                
        # 尝试从 .env 加载高优先级的账号密码配置
        if os.path.exists(ENV_FILE):
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k, v = k.strip(), v.strip().strip("'").strip('"')
                        if k.upper() == "ACCOUNT":
                            data["account"] = v
                        elif k.upper() == "PASSWORD":
                            data["password"] = v
                            
        return data
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config: dict) -> bool:
    """
    将配置字典写入 config.json。
    返回 True 表示保存成功，False 表示失败。
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
