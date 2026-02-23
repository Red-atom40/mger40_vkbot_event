import json
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent.parent / "config.json"


class Config:
    """
        Читает параметры из config.json в корне проекта:\n
        vk_token, session_timeout, db_path, key_path, log_level, log_format
    """

    def __init__(self, path: Path = _CONFIG_PATH) -> None:
        """
            Загружает параметры из JSON-файла
        """

        with open(path, encoding="utf-8") as f:
            data: dict = json.load(f)

        self.vk_token: str = data.get("vk_token", "")
        self.session_timeout: int = int(data.get("session_timeout", 600))
        self.db_path: str = data.get("db_path", "quiz.db")
        self.key_path: str = data.get("key_path", "secret.key")
        self.log_level: str = data.get("log_level", "INFO").upper()
        self.log_format: str = data.get("log_format", "text").lower()
        self.admin_ids: list[str] = [str(i) for i in data.get("admin_ids", [])]
        self.group_id: int = int(data.get("group_id", 0))
        self.event_links: list[str] = data.get("event_links", [])
        self.broadcast_tag: str = data.get("broadcast_tag", "@мероприятие")
