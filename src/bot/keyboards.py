from vk_api.keyboard import VkKeyboard, VkKeyboardColor


def start_keyboard() -> str:
    """Возвращает JSON клавиатуры с кнопкой «Заявка» для приветственного сообщения."""
    kb = VkKeyboard(one_time=True)
    kb.add_button("Заявка", color=VkKeyboardColor.PRIMARY)
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
