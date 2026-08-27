"""滴鱼简历助手 —— EXE 入口。

打包后的启动流程：挑空闲端口 → 后台线程起 uvicorn → 就绪后打开浏览器 →
主线程驻留保活；用户关闭本窗口即退出服务。
"""
import socket
import threading
import time
import webbrowser


def _free_port(start=8000, tries=11):
    for p in range(start, start + tries):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            s.close()
            return p
        except OSError:
            continue
    return start


def main():
    port = _free_port()
    url = f"http://127.0.0.1:{port}"

    import uvicorn
    from app import app

    # 始终监听局域网地址；是否允许远程访问由应用内的扫码直传开关安全控制。
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(150):
        if server.started:
            break
        time.sleep(0.1)

    print()
    print("=" * 52)
    print("  滴鱼简历助手已启动")
    print(f"  地址：{url}  （浏览器应已自动打开）")
    print("  使用期间请保持本窗口开启；关闭窗口即退出程序。")
    print("  你的全部数据保存在本程序旁的 data 文件夹内。")
    print("=" * 52)
    print()

    if not server.started:
        print("[警告] 服务未能在预期时间内就绪，仍尝试打开浏览器…")
    try:
        webbrowser.open(url)
    except Exception:
        print(f"[提示] 请手动在浏览器打开：{url}")

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
