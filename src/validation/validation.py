import re
from datetime import date, datetime
from typing import Callable


ValidationResult = tuple[bool, str | None]


def _parse_date(value: str) -> date | None:
    """
        Парсит дату в формате ДД.ММ.ГГГГ.\n
        Возвращает None при ошибке
    """

    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def validate_fio(value: str) -> ValidationResult:
    """
        ФИО — три слова через пробел, каждое начинается с заглавной буквы,
        состоит только из букв (допускается дефис, например Салтыков-Щедрин)
    """

    parts = value.strip().split()
    if len(parts) != 3:
        return False, "Введите ФИО полностью — ровно три слова (Фамилия Имя Отчество)."

    word_re = re.compile(r"^[А-ЯЁ][а-яёА-ЯЁ\-]+$")
    for part in parts:
        if not word_re.match(part):
            return False, (
                "Каждое слово ФИО должно начинаться с заглавной буквы "
                "и содержать только русские буквы."
            )
    return True, None


def validate_birth_date(value: str) -> ValidationResult:
    """
        Дата рождения — формат ДД.ММ.ГГГГ, не в будущем,
        возраст от 14 до 100 лет
    """

    d = _parse_date(value)
    if d is None:
        return False, "Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ (например, 15.03.1998)."

    today = date.today()
    if d >= today:
        return False, "Дата рождения не может быть в будущем."

    age = (today - d).days // 365
    if age < 14:
        return False, "Возраст должен быть не менее 14 лет."
    if age > 100:
        return False, "Введите корректную дату рождения."

    return True, None


def validate_region(value: str) -> ValidationResult:
    """
        Регион — не пустой, только буквы, пробелы, дефисы и скобки
    """

    if not value.strip():
        return False, "Регион не может быть пустым."

    if not re.match(r"^[А-ЯЁа-яёA-Za-z\s\-()\.]+$", value.strip()):
        return False, "Регион содержит недопустимые символы."

    return True, None


def validate_city(value: str) -> ValidationResult:
    """
        Город — не пустой
    """

    if not value.strip():
        return False, "Название города не может быть пустым."
    return True, None


def validate_street(value: str) -> ValidationResult:
    """
        Улица — не пустая
    """

    if not value.strip():
        return False, "Название улицы не может быть пустым."
    return True, None


def validate_house(value: str) -> ValidationResult:
    """
        Дом — не пустой
    """

    if not value.strip():
        return False, "Укажите номер дома."
    return True, None


def validate_passport_number(value: str) -> ValidationResult:
    """
        Серия и номер паспорта — ровно 10 цифр без пробелов и дефисов
    """

    cleaned = value.strip().replace(" ", "").replace("-", "")
    if not re.fullmatch(r"\d{10}", cleaned):
        return False, (
            "Введите серию и номер паспорта без пробелов — 10 цифр "
            "(например, 4519123456)."
        )
    return True, None


def validate_passport_issued_by(value: str) -> ValidationResult:
    """
        Кем выдан паспорт — не пустое
    """

    if not value.strip():
        return False, "Укажите, кем выдан паспорт."
    return True, None


def validate_passport_issue_date(value: str) -> ValidationResult:
    """
        Дата выдачи паспорта — формат ДД.ММ.ГГГГ, не в будущем,
        не раньше 01.01.1997 (год введения современного паспорта РФ)
    """

    d = _parse_date(value)
    if d is None:
        return False, "Неверный формат даты. Введите дату в формате ДД.ММ.ГГГГ (например, 20.05.2015)."

    if d > date.today():
        return False, "Дата выдачи паспорта не может быть в будущем."

    if d < date(1997, 1, 1):
        return False, "Введите корректную дату выдачи паспорта (не ранее 1997 года)."

    return True, None


def validate_phone(value: str) -> ValidationResult:
    """
        Телефон — формат +7XXXXXXXXXX (11 цифр)\n
        Также принимает 8XXXXXXXXXX, нормализуя к +7
    """

    cleaned = re.sub(r"[\s\-()]", "", value.strip())

    if re.fullmatch(r"8\d{10}", cleaned):
        return True, None

    if re.fullmatch(r"\+7\d{10}", cleaned):
        return True, None

    return False, (
        "Введите номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX "
        "(например, +79161234567)."
    )


def validate_contact_info(value: str) -> ValidationResult:
    """
        Контакт — email (user@example.com) или Telegram-username (@username)
    """

    stripped = value.strip()

    email_re = re.compile(r"^[\w.\-+]+@[\w.\-]+\.[a-zA-Z]{2,}$")
    tg_re = re.compile(r"^@[a-zA-Z0-9_]{4,32}$")

    if email_re.match(stripped) or tg_re.match(stripped):
        return True, None

    return False, (
        "Введите email (например, ivan@mail.ru) или Telegram-username "
        "(например, @ivan_ivanov)."
    )


def validate_education_level(value: str) -> ValidationResult:
    """
        Образование — одно из допустимых значений
    """

    if not value.strip():
        return False, "Укажите уровень образования."
    return True, None


def validate_is_member(value: str) -> ValidationResult:
    """
        Членство в партии — строго «да» или «нет»
    """

    if value.strip().lower() not in {"да", "нет"}:
        return False, "Ответьте «да» или «нет»."
    return True, None


def validate_previous_organizations(value: str) -> ValidationResult:
    """
        Предыдущие организации — не пустое (допускается «нет»)
    """

    if not value.strip():
        return False, (
            "Укажите организации, в которых вы состояли, "
            "или напишите «нет»."
        )
    return True, None


def validate_study_or_work_place(value: str) -> ValidationResult:
    """
        Место учёбы/работы — не пустое
    """

    if not value.strip():
        return False, "Укажите место учёбы или работы."
    return True, None


_VALIDATORS: dict[str, Callable[[str], ValidationResult]] = {
    "fio":                   validate_fio,
    "birth_date":            validate_birth_date,
    "region":                validate_region,
    "city":                  validate_city,
    "street":                validate_street,
    "house":                 validate_house,
    "passport_number":       validate_passport_number,
    "passport_issued_by":    validate_passport_issued_by,
    "passport_issue_date":   validate_passport_issue_date,
    "phone":                 validate_phone,
    "contact_info":          validate_contact_info,
    "education_level":       validate_education_level,
    "is_member":             validate_is_member,
    "previous_organizations": validate_previous_organizations,
    "study_or_work_place":   validate_study_or_work_place,
}


def validate(key: str, value: str) -> ValidationResult:
    """
        Валидирует значение для указанного ключа шага опроса.

        :param key:   ключ поля (например, "fio", "phone")
        :param value: ответ пользователя
        :return:      (True, None) если валидно, иначе (False, "текст ошибки")
    """

    validator = _VALIDATORS.get(key)
    if validator is None:
        # Для неизвестных полей просто проверяем непустоту
        return (bool(value.strip()), "Поле не может быть пустым." if not value.strip() else None)
    return validator(value)
