import os
from cryptography.fernet import Fernet


class Encryptor:
    """
        Шифрует и расшифровывает строки алгоритмом Fernet\n
        Ключ хранится в файле key_path; при первом запуске генерируется автоматически\n
        Без key_path файла расшифровать данные невозможно
    """

    def __init__(self, key_path: str) -> None:
        """
            Загружает или создаёт ключ по пути key_path и инициализирует Fernet
        """

        self._fernet = Fernet(self._load_or_create_key(key_path))

    @staticmethod
    def _load_or_create_key(key_path: str) -> bytes:
        """
            Загружает ключ из файла или генерирует новый, если файл не существует
        """

        # Если файл с ключом уже существует, читаем его
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        # Иначе генерируем новый ключ и сохраняем его в файл
        key = Fernet.generate_key()
        with open(key_path, "wb") as f:
            f.write(key)
        return key

    def encrypt(self, plaintext: str) -> str:
        """
            Шифрует строку и возвращает результат в виде base64-строки
        """

        return self._fernet.encrypt(plaintext.encode()).decode()
