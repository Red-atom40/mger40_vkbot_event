from dataclasses import dataclass, field
import datetime
from typing import NamedTuple


@dataclass
class Quiz:
    """
    Класс для хранения данных анкеты, которую проходит пользователь в боте\n
    Полностью соответствует таблице applications в БД
    """

    vk_id: int
    fio: str
    birth_date: str
    region: str
    city: str
    phone: str
    contact_info: str
    education_level: str
    is_member: str
    previous_organizations: str
    study_or_work_place: str
    created_at: float = field(
        default_factory=lambda: datetime.datetime.now().timestamp()
    )

    @classmethod
    def from_answers(cls, answers: dict[str, str], vk_id: int) -> "Quiz":
        return cls(
            vk_id=vk_id,
            fio=answers["fio"],
            birth_date=answers["birth_date"],
            region=answers["region"],
            city=answers["city"],
            phone=answers["phone"],
            contact_info=answers["contact_info"],
            education_level=answers["education_level"],
            is_member=answers["is_member"],
            previous_organizations=answers["previous_organizations"],
            study_or_work_place=answers["study_or_work_place"],
        )


class Step(NamedTuple):
    """Класс для хранения данных одного шага анкеты"""
    key: str
    question: str


# Шаги анкеты с заранее заданными вопросами и ключами для хранения ответов в словаре
STEPS: list[Step] = [
    Step("fio", "Введите ваше ФИО полностью (Фамилия Имя Отчество):"),
    Step("birth_date", "Дата рождения (ДД.ММ.ГГГГ):"),
    Step("region", "Регион постоянной регистрации:"),
    Step("city", "Город / населённый пункт:"),
    Step("phone", "Контактный телефон (7...):"),
    Step("contact_info", "Email / Telegram:"),
    Step(
        "education_level",
        "Образование:\n  школьное / среднее специальное / высшее / иное",
    ),
    Step("is_member", "Являетесь ли вы членом партии «Единая Россия»? (да / нет):"),
    Step(
        "previous_organizations",
        "В каких молодёжных / политических организациях состояли ранее?\n(если нигде — напишите «нет»)",
    ),
    Step("study_or_work_place", "Место учёбы / работы (название и город):"),
]

START_COMMANDS = {"вступить", "заявка", "/start", "start"}


class Session:
    """Класс сессии прохождения анкеты пользователем"""

    def __init__(self, vk_id: int, timeout: int) -> None:
        """Инициализатор сессии прохождения анкеты пользователемы"""
        self.vk_id = vk_id
        self.timeout = timeout
        self.step_index: int = 0
        self.answers: dict[str, str] = {}
        self.started_at: datetime.datetime = datetime.datetime.now()

    def is_expired(self) -> bool:
        """Проверяет, истекло ли время сессии"""
        elapsed = (datetime.datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout

    def touch(self) -> None:
        self.started_at = datetime.datetime.now()


@dataclass
class Stats:
    """
    Класс для хранения статистики по заявкам, отображаемой в админ-панели по команде /stats
    """

    total: int
    average_age: float | None
    top_cities: list[tuple[str, int]]
    top_regions: list[tuple[str, int]]
    top_education: list[tuple[str, int]]
    party_members: dict[str, int]


def format_stats(s: Stats) -> str:
    """Форматирует статистику для отображения в админ-панели по команде /статистика"""
    lines = [
        "Статистика заявок",
        f"Всего заявок: {s.total}",
        f"Средний возраст: {s.average_age if s.average_age is not None else '—'}",
        "",
        "Топ городов:",
    ]
    for i, (city, cnt) in enumerate(s.top_cities, 1):
        lines.append(f"  {i}. {city} — {cnt}")
    lines += ["", "Топ регионов:"]
    for i, (region, cnt) in enumerate(s.top_regions, 1):
        lines.append(f"  {i}. {region} — {cnt}")
    lines += ["", "Образование:"]
    for i, (edu, cnt) in enumerate(s.top_education, 1):
        lines.append(f"  {i}. {edu} — {cnt}")
    lines += ["", "Членство в ЕР:"]
    for answer, cnt in sorted(s.party_members.items()):
        lines.append(f"  {answer}: {cnt}")
    return "\n".join(lines)
