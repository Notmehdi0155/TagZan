from .connection import get_connection
conn = get_connection()
cur = conn.cursor()

def save_video(code, file_id):
    try:
        cur.execute("INSERT OR REPLACE INTO videos (code, file_id) VALUES (?, ?)", (code, file_id))
        conn.commit()
    except Exception as e:
        print("[!] خطا در ذخیره فایل:", e)

def get_video(code):
    try:
        cur.execute("SELECT file_id FROM videos WHERE code = ?", (code,))
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        print("[!] خطا در دریافت فایل:", e)
        return None
