import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """
        Читает параметры из переменных окружения или .env файла:\n
        vk_token, session_timeout, db_path, key_path, log_level, log_format
    """

    def __init__(self) -> None:
        """
            Загружает параметры из переменных окружения
        """

        self.vk_token: str = os.getenv("VK_TOKEN", "")
        self.session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "600"))
        self.db_path: str = os.getenv("DB_PATH", "../quiz.db")
        self.key_path: str = os.getenv("KEY_PATH", "../secret.key")
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        self.log_format: str = os.getenv("LOG_FORMAT", "text").lower()
