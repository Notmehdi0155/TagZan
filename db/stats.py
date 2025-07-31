import time
from .connection import get_connection

conn = get_connection()
cur = conn.cursor()

def get_active_users(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
        return cur.fetchone()[0]
    except Exception as e:
        print("[!] خطا در دریافت کاربران فعال:", e)
        return 0

def get_start_count(seconds):
    try:
        since = int(time.time()) - seconds
        cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= ?", (since,))
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
            cur.execute("SELECT COUNT(*) FROM users WHERE joined_at >= ?", (since,))
            joined = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM users WHERE last_start >= ?", (since,))
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
