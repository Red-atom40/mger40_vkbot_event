import sqlite3
from dataclasses import dataclass
from datetime import date


@dataclass
class Stats:
    """
        Сводная статистика по заявкам из базы данных
    """

    total: int
    average_age: float | None
    top_cities: list[tuple[str, int]]
    top_regions: list[tuple[str, int]]
    top_education: list[tuple[str, int]]
    party_members: dict[str, int]


class StatsRepository:
    """
        Читает и агрегирует статистику из таблицы applications
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def collect(self, top_n: int = 10) -> Stats:
        """
            Возвращает Stats с агрегированными данными.
            top_n — сколько позиций показывать в топах (по умолчанию 10)
        """

        with self._connect() as conn:
            total         = self._total(conn)
            average_age   = self._average_age(conn)
            top_cities    = self._top(conn, "city", top_n)
            top_regions   = self._top(conn, "region", top_n)
            top_education = self._top(conn, "education_level", top_n)
            party_members = self._party_members(conn)

        return Stats(
            total=total,
            average_age=average_age,
            top_cities=top_cities,
            top_regions=top_regions,
            top_education=top_education,
            party_members=party_members,
        )

    @staticmethod
    def _total(conn: sqlite3.Connection) -> int:
        row = conn.execute("SELECT COUNT(*) FROM applications").fetchone()
        return row[0]

    @staticmethod
    def _average_age(conn: sqlite3.Connection) -> float | None:
        """
            Считает средний возраст.
            birth_date хранится как ДД.ММ.ГГГГ — парсим в Python
        """

        rows = conn.execute("SELECT birth_date FROM applications").fetchall()
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

    @staticmethod
    def _top(conn: sqlite3.Connection, column: str, n: int) -> list[tuple[str, int]]:
        """
            Топ N значений по столбцу column
        """

        rows = conn.execute(
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

    @staticmethod
    def _party_members(conn: sqlite3.Connection) -> dict[str, int]:
        rows = conn.execute(
            """
            SELECT is_member, COUNT(*) AS cnt
            FROM applications
            GROUP BY is_member
            """
        ).fetchall()
        return {row["is_member"]: row["cnt"] for row in rows}
