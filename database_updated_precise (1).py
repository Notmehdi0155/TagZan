import sqlite3
import time

# اتصال به دیتابیس
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# ---------- ساخت جدول‌ها ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    backup_chat_id INTEGER,
    backup_msg_id INTEGER
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS forced_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    joined_at INTEGER,
    start_count INTEGER DEFAULT 0,
    last_start INTEGER
)
""")

conn.commit()

# ---------- مدیریت فایل‌ها ----------

def save_file(file_id, code, backup_chat_id=None, backup_msg_id=None):
    try:
        cur.execute("INSERT OR REPLACE INTO videos (code, file_id, backup_chat_id, backup_msg_id) VALUES (?, ?, ?, ?)", (code, file_id, backup_chat_id, backup_msg_id))
        conn.commit()
        print(f"[+] فایل ذخیره شد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_file(code):
    try:
        cur.execute("SELECT file_id, backup_chat_id, backup_msg_id FROM videos WHERE code = ?", (code,))
        row = cur.fetchone()
        return row if row else None
    except Exception as e:
        print("[!] خطا در دریافت فایل:", e)
        return None

# ---------- مدیریت کانال‌ها ----------

def add_channel(link):
    try:
        cur.execute("INSERT OR IGNORE INTO forced_channels (link) VALUES (?)", (link,))
        conn.commit()
        print(f"[+] کانال اضافه شد: {link}")
    except Exception as e:
        print("[!] خطا در افزودن کانال:", e)

def remove_channel(link):
    try:
        cur.execute("DELETE FROM forced_channels WHERE link = ?", (link,))
        conn.commit()
        print(f"[-] کانال حذف شد: {link}")
    except Exception as e:
        print("[!] خطا در حذف کانال:", e)

def get_channels():
    try:
        cur.execute("SELECT link FROM forced_channels")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کانال‌ها:", e)
        return []

# ---------- مدیریت کاربران ----------

def save_user_id(user_id):
    """ثبت یا بروزرسانی کاربر در جدول users"""
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
        print(f"[+] کاربر ثبت شد: {user_id}")
    except Exception as e:
        print("[!] خطا در ذخیره آیدی:", e)

def get_all_user_ids():
    try:
        cur.execute("SELECT id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کاربران:", e)
        return []

# ---------- آمارگیری ----------

def get_active_users(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
        return cur.fetchone()[0]
    except Exception as e:
        print("[!] خطا در دریافت کاربران فعال:", e)
        return 0

def get_start_count(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= ?", (since,))
        return cur.fetchone()[0]
    except Exception as e:
        print("[!] خطا در دریافت تعداد استارت:", e)
        return 0

def get_user_stats():
    try:
        now = int(time.time())
        cur.execute("SELECT COUNT(*) FROM users")
        total = cur.fetchone()[0]

        def count_since(seconds):
            since = now - seconds
            cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
            joined = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= ?", (since,))
            starts = cur.fetchone()[0]
            return joined, starts

        hour_join, hour_start = count_since(3600)
        day_join, day_start = count_since(86400)
        week_join, week_start = count_since(7 * 86400)
        month_join, month_start = count_since(30 * 86400)

        return {
            "total": total,
            "hour_join": hour_join, "hour_start": hour_start,
            "day_join": day_join, "day_start": day_start,
            "week_join": week_join, "week_start": week_start,
            "month_join": month_join, "month_start": month_start
        }

    except Exception as e:
        print("[!] خطا در آمارگیری:", e)
        return {}
