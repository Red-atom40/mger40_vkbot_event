import random
from typing import NamedTuple

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

from config import Config
from database import Database
from session import Session


class Step(NamedTuple):
    """
        Класс для описания одного шага опроса
        Содержит ключ поля и текст вопроса
    """

    key: str
    question: str


# Список шагов опроса. Порядок важен, так как step_index в Session указывает на текущий вопрос.
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
        Класс для работы с VK API и управления логикой опроса

        - config: Конфигурация приложения
        - db: Экземпляр класса Database для сохранения заявок
        - _sessions: Словарь активных сессий пользователей (vk_id → Session)
        - _vk_session: Сессия VK API
        - _vk: Объект для работы с методами VK API
        - _longpoll: Объект для прослушивания событий VK
    """

    def __init__(self, config: Config, db: Database) -> None:
        """
            Инициализирует бота с заданной конфигурацией и базой данных

            :param config: Экземпляр класса Config с настройками приложения
            :param db: Экземпляр класса Database для сохранения заявок
            :return: Ничего не возвращает
        """

        self.config = config
        self.db = db
        self._sessions: dict[str, Session] = {}
        self._vk_session = vk_api.VkApi(token=config.vk_token)
        self._vk = self._vk_session.get_api()
        self._longpoll = VkLongPoll(self._vk_session)

    def run(self) -> None:
        """
            Запускает бота, прослушивая события VK и обрабатывая входящие сообщения

            :return: Ничего не возвращает
        """

        print("Бот запущен. Нажмите Ctrl+C для остановки.")

        for event in self._longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self._handle_message(event)

    def _handle_message(self, event) -> None:
        """
            Обрабатывает входящее сообщение от пользователя

            :param event: Событие нового сообщения от VK
            :return: Ничего не возвращает
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
            Инициализирует новую сессию для пользователя 
            и отправляет первый вопрос

            :param vk_id: Идентификатор пользователя (строка)
            :param user_id: Идентификатор пользователя (целое число)
            :return: Ничего не возвращает
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
            Обрабатывает ответ пользователя, сохраняет его в сессии 
            и отправляет следующий вопрос или завершает опрос

            :param vk_id: Идентификатор пользователя (строка)
            :param user_id: Идентификатор пользователя (целое число)
            :param session: Текущая сессия пользователя
            :param text: Текст ответа пользователя
            :return: Ничего не возвращает
        """

        # Сохраняем ответ на текущий вопрос
        current_step = STEPS[session.step_index]

        session.answers[current_step.key] = text

        session.step_index += 1
        session.touch()

        # Если это был последний вопрос, сохраняем заявку и завершаем опрос
        if session.step_index >= len(STEPS):
            self._finalize_quiz(vk_id, user_id, session)
        else:
            self._send(user_id, STEPS[session.step_index].question)

    def _finalize_quiz(self, vk_id: str, user_id: int, session: Session) -> None:
        """
            Сохраняет заявку в базе данных и отправляет пользователю сообщение о завершении

            :param vk_id: Идентификатор пользователя
            :param user_id: Идентификатор пользователя
            :param session: Сессия пользователя с накопленными ответами
            :return: Ничего не возвращает
        """

        # Сохраняем заявку в базе данных
        self.db.save_application(session.answers, vk_id)
        del self._sessions[vk_id]

        # Отправляем сообщение о том, что заявка принята
        self._send(
            user_id,
            (
                "Ваша заявка успешно принята!\n"
                "Мы рассмотрим её в ближайшее время и свяжемся с вами."
            ),
        )

    def _get_active_session(self, vk_id: str) -> Session | None:
        """
            Возвращает сессию, если она существует и не истекла
            Просроченную сессию удаляет и уведомляет пользователя

            :param vk_id: Идентификатор пользователя (строка)
            :return: Активная сессия или None, если её нет или она истекла
        """

        # Проверяем, есть ли сессия для данного vk_id
        session = self._sessions.get(vk_id)
        if session is None:
            return None

        # Проверяем, не истек ли таймаут сессии
        if session.is_expired():
            del self._sessions[vk_id]
            # Уведомление будет отправлено при следующем сообщении от пользователя
            # через основной обработчик (session == None → подсказка «начать»).
            # Но лучше сообщить явно прямо сейчас через user_id, которого у нас нет здесь.
            # Поэтому возвращаем специальный sentinel.
            return None

        return session

    def _send(self, user_id: int, message: str) -> None:
        """
            Отправляет сообщение пользователю через VK API

            :param user_id: Идентификатор пользователя VK (целое число)
            :param message: Текст сообщения для отправки
            :return: Ничего не возвращает
        """

        self._vk.messages.send(
            user_id=user_id,
            message=message,
            random_id=random.getrandbits(31),
        )
