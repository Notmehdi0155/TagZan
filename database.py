import sqlite3

# اتصال به دیتابیس (فایل در کنار پروژه ایجاد می‌شود)
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# ---------- ساخت جدول‌ها در صورت نبود ----------

# جدول ویدیوها (کد اختصاصی → file_id)
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
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

# ---------- مدیریت فایل‌ها ----------

def save_file(file_id, code):
    """ذخیره یک فایل با کد اختصاصی در جدول ویدیوها"""
    try:
        cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        print(f"[+] فایل ذخیره شد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_file(code):
    """دریافت file_id با استفاده از کد اختصاصی"""
    try:
        cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        print("[!] خطا در دریافت فایل:", e)
        return None

# ---------- مدیریت کانال‌های عضویت اجباری ----------

def add_channel(link):
    """افزودن لینک کانال به لیست عضویت اجباری"""
    try:
        cur.execute("INSERT OR IGNORE INTO forced_channels (link) VALUES (?)", (link,))
        conn.commit()
        print(f"[+] کانال اضافه شد: {link}")
    except Exception as e:
        print("[!] خطا در افزودن کانال:", e)

def remove_channel(link):
    """حذف لینک کانال از لیست عضویت اجباری"""
    try:
        cur.execute("DELETE FROM forced_channels WHERE link = ?", (link,))
        conn.commit()
        print(f"[-] کانال حذف شد: {link}")
    except Exception as e:
        print("[!] خطا در حذف کانال:", e)

def get_channels():
    """دریافت همه لینک‌های ثبت شده کانال‌های عضویت اجباری"""
    try:
        cur.execute("SELECT link FROM forced_channels")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کانال‌ها:", e)
        return []

# ---------- مدیریت کاربران برای ارسال همگانی ----------

def save_user_id(user_id):
    """ذخیره آیدی کاربر برای ارسال همگانی"""
    try:
        cur.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        conn.commit()
        print(f"[+] کاربر ذخیره شد: {user_id}")
    except Exception as e:
        print("[!] خطا در ذخیره آیدی:", e)

def get_all_user_ids():
    """دریافت همه آیدی‌های ثبت شده کاربران"""
    try:
        cur.execute("SELECT id FROM users")
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت لیست کاربران:", e)
        return []



# ---------- مجموعه فایل‌ها ----------

# جدول مجموعه‌ها (code → cover, caption)
cur.execute("""
CREATE TABLE IF NOT EXISTS collections (
    code TEXT PRIMARY KEY,
    cover_id TEXT,
    caption TEXT
)
""")

# جدول فایل‌های مجموعه (code → file_id)
cur.execute("""
CREATE TABLE IF NOT EXISTS collection_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    file_id TEXT NOT NULL
)
""")

conn.commit()

def save_collection(code, files, cover_id=None, caption=None):
    try:
        cur.execute("INSERT OR REPLACE INTO collections (code, cover_id, caption) VALUES (?, ?, ?)",
                    (code, cover_id, caption))
        for file_id in files:
            cur.execute("INSERT INTO collection_files (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
        print(f"[+] مجموعه فایل‌ها ذخیره شد: {code}")
    except Exception as e:
        print("[!] خطا در ذخیره مجموعه:", e)

def get_collection(code):
    try:
        cur.execute("SELECT cover_id, caption FROM collections WHERE code = ?", (code,))
        meta = cur.fetchone()
        if not meta:
            return None
        cur.execute("SELECT file_id FROM collection_files WHERE code = ?", (code,))
        files = [row[0] for row in cur.fetchall()]
        return {
            "cover_id": meta[0],
            "caption": meta[1],
            "files": files
        }
    except Exception as e:
        print("[!] خطا در دریافت مجموعه:", e)
        return None
