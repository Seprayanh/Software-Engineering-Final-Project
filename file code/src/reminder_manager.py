# 文件路径: src/reminder_manager.py
import threading
import time
import datetime
import winsound

class ReminderEngine:
    def __init__(self, callback_func=None):
        self.tasks = {} 
        self.running = True
        self.callback = callback_func
        self.lock = threading.Lock()
        
        # 守护线程，随主程序退出而退出
        self.monitor_thread = threading.Thread(target=self.monitor_tasks, daemon=True)
        self.monitor_thread.start()

    def add_reminder(self, task_id, task_name, target_time_str, days=0, hours=0, minutes=0):
        try:
            # 简单的清洗逻辑
            clean_time_str = target_time_str.replace("T", " ")
            # 尝试解析两种格式
            try:
                target_time = datetime.datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                target_time = datetime.datetime.strptime(clean_time_str, "%Y-%m-%d %H:%M")

            # 计算提醒触发时间
            offset_minutes = (int(days) * 1440) + (int(hours) * 60) + int(minutes)
            offset = datetime.timedelta(minutes=offset_minutes)
            trigger_time = target_time - offset
            
            # 仅添加未来的提醒
            if trigger_time > datetime.datetime.now():
                with self.lock:
                    self.tasks[task_id] = {
                        "id": task_id,
                        "name": task_name,
                        "trigger": trigger_time,
                        "target_str": target_time.strftime("%m-%d %H:%M"),
                        "notified": False
                    }
        except Exception as e:
            print(f"Reminder Error: {e}")

    def monitor_tasks(self):
        while self.running:
            try:
                now = datetime.datetime.now()
                notify_list = []
                
                # 快速上锁检查，避免阻塞太久
                with self.lock:
                    for t_id, task in self.tasks.items():
                        if not task["notified"] and now >= task["trigger"]:
                            task["notified"] = True
                            notify_list.append(task)
                
                # 在锁外执行回调和声音，防止卡死
                for task in notify_list:
                    try:
                        # 播放简短的提示音
                        winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
                    except: 
                        pass
                    
                    if self.callback:
                        self.callback(task)
            except Exception as e:
                print(f"Monitor loop error: {e}")
            
            # 每秒检查一次足矣，不要太快
            time.sleep(1)

    def stop(self):
        self.running = False