import psycopg2
from psycopg2.extras import RealDictCursor
import time

# اتصال به دیتابیس PostgreSQL
conn = psycopg2.connect(
    dbname="DB_NAME",
    user="DB_USER",
    password="DB_PASSWORD",
    host="DB_HOST",
    port="5432"  # یا پورت دیتابیست
)
cur = conn.cursor()

# ---------- ساخت جدول‌ها ----------

cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS forced_channels (
    id SERIAL PRIMARY KEY,
    link TEXT UNIQUE NOT NULL
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY,
    joined_at BIGINT,
    start_count INTEGER DEFAULT 0,
    last_start BIGINT
)
""")

conn.commit()

# ---------- مدیریت فایل‌ها ----------

def save_file(file_id, code):
    try:
        cur.execute("""
            INSERT INTO videos (code, file_id)
            VALUES (%s, %s)
            ON CONFLICT (code) DO UPDATE SET file_id = EXCLUDED.file_id
        """, (code, file_id))
        conn.commit()
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_file(code):
    try:
        cur.execute("SELECT file_id FROM videos WHERE code = %s", (code,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        print("[!] خطا در دریافت فایل:", e)
        return None

# ---------- مدیریت کانال‌ها ----------

def add_channel(link):
    try:
        cur.execute("INSERT INTO forced_channels (link) VALUES (%s) ON CONFLICT DO NOTHING", (link,))
        conn.commit()
    except Exception as e:
        print("[!] خطا در افزودن کانال:", e)

def remove_channel(link):
    try:
        cur.execute("DELETE FROM forced_channels WHERE link = %s", (link,))
        conn.commit()
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
    now = int(time.time())
    try:
        cur.execute("""
            INSERT INTO users (id, joined_at, start_count, last_start)
            VALUES (%s, %s, 1, %s)
            ON CONFLICT (id) DO UPDATE SET
                start_count = users.start_count + 1,
                last_start = EXCLUDED.last_start
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

# ---------- آمارگیری ----------

def get_active_users(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= %s", (since,))
        return cur.fetchone()[0]
    except Exception as e:
        print("[!] خطا در دریافت کاربران فعال:", e)
        return 0

def get_start_count(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= %s", (since,))
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
            cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= %s", (since,))
            joined = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= %s", (since,))
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
