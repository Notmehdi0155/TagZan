import time
from .connection import get_connection

conn = get_connection()
cur = conn.cursor()

def save_user_id(user_id):
    try:
        now = int(time.time())
        cur.execute("""
            INSERT INTO users (id, joined_at, start_count, last_start)
            VALUES (?, ?, 1, ?)
            ON CONFLICT(id) DO UPDATE SET
                start_count = start_count + 1,
                last_start = excluded.last_start
        """, (user_id, now, now))
        conn.commit()
    except Exception as e:
        print("[!] خطا در ذخیره آیدی:", e)

def get_all_user_ids():
    try:
        cur.execute("SELECT id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کاربران:", e)
        return []
