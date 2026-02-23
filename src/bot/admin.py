from loguru import logger

from bot.client import VkClient
from database.database import Database, Stats


class AdminHandler:
    """
        Обрабатывает команды администраторов, поступающие через личные сообщения бота.\n
        Команды начинаются с «/»; доступ проверяется через Database
    """

    def __init__(
        self,
        admins: Database,
        client: VkClient,
    ) -> None:
        self._admins = admins
        self._client = client

    def is_admin_command(self, vk_id: str, text: str) -> bool:
        """
            True если отправитель — администратор и сообщение начинается с «/»
        """

        return self._admins.is_admin(vk_id) and text.startswith("/")

    def handle(self, vk_id: str, user_id: int, text: str) -> None:
        """
            Парсит команду и вызывает соответствующий метод
        """

        parts = text.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]

        logger.info(f"Admin command vk_id={vk_id}: {text!r}")

        match cmd:
            case "/help":
                self._cmd_help(user_id)
            case "/stats":
                self._cmd_stats(user_id)
            case "/addadmin":
                self._cmd_addadmin(vk_id, user_id, args)
            case "/removeadmin":
                self._cmd_removeadmin(vk_id, user_id, args)
            case "/admins":
                self._cmd_admins(user_id)
            case _:
                self._client.send(
                    user_id,
                    f"Неизвестная команда: {cmd}\nНапишите /help для списка команд.",
                )

    def _cmd_help(self, user_id: int) -> None:
        """
            Список всех команд для администраторов
        """
        self._client.send(
            user_id,
            (
                "Команды администратора:\n"
                "/stats — статистика по заявкам\n"
                "/addadmin <vk_id> — добавить администратора\n"
                "/removeadmin <vk_id> — удалить администратора\n"
                "/admins — список всех администраторов"
            ),
        )

    def _cmd_stats(self, user_id: int) -> None:
        """
            Собирает статистику по заявкам через StatsRepository и отправляет администратору в виде текста
        """
        stats = self._admins.collect_stats()
        self._client.send(user_id, _format_stats(stats))

    def _cmd_addadmin(self, vk_id: str, user_id: int, args: list[str]) -> None:
        """
            Добавляет администратора с данным vk_id в БД\n
        """
        if not args:
            self._client.send(
                user_id, "Укажите vk_id пользователя: /addadmin 123456")
            return

        target = args[0]

        if self._admins.is_admin(target):
            self._client.send(
                user_id, f"Пользователь {target} уже является администратором.")
            return

        self._admins.add_admin(target, added_by=vk_id)
        logger.info(f"Admin added: {target} by {vk_id}")
        self._client.send(
            user_id, f"Пользователь {target} добавлен в администраторы.")

    def _cmd_removeadmin(self, vk_id: str, user_id: int, args: list[str]) -> None:
        """
            Удаляет администратора с данным vk_id из БД\n
        """
        if not args:
            self._client.send(
                user_id, "Укажите vk_id пользователя: /removeadmin 123456")
            return

        target = args[0]

        if not self._admins.remove_admin(target):
            self._client.send(
                user_id,
                f"Пользователь {target} — суперадмин из config.json, его нельзя удалить через бота.",
            )
            return

        logger.info(f"Admin removed: {target} by {vk_id}")
        self._client.send(
            user_id, f"Пользователь {target} удалён из администраторов.")

    def _cmd_admins(self, user_id: int) -> None:
        """
            Отправляет администратору список всех администраторов, включая суперадминов (которые идут первыми)
        """
        admins = self._admins.list_admins()
        if not admins:
            self._client.send(user_id, "Список администраторов пуст.")
            return
        self._client.send(user_id, "Администраторы:\n" + "\n".join(admins))


def _format_stats(s: Stats) -> str:
    """
        Форматирует статистику в удобочитаемый текст для отправки администратору
    """
    lines = [
        "Статистика заявок",
        f"Всего заявок: {s.total}",
        f"Средний возраст: {s.average_age if s.average_age is not None else '—'}",
    ]

    lines += ["", "Топ городов:"]
    for i, (city, cnt) in enumerate(s.top_cities, 1):
        lines.append(f"  {i}. {city} — {cnt}")

    lines += ["", "Топ регионов:"]
    for i, (region, cnt) in enumerate(s.top_regions, 1):
        lines.append(f"  {i}. {region} — {cnt}")

    lines += ["", "Образование:"]
    for i, (edu, cnt) in enumerate(s.top_education, 1):
        lines.append(f"  {i}. {edu} — {cnt}")

    lines += ["", "Членство в ЕР:"]
    for answer, cnt in sorted(s.party_members.items()):
        lines.append(f"  {answer}: {cnt}")

    return "\n".join(lines)
