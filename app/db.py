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
                photo_enabled INTEGER DEFAULT 1,
                photo_message TEXT DEFAULT '[Photo]',
                video_enabled INTEGER DEFAULT 1,
                video_message TEXT DEFAULT '[Video]',
                enabled INTEGER DEFAULT 1,
                PRIMARY KEY (accid, chat_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                contact_id INTEGER PRIMARY KEY
            )
        """)
        # Added dc_msg_id and dc_chat_id to store Delta Chat database ID and chat association
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_msg_id INTEGER,
                dc_msg_id INTEGER,
                dc_chat_id INTEGER,
                text TEXT,
                media_path TEXT,
                media_type TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Migration: ensure telegram_msg_id + dc_chat_id is indexed and unique
        conn.execute("DROP INDEX IF EXISTS idx_messages_tgid")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_tgid_chat ON messages(dc_chat_id, telegram_msg_id)")
        
        # Migration: if dc_msg_id doesn't exist, add it
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN dc_msg_id INTEGER")
        except sqlite3.OperationalError:
            pass # already exists

        # Migration: if dc_chat_id doesn't exist, add it
        try:
            conn.execute("ALTER TABLE messages ADD COLUMN dc_chat_id INTEGER")
        except sqlite3.OperationalError:
            pass # already exists

        # Create index for dc_chat_id after ensuring column exists
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_chatid ON messages(dc_chat_id)")

        # Migration: if photo_enabled doesn't exist, add its set
        try:
            conn.execute("ALTER TABLE channels ADD COLUMN photo_enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE channels ADD COLUMN photo_message TEXT DEFAULT '[Photo]'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE channels ADD COLUMN video_enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE channels ADD COLUMN video_message TEXT DEFAULT '[Video]'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE channels ADD COLUMN enabled INTEGER DEFAULT 1")
        except sqlite3.OperationalError:
            pass
