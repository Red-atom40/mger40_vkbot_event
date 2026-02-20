import random
import time
from typing import Iterator

import vk_api
import vk_api.exceptions
from vk_api.longpoll import VkLongPoll, VkEventType, Event

_RECONNECT_DELAY = 5


class VkClient:
    """
        Тонкая обёртка над VK API: отправка сообщений и прослушивание LongPoll
    """

    def __init__(self, token: str) -> None:
        self._session = vk_api.VkApi(token=token)
        self._api = self._session.get_api()
        self._longpoll = VkLongPoll(self._session)

    def send(self, user_id: int, message: str) -> None:
        """
            Отправляет текстовое сообщение пользователю\n
            При ошибке VK API печатает её и продолжает работу
        """

        print(f"Sending message to vk_id={user_id}: {message!r}")
        try:
            self._api.messages.send(
                user_id=user_id,
                message=message,
                random_id=random.getrandbits(31),
            )
        except vk_api.exceptions.ApiError as e:
            print(f"VK API error when sending to vk_id={user_id}: {e}")

    def listen(self) -> Iterator[Event]:
        """
            Генератор входящих сообщений (только MESSAGE_NEW to_me)\n
            При сетевых ошибках переподключается через _RECONNECT_DELAY сек
        """

        while True:
            try:
                for event in self._longpoll.listen():
                    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                        yield event
            except Exception as e:
                print(f"LongPoll error: {e}. Reconnecting in {_RECONNECT_DELAY}s...")
                time.sleep(_RECONNECT_DELAY)
