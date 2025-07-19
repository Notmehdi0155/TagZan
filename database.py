import sqlite3

# اتصال به دیتابیس و ساخت جدول‌ها در صورت نبود
conn = sqlite3.connect("videos.db", check_same_thread=False)
cur = conn.cursor()

# جدول ویدیوها (برای لینک‌های تولید شده و فایل‌ها)
cur.execute("""
CREATE TABLE IF NOT EXISTS videos (
    code TEXT PRIMARY KEY,
    file_id TEXT NOT NULL
)
""")

# جدول لینک‌های عضویت اجباری
cur.execute("""
CREATE TABLE IF NOT EXISTS forced_channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link TEXT UNIQUE NOT NULL
)
""")

conn.commit()

# ذخیره فایل و کد اختصاصی
def save_file(file_id, code):
    print(f"Saving file_id: {file_id} with code: {code}")
    cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
    conn.commit()

# دریافت فایل با کد اختصاصی
def get_file(code):
    print(f"Getting file for code: {code}")
    cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
    row = cur.fetchone()
    if row:
        print(f"Found file_id: {row[0]} for code: {code}")
    else:
        print(f"No file found for code: {code}")
    return row[0] if row else None

# افزودن لینک عضویت اجباری
def add_forced_channel(link):
    try:
        cur.execute("INSERT OR IGNORE INTO forced_channels (link) VALUES (?)", (link,))
        conn.commit()
        return True
    except Exception as e:
        print("Error adding channel:", e)
        return False

# حذف لینک عضویت اجباری
def remove_forced_channel(link):
    try:
        cur.execute("DELETE FROM forced_channels WHERE link = ?", (link,))
        conn.commit()
        return True
    except Exception as e:
        print("Error removing channel:", e)
        return False

# دریافت همه لینک‌های عضویت اجباری
def get_forced_channels():
    cur.execute("SELECT link FROM forced_channels")
    return [row[0] for row in cur.fetchall()]
