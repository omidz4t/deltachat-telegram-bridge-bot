import sqlite3
from pathlib import Path
from typing import Optional
from models.channel import Channel

class ChannelRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    accid INTEGER PRIMARY KEY,
                    chat_id INTEGER,
                    name TEXT,
                    link TEXT
                )
            """)

    def get_by_accid(self, accid: int) -> Optional[Channel]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT accid, chat_id, name, link FROM channels WHERE accid = ?", (accid,))
            row = cur.fetchone()
            if row:
                return Channel(accid=row[0], chat_id=row[1], name=row[2], link=row[3])
        return None

    def save(self, channel: Channel):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO channels (accid, chat_id, name, link)
                VALUES (?, ?, ?, ?)
            """, (channel.accid, channel.chat_id, channel.name, channel.link))
