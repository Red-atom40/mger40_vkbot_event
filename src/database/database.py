import sqlite3

from domain.quiz import Quiz
from tools.encryption import Encryptor


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

    def save_application(self, quiz: Quiz) -> None:
        """
        Сохраняет заявку в БД; номер паспорта шифруется перед записью\n
        При повторном вызове с тем же vk_id запись перезаписывается (INSERT OR REPLACE)
        """

        encrypted_passport = self.encryptor.encrypt(quiz.passport_number)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO applications (
                    vk_id, fio, birth_date, region, city, street, house,
                    passport_number, passport_issued_by, passport_issue_date,
                    phone, contact_info, education_level, is_member,
                    previous_organizations, study_or_work_place, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    quiz.vk_id,
                    quiz.fio,
                    quiz.birth_date,
                    quiz.region,
                    quiz.city,
                    quiz.street,
                    quiz.house,
                    encrypted_passport,
                    quiz.passport_issued_by,
                    quiz.passport_issue_date,
                    quiz.phone,
                    quiz.contact_info,
                    quiz.education_level,
                    quiz.is_member,
                    quiz.previous_organizations,
                    quiz.study_or_work_place,
                    quiz.created_at,
                ),
            )
