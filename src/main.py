from config import Config
from database.database import Database
from tools.encryption import Encryptor
from bot.bot import VKBot
from bot.client import VkClient


# TODO: добавить логирование
# TODO: добавить какую-то админку + система выдачи админ прав
# TODO: рассылки о предстоящих мероприятиях (с подтверждением участия), интегрировать ссылки на группы и чаты в рассылки
# TODO: переделать VK_TOKEN на VK Implicit Flow



def main() -> None:
    config = Config()

    # Проверяем, что токен VK задан
    if not config.vk_token:
        raise RuntimeError(
            "VK_TOKEN не задан. Создайте файл .env или установите переменную окружения."
        )

    encryptor = Encryptor(config.key_path)
    db = Database(config.db_path, encryptor)
    client = VkClient(config.vk_token)
    bot = VKBot(config, db, client)
    bot.run()


if __name__ == "__main__":
    main()
