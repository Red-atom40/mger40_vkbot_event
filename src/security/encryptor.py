import os

from cryptography.fernet import Fernet


class Encryptor:
    def __init__(self, key_path: str) -> None:
        """Инициализатор класса Encryptor, который отвечает за шифрование данных перед сохранением в БД\n"""
        self.fernet = Fernet(self._load_or_create_key(key_path))

    def encrypt(self, data: str) -> str:
        return self.fernet.encrypt(data.encode()).decode()

    @staticmethod
    def _load_or_create_key(key_path: str) -> bytes:
        # Ищем файл с ключом
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        # Если файла нет, создаём новый ключ
        else:
            key = Fernet.generate_key()
            with open(key_path, "wb") as f:
                f.write(key)
            return key
