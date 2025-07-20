import sqlite3
import time

conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# ---------- ساخت جدول‌ها در صورت نبود ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
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
    joined_at INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS starts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    timestamp INTEGER
)
""")

conn.commit()

# ---------- مدیریت فایل‌ها ----------

def save_file(file_id, code):
    try:
        cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        print(f"[+] فایل ذخیره شد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_file(code):
    try:
        cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
        row = cur.fetchone()
        return row[0] if row else None
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
    """ثبت اولین ورود کاربر به ربات (برای ارسال همگانی)"""
    try:
        now = int(time.time())
        cur.execute("INSERT OR IGNORE INTO users (id, joined_at) VALUES (?, ?)", (user_id, now))
        conn.commit()
        print(f"[+] کاربر ذخیره شد: {user_id}")
    except Exception as e:
        print("[!] خطا در ذخیره آیدی:", e)

def get_all_user_ids():
    try:
        cur.execute("SELECT id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کاربران:", e)
        return []

# ---------- ثبت و آمار استارت ----------

def log_start(user_id):
    """ثبت استارت ربات"""
    try:
        now = int(time.time())
        cur.execute("INSERT INTO starts (user_id, timestamp) VALUES (?, ?)", (user_id, now))
        conn.commit()
        print(f"[+] استارت ثبت شد: {user_id}")
    except Exception as e:
        print("[!] خطا در ثبت استارت:", e)

def get_user_stats(since_seconds_ago):
    """تعداد کاربران جدید از زمان مشخص‌شده تاکنون"""
    since = int(time.time()) - since_seconds_ago
    cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
    return cur.fetchone()[0]

def get_start_stats(since_seconds_ago):
    """تعداد استارت‌های ثبت‌شده از زمان مشخص‌شده تاکنون"""
    since = int(time.time()) - since_seconds_ago
    cur.execute("SELECT COUNT(*) FROM starts WHERE timestamp >= ?", (since,))
    return cur.fetchone()[0]
