import threading
import time

from loguru import logger

from bot.client import VkClient
from database.database import Database

_RECONNECT_DELAY = 5
_BROADCAST_TAG = "@мероприятие"


class Broadcaster:
    """
        Слушает новые посты на стене группы через VkBotLongPoll.\n
        Когда пост содержит тег _BROADCAST_TAG — рассылает его всем зарегистрированным пользователям
        с прикреплёнными ссылками на чаты.
    """

    def __init__(
        self,
        client: VkClient,
        db: Database,
        group_id: int,
        event_links: list[str],
        broadcast_tag: str = _BROADCAST_TAG,
    ) -> None:
        self._client = client
        self._db = db
        self._group_id = group_id
        self._event_links = event_links
        self._broadcast_tag = broadcast_tag.lower()

    def start(self) -> None:
        """
            Запускает прослушивание стены в daemon-потоке (не блокирует основной цикл)
        """

        t = threading.Thread(target=self._run, daemon=True, name="broadcaster")
        t.start()
        logger.info(f"Broadcaster started for group_id={self._group_id}")

    def _run(self) -> None:
        while True:
            try:
                for post_text in self._client.listen_wall(self._group_id):
                    if self._broadcast_tag in post_text.lower():
                        self._broadcast(post_text)
            except Exception as e:
                logger.warning(f"Broadcaster error: {e}. Reconnecting in {_RECONNECT_DELAY}s...")
                time.sleep(_RECONNECT_DELAY)

    def _broadcast(self, post_text: str) -> None:
        """
            Рассылает пост + ссылки на чаты всем зарегистрированным пользователям
        """

        vk_ids = self._db.get_all_vk_ids()
        if not vk_ids:
            logger.info("Broadcast triggered but no registered users found")
            return

        links_block = "\n".join(self._event_links)
        message = f"{post_text}\n\n{links_block}"

        logger.info(f"Broadcasting to {len(vk_ids)} users")

        sent = 0
        for vk_id in vk_ids:
            self._client.send(int(vk_id), message)
            sent += 1

        logger.info(f"Broadcast complete: sent to {sent}/{len(vk_ids)} users")
