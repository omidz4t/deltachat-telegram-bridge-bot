import sqlite3
from typing import List, Optional
from models.message import Message

class MessageRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, msg: Message):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages (telegram_msg_id, dc_msg_id, text, media_path, media_type)
                VALUES (?, ?, ?, ?, ?)
            """, (msg.telegram_msg_id, msg.dc_msg_id, msg.text, msg.media_path, msg.media_type))

    def get_latest(self, limit: int = 10) -> List[Message]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT telegram_msg_id, dc_msg_id, text, media_path, media_type, id
                FROM messages
                WHERE dc_msg_id IS NOT NULL
                ORDER BY id DESC
                LIMIT ?
            """, (limit,))
            rows = cur.fetchall()
            messages = []
            for row in rows:
                messages.append(Message(
                    telegram_msg_id=row[0],
                    dc_msg_id=row[1],
                    text=row[2],
                    media_path=row[3],
                    media_type=row[4],
                    id=row[5]
                ))
            messages.reverse()
            return messages

    def get_by_telegram_id(self, telegram_msg_id: int) -> Optional[Message]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT telegram_msg_id, dc_msg_id, text, media_path, media_type, id
                FROM messages
                WHERE telegram_msg_id = ?
                LIMIT 1
            """, (telegram_msg_id,))
            row = cur.fetchone()
            if row:
                return Message(
                    telegram_msg_id=row[0],
                    dc_msg_id=row[1],
                    text=row[2],
                    media_path=row[3],
                    media_type=row[4],
                    id=row[5]
                )
            return None
