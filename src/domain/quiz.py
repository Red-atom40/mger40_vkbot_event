from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Quiz:
    """
        Модель заявки, заполненной пользователем в ходе опроса.\n
        Поля совпадают со столбцами таблицы applications в БД.
    """

    vk_id: str
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
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())

    @classmethod
    def from_answers(cls, answers: dict[str, str], vk_id: str) -> "Quiz":
        """
            Создаёт Quiz из словаря ответов сессии и vk_id пользователя
        """

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
