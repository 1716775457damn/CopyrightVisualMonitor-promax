# -*- encoding=utf8 -*-
"""
Airtest 核心视觉接管引擎
负责被 Rust 主进程唤起，通过跨网络或标准输入输出接收 JSON 指令，
然后在一瞬间进行模板匹配并执行原生模拟鼠标键盘点击。
"""
import sys
import json
from airtest.core.api import *

# 接管当前平台
auto_setup(__file__)

def process_interaction(payload):
    """
    处理来自 Rust 反传的字典指令
    """
    action = payload.get("action")
    target_img = payload.get("target")

    try:
        # 心跳存活与唤回
        if action == "PING":
            return {"status": "ok", "msg": "PONG"}
            
        # 寻找指定的高抗干扰模板特征戳
        elif action == "TOUCH":
            # 引入对不同分辨率的兼容
            touch(Template(rf"assets/{target_img}", resolution=(1920, 1080), threshold=0.75))
            return {"status": "ok", "msg": f"Successfully touched {target_img}"}
            
        elif action == "EXISTS":
            pos = exists(Template(rf"assets/{target_img}", threshold=0.75))
            if pos:
                return {"status": "ok", "pos": pos, "msg": f"Found at {pos}"}
            else:
                return {"status": "not_found", "msg": "Target missing"}
                
        elif action == "TEXT":
            content = payload.get("content")
            text(content)
            return {"status": "ok", "msg": "Text injected"}
            
        else:
            return {"status": "error", "msg": f"Unknown action: {action}"}
            
    except Exception as e:
        return {"status": "error", "msg": str(e)}

def main():
    print(json.dumps({"status": "ready", "msg": "Airtest Vision Engine online."}), flush=True)
    
    # 无限循环接收标准输入中的指令
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
            
        if line == "EXIT":
            print(json.dumps({"status": "shutdown", "msg": "Shutting down..."}), flush=True)
            break
            
        try:
            command = json.loads(line)
            result = process_interaction(command)
            # 通过标准输出将 JSON 对象回传给 Rust (Rust 将负责反序列化更新界面进度)
            print(json.dumps(result), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({"status": "error", "msg": "Invalid JSON format"}), flush=True)

if __name__ == '__main__':
    main()
