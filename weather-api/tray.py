"""
台灣氣溫查詢 — 系統匣服務
用法：python tray.py
"""
import asyncio
import os
import sys
import threading
import time
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import httpx
import pystray
from PIL import Image, ImageDraw
from uvicorn import Config, Server

API_HOST = "127.0.0.1"
API_PORT = 3002
API_URL  = f"http://{API_HOST}:{API_PORT}"

# ── 伺服器管理 ────────────────────────────────────────────
_server: Server | None = None
_thread: threading.Thread | None = None
_lock   = threading.Lock()


def _run_server(server: Server):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())
    loop.close()


def start_server():
    global _server, _thread
    with _lock:
        if _thread and _thread.is_alive():
            return
        from app import app as fastapi_app
        config = Config(app=fastapi_app, host=API_HOST, port=API_PORT,
                        log_level="warning")
        _server = Server(config)
        _thread = threading.Thread(target=_run_server, args=(_server,), daemon=True)
        _thread.start()


def stop_server():
    global _server, _thread
    with _lock:
        if _server:
            _server.should_exit = True
        if _thread:
            _thread.join(timeout=8)
        _server = None
        _thread = None


def wait_ready(timeout: int = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{API_URL}/api/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


# ── 圖示 ─────────────────────────────────────────────────
def _make_icon(size: int = 64) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.ellipse([0, 0, size - 1, size - 1], fill=(99, 102, 241, 255))
    sx, sy, sw, sh = 27, 8, 10, 30
    d.rounded_rectangle([sx, sy, sx + sw, sy + sh], radius=4,
                        fill=(255, 255, 255, 220))
    d.rounded_rectangle([sx + 2, sy + sh // 2, sx + sw - 2, sy + sh - 2],
                        radius=2, fill=(239, 68, 68, 255))
    br, bx = 9, size // 2
    by = sy + sh + br - 2
    d.ellipse([bx - br, by - br, bx + br, by + br], fill=(239, 68, 68, 255))
    for gy in [sy + 8, sy + 16, sy + 24]:
        d.line([sx + sw, gy, sx + sw + 5, gy], fill=(255, 255, 255, 180), width=2)
    return img


# ── 選單動作 ──────────────────────────────────────────────
def on_open(icon, item):
    webbrowser.open(API_URL)


def _do_restart(icon):
    icon.title = "台灣氣溫查詢（重啟中…）"
    stop_server()
    time.sleep(1)
    start_server()
    wait_ready()
    icon.title = "台灣氣溫查詢"


def on_restart(icon, item):
    threading.Thread(target=_do_restart, args=(icon,), daemon=True).start()


def on_update_history(icon, item):
    def _do():
        try:
            httpx.post(f"{API_URL}/api/update-all", timeout=5)
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


def on_refresh_forecast(icon, item):
    def _do():
        try:
            httpx.post(f"{API_URL}/api/refresh-forecast", timeout=5)
        except Exception:
            pass
    threading.Thread(target=_do, daemon=True).start()


def on_quit(icon, item):
    stop_server()
    icon.stop()


# ── 主程式 ────────────────────────────────────────────────
def main():
    start_server()
    if wait_ready():
        webbrowser.open(API_URL)

    menu = pystray.Menu(
        pystray.MenuItem("開啟介面", on_open, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("重啟服務", on_restart),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("更新歷史資料", on_update_history),
        pystray.MenuItem("更新預報資料", on_refresh_forecast),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("關閉", on_quit),
    )
    icon = pystray.Icon("台灣氣溫查詢", _make_icon(), "台灣氣溫查詢", menu)
    icon.run()


if __name__ == "__main__":
    main()
