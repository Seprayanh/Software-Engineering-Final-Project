import threading
import socketserver
import time
import sys
import os

try:
    import webview
except ImportError:
    webview = None

# 引入后端逻辑
from src.web import TodoHandler
from src.reminder_manager import ReminderEngine

class ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

class WindowApi:
    def __init__(self, normal_size, compact_size):
        self.window = None
        self.normal_width = 420
        self.normal_height = 750
        self.compact_width, self.compact_height = compact_size
        self.is_compact = False
        self.engine = ReminderEngine(self.notify_frontend)

    def set_window(self, window):
        self.window = window

    def minimize(self):
        if self.window: self.window.minimize()

    def close(self):
        if self.engine: self.engine.stop()
        if self.window: self.window.destroy()

    def toggle_compact(self):
        if self.window:
            if self.is_compact:
                # 切回主界面：强制设置大尺寸
                self.window.resize(self.normal_width, self.normal_height)
                self.is_compact = False
            else:
                # 切回时钟：强制设置小尺寸
                self.window.resize(self.compact_width, self.compact_height)
                self.is_compact = True
        return self.is_compact

    def notify_frontend(self, task_info):
        """提醒触发时调用前端 JS"""
        if self.window:
            try:
                if self.window.minimized: self.window.restore()
                self.window.show()
                
                # 如果当前是微缩模式，强制展开
                if self.is_compact:
                    self.toggle_compact()
                
                safe_name = task_info['name'].replace("'", "\\'")
                js = f"showReminderModal({task_info['id']}, '{safe_name}')"
                self.window.evaluate_js(js)
            except Exception as e:
                print(f"Notify Error: {e}")

def run_desktop(width=420, height=750):
    # 1. 启动服务器
    try:
        server = ThreadingServer(("127.0.0.1", 0), TodoHandler)
        port = server.server_address[1]
    except OSError as e:
        print(f"Port error: {e}")
        return

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    url = f"http://127.0.0.1:{port}/?t={time.time()}"

    # 2. 定义窗口还原时的修复逻辑 (关键修复)
    def fix_size_on_restore():
        # 给系统一点时间完成还原动画，然后强制纠正尺寸
        time.sleep(0.1)
        if webview_window:
            if api.is_compact:
                webview_window.resize(220, 110)
            else:
                webview_window.resize(420, 750)

    # 3. 启动 GUI
    if webview:
        api = WindowApi((width, height), (220, 110))
        
        webview_window = webview.create_window(
            title="ToDo Pro",
            url=url,
            width=width,
            height=height,
            frameless=True,
            easy_drag=True, 
            on_top=False,
            resizable=False,
            js_api=api
        )
        api.set_window(webview_window)
        
        # --- 绑定还原事件 ---
        # 当窗口从最小化还原时，触发 fix_size_on_restore
        webview_window.events.restored += lambda: threading.Thread(target=fix_size_on_restore, daemon=True).start()
        
        webview.start(debug=False)
        server.shutdown()
    else:
        print("CRITICAL: pywebview module missing.")