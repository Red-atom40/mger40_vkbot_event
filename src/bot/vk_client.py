from collections.abc import Iterator
from pathlib import Path
import time
from random import getrandbits

from loguru import logger

import vk_api
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEvent
from vk_api.longpoll import VkLongPoll, VkEventType, Event
from vk_api.upload import VkUpload


class VkClient:
    def __init__(self, token: str, reconnect_delay: int = 5) -> None:
        """Клиент для взаимодействия с VK API, обрабатывающий отправку сообщений и прослушивание событий"""
        self.session = vk_api.VkApi(token=token)
        self.api = self.session.get_api()
        self.upload = VkUpload(self.session)
        self.longpoll = VkLongPoll(self.session)
        self.reconnect_delay = reconnect_delay
        self._message_photo_cache: dict[str, str] = {}

    def _get_uploaded_message_photo_attachment(self, user_id: int, image_path: str) -> str | None:
        """Загружает локальное изображение для сообщений и возвращает attachment-строку."""
        abs_path = str(Path(image_path).resolve())
        cached = self._message_photo_cache.get(abs_path)
        if cached is not None:
            return cached

        path = Path(abs_path)
        if not path.is_file():
            logger.warning(f"Image file does not exist: {abs_path}")
            return None

        try:
            saved = self.upload.photo_messages(str(path), peer_id=user_id)
            if not saved:
                return None

            photo = saved[0]
            attachment = f"photo{photo['owner_id']}_{photo['id']}"
            access_key = photo.get("access_key")
            if access_key:
                attachment = f"{attachment}_{access_key}"

            self._message_photo_cache[abs_path] = attachment
            return attachment
        except Exception as e:
            logger.error(f"Failed to upload message image {abs_path}: {e}")
            return None

    def send(
        self,
        user_id: int,
        msg: str,
        keyboard: str | None = None,
        image_path: str | None = None,
    ) -> int | None:
        """Отправляет сообщение пользователю и возвращает message_id, если VK API его вернул."""
        logger.debug(f"Sending message to {user_id}: {msg!r}")
        try:
            kwargs: dict = dict(
                user_id=user_id,
                message=msg,
                random_id=getrandbits(31),
            )
            if keyboard is not None:
                kwargs["keyboard"] = keyboard
            if image_path is not None:
                attachment = self._get_uploaded_message_photo_attachment(user_id, image_path)
                if attachment is not None:
                    kwargs["attachment"] = attachment
            return self.api.messages.send(**kwargs)
        except vk_api.exceptions.ApiError as e:
            logger.error(f"Failed to send message to {user_id}: {e}")
            return None

    def delete_message(self, message_id: int, delete_for_all: bool = True) -> bool:
        """Удаляет сообщение по message_id. Возвращает True при успешном удалении."""
        try:
            result = self.api.messages.delete(
                message_ids=message_id,
                delete_for_all=1 if delete_for_all else 0,
            )
            return bool(result.get(str(message_id), 0) == 1)
        except vk_api.exceptions.ApiError as e:
            logger.warning(f"Failed to delete message {message_id}: {e}")
            return False

    def edit_message(
        self,
        user_id: int,
        message_id: int,
        msg: str,
        keyboard: str | None = None,
    ) -> bool:
        """Редактирует отправленное сообщение в диалоге с пользователем."""
        try:
            kwargs: dict = {
                "peer_id": user_id,
                "message_id": message_id,
                "message": msg,
            }
            if keyboard is not None:
                kwargs["keyboard"] = keyboard
            self.api.messages.edit(**kwargs)
            return True
        except vk_api.exceptions.ApiError as e:
            logger.warning(f"Failed to edit message {message_id} for user {user_id}: {e}")
            return False

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
