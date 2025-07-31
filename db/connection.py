import sqlite3

def get_connection():
    conn = sqlite3.connect("data/videos.db", check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn
