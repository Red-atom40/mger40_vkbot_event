import re
import sqlite3

from loguru import logger

from bot.keyboards import education_keyboard, empty_keyboard, start_keyboard, yes_no_keyboard
from bot.vk_client import VkClient
from database.database import Database
from config import Config
from models.quiz import START_COMMANDS, STEPS, Quiz, Session, format_stats
from validation.validator import canonicalize_education_level, validate
from validation.admin_validator import parse_vk_id, parse_link_index, parse_event_index


_VK_MENTION_RE = re.compile(r"\[(?:id|club)\d+\|([^\]]+)\]")
USER_HELP_COMMANDS = {"/помощь", "/help", "помощь", "help"}


def format_event_id(event_id: str) -> str:
    """Форматирует event_id (YYYYMMDDHHMMSS) в удобочитаемый вид ДД.ММ.ГГГГ ЧЧ:ММ"""
    try:
        return (
            f"{event_id[6:8]}.{event_id[4:6]}.{event_id[:4]} "
            f"{event_id[8:10]}:{event_id[10:12]}"
        )
    except IndexError:
        return event_id


# Нужно для удаления упоминаний в виде [id123|@username] из текста сообщений
def strip_vk_mentions(text: str) -> str:
    """Заменяет VK-теги упоминаний ([id123|@username]) на их отображаемый текст."""
    return _VK_MENTION_RE.sub(r"\1", text)


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
        text = strip_vk_mentions(event.text).strip()

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

        if text.lower() in USER_HELP_COMMANDS:
            self.send_user_help(user_id)
            return

        session = self.session.get(user_id)
        if session is not None and session.is_expired():
            del self.session[user_id]
            session = None

        if session is None:
            self.send_welcome(user_id)
            return

        self.process_answer(user_id, session, text)

    def handle_rsvp(self, user_id: int, event_id: str, text: str) -> None:
        answer = text.lower().strip()
        if answer not in ("да", "нет"):
            self.client.send(user_id, "Пожалуйста, ответьте «да» или «нет».", keyboard=yes_no_keyboard())
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
            keyboard=empty_keyboard(),
        )

    def send_user_help(self, user_id: int) -> None:
        """Отправляет список пользовательских команд и кнопку старта анкеты."""
        self.client.send(
            user_id,
            "Команды пользователя:\n"
            "/start — начать заполнение анкеты\n"
            "/заявка — начать заполнение анкеты\n"
            "/помощь — подсказка по командам\n\n"
            "Также можно нажать кнопку «Заявка» ниже.",
            keyboard=start_keyboard(),
        )

    def send_welcome(self, user_id: int) -> None:
        """Отправляет приветствие с кнопкой старта анкеты."""
        self.client.send(
            user_id,
            "Привет! Добро пожаловать в «Молодую Гвардию».\n"
            "Чтобы подать заявку, нажмите кнопку «Заявка» или напишите /start.",
            keyboard=start_keyboard(),
        )

    def keyboard_for_step(self, step_key: str) -> str | None:
        """Возвращает клавиатуру для конкретного шага анкеты."""
        if step_key == "education_level":
            return education_keyboard()
        if step_key == "is_member":
            return yes_no_keyboard()
        return None

    def _skip_optional_steps(self, session: Session) -> None:
        """Пропускает условные шаги анкеты, которые не нужны для текущих ответов."""
        while session.step_index < len(STEPS):
            step = STEPS[session.step_index]
            if step.key == "education_other" and session.answers.get("education_level") != "иное":
                session.step_index += 1
                continue
            break

    def process_answer(self, user_id: int, session: Session, text: str) -> None:
        """Обрабатывает ответ пользователя на текущий вопрос анкеты, сохраняет его и переходит к следующему вопросу или завершает анкету"""
        self._skip_optional_steps(session)
        if session.step_index >= len(STEPS):
            self.finalize_quiz(user_id, session)
            return

        current_step = STEPS[session.step_index]
        ok, error_msg = validate(current_step.key, text, session.answers)

        if not ok:
            self.client.send(
                user_id,
                f"{error_msg}\n\n{current_step.question}",
                keyboard=self.keyboard_for_step(current_step.key),
            )
            return

        if current_step.key == "education_level":
            canonical_education = canonicalize_education_level(text)
            if canonical_education is None:
                self.client.send(
                    user_id,
                    "Выберите образование кнопкой из предложенных вариантов.",
                    keyboard=education_keyboard(),
                )
                return
            text = canonical_education

        logger.debug(
            f"Answer saved vk_id={user_id} step={session.step_index} key={current_step.key}"
        )
        session.answers[current_step.key] = text
        if current_step.key == "education_other":
            session.answers["education_level"] = f"иное: {text.strip()}"

        session.step_index += 1
        self._skip_optional_steps(session)
        session.touch()

        if session.step_index >= len(STEPS):
            self.finalize_quiz(user_id, session)
        else:
            next_step = STEPS[session.step_index]
            self.client.send(
                user_id,
                next_step.question,
                keyboard=self.keyboard_for_step(next_step.key),
            )

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
            keyboard=empty_keyboard(),
        )

    # Admin Panel команды

    def _send_long(self, user_id: int, text: str, chunk_size: int = 4000) -> None:
        """Отправляет длинное сообщение, разбивая его на части по chunk_size символов"""
        while text:
            self.client.send(user_id, text[:chunk_size])
            text = text[chunk_size:]

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
                    "/удалить_ссылку <N> — удалить ссылку №N\n"
                    "/мероприятия — список мероприятий и статистика ответов\n"
                    "/участники <N> — список участников мероприятия №N с контактами",
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
            case "/мероприятия":
                self.cmd_list_events(user_id)
            case "/участники":
                self.cmd_event_participants(user_id, args)
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

    # Работа с мероприятиями и участниками

    def cmd_list_events(self, user_id: int) -> None:
        """Отправляет администратору список мероприятий со статистикой ответов"""
        events = self.db.get_events_list()
        if not events:
            self.client.send(user_id, "Мероприятия не найдены.")
            return
        lines = ["Мероприятия:"]
        for i, e in enumerate(events, 1):
            label = format_event_id(e["event_id"])
            title = f" «{e['title']}»" if e["title"] else ""
            lines.append(
                f"  {i}. {label}{title}\n"
                f"     приглашено: {e['total']}, "
                f"придут: {e['yes_count']}, не придут: {e['no_count']}, ожидаем: {e['pending_count']}"
            )
        self.client.send(user_id, "\n".join(lines))

    def cmd_event_participants(self, user_id: int, args: list[str]) -> None:
        """Отправляет администратору список подтверждённых участников мероприятия с контактными данными"""
        idx, err = parse_event_index(args)
        if err:
            self.client.send(user_id, f"{err} Пример: /участники 1")
            return
        events = self.db.get_events_list()
        if idx >= len(events):
            self.client.send(
                user_id,
                f"Мероприятие №{idx + 1} не найдено. Всего мероприятий: {len(events)}.",
            )
            return
        event_id = events[idx]["event_id"]
        participants = self.db.get_event_participants(event_id)
        label = format_event_id(event_id)
        if not participants:
            self.client.send(
                user_id,
                f"Нет подтверждённых участников для мероприятия от {label}.",
            )
            return
        lines = [f"Участники мероприятия от {label} (подтвердили: {len(participants)}):"]
        for i, p in enumerate(participants, 1):
            lines.append(
                f"{i}. {p['fio']}\n"
                f"   Тел: {p['phone']} | Email/TG: {p['contact_info']}\n"
                f"   Город: {p['city']}, {p['region']} | VK ID: {p['vk_id']}"
            )
        logger.info(f"Participants list for event {event_id} sent to vk_id={user_id}")
        self._send_long(user_id, "\n".join(lines))
