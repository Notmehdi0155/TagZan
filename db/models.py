from .connection import get_connection

conn = get_connection()
cur = conn.cursor()

def setup_tables():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS videos (
        code TEXT PRIMARY KEY,
        file_id TEXT NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS forced_channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        link TEXT UNIQUE NOT NULL
    )""")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        joined_at INTEGER,
        start_count INTEGER DEFAULT 0,
        last_start INTEGER
    )""")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_last_start ON users (last_start);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_joined_at ON users (joined_at);")
    conn.commit()
