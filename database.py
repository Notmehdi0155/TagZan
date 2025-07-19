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
