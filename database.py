import sqlite3

# اتصال به دیتابیس (فایل در کنار پروژه ایجاد می‌شود)
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# ---------- ساخت جدول‌ها در صورت نبود ----------

# جدول فایل‌ها (کد اختصاصی → لیست فایل‌ها)
cur.execute("""
CREATE TABLE IF NOT EXISTS video_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    file_id TEXT NOT NULL
)
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

# ---------- مدیریت فایل‌ها (چندتایی) ----------

def save_files(file_ids, code):
    """ذخیره چند فایل برای یک کد"""
    try:
        for fid in file_ids:
            cur.execute("INSERT INTO video_files (code, file_id) VALUES (?, ?)", (code, fid))
        conn.commit()
        print(f"[+] {len(file_ids)} فایل برای کد {code} ذخیره شد")
    except Exception as e:
        print("[!] خطا در ذخیره فایل‌ها:", e)

def get_files(code):
    """دریافت همه فایل‌های مرتبط با کد"""
    try:
        cur.execute("SELECT file_id FROM video_files WHERE code = ?", (code,))
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت فایل‌ها:", e)
        return []

# ---------- مدیریت کانال‌های عضویت اجباری ----------

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

def get_channels():
    try:
        cur.execute("SELECT link FROM forced_channels")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت کانال‌ها:", e)
        return []

# ---------- مدیریت کاربران ----------

def save_user_id(user_id):
    try:
        cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        conn.commit()
    except Exception as e:
        print("[!] خطا در ذخیره کاربر:", e)

def get_all_user_ids():
    try:
        cur.execute("SELECT id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت کاربران:", e)
        return []
