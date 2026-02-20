
from typing import NamedTuple


class Step(NamedTuple):
    """
        Один шаг опроса: ключ поля (key) и текст вопроса (question)
    """

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

# Команды, которые запускают опрос
START_COMMANDS = {"вступить", "заявка", "/start", "start"}