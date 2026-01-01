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

    def get_by_accid(self, accid: int) -> list[Channel]:
        channels = []
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT accid, chat_id, name, link, photo_enabled, photo_message, video_enabled, video_message, enabled FROM channels WHERE accid = ?", (accid,))
            for row in cur.fetchall():
                channels.append(Channel(
                    accid=row[0], 
                    chat_id=row[1], 
                    name=row[2], 
                    link=row[3], 
                    photo_enabled=bool(row[4]),
                    photo_message=row[5],
                    video_enabled=bool(row[6]),
                    video_message=row[7],
                    enabled=bool(row[8])
                ))
        return channels

    def save(self, channel: Channel):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO channels (accid, chat_id, name, link, photo_enabled, photo_message, video_enabled, video_message, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (channel.accid, channel.chat_id, channel.name, channel.link, 
                  int(channel.photo_enabled), channel.photo_message, 
                  int(channel.video_enabled), channel.video_message, int(channel.enabled)))

    def update_enabled(self, accid: int, chat_id: int, enabled: bool):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE channels SET enabled = ? WHERE accid = ? AND chat_id = ?", (int(enabled), accid, chat_id))

    def get_by_chat_id(self, accid: int, chat_id: int) -> Optional[Channel]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT accid, chat_id, name, link, photo_enabled, photo_message, video_enabled, video_message, enabled FROM channels WHERE accid = ? AND chat_id = ?", (accid, chat_id))
            row = cur.fetchone()
            if row:
                return Channel(
                    accid=row[0], 
                    chat_id=row[1], 
                    name=row[2], 
                    link=row[3], 
                    photo_enabled=bool(row[4]),
                    photo_message=row[5],
                    video_enabled=bool(row[6]),
                    video_message=row[7],
                    enabled=bool(row[8])
                )
        return None
