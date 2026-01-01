import sqlite3

class AdminRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def add_admin(self, contact_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR IGNORE INTO admins (contact_id) VALUES (?)", (contact_id,))

    def is_admin(self, contact_id: int) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT 1 FROM admins WHERE contact_id = ?", (contact_id,))
            return cur.fetchone() is not None

    def remove_admin(self, contact_id: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM admins WHERE contact_id = ?", (contact_id,))
