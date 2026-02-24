from collections.abc import Iterator
import time
from random import getrandbits

from loguru import logger

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.longpoll import VkLongPoll, VkEventType, Event

reconnect_delay = 5


class VkClient:
    def __init__(self, token: str) -> None:
        """Клиент для взаимодействия с VK API, обрабатывающий отправку сообщений и прослушивание событий"""
        self.session = vk_api.VkApi(token=token)
        self.api = self.session.get_api()
        self.longpoll = VkLongPoll(self.session)

    def send(self, user_id: int, msg: str) -> None:
        """Метод для отправки сообщения пользователю с указанным vk_id"""
        logger.debug(f"Sending message to {user_id}: {msg!r}")
        try:
            self.api.messages.send(
                user_id=user_id,
                message=msg,
                random_id=getrandbits(31),
            )
        except vk_api.exceptions.ApiError as e:
            logger.error(f"Failed to send message to {user_id}: {e}")

    def listen(self) -> Iterator[Event]:
        """Генератор для прослушивания новых сообщений, направленных боту"""
        while True:
            try:
                yield from (
                    e
                    for e in self.longpoll.listen()
                    if e.type == VkEventType.MESSAGE_NEW and e.to_me
                )
            except Exception as e:
                logger.warning(f"LongPoll error: {e}. Reconnecting...")
                time.sleep(reconnect_delay)

    def listen_wall(self, group_id: int) -> Iterator[str]:
        """Генератор для прослушивания новых постов на стене группы, содержащих тег для трансляции мероприятий"""
        bot_longpoll = VkBotLongPoll(self.session, group_id)
        yield from (
            e.object.get("text", "")
            for e in bot_longpoll.listen()
            if e.type == VkBotEventType.WALL_POST_NEW
        )
