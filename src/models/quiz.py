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
    street: str
    house: str
    passport_number: str
    passport_issued_by: str
    passport_issue_date: str
    phone: str
    contact_info: str
    education_level: str
    is_member: str
    previous_organizations: str
    study_or_work_place: str
    created_at: float = field(
        default_factory=lambda: datetime.datetime.now().timestamp())

    @classmethod
    def from_answers(cls, answers: dict[str, str], vk_id: int) -> "Quiz":
        return cls(
            vk_id=vk_id,
            fio=answers["fio"],
            birth_date=answers["birth_date"],
            region=answers["region"],
            city=answers["city"],
            street=answers["street"],
            house=answers["house"],
            passport_number=answers["passport_number"],
            passport_issued_by=answers["passport_issued_by"],
            passport_issue_date=answers["passport_issue_date"],
            phone=answers["phone"],
            contact_info=answers["contact_info"],
            education_level=answers["education_level"],
            is_member=answers["is_member"],
            previous_organizations=answers["previous_organizations"],
            study_or_work_place=answers["study_or_work_place"],
        )


class Step(NamedTuple):
    key: str
    question: str


STEPS: list[Step] = [
    Step("fio",                    "Введите ваше ФИО полностью (Фамилия Имя Отчество):"),
    Step("birth_date",             "Дата рождения (ДД.ММ.ГГГГ):"),
    Step("region",                 "Регион постоянной регистрации:"),
    Step("city",                   "Город / населённый пункт:"),
    Step("street",                 "Улица:"),
    Step("house",                  "Дом / корпус / квартира:"),
    Step("passport_number",
         "Серия и номер паспорта (без пробелов, например 4519123456):"),
    Step("passport_issued_by",     "Кем выдан паспорт:"),
    Step("passport_issue_date",    "Дата выдачи паспорта (ДД.ММ.ГГГГ):"),
    Step("phone",                  "Контактный телефон (+7...):"),
    Step("contact_info",           "Email / Telegram:"),
    Step("education_level",
         "Образование:\n  школьное / среднее специальное / высшее / иное"),
    Step("is_member",
         "Являетесь ли вы членом партии «Единая Россия»? (да / нет):"),
    Step("previous_organizations",
         "В каких молодёжных / политических организациях состояли ранее?\n(если нигде — напишите «нет»)"),
    Step("study_or_work_place",    "Место учёбы / работы (название и город):"),
]

START_COMMANDS = {"вступить", "заявка", "/start", "start"}


class Session:
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
