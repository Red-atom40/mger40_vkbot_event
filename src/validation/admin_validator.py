def parse_vk_id(args: list[str]) -> tuple[int, None] | tuple[None, str]:
    """Парсит числовой vk_id из аргументов команды, если он передан напрямую."""
    if not args:
        return None, "Укажите пользователя в формате @user, ссылкой на профиль или vk_id."
    try:
        return int(args[0]), None
    except ValueError:
        return None, "vk_id не распознан как число."


def parse_event_index(args: list[str]) -> tuple[int, None] | tuple[None, str]:
    """Парсит порядковый номер мероприятия (1-based) из аргументов команды"""
    if not args:
        return None, "Укажите номер мероприятия."
    try:
        return int(args[0]) - 1, None
    except ValueError:
        return None, "Номер мероприятия должен быть числом."
