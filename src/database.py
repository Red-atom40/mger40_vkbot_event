import sqlite3
from datetime import datetime

from encryption import Encryptor


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    vk_id                   TEXT PRIMARY KEY,
    fio                     TEXT NOT NULL,
    birth_date              TEXT NOT NULL,
    region                  TEXT NOT NULL,
    city                    TEXT NOT NULL,
    street                  TEXT NOT NULL,
    house                   TEXT NOT NULL,
    passport_number         TEXT NOT NULL,
    passport_issued_by      TEXT NOT NULL,
    passport_issue_date     TEXT NOT NULL,
    phone                   TEXT NOT NULL,
    contact_info            TEXT NOT NULL,
    education_level         TEXT NOT NULL,
    is_member               TEXT NOT NULL,
    previous_organizations  TEXT NOT NULL,
    study_or_work_place     TEXT NOT NULL,
    created_at              REAL NOT NULL
);
"""


class Database:
    """
        Репозиторий заявок: создаёт таблицу, сохраняет и проверяет записи\n
        Паспортные данные шифруются через Encryptor перед записью
    """

    def __init__(self, db_path: str, encryptor: Encryptor) -> None:
        """
            Открывает (или создаёт) базу данных и инициализирует таблицу
        """

        self.db_path = db_path
        self.encryptor = encryptor
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        """
            Открывает соединение с SQLite
        """

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """
            Создаёт таблицу applications, если она ещё не существует
        """

        with self._connect() as conn:
            conn.execute(CREATE_TABLE_SQL)

    def has_application(self, vk_id: str) -> bool:
        """
            Возвращает True, если заявка от пользователя с данным vk_id уже есть
        """

        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM applications WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def save_application(self, answers: dict, vk_id: str) -> None:
        """
        Сохраняет заявку в БД; номер паспорта шифруется перед записью\n
        При повторном вызове с тем же vk_id запись перезаписывается (INSERT OR REPLACE)
        """

        encrypted_passport = self.encryptor.encrypt(answers["passport_number"])

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO applications VALUES (
                    :vk_id, :fio, :birth_date, :region, :city, :street, :house,
                    :passport_number, :passport_issued_by, :passport_issue_date,
                    :phone, :contact_info, :education_level, :is_member,
                    :previous_organizations, :study_or_work_place, :created_at
                )
                """,
                {
                    "vk_id": vk_id,
                    "fio": answers["fio"],
                    "birth_date": answers["birth_date"],
                    "region": answers["region"],
                    "city": answers["city"],
                    "street": answers["street"],
                    "house": answers["house"],
                    "passport_number": encrypted_passport,
                    "passport_issued_by": answers["passport_issued_by"],
                    "passport_issue_date": answers["passport_issue_date"],
                    "phone": answers["phone"],
                    "contact_info": answers["contact_info"],
                    "education_level": answers["education_level"],
                    "is_member": answers["is_member"],
                    "previous_organizations": answers["previous_organizations"],
                    "study_or_work_place": answers["study_or_work_place"],
                    "created_at": datetime.now().timestamp(),
                },
            )
