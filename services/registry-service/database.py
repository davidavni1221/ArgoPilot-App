import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "registry.db"

def get_db():
    # mode=rw: אם הקובץ חסר, להיכשל במקום ליצור מסד ריק בשקט
    conn = sqlite3.connect(DB_PATH.as_uri() + "?mode=rw", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # SQLite לא אוכף מפתחות זרים כברירת מחדל; בלי זה אפשר ליצור חלקה לחווה שלא קיימת
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()