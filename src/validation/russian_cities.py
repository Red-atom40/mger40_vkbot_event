import json
import re
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path


_CITY_PREFIX_RE = re.compile(r"^(?:г\.?|город)\s+", re.IGNORECASE)
_MULTISPACE_RE = re.compile(r"\s+")
_CITY_DATA_FILE = Path(__file__).with_name("russian-cities.json")


def normalize_city_name(value: str) -> str:
    """Приводит название города к нормализованной форме для сравнения."""
    text = value.strip().replace("ё", "е").replace("Ё", "Е")
    text = _CITY_PREFIX_RE.sub("", text)
    text = _MULTISPACE_RE.sub(" ", text)
    return text.casefold()


@lru_cache(maxsize=1)
def _city_index() -> dict[str, str]:
    """Загружает JSON-справочник и возвращает dict: нормализованное → оригинальное имя."""
    with _CITY_DATA_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    return {
        normalize_city_name(row["name"]): row["name"]
        for row in payload
        if row.get("name")
    }


def is_russian_city(value: str) -> bool:
    """Проверяет, что введённый город присутствует в справочнике городов РФ."""
    normalized = normalize_city_name(value)
    return bool(normalized) and normalized in _city_index()


def suggest_cities(value: str, n: int = 3, cutoff: float = 0.72) -> list[str]:
    """Возвращает список похожих названий городов для подсказки при ошибке."""
    idx = _city_index()
    normalized = normalize_city_name(value)
    matches = get_close_matches(normalized, idx.keys(), n=n, cutoff=cutoff)
    return [idx[m] for m in matches]
