from datetime import datetime


class Session:
    """
        Хранит состояние пользователя во время опроса:\n
        step_index — текущий вопрос, answers — накопленные ответы,\n
        started_at — момент последнего действия для проверки таймаута
    """

    def __init__(self, vk_id: str, timeout_seconds: int) -> None:
        """
            Создаёт новую сессию с нулевым шагом и пустыми ответами
        """

        self.vk_id = vk_id
        self.timeout_seconds = timeout_seconds
        self.step_index: int = 0
        self.answers: dict[str, str] = {}
        self.started_at: datetime = datetime.now()

    def is_expired(self) -> bool:
        """
            Возвращает True, если с момента последнего действия истёк таймаут
        """

        elapsed = (datetime.now() - self.started_at).total_seconds()
        return elapsed > self.timeout_seconds

    def touch(self) -> None:
        """
            Сбрасывает таймер — вызывать после каждого ответа пользователя
        """

        self.started_at = datetime.now()
