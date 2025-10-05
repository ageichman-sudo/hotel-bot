import sqlite3
from pathlib import Path
from bot.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id TEXT,
            room_name TEXT,
            description TEXT NOT NULL,
            assignee TEXT,
            status TEXT DEFAULT 'pending',
            deadline TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pms_booking_id TEXT
        )
    """)
    conn.commit()
    conn.close()

def create_task(description: str, assignee: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (description, assignee) VALUES (?, ?)", (description, assignee))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def get_active_tasks(limit: int = 20):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, description, room_name FROM tasks WHERE status != 'done' ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def complete_task(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated

def get_task_room_id(task_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT room_id FROM tasks WHERE id = ?", (task_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None
