import http.server
import json
import os
import sys
from src.database import TaskManager

def get_resource_base():
    if hasattr(sys, '_MEIPASS'): return sys._MEIPASS
    return os.path.abspath(".")

def get_data_dir():
    if getattr(sys, 'frozen', False): base = os.path.dirname(sys.executable)
    else: base = os.path.abspath(".")
    path = os.path.join(base, "data")
    os.makedirs(path, exist_ok=True)
    return path

TEMPLATE_DIR = os.path.join(get_resource_base(), "src", "templates")
db = TaskManager(os.path.join(get_data_dir(), "todo.db"))

class TodoHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=TEMPLATE_DIR, **kwargs)

    def log_message(self, format, *args): pass 

    def do_GET(self):
        if self.path == '/favicon.ico':
            self.send_response(204); self.end_headers(); return

        if self.path.startswith('/api/tasks'):
            self.send_json(db.get_tasks())
        elif self.path.startswith('/api/stats'):
            self.send_json(db.get_star_stats())
        elif self.path.startswith('/api/profile'):
            self.send_json(db.get_profile())
        else:
            super().do_GET()

    def do_POST(self):
        try:
            length = int(self.headers['Content-Length'])
            body = json.loads(self.rfile.read(length).decode('utf-8'))
            
            if self.path.startswith('/api/tasks/add'):
                new_id = db.add_task(body.get('content'), body.get('priority'), body.get('category'), body.get('deadline'), body.get('remind_offset', 0))
                self.send_json({"status": "ok", "id": new_id})
            
            elif self.path.startswith('/api/tasks/status'):
                db.update_status(body['id'], body['status'])
                self.send_json({"status": "ok"})
                
            elif self.path.startswith('/api/profile'):
                # 支持保存任意配置 (theme, lang, name, role)
                db.update_profile_batch(body)
                self.send_json({"status": "ok"})
                
        except Exception as e:
            print(f"POST Error: {e}")
            self.send_response(500); self.end_headers()

    def do_DELETE(self):
        if self.path.startswith('/api/tasks/'):
            try:
                tid = int(self.path.split('/')[-1])
                db.delete_task(tid)
                self.send_json({"status": "deleted"})
            except:
                self.send_response(500)

    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())