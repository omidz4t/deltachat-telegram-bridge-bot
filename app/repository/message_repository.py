import sqlite3
from typing import List, Optional
from models.message import Message

class MessageRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save(self, msg: Message):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                REPLACE INTO messages (telegram_msg_id, dc_msg_id, dc_chat_id, text, media_path, media_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (msg.telegram_msg_id, msg.dc_msg_id, msg.dc_chat_id, msg.text, msg.media_path, msg.media_type))

    def get_latest(self, chat_id: int, limit: int = 10) -> List[Message]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT telegram_msg_id, dc_msg_id, dc_chat_id, text, media_path, media_type, id
                FROM messages
                WHERE dc_chat_id = ? AND dc_msg_id IS NOT NULL
                ORDER BY telegram_msg_id DESC
                LIMIT ?
            """, (chat_id, limit))
            rows = cur.fetchall()
            messages = []
            for row in rows:
                messages.append(Message(
                    telegram_msg_id=row[0],
                    dc_msg_id=row[1],
                    dc_chat_id=row[2],
                    text=row[3],
                    media_path=row[4],
                    media_type=row[5],
                    id=row[6]
                ))
            messages.reverse()
            return messages

    def get_by_telegram_id(self, telegram_msg_id: int, dc_chat_id: int) -> Optional[Message]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("""
                SELECT telegram_msg_id, dc_msg_id, dc_chat_id, text, media_path, media_type, id
                FROM messages
                WHERE telegram_msg_id = ? AND dc_chat_id = ?
                LIMIT 1
            """, (telegram_msg_id, dc_chat_id))
            row = cur.fetchone()
            if row:
                return Message(
                    telegram_msg_id=row[0],
                    dc_msg_id=row[1],
                    dc_chat_id=row[2],
                    text=row[3],
                    media_path=row[4],
                    media_type=row[5],
                    id=row[6]
                )
            return None
