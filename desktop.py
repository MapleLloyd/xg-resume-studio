"""桌面版启动器 —— 打开独立窗口运行简历系统，不依赖浏览器。

用法：python desktop.py  或  双击 start_desktop.bat
"""
import socket
import threading
import time

import uvicorn
import webview

from app import app


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def main():
    port = _free_port()
    url = f"http://127.0.0.1:{port}"
    # 与浏览器/EXE 版一致：监听局域网，远程入口由首页开关控制。
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    print(f"[desktop] 本地服务已启动: {url}", flush=True)

    webview.create_window(
        "滴鱼简历助手 XG Resume Studio",
        url,
        width=1280,
        height=860,
        min_size=(1024, 700),
        background_color="#f6f7fb",
    )
    webview.start()
    server.should_exit = True


if __name__ == "__main__":
    main()
