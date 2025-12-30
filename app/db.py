import sqlite3
from pathlib import Path

def init_db(db_path: str):
    Path(db_path).parent.mkdir(exist_ok=True, parents=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                accid INTEGER,
                chat_id INTEGER,
                name TEXT,
                link TEXT,
                PRIMARY KEY (accid, chat_id)
            )
        """)
        # Added dc_msg_id to store Delta Chat database ID
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_msg_id INTEGER,
                dc_msg_id INTEGER,
                text TEXT,
                media_path TEXT,
                media_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: if dc_msg_id doesn't exist, add it
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN dc_msg_id INTEGER")
        except sqlite3.OperationalError:
            pass # already exists
