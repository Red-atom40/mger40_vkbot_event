from datetime import date, datetime
import sqlite3
import threading

from models.quiz import Quiz, Stats


create_application_table = """
CREATE TABLE IF NOT EXISTS applications (
    vk_id                   INTEGER PRIMARY KEY,
    fio                     TEXT NOT NULL,
    birth_date              TEXT NOT NULL,
    region                  TEXT NOT NULL,
    city                    TEXT NOT NULL,
    phone                   TEXT NOT NULL,
    contact_info            TEXT NOT NULL,
    education_level         TEXT NOT NULL,
    is_member               TEXT NOT NULL,
    previous_organizations  TEXT NOT NULL,
    study_or_work_place     TEXT NOT NULL,
    created_at              REAL NOT NULL
);
"""

create_admins_table = """
CREATE TABLE IF NOT EXISTS admins (
    vk_id       INTEGER PRIMARY KEY,
    added_by    INTEGER NOT NULL,
    added_at    REAL NOT NULL
);
"""

create_rsvp_table = """
CREATE TABLE IF NOT EXISTS rsvp (
    vk_id       INTEGER NOT NULL,
    event_id    TEXT NOT NULL,
    answer      TEXT,
    answered_at REAL,
    PRIMARY KEY (vk_id, event_id)
);
"""

create_event_links_table = """
CREATE TABLE IF NOT EXISTS event_links (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    link    TEXT NOT NULL
);
"""

create_events_table = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    created_at  REAL NOT NULL
);
"""


class Database:
    def __init__(
        self,
        db_path: str,
        superadmin_ids: list[int] | None = None,
    ) -> None:
        """Инициализатор класса Database для работы с базой данных SQLite\n"""
        self.superadmins: tuple[int, ...] = tuple(superadmin_ids or [])
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def close(self) -> None:
        self.conn.close()

    def _init_db(self) -> None:
        with self.lock:
            self.conn.row_factory = sqlite3.Row
            self.conn.execute(create_application_table)
            self.conn.execute(create_admins_table)
            self.conn.execute(create_rsvp_table)
            self.conn.execute(create_event_links_table)
            self.conn.execute(create_events_table)
            self.conn.commit()

    def has_application(self, vk_id: int) -> bool:
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM applications WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def get_all_vk_ids(self) -> list[int]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT vk_id FROM applications").fetchall()
        return [row["vk_id"] for row in rows]

    def save_application(self, quiz: Quiz) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO applications (
                    vk_id, fio, birth_date, region, city,
                    phone, contact_info, education_level, is_member,
                    previous_organizations, study_or_work_place, created_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    quiz.vk_id,
                    quiz.fio,
                    quiz.birth_date,
                    quiz.region,
                    quiz.city,
                    quiz.phone,
                    quiz.contact_info,
                    quiz.education_level,
                    quiz.is_member,
                    quiz.previous_organizations,
                    quiz.study_or_work_place,
                    quiz.created_at,
                ),
            )
            self.conn.commit()

    def is_admin(self, vk_id: int) -> bool:
        if vk_id in self.superadmins:
            return True
        with self.lock:
            row = self.conn.execute(
                "SELECT 1 FROM admins WHERE vk_id = ?", (vk_id,)
            ).fetchone()
        return row is not None

    def add_admin(self, vk_id: int, added_by: int) -> None:
        with self.lock:
            self.conn.execute(
                """INSERT OR IGNORE INTO admins (
                    vk_id, added_by, added_at
                ) VALUES (
                    ?, ?, ?
                )
                """,
                (vk_id, added_by, datetime.now().timestamp()),
            )
            self.conn.commit()

    def remove_admin(self, vk_id: int) -> bool:
        if vk_id in self.superadmins:
            return False
        with self.lock:
            self.conn.execute("DELETE FROM admins WHERE vk_id = ?", (vk_id,))
            self.conn.commit()
        return True

    def list_admins(self) -> list[int]:
        with self.lock:
            rows = self.conn.execute(
                "SELECT vk_id FROM admins ORDER BY added_at"
            ).fetchall()
        db_admins = [row["vk_id"] for row in rows]
        return sorted(self.superadmins) + [
            a for a in db_admins if a not in self.superadmins
        ]

    def collect_stats(self, top_n: int = 10) -> Stats:
        """Собирает статистику по заявкам для отображения в админ-панели по команде /stats"""
        with self.lock:
            total = self.stat_total()
            average_age = self.stat_average_age()
            top_cities = self.stat_top("city", top_n)
            top_education = self.stat_top("education_level", top_n)
            party_members = self.stat_party_members()

        return Stats(
            total=total,
            average_age=average_age,
            top_cities=top_cities,
            top_education=top_education,
            party_members=party_members,
        )

    def stat_total(self) -> int:
        """Возвращает общее количество заявок в базе данных"""
        row = self.conn.execute("SELECT COUNT(*) FROM applications").fetchone()
        return row[0]

    def stat_average_age(self) -> float | None:
        """
        Вычисляет средний возраст заявителей на основе их дат рождения.\n
        Возвращает None, если данных нет или все даты некорректны
        """
        rows = self.conn.execute(
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

    def stat_top(self, column: str, n: int) -> list[tuple[str, int]]:
        """Возвращает топ-n значений для указанной колонки."""
        rows = self.conn.execute(
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

    def stat_party_members(self) -> dict[str, int]:
        """Возвращает количество заявителей, являющихся членами партии и не являющихся членами партии"""
        rows = self.conn.execute(
            """
            SELECT is_member, COUNT(*) AS cnt
            FROM applications
            GROUP BY is_member
            """
        ).fetchall()
        return {row["is_member"]: row["cnt"] for row in rows}

    def save_event(self, event_id: str, title: str) -> None:
        """Сохраняет заголовок мероприятия при создании рассылки"""
        with self.lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO events (event_id, title, created_at) VALUES (?, ?, ?)",
                (event_id, title, datetime.now().timestamp()),
            )
            self.conn.commit()

    def add_pending_rsvp(self, vk_id: int, event_id: str) -> None:
        """Добавляет запись о том, что пользователю с vk_id была отправлена информация о мероприятии event_id и ожидается его ответ (да/нет)"""
        with self.lock:
            self.conn.execute(
                "INSERT OR IGNORE INTO rsvp (vk_id, event_id) VALUES (?, ?)",
                (vk_id, event_id),
            )
            self.conn.commit()

    def get_pending_rsvp_event(self, vk_id: int) -> str | None:
        """Проверяет, есть ли у пользователя с vk_id текущая незавершённая заявка на мероприятие. Если есть, возвращает event_id, иначе None"""
        with self.lock:
            row = self.conn.execute(
                "SELECT event_id FROM rsvp WHERE vk_id = ? AND answer IS NULL",
                (vk_id,),
            ).fetchone()
        return row["event_id"] if row else None

    def save_rsvp_answer(self, vk_id: int, event_id: str, answer: str) -> None:
        """Сохраняет ответ пользователя на приглашение (да/нет) для конкретного мероприятия event_id"""
        with self.lock:
            self.conn.execute(
                "UPDATE rsvp SET answer = ?, answered_at = ? WHERE vk_id = ? AND event_id = ?",
                (answer, datetime.now().timestamp(), vk_id, event_id),
            )
            self.conn.commit()

    def get_event_links(self) -> list[str]:
        """Возвращает список ссылок на мероприятия для рассылки пользователям"""
        with self.lock:
            rows = self.conn.execute(
                "SELECT link FROM event_links ORDER BY id"
            ).fetchall()
        return [row["link"] for row in rows]

    def add_event_link(self, link: str) -> None:
        """Добавляет новую ссылку на мероприятие для рассылки пользователям. Сохраняет в базе данных"""
        with self.lock:
            self.conn.execute(
                "INSERT INTO event_links (link) VALUES (?)", (link,))
            self.conn.commit()

    def remove_event_link(self, index: int) -> str | None:
        """Удаляет ссылку по порядковому номеру (0-based). Возвращает удалённое значение или None."""
        with self.lock:
            row = self.conn.execute(
                "SELECT id, link FROM event_links ORDER BY id LIMIT 1 OFFSET ?", (
                    index,)
            ).fetchone()
            if row is None:
                return None
            removed = row["link"]
            self.conn.execute(
                "DELETE FROM event_links WHERE id = ?", (row["id"],))
            self.conn.commit()
        return removed

    def get_events_list(self) -> list[dict]:
        """Возвращает список всех мероприятий со статистикой ответов и заголовком"""
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT
                    r.event_id,
                    COALESCE(e.title, '') AS title,
                    COUNT(*) AS total,
                    SUM(CASE WHEN r.answer = 'да' THEN 1 ELSE 0 END) AS yes_count,
                    SUM(CASE WHEN r.answer = 'нет' THEN 1 ELSE 0 END) AS no_count,
                    SUM(CASE WHEN r.answer IS NULL THEN 1 ELSE 0 END) AS pending_count
                FROM rsvp r
                LEFT JOIN events e ON r.event_id = e.event_id
                GROUP BY r.event_id
                ORDER BY r.event_id DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_event_participants(self, event_id: str) -> list[dict]:
        """Возвращает контактные данные участников мероприятия, ответивших 'да'"""
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT
                    r.vk_id,
                    a.fio,
                    a.phone,
                    a.contact_info,
                    a.city,
                    a.region
                FROM rsvp r
                JOIN applications a ON r.vk_id = a.vk_id
                WHERE r.event_id = ? AND r.answer = 'да'
                ORDER BY a.fio
                """,
                (event_id,),
            ).fetchall()
        return [dict(row) for row in rows]
