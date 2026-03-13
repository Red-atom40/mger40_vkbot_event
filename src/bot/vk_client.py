from collections.abc import Iterator
import time
from random import getrandbits

from loguru import logger

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEvent
from vk_api.longpoll import VkLongPoll, VkEventType, Event


class VkClient:
    def __init__(self, token: str, reconnect_delay: int = 5) -> None:
        """Клиент для взаимодействия с VK API, обрабатывающий отправку сообщений и прослушивание событий"""
        self.session = vk_api.VkApi(token=token)
        self.api = self.session.get_api()
        self.longpoll = VkLongPoll(self.session)
        self.reconnect_delay = reconnect_delay

    def send(self, user_id: int, msg: str, keyboard: str | None = None) -> None:
        """Отправляет сообщение пользователю. Опционально прикрепляет клавиатуру (JSON-строка)."""
        logger.debug(f"Sending message to {user_id}: {msg!r}")
        try:
            kwargs: dict = dict(
                user_id=user_id,
                message=msg,
                random_id=getrandbits(31),
            )
            if keyboard is not None:
                kwargs["keyboard"] = keyboard
            self.api.messages.send(**kwargs)
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
                time.sleep(self.reconnect_delay)

    def listen_bot_events(self, group_id: int) -> Iterator[VkBotEvent]:
        """Генератор для прослушивания всех событий группы (посты на стене, вступления и т.д.)"""
        bot_longpoll = VkBotLongPoll(self.session, group_id)
        yield from bot_longpoll.listen()
