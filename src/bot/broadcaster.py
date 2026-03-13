from datetime import datetime
import time
import threading

from loguru import logger

from vk_api.bot_longpoll import VkBotEventType

from bot.keyboards import start_keyboard, yes_no_keyboard
from bot.vk_client import VkClient
from database.database import Database

_WELCOME_MESSAGE = (
    "Добро пожаловать в «Молодую Гвардию»!\n\n"
    "Если хотите вступить в организацию — нажмите кнопку «Заявка» "
    "или напишите «заявка»."
)


class Broadcaster:
    def __init__(
        self,
        client: VkClient,
        db: Database,
        group_id: int,
        broadcast_tag: str,
        reconnect_delay: int = 5,
    ):
        """Инициализирует Broadcaster для прослушивания событий группы"""
        self.client = client
        self.db = db
        self.group_id = group_id
        self.broadcast_tag = broadcast_tag
        self.reconnect_delay = reconnect_delay
        self._welcome_last_sent_at: dict[int, float] = {}

    def start(self) -> None:
        """Запускает поток для прослушивания событий группы"""
        t = threading.Thread(target=self.run, daemon=True, name="BroadcasterThread")
        t.start()
        logger.info("Broadcaster started.")

    def run(self) -> None:
        while True:
            try:
                for event in self.client.listen_bot_events(self.group_id):
                    if event.type == VkBotEventType.WALL_POST_NEW:
                        post_text = event.object.get("text", "")
                        if self.broadcast_tag in post_text.lower():
                            self.broadcast(post_text)
                    elif event.type == VkBotEventType.GROUP_JOIN:
                        vk_id = event.object.get("user_id")
                        logger.info(f"Event GROUP_JOIN received: vk_id={vk_id}")
                        if vk_id:
                            self._on_join(vk_id, source="GROUP_JOIN")
                        else:
                            logger.warning("GROUP_JOIN without user_id in payload")
                    elif event.type == VkBotEventType.MESSAGE_ALLOW:
                        vk_id = event.object.get("user_id")
                        logger.info(f"Event MESSAGE_ALLOW received: vk_id={vk_id}")
                        if vk_id:
                            self._on_join(vk_id, source="MESSAGE_ALLOW")
                        else:
                            logger.warning("MESSAGE_ALLOW without user_id in payload")
            except Exception as e:
                logger.error(f"Error in broadcaster: {e}")
                time.sleep(self.reconnect_delay)

    def _on_join(self, vk_id: int, source: str) -> None:
        """Отправляет приветственное сообщение с кнопкой «Заявка» новому участнику."""
        now = time.time()
        last_sent = self._welcome_last_sent_at.get(vk_id)
        if last_sent is not None and now - last_sent < 60:
            logger.info(
                f"Welcome skipped (duplicate event): vk_id={vk_id}, source={source}, "
                f"delta={round(now - last_sent, 1)}s"
            )
            return

        logger.info(f"Sending welcome: vk_id={vk_id}, source={source}")
        self.client.send(vk_id, _WELCOME_MESSAGE, keyboard=start_keyboard())
        self._welcome_last_sent_at[vk_id] = now

    def broadcast(self, post_text: str) -> None:
        """Отправляет сообщение о новом мероприятии всем пользователям"""
        vk_ids = self.db.get_all_vk_ids()
        if not vk_ids:
            logger.warning("No users to broadcast to.")
            return

        event_id = datetime.now().strftime("%Y%m%d%H%M%S")
        first_line = post_text.strip().splitlines()[0] if post_text.strip() else post_text
        title = first_line[:80] + ("…" if len(first_line) > 80 else "")
        self.db.save_event(event_id, title)
        links_block = "\n".join(self.db.get_event_links())
        message = f"{post_text}\n\n{links_block}"

        logger.info(f"Broadcasting event {event_id} to {len(vk_ids)} users.")

        for vk_id in vk_ids:
            self.db.add_pending_rsvp(vk_id, event_id)
            self.client.send(vk_id, message)
            self.client.send(vk_id, "Вы планируете посетить это мероприятие?", keyboard=yes_no_keyboard())

        logger.info(f"Broadcast for event {event_id} sent to all users.")
