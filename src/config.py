import json
from pathlib import Path

config_path = Path("config.json")


class Config:
    def __init__(self, path: Path = config_path) -> None:
        """Загружает конфигурацию из файла config.json"""
        with open(path, encoding="utf-8") as f:
            data: dict = json.load(f)

        self.vk_token: str = data.get("vk_token", "")
        self.session_timeout: int = int(data.get("session_timeout", 600))
        self.db_path: str = data.get("db_path", "quiz.db")
        self.key_path: str = data.get("key_path", "secret.key")
        self.log_level: str = data.get("log_level", "INFO").upper()
        self.admin_ids: list[int] = [int(i) for i in data.get("admin_ids", [])]
        self.group_id: int = int(data.get("group_id", 0))
        self.event_links: list[str] = data.get("event_links", [])
        self.broadcast_tag: str = data.get("broadcast_tag", "#мероприятие")
        self.reconnect_delay: int = int(data.get("reconnect_delay", 5))
