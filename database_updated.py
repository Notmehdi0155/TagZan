
import sqlite3
import time
from threading import Lock

# ---------- اتصال به دیتابیس ----------
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()
db_lock = Lock()

# ---------- ساخت جدول‌ها ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT,
    backup_chat_id INTEGER,
    backup_msg_id INTEGER
)
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

# ---------- توابع امن ----------

def safe_execute(query, args=(), fetch=False):
    with db_lock:
        try:
            cur.execute(query, args)
            if fetch:
                return cur.fetchall()
            conn.commit()
        except Exception as e:
            print("[!] خطا در اجرای کوئری:", e)
            return None

# ---------- مدیریت فایل‌ها ----------

def save_file(code, file_id=None, backup_chat_id=None, backup_msg_id=None):
    try:
        safe_execute(
            "INSERT OR REPLACE INTO videos (code, file_id, backup_chat_id, backup_msg_id) VALUES (?, ?, ?, ?)",
            (code, file_id, backup_chat_id, backup_msg_id)
        )
        print(f"[+] فایل ذخیره شد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_file(code):
    try:
        result = safe_execute(
            "SELECT file_id, backup_chat_id, backup_msg_id FROM videos WHERE code = ?",
            (code,), fetch=True
        )
        return result[0] if result else None
    except Exception as e:
        print("[!] خطا در دریافت فایل:", e)
        return None

# ---------- مدیریت کانال‌ها ----------

def add_channel(link):
    safe_execute(
        "INSERT OR IGNORE INTO forced_channels (link) VALUES (?)",
        (link,)
    )
    print(f"[+] کانال اضافه شد: {link}")

def remove_channel(link):
    safe_execute(
        "DELETE FROM forced_channels WHERE link = ?",
        (link,)
    )
    print(f"[-] کانال حذف شد: {link}")

def get_channels():
    try:
        result = safe_execute("SELECT link FROM forced_channels", fetch=True)
        return [row[0] for row in result] if result else []
    except Exception as e:
        print("[!] خطا در دریافت لیست کانال‌ها:", e)
        return []

# ---------- مدیریت کاربران ----------

def add_user(user_id):
    ts = int(time.time())
    safe_execute(
        "INSERT OR IGNORE INTO users (id, joined_at) VALUES (?, ?)",
        (user_id, ts)
    )

def update_user_start(user_id):
    ts = int(time.time())
    safe_execute(
        "UPDATE users SET start_count = start_count + 1, last_start = ? WHERE id = ?",
        (ts, user_id)
    )
