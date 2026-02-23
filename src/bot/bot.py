import sqlite3

from loguru import logger

from domain.quiz import Quiz
from domain.step import STEPS, START_COMMANDS

from bot.client import VkClient
from config import Config
from database.database import Database
from domain.session import Session
from validation.validators import validate



class VKBot:
    """
        Основной класс бота: слушает LongPoll, ведёт опрос по шагам STEPS
        и сохраняет заявки через Database
    """

    def __init__(self, config: Config, db: Database, client: VkClient) -> None:
        """
            Принимает конфиг, репозиторий заявок и VK-клиент
        """

        self.config = config
        self.db = db
        self._client = client
        self._sessions: dict[str, Session] = {}

    def run(self) -> None:
        """
            Запускает бесконечный цикл LongPoll и передаёт события в _handle_message
        """

        logger.info("VK Bot is running... Press Ctrl+C to stop.")

        try:
            for event in self._client.listen():
                try:
                    self._handle_message(event)
                except Exception as e:
                    logger.exception(f"Error handling message: {e}")
        except KeyboardInterrupt:
            logger.info("VK Bot stopped by user.")

    def _handle_message(self, event) -> None:
        """
            Роутер входящих сообщений: старт опроса или следующий шаг
        """

        vk_id = str(event.user_id)
        text = event.text.strip()

        logger.debug(f"Received message from vk_id={vk_id}: {text!r}")

        # Пользователь хочет начать опрос
        if text.lower() in START_COMMANDS:
            self._start_quiz(vk_id, event.user_id)
            return

        session = self._get_active_session(vk_id)

        if session is None:
            # Нет активной сессии — подсказываем как начать
            self._client.send(
                event.user_id,
                'Здравствуйте! Отправьте «вступить», чтобы подать заявку в «Молодую Гвардию».',
            )
            return

        self._process_answer(vk_id, event.user_id, session, text)

    def _start_quiz(self, vk_id: str, user_id: int) -> None:
        """
            Создаёт сессию и отправляет первый вопрос; отказывает, если заявка уже есть
        """

        # Проверяем, есть ли уже заявка от этого пользователя
        if self.db.has_application(vk_id):
            logger.warning(f"Duplicate application attempt vk_id={vk_id}")
            self._client.send(
                user_id, "Ваша заявка уже принята. Спасибо за интерес к «Молодой Гвардии»!")
            return

        logger.info(f"Quiz started vk_id={vk_id}")
        session = Session(vk_id, self.config.session_timeout)
        self._sessions[vk_id] = session

        # Отправляем приветственное сообщение и первый вопрос
        self._client.send(
            user_id,
            (
                "Добро пожаловать! Вы начинаете заполнение заявки на вступление в «Молодую Гвардию».\n"
                f"На ответы отводится {self.config.session_timeout // 60} минут. "
                "Если время выйдет — нужно начать заново.\n\n"
                + STEPS[0].question
            ),
        )

    def _process_answer(
        self, vk_id: str, user_id: int, session: Session, text: str
    ) -> None:
        """
            Валидирует ответ, сохраняет его в сессии и отправляет следующий вопрос\n
            При ошибке валидации повторяет текущий вопрос с пояснением
        """

        # Валидируем ответ на текущий вопрос
        current_step = STEPS[session.step_index]
        ok, error_msg = validate(current_step.key, text)

        if not ok:
            self._client.send(
                user_id, f"{error_msg}\n\n{current_step.question}")
            return

        # Сохраняем ответ и переходим к следующему шагу
        logger.debug(f"Answer saved vk_id={vk_id} step={session.step_index} key={current_step.key}")
        session.answers[current_step.key] = text
        session.step_index += 1
        session.touch()

        if session.step_index >= len(STEPS):
            self._finalize_quiz(vk_id, user_id, session)
        else:
            self._client.send(user_id, STEPS[session.step_index].question)

    def _finalize_quiz(self, vk_id: str, user_id: int, session: Session) -> None:
        """
            Сохраняет готовую заявку в БД, удаляет сессию и благодарит пользователя
        """

        # Сохраняем заявку в базе данных
        logger.info(f"Saving application vk_id={vk_id}")
        try:
            self.db.save_application(Quiz.from_answers(session.answers, vk_id))
        except sqlite3.Error as e:
            logger.error(f"DB error vk_id={vk_id}: {e}")
            self._client.send(
                user_id,
                "Не удалось сохранить заявку из-за внутренней ошибки. Попробуйте ещё раз позже.",
            )
            return

        logger.info(f"Application accepted vk_id={vk_id}")
        del self._sessions[vk_id]

        self._client.send(
            user_id,
            (
                "Ваша заявка успешно принята!\n"
                "Мы рассмотрим её в ближайшее время и свяжемся с вами."
            ),
        )

    def _get_active_session(self, vk_id: str) -> Session | None:
        """
            Возвращает активную сессию или None; просроченную сессию удаляет
        """

        # Проверяем, есть ли сессия для данного vk_id
        session = self._sessions.get(vk_id)
        if session is None:
            return None

        # Проверяем, не истек ли таймаут сессии
        if session.is_expired():
            del self._sessions[vk_id]
            return None

        return session
