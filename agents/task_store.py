"""SQLite-backed task storage: the 'tools' of the task agent act on this."""
import sqlite3
from datetime import datetime
from typing import Optional

import config


class TaskStore:
    def __init__(self, path: Optional[str] = None):
        self.path = path or config.DB_PATH
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    owner TEXT NOT NULL DEFAULT 'me',
                    due_date TEXT,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    status TEXT NOT NULL DEFAULT 'open',
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL
                )"""
            )

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def add(self, title: str, owner: str = "me", due_date: Optional[str] = None, priority: str = "medium", source: str = "manual") -> dict:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO tasks (title, owner, due_date, priority, source, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (title, owner, due_date, priority, source, datetime.now().isoformat(timespec="seconds")),
            )
            row = c.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
        return dict(row)

    def list(self, status: str = "all", owner: Optional[str] = None) -> list[dict]:
        query, params = "SELECT * FROM tasks WHERE 1=1", []
        if status in ("open", "done"):
            query += " AND status = ?"
            params.append(status)
        if owner:
            query += " AND LOWER(owner) = LOWER(?)"
            params.append(owner)
        query += " ORDER BY COALESCE(due_date, '9999-12-31'), id"
        with self._conn() as c:
            return [dict(r) for r in c.execute(query, params).fetchall()]

    def complete(self, task_id: int) -> bool:
        with self._conn() as c:
            cur = c.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
            return cur.rowcount > 0

    def clear(self):
        with self._conn() as c:
            c.execute("DELETE FROM tasks")
