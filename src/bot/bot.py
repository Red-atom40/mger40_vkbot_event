import json
import re
import sqlite3
from datetime import datetime

from loguru import logger

from bot.keyboards import (
    education_keyboard,
    empty_keyboard,
    event_rsvp_keyboard,
    profile_fields_keyboard,
    quiz_stop_inline_keyboard,
    start_keyboard,
    yes_no_keyboard,
)
from bot.vk_client import VkClient
from database.database import Database
from config import Config
from models.quiz import START_COMMANDS, STEPS, Quiz, Session, format_stats
from validation.validator import canonicalize_education_level, validate
from validation.admin_validator import parse_vk_id, parse_link_index, parse_event_index


_VK_MENTION_RE = re.compile(r"\[(?:id|club)\d+\|([^\]]+)\]")
USER_HELP_COMMANDS = {"/помощь", "/help", "помощь", "help"}
USER_STOP_COMMANDS = {"/стоп", "/stop", "стоп", "stop"}
USER_PROFILE_COMMANDS = {"мои данные", "/мои_данные", "/profile"}
USER_EDIT_PROFILE_COMMANDS = {
    "изменить данные",
    "редактировать данные",
    "настроить данные",
}
USER_CANCEL_COMMANDS = {"отмена", "/отмена", "cancel", "/cancel"}

PROFILE_FIELD_BY_LABEL: dict[str, str] = {
    "фио": "fio",
    "дата рождения": "birth_date",
    "регион": "region",
    "город": "city",
    "телефон": "phone",
    "email/telegram": "contact_info",
    "образование": "education_level",
    "членство в ер": "is_member",
    "предыдущие организации": "previous_organizations",
    "учеба/работа": "study_or_work_place",
}

PROFILE_FIELD_TITLE: dict[str, str] = {
    "fio": "ФИО",
    "birth_date": "Дата рождения",
    "region": "Регион",
    "city": "Город",
    "phone": "Телефон",
    "contact_info": "Email/Telegram",
    "education_level": "Образование",
    "is_member": "Членство в ЕР",
    "previous_organizations": "Предыдущие организации",
    "study_or_work_place": "Учеба/работа",
}

PROFILE_FIELD_ORDER: tuple[str, ...] = (
    "fio",
    "birth_date",
    "region",
    "city",
    "phone",
    "contact_info",
    "education_level",
    "is_member",
    "previous_organizations",
    "study_or_work_place",
)

STEP_QUESTION_BY_KEY: dict[str, str] = {
    step.key: step.question for step in STEPS
}
RECENT_EVENTS_LOOKBACK_SECONDS = 30 * 24 * 60 * 60


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
        self.profile_edit_field: dict[int, str] = {}
        self.quiz_stop_prompt_message: dict[int, int] = {}

    def main_keyboard(self, user_id: int) -> str:
        """Возвращает основную клавиатуру в зависимости от статуса анкеты."""
        return start_keyboard(self.db.has_application(user_id))

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
        lower_text = text.lower()
        payload = self._extract_payload(event)

        logger.debug(f"received message from {user_id}: {text!r}")

        if self._handle_quiz_stop_payload(user_id, payload, event):
            return

        if self._handle_rsvp_payload(user_id, payload):
            return

        if lower_text in START_COMMANDS:
            self.start_quiz(user_id)
            return

        if lower_text in USER_HELP_COMMANDS:
            self.send_user_help(user_id)
            return

        if lower_text in USER_STOP_COMMANDS:
            self.cancel_quiz(user_id)
            return

        if lower_text in USER_PROFILE_COMMANDS:
            self.send_profile(user_id)
            return

        if lower_text in USER_EDIT_PROFILE_COMMANDS:
            self.start_profile_edit(user_id)
            return

        if self.db.is_admin(user_id) and text.startswith("/"):
            self.handle_admin(user_id, text)
            return

        event_id = self.db.get_pending_rsvp_event(user_id)
        if event_id:
            self.handle_rsvp(user_id, event_id, text)
            return

        if user_id in self.profile_edit_field:
            if lower_text in USER_CANCEL_COMMANDS:
                del self.profile_edit_field[user_id]
                self.client.send(
                    user_id,
                    "Редактирование отменено.",
                    keyboard=self.main_keyboard(user_id),
                )
                return
            self.process_profile_edit_value(user_id, text)
            return

        selected_field = PROFILE_FIELD_BY_LABEL.get(text.casefold())
        if selected_field is not None:
            self.start_field_edit(user_id, selected_field)
            return

        session = self.session.get(user_id)
        if session is not None and session.is_expired():
            del self.session[user_id]
            session = None

        if session is None:
            self.send_welcome(user_id)
            return

        self.process_answer(user_id, session, text)

    def _extract_payload(self, event) -> dict | None:
        """Извлекает payload из события LongPoll при нажатии кнопки с payload."""
        raw_payload = None
        extra_values = getattr(event, "extra_values", None)
        if isinstance(extra_values, dict):
            raw_payload = extra_values.get("payload")

        if raw_payload is None:
            raw_payload = getattr(event, "payload", None)

        if raw_payload is None:
            return None

        if isinstance(raw_payload, dict):
            return raw_payload

        if isinstance(raw_payload, str):
            try:
                parsed = json.loads(raw_payload)
            except json.JSONDecodeError:
                logger.warning(f"Invalid payload JSON from user {event.user_id}: {raw_payload!r}")
                return None
            return parsed if isinstance(parsed, dict) else None

        return None

    def _handle_rsvp_payload(self, user_id: int, payload: dict | None) -> bool:
        """Сохраняет RSVP-ответ из payload inline-кнопки. Возвращает True, если payload обработан."""
        if not payload or payload.get("type") != "rsvp":
            return False

        event_id = str(payload.get("event_id", "")).strip()
        answer = str(payload.get("answer", "")).strip().lower()

        if not event_id or answer not in ("да", "нет"):
            self.client.send(user_id, "Не удалось обработать ответ. Попробуйте ещё раз.")
            return True

        self.db.save_rsvp_answer(user_id, event_id, answer)
        self._cleanup_rsvp_prompt_message(user_id, event_id)
        logger.info(f"RSVP via payload vk_id={user_id} event={event_id} answer={answer!r}")
        self.client.send(user_id, "Спасибо! Ваш ответ записан.")
        return True

    def _handle_quiz_stop_payload(self, user_id: int, payload: dict | None, event) -> bool:
        """Обрабатывает нажатие inline-кнопки остановки анкеты."""
        if not payload or payload.get("type") != "quiz_stop":
            return False

        message_id = getattr(event, "message_id", None)
        if not isinstance(message_id, int):
            message_id = self.quiz_stop_prompt_message.get(user_id)
        if isinstance(message_id, int):
            self.client.edit_message(
                user_id,
                message_id,
                "Заявка остановлена.",
                keyboard=empty_keyboard(),
            )

        self.quiz_stop_prompt_message.pop(user_id, None)
        self.cancel_quiz(user_id)
        return True

    def _cleanup_rsvp_prompt_message(self, user_id: int, event_id: str) -> None:
        """Очищает второе сообщение RSVP после ответа: редактирует, при ошибке удаляет."""
        message_id = self.db.pop_rsvp_message_id(user_id, event_id)
        if message_id is None:
            return
        edited = self.client.edit_message(
            user_id,
            message_id,
            "Ответ принят.",
            keyboard=empty_keyboard(),
        )
        if edited:
            return

        deleted = self.client.delete_message(message_id, delete_for_all=True)
        if not deleted:
            logger.warning(
                f"Unable to cleanup RSVP message: vk_id={user_id}, event_id={event_id}, message_id={message_id}"
            )

    def handle_rsvp(self, user_id: int, event_id: str, text: str) -> None:
        answer = text.lower().strip()
        if answer not in ("да", "нет"):
            self.client.send(user_id, "Пожалуйста, ответьте «да» или «нет».", keyboard=yes_no_keyboard())
            return
        self.db.save_rsvp_answer(user_id, event_id, answer)
        self._cleanup_rsvp_prompt_message(user_id, event_id)

        logger.info(f"RSVP vk_id={user_id} event={event_id} answer={answer!r}")

        self.client.send(user_id, "Спасибо! Ваш ответ записан.")

    def start_quiz(self, user_id: int) -> None:
        """Начинает новый сеанс заполнения заявки для пользователя"""
        self.profile_edit_field.pop(user_id, None)

        if self.db.has_application(user_id):
            logger.warning(f"Duplicate application attempt vk_id={user_id}")

            self.client.send(
                user_id,
                "Ваша заявка уже принята. Если нужно изменить данные, нажмите «Мои данные».",
                keyboard=self.main_keyboard(user_id),
            )
            return

        logger.info(f"Quiz started vk_id={user_id}")

        self.send_pinned_start_message(user_id)
        self.session[user_id] = Session(user_id, self.config.session_timeout)
        self.client.send(
            user_id,
            "Добро пожаловать! Вы начинаете заполнение заявки на вступление в «Молодую Гвардию».\n"
            f"На ответы отводится {self.config.session_timeout // 60} минут. "
            "Если время выйдет — нужно начать заново.",
            keyboard=empty_keyboard(),
        )
        stop_message_id = self.client.send(
            user_id,
            "Для досрочного завершения введите /стоп или нажмите \"Остановить анкету\".",
            keyboard=quiz_stop_inline_keyboard(),
        )
        if stop_message_id is not None:
            self.quiz_stop_prompt_message[user_id] = stop_message_id
        else:
            self.quiz_stop_prompt_message.pop(user_id, None)

        self.client.send(
            user_id,
            STEPS[0].question,
            keyboard=empty_keyboard(),
        )

    def cancel_quiz(self, user_id: int) -> None:
        """Прерывает текущую анкету пользователя по его команде."""
        self.quiz_stop_prompt_message.pop(user_id, None)
        session = self.session.pop(user_id, None)
        if session is None:
            self.client.send(
                user_id,
                "Активной анкеты нет.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        logger.info(f"Quiz canceled vk_id={user_id}")
        self.client.send(
            user_id,
            "Заявка остановлена. Чтобы начать заново, нажмите «Заявка» или введите /start.",
            keyboard=self.main_keyboard(user_id),
        )

    def send_user_help(self, user_id: int) -> None:
        """Отправляет список пользовательских команд и кнопку старта анкеты."""
        self.client.send(
            user_id,
            self._main_commands_text(),
            keyboard=self.main_keyboard(user_id),
        )

    def send_pinned_start_message(self, user_id: int) -> None:
        """Отправляет приветствие с основными командами и закрепляет его в чате."""
        message_id = self.client.send(
            user_id,
            "Привет! Добро пожаловать в «Молодую Гвардию».\n\n" + self._main_commands_text(),
            keyboard=self.main_keyboard(user_id),
        )
        if message_id is None:
            return

        pinned = self.client.pin_message(user_id, message_id)
        if not pinned:
            logger.warning(f"Unable to pin start message: vk_id={user_id}, message_id={message_id}")

    def _main_commands_text(self) -> str:
        """Возвращает единый текст с основными пользовательскими командами."""
        return (
            "Основные команды:\n"
            "/заявка — начать заполнение анкеты\n"
            "/стоп — прервать текущую анкету\n"
            "Мои данные — посмотреть сохранённые данные\n"
            "/помощь — подсказка по командам\n\n"
            "Также можно пользоваться кнопками ниже."
        )

    def send_welcome(self, user_id: int) -> None:
        """Отправляет приветствие с кнопкой старта анкеты."""
        if self.db.has_application(user_id):
            self.client.send(
                user_id,
                "Привет! Ваша анкета уже сохранена.\n"
                "Нажмите «Мои данные», чтобы посмотреть или изменить информацию.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        self.client.send(
            user_id,
            "Привет! Добро пожаловать в «Молодую Гвардию».\n"
            "Чтобы подать заявку, нажмите кнопку «Заявка» или напишите /start.\n"
            "Чтобы прервать анкету в любой момент, введите /стоп.",
            keyboard=self.main_keyboard(user_id),
        )

    def _format_application(self, app: dict) -> str:
        """Форматирует анкету пользователя в многострочный текст."""
        lines = ["Ваши данные:"]
        for field in PROFILE_FIELD_ORDER:
            title = PROFILE_FIELD_TITLE[field]
            lines.append(f"{title}: {app.get(field, '')}")
        return "\n".join(lines)

    def send_profile(self, user_id: int) -> None:
        """Отправляет пользователю сохраненные данные анкеты."""
        app = self.db.get_application(user_id)
        if app is None:
            self.client.send(
                user_id,
                "У вас пока нет сохранённой анкеты. Нажмите «Заявка», чтобы заполнить её.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        self.client.send(
            user_id,
            self._format_application(app),
            keyboard=self.main_keyboard(user_id),
        )

    def start_profile_edit(self, user_id: int) -> None:
        """Запускает режим выбора поля для редактирования анкеты."""
        if user_id in self.session:
            self.client.send(
                user_id,
                "Сейчас вы заполняете анкету. Введите /стоп, чтобы прервать её и перейти к редактированию данных.",
                keyboard=empty_keyboard(),
            )
            return

        if self.db.get_application(user_id) is None:
            self.client.send(
                user_id,
                "У вас пока нет сохранённой анкеты. Нажмите «Заявка», чтобы заполнить её.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        self.client.send(
            user_id,
            "Выберите поле, которое хотите изменить.",
            keyboard=profile_fields_keyboard(),
        )

    def start_field_edit(self, user_id: int, field_key: str) -> None:
        """Переходит к вводу нового значения выбранного поля анкеты."""
        if user_id in self.session:
            self.client.send(
                user_id,
                "Сейчас вы заполняете анкету. Введите /стоп, чтобы прервать её и перейти к редактированию данных.",
                keyboard=empty_keyboard(),
            )
            return

        if self.db.get_application(user_id) is None:
            self.client.send(
                user_id,
                "У вас пока нет сохранённой анкеты. Нажмите «Заявка», чтобы заполнить её.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        self.profile_edit_field[user_id] = field_key
        question = STEP_QUESTION_BY_KEY.get(field_key, "Введите новое значение:")
        if field_key == "education_level":
            question += "\nЕсли выберете «иное», следующим сообщением укажите какое именно."

        self.client.send(
            user_id,
            question,
            keyboard=self.keyboard_for_step(field_key),
        )

    def process_profile_edit_value(self, user_id: int, text: str) -> None:
        """Валидирует и сохраняет новое значение выбранного поля анкеты."""
        field_key = self.profile_edit_field.get(user_id)
        if field_key is None:
            return

        app = self.db.get_application(user_id)
        if app is None:
            del self.profile_edit_field[user_id]
            self.client.send(
                user_id,
                "Анкета не найдена. Нажмите «Заявка», чтобы заполнить её заново.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        answers = {k: str(v) for k, v in app.items()}

        if field_key == "education_level":
            ok, error_msg = validate("education_level", text, answers)
            if not ok:
                self.client.send(
                    user_id,
                    f"{error_msg}\n\n{STEP_QUESTION_BY_KEY['education_level']}",
                    keyboard=education_keyboard(),
                )
                return

            canonical_education = canonicalize_education_level(text)
            if canonical_education is None:
                self.client.send(
                    user_id,
                    "Выберите образование кнопкой из предложенных вариантов.",
                    keyboard=education_keyboard(),
                )
                return

            if canonical_education == "иное":
                self.profile_edit_field[user_id] = "education_other"
                self.client.send(
                    user_id,
                    "Укажите, пожалуйста, какое у вас образование:",
                    keyboard=empty_keyboard(),
                )
                return

            self.db.update_application_field(user_id, "education_level", canonical_education)
            del self.profile_edit_field[user_id]
            self.client.send(
                user_id,
                f"Поле «{PROFILE_FIELD_TITLE['education_level']}» обновлено.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        if field_key == "education_other":
            ok, error_msg = validate("education_other", text, answers)
            if not ok:
                self.client.send(
                    user_id,
                    f"{error_msg}\n\nУкажите, пожалуйста, какое у вас образование:",
                    keyboard=empty_keyboard(),
                )
                return

            self.db.update_application_field(user_id, "education_level", f"иное: {text.strip()}")
            del self.profile_edit_field[user_id]
            self.client.send(
                user_id,
                f"Поле «{PROFILE_FIELD_TITLE['education_level']}» обновлено.",
                keyboard=self.main_keyboard(user_id),
            )
            return

        new_value = text.strip()
        ok, error_msg = validate(field_key, new_value, answers)
        if not ok:
            question = STEP_QUESTION_BY_KEY.get(field_key, "Введите новое значение:")
            self.client.send(
                user_id,
                f"{error_msg}\n\n{question}",
                keyboard=self.keyboard_for_step(field_key),
            )
            return

        if field_key == "region":
            current_city = str(app.get("city", "")).strip()
            if current_city:
                city_ok, city_error = validate("city", current_city, {"region": new_value})
                if not city_ok:
                    self.client.send(
                        user_id,
                        "Нельзя обновить регион без города. Текущий город не относится к выбранному региону. "
                        "Сначала измените город, затем регион.",
                        keyboard=profile_fields_keyboard(),
                    )
                    return

        if field_key == "city":
            region = str(app.get("region", "")).strip()
            ok, error_msg = validate("city", new_value, {"region": region})
            if not ok:
                question = STEP_QUESTION_BY_KEY.get("city", "Введите новое значение:")
                self.client.send(
                    user_id,
                    f"{error_msg}\n\n{question}",
                    keyboard=self.keyboard_for_step("city"),
                )
                return

        self.db.update_application_field(user_id, field_key, new_value)
        del self.profile_edit_field[user_id]
        self.client.send(
            user_id,
            f"Поле «{PROFILE_FIELD_TITLE[field_key]}» обновлено.",
            keyboard=self.main_keyboard(user_id),
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
        registration_ts = datetime.now().timestamp()
        quiz = Quiz.from_answers(session.answers, user_id)
        quiz.created_at = registration_ts
        try:
            self.db.save_application(quiz)
        except sqlite3.Error as e:
            logger.error(f"DB error vk_id={user_id}: {e}")
            self.client.send(
                user_id,
                "Не удалось сохранить заявку из-за внутренней ошибки. Попробуйте ещё раз позже.",
            )
            return

        logger.info(f"Application accepted vk_id={user_id}")

        del self.session[user_id]
        self.quiz_stop_prompt_message.pop(user_id, None)
        self.client.send(
            user_id,
            "Ваша заявка успешно принята!\nМы рассмотрим её в ближайшее время и свяжемся с вами.",
            keyboard=self.main_keyboard(user_id),
        )
        self._send_recent_events_after_registration(user_id, registration_ts)

    def _send_recent_events_after_registration(self, user_id: int, registration_ts: float) -> None:
        """Отправляет новому участнику мероприятия за последний месяц до регистрации."""
        events = self.db.get_recent_events_for_user(
            user_id,
            before_ts=registration_ts,
            within_seconds=RECENT_EVENTS_LOOKBACK_SECONDS,
        )
        if not events:
            return

        self.client.send(
            user_id,
            "Отправляю мероприятия, опубликованные за последний месяц до вашего вступления.",
        )
        for event in events:
            event_id = str(event["event_id"])
            message_text = str(event.get("message_text", "")).strip()
            if not message_text:
                message_text = str(event.get("title", "")).strip() or (
                    f"Мероприятие от {format_event_id(event_id)}"
                )

            self.db.add_pending_rsvp(user_id, event_id)
            self.client.send(user_id, message_text)
            question_message_id = self.client.send(
                user_id,
                "Вы планируете посетить это мероприятие?",
                keyboard=event_rsvp_keyboard(event_id),
            )
            if question_message_id is not None:
                self.db.save_rsvp_message(user_id, event_id, question_message_id)

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
            case "/помощь_админ":
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
                    f"Неизвестная команда: {cmd}\nНапишите /помощь_админ для списка команд.",
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
