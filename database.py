import sqlite3

conn = sqlite3.connect("files.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id TEXT,
    code TEXT,
    file_type TEXT
)
""")
conn.commit()

def save_file(file_id, code, file_type):
    c.execute("INSERT INTO files (file_id, code, file_type) VALUES (?, ?, ?)", (file_id, code, file_type))
    conn.commit()

def save_files(file_id, code, file_type):  # سازگار با utils
    save_file(file_id, code, file_type)

def get_files(code):
    c.execute("SELECT file_id, file_type FROM files WHERE code = ?", (code,))
    return c.fetchall()