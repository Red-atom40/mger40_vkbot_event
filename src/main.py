import sys

from loguru import logger

from config import Config
from bot.bot import VKBot
from bot.broadcaster import Broadcaster
from bot.vk_client import VkClient
from database.database import Database
from security.encryptor import Encryptor


def setup_logger(level: str, log_format: str) -> None:
    logger.remove()
    if log_format == "json":
        logger.add(sys.stdout, level=level, serialize=True)
    else:
        logger.add(sys.stdout, level=level)


def main() -> None:
    config = Config()
    setup_logger(config.log_level, config.log_format)

    logger.info("Configuration loaded successfully.")

    encryptor = Encryptor(config.key_path)
    db = Database(config.db_path, encryptor, config.admin_ids)
    client = VkClient(config.vk_token)

    broadcaster = Broadcaster(
        client, db, config.group_id, config.event_links, config.broadcast_tag
    )
    broadcaster.start()

    bot = VKBot(config, db, client)
    bot.run()


if __name__ == "__main__":
    main()
