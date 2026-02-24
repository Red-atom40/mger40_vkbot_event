import sqlite3

from loguru import logger

from bot.vk_client import VkClient
from database.database import Database
from config import Config
from models.quiz import START_COMMANDS, STEPS, Quiz, Session, Stats
from validation.validator import validate


class VKBot:
    def __init__(self, config: Config, db: Database, client: VkClient) -> None:
        """Инициализирует VKBot с конфигурацией, базой данных и клиентом для взаимодействия с VK API"""
        self.config = config
        self.db = db
        self.client = client
        self.session: dict[int, Session] = {}

    def run(self) -> None:
        """Запускает основной цикл бота для прослушивания входящих сообщений"""
        logger.info("bot is running...")
        try:
            for event in self.client.listen():
                try:
                    self.handle_message(event)
                except Exception as e:
                    logger.exception("error: {e}")
        except KeyboardInterrupt:
            logger.info("bot stopped")

    def handle_message(self, event) -> None:
        """Обрабатывает входящее сообщение от пользователя"""
        user_id: int = event.user_id
        text = event.text.strip()

        logger.debug(f"received message from {user_id}: {text!r}")

        if self.db.is_admin(user_id) and text.startswith("/"):
            self._handle_admin(user_id, text)
            return

        event_id = self.db.get_pending_rsvp_event(user_id)
        if event_id:
            self._handle_rsvp(user_id, event_id, text)
            return

        if text.lower() in START_COMMANDS:
            self._start_quiz(user_id)
            return

        session = self.session.get(user_id)
        if session is not None and session.is_expired():
            del self.session[user_id]
            session = None

        if session is None:
            self.client.send(
                user_id, "Привет! Чтобы начать заполнение анкеты, напиши «вступить» или «заявка».")
            return

        self._process_answer(user_id, session, text)

    def _handle_rsvp(self, user_id: int, event_id: str, text: str) -> None:
        answer = text.lower().strip()
        if answer not in ("да", "нет"):
            self.client.send(user_id, "Пожалуйста, ответьте «да» или «нет».")
            return
        self.db.save_rsvp_answer(user_id, event_id, answer)

        logger.info(f"RSVP vk_id={user_id} event={event_id} answer={answer!r}")

        self.client.send(user_id, "Спасибо! Ваш ответ записан.")

    def _start_quiz(self, user_id: int) -> None:
        """Начинает новый сеанс заполнения заявки для пользователя"""
        if self.db.has_application(user_id):

            logger.warning(f"Duplicate application attempt vk_id={user_id}")

            self.client.send(
                user_id, "Ваша заявка уже принята. Спасибо за интерес к «Молодой Гвардии»!")
            return

        logger.info(f"Quiz started vk_id={user_id}")

        self.session[user_id] = Session(user_id, self.config.session_timeout)
        self.client.send(
            user_id,
            "Добро пожаловать! Вы начинаете заполнение заявки на вступление в «Молодую Гвардию».\n"
            f"На ответы отводится {self.config.session_timeout // 60} минут. "
            "Если время выйдет — нужно начать заново.\n\n"
            + STEPS[0].question,
        )

    def _process_answer(self, user_id: int, session: Session, text: str) -> None:
        current_step = STEPS[session.step_index]
        ok, error_msg = validate(current_step.key, text)

        if not ok:
            self.client.send(
                user_id, f"{error_msg}\n\n{current_step.question}")
            return

        logger.debug(
            f"Answer saved vk_id={user_id} step={session.step_index} key={current_step.key}")
        session.answers[current_step.key] = text
        session.step_index += 1
        session.touch()

        if session.step_index >= len(STEPS):
            self.finalize_quiz(user_id, session)
        else:
            self.client.send(user_id, STEPS[session.step_index].question)

    def finalize_quiz(self, user_id: int, session: Session) -> None:
        logger.info(f"Saving application vk_id={user_id}")
        try:
            self.db.save_application(
                Quiz.from_answers(session.answers, user_id))
        except sqlite3.Error as e:
            logger.error(f"DB error vk_id={user_id}: {e}")
            self.client.send(
                user_id,
                "Не удалось сохранить заявку из-за внутренней ошибки. Попробуйте ещё раз позже.",
            )
            return

        logger.info(f"Application accepted vk_id={user_id}")

        del self.session[user_id]
        self.client.send(
            user_id,
            "Ваша заявка успешно принята!\nМы рассмотрим её в ближайшее время и свяжемся с вами.",
        )

    def _handle_admin(self, user_id: int, text: str) -> None:
        parts = text.strip().split()
        cmd, args = parts[0].lower(), parts[1:]

        logger.info(f"Admin command vk_id={user_id}: {text!r}")

        match cmd:
            case "/help":
                self.client.send(
                    user_id,
                    "Команды администратора:\n"
                    "/stats — статистика по заявкам\n"
                    "/addadmin <vk_id> — добавить администратора\n"
                    "/removeadmin <vk_id> — удалить администратора\n"
                    "/admins — список всех администраторов",
                )
            case "/stats":
                self.client.send(user_id, format_stats(
                    self.db.collect_stats()))
            case "/addadmin":
                self.cmd_addadmin(user_id, args)
            case "/removeadmin":
                self.cmd_removeadmin(user_id, args)
            case "/admins":
                admins = self.db.list_admins()
                msg = "Администраторы:\n" + \
                    "\n".join(
                        str(a) for a in admins) if admins else "Список администраторов пуст."
                self.client.send(user_id, msg)
            case _:
                self.client.send(
                    user_id, f"Неизвестная команда: {cmd}\nНапишите /help для списка команд.")

    def cmd_addadmin(self, user_id: int, args: list[str]) -> None:
        if not args:
            self.client.send(
                user_id, "Укажите vk_id пользователя: /addadmin 123456")
            return
        try:
            target = int(args[0])
        except ValueError:
            self.client.send(user_id, "vk_id должен быть числом.")
            return
        if self.db.is_admin(target):
            self.client.send(
                user_id, f"Пользователь {target} уже является администратором.")
            return
        self.db.add_admin(target, added_by=user_id)
        logger.info(f"Admin added: {target} by {user_id}")
        self.client.send(
            user_id, f"Пользователь {target} добавлен в администраторы.")

    def cmd_removeadmin(self, user_id: int, args: list[str]) -> None:
        if not args:
            self.client.send(
                user_id, "Укажите vk_id пользователя: /removeadmin 123456")
            return
        try:
            target = int(args[0])
        except ValueError:
            self.client.send(user_id, "vk_id должен быть числом.")
            return
        if not self.db.remove_admin(target):
            self.client.send(
                user_id,
                f"Пользователь {target} — суперадмин из config.json, его нельзя удалить через бота.",
            )
            return
        logger.info(f"Admin removed: {target} by {user_id}")
        self.client.send(
            user_id, f"Пользователь {target} удалён из администраторов.")


def format_stats(s: Stats) -> str:
    """Форматирует статистику для отображения в админ-панели по команде /stats"""
    lines = [
        "Статистика заявок",
        f"Всего заявок: {s.total}",
        f"Средний возраст: {s.average_age if s.average_age is not None else '—'}",
        "", "Топ городов:",
    ]
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
