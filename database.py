# database.py

import sqlite3
from datetime import datetime

conn = sqlite3.connect('data.db', check_same_thread=False)
c = conn.cursor()

# ساخت جدول کاربران
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    fullname TEXT,
    invited_by INTEGER,
    joined INTEGER DEFAULT 0,
    left INTEGER DEFAULT 0,
    join_time TEXT
)
''')
conn.commit()

def add_user(user_id, username, fullname, invited_by=None):
    c.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
    if not c.fetchone():
        c.execute('INSERT INTO users (user_id, username, fullname, invited_by, join_time) VALUES (?, ?, ?, ?, ?)',
                  (user_id, username, fullname, invited_by, datetime.utcnow().isoformat()))
        conn.commit()

def update_joined(user_id):
    c.execute('UPDATE users SET joined = 1, left = 0 WHERE user_id = ?', (user_id,))
    conn.commit()

def update_left(user_id):
    c.execute('UPDATE users SET left = 1 WHERE user_id = ?', (user_id,))
    conn.commit()

def get_user(user_id):
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return c.fetchone()

def get_all_joined_users():
    c.execute('SELECT user_id FROM users WHERE joined = 1')
    return c.fetchall()

def get_stats(user_id):
    c.execute('SELECT COUNT(*) FROM users WHERE invited_by = ? AND joined = 1', (user_id,))
    joined = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM users WHERE invited_by = ? AND left = 1', (user_id,))
    left = c.fetchone()[0]
    score = joined - left
    return joined, left, score

def get_top_inviters(limit=10):
    c.execute('SELECT invited_by FROM users WHERE joined = 1 AND invited_by IS NOT NULL')
    data = c.fetchall()
    stats = {}
    for (uid,) in data:
        stats[uid] = stats.get(uid, 0) + 1
    sorted_stats = sorted(stats.items(), key=lambda x: -x[1])[:limit]
    return sorted_stats
# ادامه فایل database.py

# ساخت جدول مسابقه برای ذخیره زمان شروع و مدت مسابقه (روز)
c.execute('''
CREATE TABLE IF NOT EXISTS competition (
    id INTEGER PRIMARY KEY,
    start_time TEXT,
    duration_days INTEGER
)
''')
conn.commit()

def set_competition(start_time, duration_days):
    # حذف رکورد قبلی (اگر بود) و اضافه کردن رکورد جدید
    c.execute('DELETE FROM competition')
    c.execute('INSERT INTO competition (start_time, duration_days) VALUES (?, ?)',
              (start_time.isoformat(), duration_days))
    conn.commit()

def get_competition():
    c.execute('SELECT start_time, duration_days FROM competition ORDER BY id DESC LIMIT 1')
    row = c.fetchone()
    if row:
        start_time_str, duration_days = row
        try:
            start_time = datetime.fromisoformat(start_time_str)
        except Exception:
            start_time = None
        return {'start_time': start_time, 'duration_days': duration_days}
    else:
        return None
