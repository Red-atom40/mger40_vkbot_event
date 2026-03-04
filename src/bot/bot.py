import sqlite3

from loguru import logger

from bot.vk_client import VkClient
from database.database import Database
from config import Config
from models.quiz import START_COMMANDS, STEPS, Quiz, Session, Stats, format_stats
from validation.validator import validate
from validation.admin_validator import parse_vk_id, parse_link_index


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
                except Exception:
                    logger.exception("error: {e}")
        except KeyboardInterrupt:
            logger.info("bot stopped")

    def handle_message(self, event) -> None:
        """Обрабатывает входящее сообщение от пользователя"""
        user_id: int = event.user_id
        text = event.text.strip()

        logger.debug(f"received message from {user_id}: {text!r}")

        if self.db.is_admin(user_id) and text.startswith("/"):
            self.handle_admin(user_id, text)
            return

        event_id = self.db.get_pending_rsvp_event(user_id)
        if event_id:
            self.handle_rsvp(user_id, event_id, text)
            return

        if text.lower() in START_COMMANDS:
            self.start_quiz(user_id)
            return

        session = self.session.get(user_id)
        if session is not None and session.is_expired():
            del self.session[user_id]
            session = None

        if session is None:
            self.client.send(
                user_id,
                "Привет! Чтобы начать заполнение анкеты, напиши «вступить» или «заявка».",
            )
            return

        self.process_answer(user_id, session, text)

    def handle_rsvp(self, user_id: int, event_id: str, text: str) -> None:
        answer = text.lower().strip()
        if answer not in ("да", "нет"):
            self.client.send(user_id, "Пожалуйста, ответьте «да» или «нет».")
            return
        self.db.save_rsvp_answer(user_id, event_id, answer)

        logger.info(f"RSVP vk_id={user_id} event={event_id} answer={answer!r}")

        self.client.send(user_id, "Спасибо! Ваш ответ записан.")

    def start_quiz(self, user_id: int) -> None:
        """Начинает новый сеанс заполнения заявки для пользователя"""
        if self.db.has_application(user_id):
            logger.warning(f"Duplicate application attempt vk_id={user_id}")

            self.client.send(
                user_id,
                "Ваша заявка уже принята. Спасибо за интерес к «Молодой Гвардии»!",
            )
            return

        logger.info(f"Quiz started vk_id={user_id}")

        self.session[user_id] = Session(user_id, self.config.session_timeout)
        self.client.send(
            user_id,
            "Добро пожаловать! Вы начинаете заполнение заявки на вступление в «Молодую Гвардию».\n"
            f"На ответы отводится {self.config.session_timeout // 60} минут. "
            "Если время выйдет — нужно начать заново.\n\n" + STEPS[0].question,
        )

    def process_answer(self, user_id: int, session: Session, text: str) -> None:
        """Обрабатывает ответ пользователя на текущий вопрос анкеты, сохраняет его и переходит к следующему вопросу или завершает анкету"""
        current_step = STEPS[session.step_index]
        ok, error_msg = validate(current_step.key, text)

        if not ok:
            self.client.send(
                user_id, f"{error_msg}\n\n{current_step.question}")
            return

        logger.debug(
            f"Answer saved vk_id={user_id} step={session.step_index} key={current_step.key}"
        )
        session.answers[current_step.key] = text
        session.step_index += 1
        session.touch()

        if session.step_index >= len(STEPS):
            self.finalize_quiz(user_id, session)
        else:
            self.client.send(user_id, STEPS[session.step_index].question)

    def finalize_quiz(self, user_id: int, session: Session) -> None:
        """Завершает анкету, сохраняет её в базе данных и отправляет пользователю сообщение о принятии заявки"""
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

    # Admin Panel команды

    def handle_admin(self, user_id: int, text: str) -> None:
        """Обрабатывает команды администратора, такие как просмотр статистики и управление администраторами и ссылками для рассылки"""
        parts = text.strip().split()
        cmd, args = parts[0].lower(), parts[1:]

        logger.info(f"Admin command vk_id={user_id}: {text!r}")

        match cmd:
            case "/помощь":
                self.client.send(
                    user_id,
                    "Команды администратора:\n"
                    "/статистика — статистика по заявкам\n"
                    "/добавить_админа <vk_id> — добавить администратора\n"
                    "/удалить_админа <vk_id> — удалить администратора\n"
                    "/админы — список всех администраторов\n"
                    "/ссылки_для_рассылок — список ссылок рассылки\n"
                    "/добавить_ссылку <текст> — добавить ссылку\n"
                    "/удалить_ссылку <N> — удалить ссылку №N",
                )
            case "/статистика":
                self.client.send(user_id, format_stats(
                    self.db.collect_stats()))
            case "/добавить_админа":
                self.cmd_addadmin(user_id, args)
            case "/удалить_админа":
                self.cmd_removeadmin(user_id, args)
            case "/админы":
                admins = self.db.list_admins()
                msg = (
                    "Администраторы:\n" + "\n".join(str(a) for a in admins)
                    if admins
                    else "Список администраторов пуст."
                )
                self.client.send(user_id, msg)
            case "/ссылки_для_рассылок":
                self.cmd_list_links(user_id)
            case "/добавить_ссылку":
                self.cmd_add_link(user_id, args)
            case "/удалить_ссылку":
                self.cmd_remove_link(user_id, args)
            case _:
                self.client.send(
                    user_id,
                    f"Неизвестная команда: {cmd}\nНапишите /помощь для списка команд.",
                )

    # Работа с администраторами

    def cmd_addadmin(self, user_id: int, args: list[str]) -> None:
        """Добавляет нового администратора по vk_id, если его нет в списке админов. Сохраняет в базе данных"""
        target, err = parse_vk_id(args)
        if err:
            self.client.send(user_id, f"{err} Пример: /добавить_админа 123456")
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
        """Удаляет администратора по vk_id, если он есть в списке админов и не является суперадмином из config.json. Сохраняет изменения в базе данных"""
        target, err = parse_vk_id(args)
        if err:
            self.client.send(user_id, f"{err} Пример: /удалить_админа 123456")
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

    # Работа со ссылками для рассылки

    def cmd_list_links(self, user_id: int) -> None:
        """Отправляет администратору список ссылок для рассылки, сохранённых в базе данных"""
        links = self.db.get_event_links()
        if not links:
            self.client.send(user_id, "Список ссылок рассылки пуст.")
            return
        lines = ["Ссылки рассылки:"]
        for i, link in enumerate(links, 1):
            lines.append(f"  {i}. {link}")
        self.client.send(user_id, "\n".join(lines))

    def cmd_add_link(self, user_id: int, args: list[str]) -> None:
        """Добавляет новую ссылку для рассылки, если её нет в базе данных. Сохраняет в базе данных"""
        if not args:
            self.client.send(
                user_id, "Укажите текст ссылки: /добавить_ссылку Ссылка на чат: https://vk.me/join/...")
            return
        new_link = " ".join(args)
        self.db.add_event_link(new_link)
        logger.info(f"Link added by vk_id={user_id}: {new_link!r}")
        self.client.send(user_id, f"Ссылка добавлена: {new_link}")

    def cmd_remove_link(self, user_id: int, args: list[str]) -> None:
        """Удаляет ссылку для рассылки по номеру, если она есть в базе данных. Сохраняет изменения в базе данных"""
        idx, err = parse_link_index(args)
        if err:
            self.client.send(user_id, f"{err} Пример: /удалить_ссылку 1")
            return
        removed = self.db.remove_event_link(idx)
        if removed is None:
            count = len(self.db.get_event_links())
            self.client.send(
                user_id, f"Нет ссылки с номером {idx + 1}. Всего ссылок: {count}.")
            return
        logger.info(f"Link {idx + 1} removed by vk_id={user_id}: {removed!r}")
        self.client.send(user_id, f"Ссылка №{idx + 1} удалена: {removed}")
