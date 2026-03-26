import threading
import time
from typing import Optional

from src.database import TaskManager


class ReminderService:
    """Simple alarm/reminder service (polling).

    - Poll alarms table for due alarms
    - Send OS notification if possible (plyer), else print to console
    - Mark alarm done after firing (at-least-once semantics)
    """

    def __init__(self, db: TaskManager, poll_seconds: int = 10):
        self.db = db
        self.poll_seconds = int(poll_seconds)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _notify(self, title: str, message: str):
        # Try plyer notifications (cross-platform)
        try:
            from plyer import notification  # type: ignore

            notification.notify(
                title=title,
                message=message,
                timeout=10,
            )
        except Exception:
            # Fallback: console output
            print(f"\n⏰ {title}: {message}")

    def _run(self):
        while not self._stop.is_set():
            try:
                due = self.db.get_due_alarms(limit=50)
                for a in due:
                    msg = (a.get("title") or "").strip()
                    if not msg:
                        msg = "你有一个提醒"
                    fire_at = a.get("fire_at") or ""
                    if fire_at:
                        body = f"{msg}\n时间: {fire_at}"
                    else:
                        body = msg
                    self._notify("TODO Pro 提醒", body)
                    # mark done
                    try:
                        self.db.mark_alarm_done(int(a.get("id")))
                    except Exception:
                        # avoid crashing; will retry next poll
                        pass
            except Exception:
                pass
            # sleep in small steps to allow quick stop
            for _ in range(max(1, self.poll_seconds)):
                if self._stop.is_set():
                    break
                time.sleep(1)
