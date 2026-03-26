import sqlite3
import os
import datetime

class TaskManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        # 任务表
        c.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                priority INTEGER DEFAULT 2,
                status TEXT DEFAULT 'pending',
                category TEXT DEFAULT '通用',
                deadline TEXT,
                remind_offset INTEGER DEFAULT 0,
                created_at DATETIME,
                completed_at DATETIME,
                updated_at DATETIME
            )
        """)
        
        # 用户配置表 (存储 昵称、身份、主题、语言)
        c.execute("""
            CREATE TABLE IF NOT EXISTS profile (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # 迁移检查
        try:
            c.execute("SELECT remind_offset FROM tasks LIMIT 1")
        except sqlite3.OperationalError:
            c.execute("ALTER TABLE tasks ADD COLUMN remind_offset INTEGER DEFAULT 0")
        
        conn.commit()
        conn.close()

    # --- 用户配置 (支持存取任意 Key) ---
    def get_profile(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT key, value FROM profile")
        data = {row['key']: row['value'] for row in c.fetchall()}
        conn.close()
        return data

    def update_profile_item(self, key, value):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("REPLACE INTO profile (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()

    def update_profile_batch(self, data_dict):
        """批量更新配置"""
        conn = self._get_conn()
        c = conn.cursor()
        for k, v in data_dict.items():
            c.execute("REPLACE INTO profile (key, value) VALUES (?, ?)", (k, v))
        conn.commit()
        conn.close()

    # --- 任务操作 ---
    def add_task(self, content, priority=2, category="General", deadline=None, remind_offset=0):
        conn = self._get_conn()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c = conn.cursor()
        c.execute(
            "INSERT INTO tasks (content, priority, category, deadline, remind_offset, created_at, updated_at, status) VALUES (?,?,?,?,?,?,?, 'pending')",
            (content, priority, category, deadline, remind_offset, now, now)
        )
        tid = c.lastrowid
        conn.commit()
        conn.close()
        return tid

    def get_tasks(self):
        conn = self._get_conn()
        c = conn.cursor()
        c.execute("SELECT * FROM tasks ORDER BY status ASC, priority DESC, id DESC")
        items = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"items": items}

    def update_status(self, tid, status):
        conn = self._get_conn()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        completed_at = now if status == 'completed' else None
        conn.execute("UPDATE tasks SET status=?, completed_at=?, updated_at=? WHERE id=?", (status, completed_at, now, tid))
        conn.commit()
        conn.close()
    
    def delete_task(self, tid):
        conn = self._get_conn()
        conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
        conn.commit()
        conn.close()

    # --- 详细统计逻辑 (满足需求) ---
    def get_star_stats(self):
        conn = self._get_conn()
        c = conn.cursor()
        
        # 基础统计
        def count(where_sql=""):
            sql = "SELECT COUNT(*) FROM tasks WHERE status='completed'"
            if where_sql: sql += f" AND {where_sql}"
            c.execute(sql)
            return c.fetchone()[0]

        total = count()
        week = count("strftime('%Y-%W', completed_at) = strftime('%Y-%W', 'now')")
        
        # 分类统计 (Work, Study, Life...)
        c.execute("SELECT category, COUNT(*) FROM tasks WHERE status='completed' GROUP BY category")
        by_cat = {row[0]: row[1] for row in c.fetchall()}

        # 优先级统计 (High=3, Med=2, Low=1)
        c.execute("SELECT priority, COUNT(*) FROM tasks WHERE status='completed' GROUP BY priority")
        p_raw = {row[0]: row[1] for row in c.fetchall()}
        by_prio = {
            "high": p_raw.get(3, 0),
            "med": p_raw.get(2, 0),
            "low": p_raw.get(1, 0)
        }

        conn.close()
        return {
            "total": total,
            "week": week,
            "by_category": by_cat,
            "by_priority": by_prio
        }