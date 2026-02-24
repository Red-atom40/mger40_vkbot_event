from datetime import datetime
import time
import threading

from loguru import logger

from bot.vk_client import VkClient
from database.database import Database


reconnect_delay = 5
broadcast_tag = "#мероприятие"


class Broadcaster:
    def __init__(
        self,
        client: VkClient,
        db: Database,
        group_id: int,
        event_links: list[str],
        broadcast_tag: str = broadcast_tag,
    ):
        """Инициализирует Broadcaster для прослушивания новых постов на стене группы"""
        self.client = client
        self.db = db
        self.group_id = group_id
        self.event_links = event_links
        self.broadcast_tag = broadcast_tag

    def start(self) -> None:
        """Запускает поток для прослушивания новых постов на стене группы и трансляции мероприятий"""
        t = threading.Thread(target=self.run, daemon=True, name="BroadcasterThread")
        t.start()
        logger.info("Broadcaster started.")

    def run(self) -> None:
        while True:
            try:
                for post_text in self.client.listen_wall(self.group_id):
                    if self.broadcast_tag in post_text.lower():
                        self.broadcast(post_text)
            except Exception as e:
                logger.error(f"Error in broadcaster: {e}")
                time.sleep(reconnect_delay)

    def broadcast(self, post_text: str) -> None:
        """Отправляет сообщение о новом мероприятии всем пользователям, у которых нет текущей заявки в процессе заполнения"""
        vk_ids = self.db.get_all_vk_ids()
        if not vk_ids:
            logger.warning("No users to broadcast to.")
            return

        event_id = datetime.now().strftime("%Y%m%d%H%M%S")
        links_block = "\n".join(self.event_links)
        message = f"{post_text}\n\n{links_block}"

        logger.info(f"Broadcasting event {event_id} to {len(vk_ids)} users.")

        for vk_id in vk_ids:
            self.db.add_pending_rsvp(vk_id, event_id)
            self.client.send(vk_id, message)
            self.client.send(
                vk_id, "Вы планируете посетить это мероприятие? (да / нет)"
            )

        logger.info(f"Broadcast for event {event_id} sent to all users.")
