from collections.abc import Callable
from datetime import date, datetime
from validation.russian_cities import is_russian_city, suggest_cities

ValidationResult = tuple[bool, str | None]
EDUCATION_LEVEL_OPTIONS: tuple[str, ...] = (
    "среднее общее",
    "среднее специальное",
    "высшее",
    "иное",
)
_EDUCATION_LEVEL_MAP: dict[str, str] = {
    option.casefold(): option for option in EDUCATION_LEVEL_OPTIONS
}

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
    city = value.strip()
    if not city:
        return False, "Город не может быть пустым."
    if is_russian_city(city):
        return True, None
    hints = suggest_cities(city)
    if hints:
        options = ", ".join(hints)
        return False, (
            f"Город «{city}» не найден.\n"
            f"Возможно, вы имели в виду: {options}?\n"
            "Введите официальное название города РФ на русском языке."
        )
    return (
        False,
        f"Город «{city}» не найден среди городов РФ.\n"
        "Введите официальное название города на русском языке (например: Москва, Казань, Тула).",
    )


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
    if value.strip().casefold() not in _EDUCATION_LEVEL_MAP:
        return (
            False,
            "Выберите один из вариантов: среднее общее / среднее специальное / высшее / иное.",
        )
    return True, None


def canonicalize_education_level(value: str) -> str | None:
    """Возвращает каноничное значение уровня образования."""
    return _EDUCATION_LEVEL_MAP.get(value.strip().casefold())


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
