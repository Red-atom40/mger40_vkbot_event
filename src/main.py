from config import Config
from database import Database
from encryption import Encryptor
from bot import VKBot


# TODO: сделать логирование
# TODO: обработка ошибок при работе с VK API и базой данных
# TODO: добавить какую-то админку
# TODO: рассылки о предстоящих мероприятиях (с подтверждением участия)
# TODO: интегрировать ссылки на группы и чаты
# TODO: переделать VK_TOKEN на VK Implicit Flow


# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )


def main() -> None:
    config = Config()

    # Проверяем, что токен VK задан
    if not config.vk_token:
        raise RuntimeError(
            "VK_TOKEN не задан. Создайте файл .env или установите переменную окружения."
        )

    encryptor = Encryptor(config.key_path)
    db = Database(config.db_path, encryptor)
    bot = VKBot(config, db)
    bot.run()


if __name__ == "__main__":
    main()
