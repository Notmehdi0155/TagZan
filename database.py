
import sqlite3
import time
import requests
from config import BOT_TOKEN, BACKUP_CHANNEL_ID

# ---------- اتصال به دیتابیس ----------
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

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

# ---------- مدیریت فایل‌ها ----------

def save_file(file_id, code):
    try:
        # ارسال فایل به کانال پشتیبان
        send_url = f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage"
        payload = {
            "chat_id": BACKUP_CHANNEL_ID,
            "from_chat_id": BACKUP_CHANNEL_ID,
            "message_id": file_id,  # فرض بر اینه file_id از پیام تلگرام گرفته شده
            "caption": f"file_code: {code}",
            "parse_mode": "HTML"
        }
        # اگر file_id از نوع فایل است نه پیام، باید sendDocument استفاده شود
        send_doc_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        r = requests.post(send_doc_url, data={
            "chat_id": BACKUP_CHANNEL_ID,
            "document": file_id,
            "caption": f"file_code: {code}"
        }).json()

        backup_chat_id = BACKUP_CHANNEL_ID
        backup_msg_id = r.get("result", {}).get("message_id")

        # ذخیره در دیتابیس
        cur.execute(
            "INSERT OR REPLACE INTO videos (code, file_id, backup_chat_id, backup_msg_id) VALUES (?, ?, ?, ?)",
            (code, file_id, backup_chat_id, backup_msg_id)
        )
        conn.commit()
        print(f"[+] فایل ذخیره شد: {code} (msg_id: {backup_msg_id})")
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
    try:
        cur.execute("INSERT OR IGNORE INTO users (id, joined_at) VALUES (?, ?)", (user_id, int(time.time())))
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

def get_active_users():
    try:
        one_hour_ago = int(time.time()) - 3600
        cur.execute("SELECT id FROM users WHERE last_start >= ?", (one_hour_ago,))
        return [row[0] for row in cur.fetchall()]
    except Exception as e:
        print("[!] خطا در دریافت کاربران فعال:", e)
        return []

def get_start_count():
    try:
        cur.execute("SELECT SUM(start_count) FROM users")
        return cur.fetchone()[0] or 0
    except Exception as e:
        print("[!] خطا در شمارش استارت:", e)
        return 0


# ---------- ارسال فایل از کانال بکاپ ----------

def send_file_from_backup(code, user_id):
    try:
        result = get_file(code)
        if not result:
            print(f"[!] هیچ فایلی با این کد یافت نشد: {code}")
            return False

        file_id, backup_chat_id, backup_msg_id = result

        if not backup_chat_id or not backup_msg_id:
            print(f"[!] اطلاعات پیام پشتیبان ناقص است برای کد: {code}")
            return False

        # ارسال فایل با copyMessage از کانال به کاربر
        copy_url = f"https://api.telegram.org/bot{BOT_TOKEN}/copyMessage"
        payload = {
            "chat_id": user_id,
            "from_chat_id": backup_chat_id,
            "message_id": backup_msg_id
        }
        r = requests.post(copy_url, data=payload).json()

        if r.get("ok"):
            print(f"[+] فایل از بکاپ ارسال شد برای کاربر: {user_id}")
            return True
        else:
            print(f"[!] خطا در ارسال از بکاپ:", r)
            return False

    except Exception as e:
        print("[!] خطا در ارسال فایل از بکاپ:", e)
        return False
