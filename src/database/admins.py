import sqlite3
from datetime import datetime


_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    vk_id       TEXT PRIMARY KEY,
    added_by    TEXT NOT NULL,
    added_at    REAL NOT NULL
);
"""


class AdminRepository:
    """
        Хранит список администраторов в таблице admins.\n
        Суперадмины задаются через config.json и не могут быть удалены через бота
    """

    def __init__(self, db_path: str, superadmin_ids: list[str]) -> None:
        self.db_path = db_path
        self._superadmins: frozenset[str] = frozenset(superadmin_ids)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    def is_admin(self, vk_id: str) -> bool:
        if vk_id in self._superadmins:
            return True
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM admins WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def add(self, vk_id: str, added_by: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO admins (vk_id, added_by, added_at) VALUES (?, ?, ?)",
                (vk_id, added_by, datetime.now().timestamp()),
            )

    def remove(self, vk_id: str) -> bool:
        """
            Удаляет администратора. Возвращает False если vk_id — суперадмин
        """

        if vk_id in self._superadmins:
            return False
        with self._connect() as conn:
            conn.execute("DELETE FROM admins WHERE vk_id = ?", (vk_id,))
        return True

    def list_all(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT vk_id FROM admins ORDER BY added_at"
            ).fetchall()
        db_admins = [row["vk_id"] for row in rows]
        # Суперадмины идут первыми
        return sorted(self._superadmins) + [a for a in db_admins if a not in self._superadmins]
