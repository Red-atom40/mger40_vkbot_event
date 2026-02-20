import os
from cryptography.fernet import Fernet


class Encryptor:
    """
        Этот класс отвечает за шифрование и расшифровку строк с помощью симметричного алгоритма cryptography.fernet
        Ключ хранится в файле key_path. При первом запуске ключ генерируется автоматически

        Если не указать .key становится невозможно расшифровать данные
    """

    def __init__(self, key_path: str) -> None:
        """
            Инициализирует Encryptor, загружая или создавая ключ

            :param key_path: Путь к файлу с ключом для шифрования
            :return: Ничего не возвращает
        """

        self._fernet = Fernet(self._load_or_create_key(key_path))

    @staticmethod
    def _load_or_create_key(key_path: str) -> bytes:
        """
            Загружает ключ из файла или создаёт новый, если файл не существует

            :param key_path: Путь к файлу с ключом
            :return: Ключ в виде байтов
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
            Шифрует строку

            :param plaintext: Строка для шифрования
            :return: Зашифрованная строка
        """

        return self._fernet.encrypt(plaintext.encode()).decode()
