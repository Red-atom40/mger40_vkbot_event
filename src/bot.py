import random
from typing import NamedTuple

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from config import Config
from database import Database
from session import Session
from validation import validate


class Step(NamedTuple):
    """
        Один шаг опроса: ключ поля (key) и текст вопроса (question)
    """

    key: str
    question: str


STEPS: list[Step] = [
    Step("fio",                    "Введите ваше ФИО полностью (Фамилия Имя Отчество):"),
    Step("birth_date",             "Дата рождения (ДД.ММ.ГГГГ):"),
    Step("region",                 "Регион постоянной регистрации:"),
    Step("city",                   "Город / населённый пункт:"),
    Step("street",                 "Улица:"),
    Step("house",                  "Дом / корпус / квартира:"),
    Step("passport_number",
         "Серия и номер паспорта (без пробелов, например 4519123456):"),
    Step("passport_issued_by",     "Кем выдан паспорт:"),
    Step("passport_issue_date",    "Дата выдачи паспорта (ДД.ММ.ГГГГ):"),
    Step("phone",                  "Контактный телефон (+7...):"),
    Step("contact_info",           "Email / Telegram:"),
    Step("education_level",
         "Образование:\n  школьное / среднее специальное / высшее / иное"),
    Step("is_member",
         "Являетесь ли вы членом партии «Единая Россия»? (да / нет):"),
    Step("previous_organizations",
         "В каких молодёжных / политических организациях состояли ранее?\n(если нигде — напишите «нет»)"),
    Step("study_or_work_place",    "Место учёбы / работы (название и город):"),
]

# Команды, которые запускают опрос
START_COMMANDS = {"вступить", "заявка", "/start", "start"}


class VKBot:
    """
        Основной класс бота: слушает LongPoll, ведёт опрос по шагам STEPS
        и сохраняет заявки через Database
    """

    def __init__(self, config: Config, db: Database) -> None:
        """
            Инициализирует VK API, LongPoll и подключает базу данных
        """

        self.config = config
        self.db = db
        self._sessions: dict[str, Session] = {}
        self._vk_session = vk_api.VkApi(token=config.vk_token)
        self._vk = self._vk_session.get_api()
        self._longpoll = VkLongPoll(self._vk_session)

    def run(self) -> None:
        """
            Запускает бесконечный цикл LongPoll и передаёт события в _handle_message
        """

        print("Бот запущен. Нажмите Ctrl+C для остановки.")

        for event in self._longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self._handle_message(event)

    def _handle_message(self, event) -> None:
        """
            Роутер входящих сообщений: старт опроса или следующий шаг
        """

        vk_id = str(event.user_id)
        text = event.text.strip()

        # Пользователь хочет начать опрос
        if text.lower() in START_COMMANDS:
            self._start_quiz(vk_id, event.user_id)
            return

        session = self._get_active_session(vk_id)

        if session is None:
            # Нет активной сессии — подсказываем как начать
            self._send(
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
            self._send(
                user_id, "Ваша заявка уже принята. Спасибо за интерес к «Молодой Гвардии»!")
            return

        session = Session(vk_id, self.config.session_timeout)
        self._sessions[vk_id] = session

        # Отправляем приветственное сообщение и первый вопрос
        self._send(
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
            self._send(user_id, f"{error_msg}\n\n{current_step.question}")
            return

        # Сохраняем ответ и переходим к следующему шагу
        session.answers[current_step.key] = text
        session.step_index += 1
        session.touch()

        if session.step_index >= len(STEPS):
            self._finalize_quiz(vk_id, user_id, session)
        else:
            self._send(user_id, STEPS[session.step_index].question)

    def _finalize_quiz(self, vk_id: str, user_id: int, session: Session) -> None:
        """
            Сохраняет готовую заявку в БД, удаляет сессию и благодарит пользователя
        """

        # Сохраняем заявку в базе данных
        self.db.save_application(session.answers, vk_id)
        del self._sessions[vk_id]

        self._send(
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

    def _send(self, user_id: int, message: str) -> None:
        """
            Отправляет текстовое сообщение пользователю через VK API
        """

        self._vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=random.getrandbits(31),
        )
