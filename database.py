
import sqlite3

# اتصال به دیتابیس (فایل در کنار پروژه ایجاد می‌شود)
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# ---------- ساخت جدول‌ها در صورت نبود ----------

# جدول فایل‌ها (چند فایل برای هر کد)
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_id TEXT NOT NULL
)
""")
cur.execute("""
CREATE INDEX IF NOT EXISTS idx_code ON videos (code)
""")
# جدول کانال‌های عضویت اجباری
cur.execute("""
CREATE TABLE IF NOT EXISTS forced_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE NOT NULL
)
""")
# جدول کاربران برای ارسال همگانی
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY
)
""")
conn.commit()

# ---------- مدیریت فایل‌ها ----------

def save_files(file_list, code):
    try:
        for file_type, file_id in file_list:
            cur.execute("INSERT INTO videos (code, file_type, file_id) VALUES (?, ?, ?)", (code, file_type, file_id))
        conn.commit()
        print(f"[+] {len(file_list)} فایل ذخیره شد برای کد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره فایل‌ها:", e)

def get_files(code):
    try:
        cur.execute("SELECT file_type, file_id FROM videos WHERE code = ?", (code,))
        return cur.fetchall()
    except Exception as e:
        print("[!] خطا در دریافت فایل‌ها:", e)
        return []

# ---------- مدیریت کانال‌ها ----------

def add_channel(link):
    try:
        cur.execute("INSERT OR IGNORE INTO forced_channels (link) VALUES (?)", (link,))
        conn.commit()
    except Exception as e:
        print("[!] خطا در افزودن کانال:", e)

def remove_channel(link):
    try:
        cur.execute("DELETE FROM forced_channels WHERE link = ?", (link,))
        conn.commit()
    except Exception as e:
        print("[!] خطا در حذف کانال:", e)
