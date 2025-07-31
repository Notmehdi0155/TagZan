from .connection import get_connection

conn = get_connection()
cur = conn.cursor()

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
        print("[!] خطا در دریافت لیست کانال‌ها:", e)
        return []
