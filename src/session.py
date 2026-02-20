from datetime import datetime


class Session:
    """
        Хранит состояние одного пользователя в процессе прохождения опроса

        - step_index — индекс текущего вопроса в STEPS
        - answers    — накопленные ответы {ключ_поля: ответ}
        - started_at — момент последнего действия; используется для проверки таймаута
    """

    def __init__(self, vk_id: str, timeout_seconds: int) -> None:
        """
            Инициализирует сессию для пользователя

            :param vk_id: Идентификатор пользователя (строка)
            :param timeout_seconds: Сколько секунд даётся на прохождение опроса
            :return: Ничего не возвращает
        """

        self.vk_id = vk_id
        self.timeout_seconds = timeout_seconds
        self.step_index: int = 0
        self.answers: dict[str, str] = {}
        self.started_at: datetime = datetime.now()

    def is_expired(self) -> bool:
        """
            Проверяет, истёк ли таймаут с момента последнего действия

            :return: bool — True, если таймаут истёк, иначе False
        """

        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    def touch(self) -> None:
        """
            Обновить таймер после каждого ответа пользователя

            :return: Ничего не возвращает
        """

        self.started_at = datetime.now()
