from config import Config
from database.admins import AdminRepository
from database.database import Database
from database.stats import StatsRepository
from log import setup_logging
from security.encryption import Encryptor
from bot.admin import AdminHandler
from bot.bot import VKBot
from bot.broadcaster import Broadcaster
from bot.client import VkClient


# TODO: переделать VK_TOKEN на VK Implicit Flow


def main() -> None:
    config = Config()
    setup_logging(config.log_level, config.log_format)

    # Проверяем, что токен VK задан
    if not config.vk_token:
        raise RuntimeError(
            "vk_token не задан. Укажите его в config.json."
        )

    encryptor = Encryptor(config.key_path)
    db = Database(config.db_path, encryptor)
    client = VkClient(config.vk_token)
    admin_repo = AdminRepository(config.db_path, config.admin_ids)
    stats_repo = StatsRepository(config.db_path)
    admin = AdminHandler(admin_repo, stats_repo, client)

    if config.group_id:
        broadcaster = Broadcaster(
            client=client,
            db=db,
            group_id=config.group_id,
            event_links=config.event_links,
            broadcast_tag=config.broadcast_tag,
        )
        broadcaster.start()

    bot = VKBot(config, db, client, admin)
    bot.run()


if __name__ == "__main__":
    main()
