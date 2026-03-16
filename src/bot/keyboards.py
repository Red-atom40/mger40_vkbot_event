from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def start_keyboard(has_application: bool = False) -> str:
    """Возвращает основную клавиатуру: «Заявка» всегда, доп. кнопки после анкеты."""
    kb = VkKeyboard(one_time=False)
    kb.add_button("Заявка", color=VkKeyboardColor.PRIMARY)
    if has_application:
        kb.add_line()
        kb.add_button("Мои данные", color=VkKeyboardColor.SECONDARY)
        kb.add_button("Изменить данные", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()


def empty_keyboard() -> str:
    """Возвращает JSON пустой клавиатуры (скрывает кнопки после начала анкеты)."""
    return VkKeyboard.get_empty_keyboard()


def yes_no_keyboard() -> str:
    """Возвращает клавиатуру с кнопками «Да» и «Нет»."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("Да", color=VkKeyboardColor.POSITIVE)
    kb.add_button("Нет", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()


def event_rsvp_keyboard(event_id: str) -> str:
    """Возвращает inline-клавиатуру RSVP, привязанную к конкретному мероприятию."""
    kb = VkKeyboard(inline=True)
    kb.add_button(
        "Да",
        color=VkKeyboardColor.POSITIVE,
        payload={"type": "rsvp", "event_id": event_id, "answer": "да"},
    )
    kb.add_button(
        "Нет",
        color=VkKeyboardColor.NEGATIVE,
        payload={"type": "rsvp", "event_id": event_id, "answer": "нет"},
    )
    return kb.get_keyboard()


def quiz_stop_inline_keyboard() -> str:
    """Возвращает inline-кнопку для досрочной остановки анкеты."""
    kb = VkKeyboard(inline=True)
    kb.add_button(
        "Остановить анкету",
        color=VkKeyboardColor.NEGATIVE,
        payload={"type": "quiz_stop"},
    )
    return kb.get_keyboard()


def education_keyboard() -> str:
    """Возвращает клавиатуру с допустимыми вариантами образования."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("среднее общее", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("среднее специальное", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("высшее", color=VkKeyboardColor.PRIMARY)
    kb.add_line()
    kb.add_button("иное", color=VkKeyboardColor.SECONDARY)
    return kb.get_keyboard()


def profile_actions_keyboard() -> str:
    """Возвращает клавиатуру действий с пользовательскими данными."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("Изменить данные", color=VkKeyboardColor.PRIMARY)
    return kb.get_keyboard()


def profile_fields_keyboard() -> str:
    """Возвращает клавиатуру выбора поля для редактирования."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("ФИО", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Дата рождения", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Регион", color=VkKeyboardColor.SECONDARY)
    kb.add_button("Город", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Телефон", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Email/Telegram", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Образование", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Членство в ЕР", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Предыдущие организации", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Учеба/работа", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("Отмена", color=VkKeyboardColor.NEGATIVE)
    return kb.get_keyboard()
