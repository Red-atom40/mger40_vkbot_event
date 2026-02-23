import sqlite3
import threading
from dataclasses import dataclass
from datetime import date, datetime

from domain.quiz import Quiz
from security.encryption import Encryptor


_CREATE_APPLICATIONS_SQL = """
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

_CREATE_ADMINS_SQL = """
CREATE TABLE IF NOT EXISTS admins (
    vk_id       TEXT PRIMARY KEY,
    added_by    TEXT NOT NULL,
    added_at    REAL NOT NULL
);
"""

_CREATE_RSVP_SQL = """
CREATE TABLE IF NOT EXISTS rsvp (
    vk_id       TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    answer      TEXT,
    answered_at REAL,
    PRIMARY KEY (vk_id, event_id)
);
"""


@dataclass
class Stats:
    """
        Сводная статистика по заявкам
    """

    total: int
    average_age: float | None
    top_cities: list[tuple[str, int]]
    top_regions: list[tuple[str, int]]
    top_education: list[tuple[str, int]]
    party_members: dict[str, int]


class Database:
    """
        Единый репозиторий: заявки, администраторы, статистика.\n
        Использует одно постоянное соединение с SQLite\n
    """

    def __init__(self, db_path: str, encryptor: Encryptor, superadmin_ids: list[str] | None = None) -> None:
        self.encryptor = encryptor
        self._superadmins: tuple[str, ...] = tuple(superadmin_ids or [])
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def close(self) -> None:
        self._conn.close()

    def _init_db(self) -> None:
        with self._lock:
            self._conn.execute(_CREATE_APPLICATIONS_SQL)
            self._conn.execute(_CREATE_ADMINS_SQL)
            self._conn.execute(_CREATE_RSVP_SQL)
            self._conn.commit()

    def has_application(self, vk_id: str) -> bool:
        """
            Возвращает True, если заявка от пользователя с данным vk_id уже есть
        """

        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM applications WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def get_all_vk_ids(self) -> list[str]:
        """
            Возвращает vk_id всех подавших заявку
        """

        with self._lock:
            rows = self._conn.execute(
                "SELECT vk_id FROM applications").fetchall()
        return [row["vk_id"] for row in rows]

    def save_application(self, quiz: Quiz) -> None:
        """
            Сохраняет заявку в БД; номер паспорта шифруется перед записью\n
            При повторном вызове с тем же vk_id запись перезаписывается (INSERT OR REPLACE)
        """

        encrypted_passport = self.encryptor.encrypt(quiz.passport_number)

        with self._lock:
            self._conn.execute(
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
            self._conn.commit()

    def is_admin(self, vk_id: str) -> bool:
        if vk_id in self._superadmins:
            return True
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM admins WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def add_admin(self, vk_id: str, added_by: str) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO admins (vk_id, added_by, added_at) VALUES (?, ?, ?)",
                (vk_id, added_by, datetime.now().timestamp()),
            )
            self._conn.commit()

    def remove_admin(self, vk_id: str) -> bool:
        """
            Удаляет администратора. Возвращает False если vk_id — суперадмин
        """

        if vk_id in self._superadmins:
            return False
        with self._lock:
            self._conn.execute("DELETE FROM admins WHERE vk_id = ?", (vk_id,))
            self._conn.commit()
        return True

    def list_admins(self) -> list[str]:
        """
            Возвращает список всех администраторов; суперадмины идут первыми
        """

        with self._lock:
            rows = self._conn.execute(
                "SELECT vk_id FROM admins ORDER BY added_at"
            ).fetchall()
        db_admins = [row["vk_id"] for row in rows]
        return sorted(self._superadmins) + [a for a in db_admins if a not in self._superadmins]

    def collect_stats(self, top_n: int = 10) -> Stats:
        """
            Возвращает Stats с агрегированными данными по заявкам.
            top_n — сколько позиций показывать в топах (по умолчанию 10)
        """

        with self._lock:
            total = self._stat_total()
            average_age = self._stat_average_age()
            top_cities = self._stat_top("city", top_n)
            top_regions = self._stat_top("region", top_n)
            top_education = self._stat_top("education_level", top_n)
            party_members = self._stat_party_members()

        return Stats(
            total=total,
            average_age=average_age,
            top_cities=top_cities,
            top_regions=top_regions,
            top_education=top_education,
            party_members=party_members,
        )

    def _stat_total(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM applications").fetchone()
        return row[0]

    def _stat_average_age(self) -> float | None:
        """
            birth_date хранится как ДД.ММ.ГГГГ — парсим в Python
        """

        rows = self._conn.execute(
            "SELECT birth_date FROM applications").fetchall()
        if not rows:
            return None

        today = date.today()
        ages: list[int] = []

        for row in rows:
            try:
                d = date(
                    int(row["birth_date"][6:10]),
                    int(row["birth_date"][3:5]),
                    int(row["birth_date"][0:2]),
                )
                ages.append((today - d).days // 365)
            except (ValueError, IndexError):
                continue

        return round(sum(ages) / len(ages), 1) if ages else None

    def _stat_top(self, column: str, n: int) -> list[tuple[str, int]]:
        rows = self._conn.execute(
            f"""
            SELECT {column}, COUNT(*) AS cnt
            FROM applications
            GROUP BY {column}
            ORDER BY cnt DESC
            LIMIT ?
            """,
            (n,),
        ).fetchall()
        return [(row[column], row["cnt"]) for row in rows]

    def _stat_party_members(self) -> dict[str, int]:
        rows = self._conn.execute(
            """
            SELECT is_member, COUNT(*) AS cnt
            FROM applications
            GROUP BY is_member
            """
        ).fetchall()
        return {row["is_member"]: row["cnt"] for row in rows}

    # ------------------------------------------------------------------
    # RSVP
    # ------------------------------------------------------------------

    def add_pending_rsvp(self, vk_id: str, event_id: str) -> None:
        """ Регистрирует ожидание ответа после рассылки """
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO rsvp (vk_id, event_id) VALUES (?, ?)",
                (vk_id, event_id),
            )
            self._conn.commit()

    def get_pending_rsvp_event(self, vk_id: str) -> str | None:
        """ Возвращает event_id если пользователь ещё не ответил, иначе None """
        with self._lock:
            row = self._conn.execute(
                "SELECT event_id FROM rsvp WHERE vk_id = ? AND answer IS NULL",
                (vk_id,),
            ).fetchone()
        return row["event_id"] if row else None

    def save_rsvp_answer(self, vk_id: str, event_id: str, answer: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE rsvp SET answer = ?, answered_at = ? WHERE vk_id = ? AND event_id = ?",
                (answer, datetime.now().timestamp(), vk_id, event_id),
            )
            self._conn.commit()
