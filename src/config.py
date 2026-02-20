import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """
        Класс конфигурации, который читает необходимые 
        параметры из переменных окружения

        - vk_token
        - session_timeout
        - db_path
        - key_path
    """

    def __init__(self) -> None:
        """
            Инициализирует конфигурацию, загружая параметры из переменных окружения

            :return: Ничего не возвращает
        """

        self.vk_token: str = os.getenv("VK_TOKEN", "")
        self.session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "600"))
        self.db_path: str = os.getenv("DB_PATH", "../quiz.db")
        self.key_path: str = os.getenv("KEY_PATH", "../secret.key")
