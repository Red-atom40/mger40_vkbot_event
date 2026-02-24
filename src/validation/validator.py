from collections.abc import Callable
from datetime import date, datetime

ValidationResult = tuple[bool, str | None]


def parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value.strip(), "%d.%m.%Y").date()
    except ValueError:
        return None


def validate_fio(value: str) -> ValidationResult:
    parts = value.strip().split()
    if len(parts) != 3:
        return False, "ФИО должно состоять из трех частей"
    return True, None


def validate_birth_date(value: str) -> ValidationResult:
    d = parse_date(value)
    if d is None:
        return False, "Неверный формат даты. Ожидается ДД.ММ.ГГГГ"

    if d > date.today():
        return False, "Дата рождения не может быть в будущем"

    if (date.today() - d).days < 14 * 365:
        return False, "Пользователь должен быть старше 14 лет"
    if (date.today() - d).days > 365 * 150:
        return False, "Пользователь не может быть старше 150 лет"

    return True, None


def validate_region(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Регион не может быть пустым."
    return True, None


def validate_city(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Город не может быть пустым."
    return True, None


def validate_street(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Улица не может быть пустой."
    return True, None


def validate_house(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Укажите номер дома."
    return True, None


def validate_passport_number(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Номер паспорта не может быть пустым."
    if not value.isdigit() or len(value) != 10:
        return False, "Номер паспорта должен состоять из 10 цифр."
    return True, None


def validate_passport_issued_by(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Укажите, кем выдан паспорт."
    return True, None


def validate_passport_issue_date(value: str) -> ValidationResult:
    d = parse_date(value)
    if d is None:
        return False, "Неверный формат даты. Ожидается ДД.ММ.ГГГГ"

    if d > date.today():
        return False, "Дата выдачи паспорта не может быть в будущем"

    if d < date(1997, 1, 1):
        return False, "Введите корректную дату выдачи паспорта (не ранее 1997 года)."

    return True, None


def validate_phone(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Номер телефона не может быть пустым."
    if not value.isdigit() or len(value) != 11 or not value.startswith("7"):
        return False, "Номер телефона должен состоять из 11 цифр и начинаться с 7."
    return True, None


def validate_contact_info(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Контактная информация не может быть пустой."
    return True, None


def validate_education_level(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Укажите уровень образования."
    return True, None


def validate_is_member(value: str) -> ValidationResult:
    if value.strip().lower() not in {"да", "нет"}:
        return False, "Ответьте «да» или «нет»."
    return True, None


def validate_previous_organizations(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Укажите предыдущие организации, в которых вы работали."
    return True, None


def validate_study_or_work_place(value: str) -> ValidationResult:
    if not value.strip():
        return False, "Укажите место учёбы или работы."
    return True, None


VALIDATORS: dict[str, Callable[[str], ValidationResult]] = {
    "fio": validate_fio,
    "birth_date": validate_birth_date,
    "region": validate_region,
    "city": validate_city,
    "street": validate_street,
    "house": validate_house,
    "passport_number": validate_passport_number,
    "passport_issued_by": validate_passport_issued_by,
    "passport_issue_date": validate_passport_issue_date,
    "phone": validate_phone,
    "contact_info": validate_contact_info,
    "education_level": validate_education_level,
    "is_member": validate_is_member,
    "previous_organizations": validate_previous_organizations,
    "study_or_work_place": validate_study_or_work_place,
}


def validate(key: str, value: str) -> ValidationResult:
    """Валидирует ответ пользователя на текущем шаге анкеты"""
    validator = VALIDATORS.get(key)
    if validator is None:
        return (
            bool(value.strip()),
            "Поле не может быть пустым." if not value.strip() else None,
        )
    return validator(value)
