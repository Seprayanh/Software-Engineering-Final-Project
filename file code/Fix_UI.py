import os
import time

# 1. 定义最新的 HTML 代码 (修复了样式，且强制微软雅黑)
html_content = r'''<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TODO Pro</title>
    <style>
        :root {
            --bg: #1e1e2e;
            --card: #252538;
            --text: #cdd6f4;
            --subtext: #a6adc8;
            --accent: #89b4fa;
            --danger: #f38ba8;
            --success: #a6e3a1;
            --warning: #f9e2af;
        }
        body, button, input, select, textarea {
            margin: 0; padding: 0;
            box-sizing: border-box;
            font-family: "Microsoft YaHei", "PingFang SC", sans-serif !important;
            background-color: var(--bg);
            color: var(--text);
            overflow: hidden; 
            user-select: none;
            display: flex; flex-direction: column; height: 100vh;
        }
        .drag-area {
            height: 38px; background: #181825;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 15px; -webkit-app-region: drag;
            border-bottom: 1px solid rgba(255,255,255,0.05); flex-shrink: 0;
        }
        .app-title { font-weight: bold; font-size: 14px; color: var(--accent); }
        .window-controls { -webkit-app-region: no-drag; display: flex; gap: 8px; }
        .control-btn { width: 12px; height: 12px; border-radius: 50%; cursor: pointer; transition: opacity 0.2s; }
        .control-btn:hover { opacity: 0.8; }
        .btn-compact { background-color: var(--success); }
        .btn-min { background-color: var(--warning); }
        .btn-close { background-color: var(--danger); }

        .container { flex: 1; padding: 15px; overflow-y: auto; scrollbar-width: none; }
        .container::-webkit-scrollbar { display: none; }

        .add-panel {
            background: var(--card); padding: 15px; border-radius: 12px;
            margin-bottom: 15px; display: flex; flex-direction: column; gap: 10px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2); -webkit-app-region: no-drag;
        }
        input, select {
            background: #313244; border: 1px solid #45475a; color: white;
            padding: 10px; border-radius: 8px; outline: none; font-size: 13px; width: 100%;
        }
        .row { display: flex; gap: 10px; }
        button.add-btn {
            background: var(--accent); color: #1e1e2e; border: none;
            padding: 10px; border-radius: 8px; font-weight: bold; cursor: pointer;
        }

        .task-list { list-style: none; padding: 0; margin: 0; padding-bottom: 20px;}
        .task-item {
            background: var(--card); padding: 12px 15px; margin-bottom: 8px; border-radius: 10px;
            display: flex; align-items: center; justify-content: space-between;
            border-left: 4px solid var(--subtext);
        }
        .prio-3 { border-left-color: var(--danger); }
        .prio-2 { border-left-color: var(--warning); }
        .prio-1 { border-left-color: var(--success); }
        
        .task-content { display: flex; flex-direction: column; gap: 4px; overflow: hidden; }
        .task-meta { font-size: 11px; color: var(--subtext); display: flex; gap: 8px; }
        .tag-badge { background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; }
        .task-item.completed .task-text { text-decoration: line-through; opacity: 0.5; }
        .actions { display: flex; gap: 12px; font-size: 16px; cursor: pointer; -webkit-app-region: no-drag; margin-left: 10px;}

        /* --- 身份选择弹窗 (修复核心) --- */
        #roleModal {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.7); z-index: 9999;
            display: none; align-items: center; justify-content: center;
            backdrop-filter: blur(5px);
        }
        .modal-content {
            background: #1e1e2e; padding: 30px; border-radius: 16px;
            text-align: center; width: 280px;
            border: 1px solid rgba(137, 180, 250, 0.2);
            box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        }
        .modal-title { margin: 0 0 10px 0; font-size: 20px; color: white; }
        .modal-desc { margin: 0 0 20px 0; color: var(--subtext); font-size: 13px; }
        .role-btn {
            display: flex; align-items: center; justify-content: center; gap: 10px;
            width: 100%; padding: 14px; margin-bottom: 12px;
            background: #313244; color: var(--text);
            border: 2px solid transparent; border-radius: 10px;
            cursor: pointer; font-size: 15px; font-weight: bold;
            transition: all 0.2s;
        }
        .role-btn:hover { background: var(--accent); color: #1e1e2e; transform: translateY(-2px); }

        #compactContainer {
            display: none; flex-direction: column; align-items: center; justify-content: center;
            height: 100%; text-align: center; cursor: pointer; -webkit-app-region: drag;
        }
        #clock { font-size: 42px; font-weight: bold; color: var(--accent); }
        #date { font-size: 12px; color: var(--subtext); margin-top: 5px; }
        body.is-compact .drag-area, body.is-compact .container { display: none !important; }
        body.is-compact #compactContainer { display: flex !important; }
    </style>
</head>
<body>
    <div class="drag-area">
        <div class="app-title">📌 TODO Pro</div>
        <div class="window-controls">
            <div class="control-btn btn-compact" onclick="toggleCompactMode()" title="时钟模式"></div>
            <div class="control-btn btn-min" onclick="minimizeWindow()" title="最小化"></div>
            <div class="control-btn btn-close" onclick="closeWindow()" title="关闭"></div>
        </div>
    </div>
    <div class="container">
        <div class="add-panel">
            <input type="text" id="content" placeholder="添加新任务...">
            <div class="row">
                <select id="priority" style="flex:1"><option value="3">🔥 高优</option><option value="2" selected>⚡ 中优</option><option value="1">☕ 低优</option></select>
                <select id="category" style="flex:1"><option value="通用">📂 通用</option><option value="学习">📚 学习</option><option value="工作">💼 工作</option><option value="生活">🏠 生活</option></select>
            </div>
            <div class="row"><input type="datetime-local" id="deadline"></div>
            <button class="add-btn" onclick="addTask()">添加任务</button>
        </div>
        <ul class="task-list" id="taskList"></ul>
    </div>
    <div id="compactContainer" onclick="toggleCompactMode()"><div id="clock">00:00</div><div id="date">--/--</div></div>
    
    <div id="roleModal">
        <div class="modal-content">
            <h3 class="modal-title">👋 欢迎初次使用</h3>
            <p class="modal-desc">请选择您的身份，我们将为您优化体验</p>
            <button class="role-btn" onclick="setRole('student')"><span>🎓</span> 我是学生</button>
            <button class="role-btn" onclick="setRole('worker')"><span>💼</span> 我是上班族</button>
        </div>
    </div>

    <script>
        const API_TASKS = '/api/tasks'; const API_PROFILE = '/api/profile'; let clockInterval;
        function minimizeWindow() { if(window.pywebview) window.pywebview.api.minimize(); }
        function closeWindow() { if(window.pywebview) window.pywebview.api.close(); }
        async function toggleCompactMode() {
            if(window.pywebview) {
                const isCompact = await window.pywebview.api.toggle_compact();
                if(isCompact) { document.body.classList.add('is-compact'); updateClock(); clockInterval = setInterval(updateClock, 1000); }
                else { document.body.classList.remove('is-compact'); clearInterval(clockInterval); }
            }
        }
        function updateClock() {
            const now = new Date(); const pad = n => n.toString().padStart(2,'0');
            document.getElementById('clock').textContent = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;
            const days = ['周日','周一','周二','周三','周四','周五','周六'];
            document.getElementById('date').textContent = `${now.getFullYear()}/${pad(now.getMonth()+1)}/${pad(now.getDate())} ${days[now.getDay()]}`;
        }
        async function checkIdentity() {
            try {
                const res = await fetch(`${API_PROFILE}?t=${Date.now()}`);
                const data = await res.json();
                if(!data || !data.role) document.getElementById('roleModal').style.display = 'flex';
            } catch(e) {}
        }
        async function setRole(role) {
            await fetch(API_PROFILE, { method: 'POST', body: JSON.stringify({role}) });
            document.getElementById('roleModal').style.display = 'none';
        }
        async function loadTasks() {
            try {
                const res = await fetch(API_TASKS); const data = await res.json();
                const list = document.getElementById('taskList'); list.innerHTML = '';
                data.items.forEach(task => {
                    const li = document.createElement('li');
                    li.className = `task-item prio-${task.priority} ${task.status==='completed'?'completed':''}`;
                    let timeStr = '';
                    if(task.deadline) {
                        const dt = new Date(task.deadline.replace(/-/g,'/'));
                        timeStr = `${dt.getMonth()+1}月${dt.getDate()}日 ${dt.getHours().toString().padStart(2,'0')}:${dt.getMinutes().toString().padStart(2,'0')}`;
                    }
                    li.innerHTML = `<div class="task-content"><span class="task-text">${task.content}</span><div class="task-meta"><span class="tag-badge">${task.category}</span>${timeStr?`<span>📅 ${timeStr}</span>`:''}</div></div><div class="actions"><div onclick="toggleTask(${task.id}, '${task.status}')">${task.status==='pending'?'⬜':'✅'}</div><div onclick="deleteTask(${task.id})">✕</div></div>`;
                    list.appendChild(li);
                });
            } catch(e){}
        }
        async function addTask() {
            const c = document.getElementById('content').value.trim(); if(!c) return;
            const payload = { content:c, priority:document.getElementById('priority').value, category:document.getElementById('category').value, deadline:document.getElementById('deadline').value.replace('T',' ') || null };
            await fetch(API_TASKS, { method:'POST', body:JSON.stringify(payload) });
            document.getElementById('content').value=''; loadTasks();
        }
        async function toggleTask(id,s) { await fetch(`${API_TASKS}/${id}`, {method:'PATCH', body:JSON.stringify({status:s==='pending'?'completed':'pending'})}); loadTasks(); }
        async function deleteTask(id) { if(confirm('删除?')) await fetch(`${API_TASKS}/${id}`, {method:'DELETE'}); loadTasks(); }
        document.addEventListener('DOMContentLoaded', () => { checkIdentity(); loadTasks(); setInterval(loadTasks, 5000); });
    </script>
</body>
</html>'''

# 2. 定义最新的 Desktop 代码 (增加了缓存清除机制)
desktop_content = r'''import threading
import socketserver
import sys
import os
import time

try:
    import webview
except ImportError:
    webview = None

from src.web import TodoHandler, reminder

class WindowApi:
    def __init__(self, normal_size, compact_size):
        self.window = None
        self.normal_width, self.normal_height = normal_size
        self.compact_width, self.compact_height = compact_size
        self.is_compact = False

    def minimize(self):
        if self.window: self.window.minimize()

    def close(self):
        if self.window: self.window.destroy()

    def toggle_compact(self):
        if self.window:
            if self.is_compact:
                self.window.resize(self.normal_width, self.normal_height)
                self.is_compact = False
            else:
                self.window.resize(self.compact_width, self.compact_height)
                self.is_compact = True
        return self.is_compact

def run_desktop(width=400, height=700):
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), TodoHandler)
    port = httpd.server_address[1]
    
    # 关键修改：加入时间戳，强制清除缓存！
    url = f"http://127.0.0.1:{port}/?mode=app&t={time.time()}"

    reminder.start()
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    def on_closed():
        reminder.stop()
        httpd.shutdown()

    if webview:
        api = WindowApi((width, height), (220, 100))
        window = webview.create_window(
            title="TODO Pro", url=url, width=width, height=height,
            frameless=True, easy_drag=True, resizable=False, on_top=True, confirm_close=True, text_select=False, js_api=api
        )
        api.window = window
        webview.start(on_closed, window)
    else:
        print("PyWebView missing.")
'''

# 3. 写入文件
print("正在修复 index.html ...")
os.makedirs("src/templates", exist_ok=True)
with open("src/templates/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("正在修复 desktop.py (缓存强制刷新) ...")
with open("src/desktop.py", "w", encoding="utf-8") as f:
    f.write(desktop_content)

print("正在重置身份信息以触发弹窗...")
if os.path.exists("profile.json"):
    try:
        os.remove("profile.json")
    except:
        pass

print("="*30)
print("修复完成！请关闭此窗口，直接双击 TodoPro.vbs 启动。")
print("="*30)