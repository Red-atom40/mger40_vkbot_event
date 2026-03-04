def parse_vk_id(args: list[str]) -> tuple[int, None] | tuple[None, str]:
    """Парсит vk_id из аргументов команды"""
    if not args:
        return None, "Укажите vk_id пользователя."
    try:
        return int(args[0]), None
    except ValueError:
        return None, "vk_id должен быть числом."


def parse_link_index(args: list[str]) -> tuple[int, None] | tuple[None, str]:
    """Парсит порядковый номер ссылки (1-based) из аргументов команды"""
    if not args:
        return None, "Укажите номер ссылки."
    try:
        return int(args[0]) - 1, None
    except ValueError:
        return None, "Номер ссылки должен быть числом."
