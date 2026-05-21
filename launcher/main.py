"""
台灣氣溫查詢啟動器
流程：檢查 Python → 安裝套件 → 建置前端 → 啟動系統匣服務
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# ── 路徑 ─────────────────────────────────────────────────
if getattr(sys, "frozen", False):
    ROOT = Path(sys.executable).parent
else:
    ROOT = Path(__file__).parent.parent

WEATHER_API_DIR = ROOT / "weather-api"
REACT_DIR       = ROOT / "temperature-dashboard"
REQUIREMENTS    = WEATHER_API_DIR / "requirements.txt"
REACT_BUILD     = REACT_DIR / "build" / "index.html"
TRAY_SCRIPT     = WEATHER_API_DIR / "tray.py"

CREATE_NO_WINDOW = 0x08000000


# ── 環境偵測 ──────────────────────────────────────────────
def _run(cmd: list, **kw) -> subprocess.CompletedProcess:
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    kw.setdefault("creationflags", CREATE_NO_WINDOW)
    return subprocess.run(cmd, **kw)


def find_python() -> list | None:
    for cand in [["py", "-3"], ["python3"], ["python"]]:
        try:
            r = _run(cand + ["--version"])
            out = r.stdout + r.stderr
            if r.returncode == 0 and "Python 3" in out:
                lines = [l for l in out.splitlines() if "Python 3" in l]
                if lines:
                    parts = lines[0].split()[1].split(".")
                    if int(parts[0]) == 3 and int(parts[1]) >= 10:
                        return cand
        except FileNotFoundError:
            continue
    return None


def packages_ok(python: list) -> bool:
    return _run(python + ["-m", "pip", "show", "fastapi"]).returncode == 0


def node_ok() -> bool:
    try:
        return _run(["node", "--version"]).returncode == 0
    except FileNotFoundError:
        return False


def winget_install(pkg_id: str) -> bool:
    r = subprocess.run(
        ["winget", "install", "--id", pkg_id,
         "--accept-source-agreements", "--accept-package-agreements"],
        capture_output=True, text=True, creationflags=CREATE_NO_WINDOW,
    )
    return r.returncode == 0


# ── 進度視窗 ──────────────────────────────────────────────
class SetupWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("台灣氣溫查詢")
        self.root.geometry("480x300")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)  # 禁止關閉
        self._center()

        tk.Label(self.root, text="台灣氣溫查詢",
                 font=("Microsoft JhengHei UI", 17, "bold"),
                 fg="white", bg="#1e1e2e").pack(pady=(18, 4))
        tk.Label(self.root, text="正在準備執行環境，請稍候…",
                 font=("Microsoft JhengHei UI", 10),
                 fg="#94a3b8", bg="#1e1e2e").pack(pady=(0, 10))

        frame = tk.Frame(self.root, bg="#1e1e2e")
        frame.pack(fill="both", expand=True, padx=20)

        self._text = tk.Text(
            frame, height=7, bg="#0f0f1a", fg="#cbd5e1",
            font=("Consolas", 9), state="disabled",
            relief="flat", bd=0, padx=6, pady=4,
        )
        self._text.pack(fill="both", expand=True)

        self._bar = ttk.Progressbar(self.root, mode="indeterminate")
        self._bar.pack(fill="x", padx=20, pady=12)
        self._bar.start(12)

    def _center(self):
        self.root.update_idletasks()
        w, h = 480, 300
        x = (self.root.winfo_screenwidth()  - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def log(self, msg: str):
        def _do():
            self._text.config(state="normal")
            self._text.insert("end", msg + "\n")
            self._text.see("end")
            self._text.config(state="disabled")
        self.root.after(0, _do)

    def close(self):
        self.root.after(0, self.root.destroy)

    def show_error(self, msg: str):
        def _do():
            self._bar.stop()
            self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
            tk.Label(self.root, text=msg, fg="#f87171", bg="#1e1e2e",
                     wraplength=440, justify="left",
                     font=("Microsoft JhengHei UI", 9)).pack(padx=20, pady=4)
            tk.Button(self.root, text="確定", command=self.root.destroy,
                      bg="#6366f1", fg="white", relief="flat",
                      padx=14, pady=4).pack(pady=6)
        self.root.after(0, _do)


# ── 串流執行並即時顯示輸出 ───────────────────────────────
def _stream(cmd: str, cwd: Path, win: "SetupWindow") -> bool:
    proc = subprocess.Popen(
        cmd, shell=True, cwd=str(cwd),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        creationflags=CREATE_NO_WINDOW,
    )
    for line in proc.stdout:
        line = line.rstrip()
        if line:
            win.log(f"    {line[:80]}")
    proc.wait()
    return proc.returncode == 0


# ── 安裝流程（背景執行緒）────────────────────────────────
def setup(win: SetupWindow) -> list | None:
    # 1. Python
    win.log("▸ 檢查 Python 3.10+…")
    python = find_python()
    if not python:
        win.log("  未找到，嘗試 winget 自動安裝…")
        if not winget_install("Python.Python.3.12"):
            win.show_error(
                "無法自動安裝 Python。\n"
                "請至 https://www.python.org/downloads/ 手動安裝後再執行。"
            )
            return None
        python = find_python()
        if not python:
            win.show_error("Python 安裝後仍無法偵測，請重新開啟程式。")
            return None
    win.log(f"  Python ✓  ({' '.join(python)})")

    # 2. pip 套件
    win.log("▸ 檢查 Python 套件…")
    if not packages_ok(python):
        win.log("  安裝中 (pip install -r requirements.txt)…")
        r = subprocess.run(
            python + ["-m", "pip", "install", "-r", str(REQUIREMENTS)],
            capture_output=True, text=True, creationflags=CREATE_NO_WINDOW,
        )
        if r.returncode != 0:
            win.show_error("套件安裝失敗：\n" + r.stderr[-400:])
            return None
    win.log("  套件 ✓")

    # 3. React build
    if not REACT_BUILD.exists():
        win.log("▸ 建置前端（首次需要 Node.js）…")
        if not node_ok():
            win.log("  未找到 Node.js，嘗試 winget 自動安裝…")
            if not winget_install("OpenJS.NodeJS.LTS"):
                win.show_error(
                    "無法自動安裝 Node.js。\n"
                    "請至 https://nodejs.org 手動安裝後再執行。"
                )
                return None
            win.log("  Node.js 已安裝，請重新執行程式以繼續。")
            win.show_error("Node.js 安裝完成。\n請關閉此視窗並重新開啟 taiwan-weather.exe。")
            return None
        win.log("  npm install... (首次需要幾分鐘，請稍候)")
        if not _stream("npm install", REACT_DIR, win):
            win.show_error("npm install 失敗，請查看上方錯誤訊息。")
            return None
        win.log("  npm run build...")
        if not _stream("npm run build", REACT_DIR, win):
            win.show_error("React 建置失敗，請查看上方錯誤訊息。")
            return None
        win.log("  前端建置完成 ✓")
    else:
        win.log("▸ 前端 build ✓")

    return python


# ── 主程式 ────────────────────────────────────────────────
def launch(python: list):
    subprocess.Popen(
        python + [str(TRAY_SCRIPT)],
        cwd=str(WEATHER_API_DIR),
        creationflags=CREATE_NO_WINDOW,
    )


def main():
    # 快速路徑：環境都齊，直接啟動不顯示視窗
    python = find_python()
    if python and packages_ok(python) and REACT_BUILD.exists():
        launch(python)
        return

    # 需要安裝：顯示進度視窗
    win = SetupWindow()

    def worker():
        py = setup(win)
        if py:
            launch(py)
            win.close()

    threading.Thread(target=worker, daemon=True).start()
    win.root.mainloop()


if __name__ == "__main__":
    main()
