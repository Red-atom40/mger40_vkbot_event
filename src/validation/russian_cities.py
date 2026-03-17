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


@lru_cache(maxsize=1)
def _region_index() -> dict[str, str]:
    """Возвращает dict: нормализованный регион → оригинальное название региона."""
    with _CITY_DATA_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    index: dict[str, str] = {}
    for row in payload:
        subject = row.get("subject")
        if not subject:
            continue
        normalized = normalize_region_name(subject)
        if normalized and normalized not in index:
            index[normalized] = subject
    return index


@lru_cache(maxsize=1)
def _city_regions_index() -> dict[str, set[str]]:
    """Возвращает dict: нормализованный город → множество нормализованных регионов."""
    with _CITY_DATA_FILE.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    index: dict[str, set[str]] = {}
    for row in payload:
        city_name = row.get("name")
        region_name = row.get("subject")
        if not city_name or not region_name:
            continue

        normalized_city = normalize_city_name(city_name)
        normalized_region = normalize_region_name(region_name)
        if not normalized_city or not normalized_region:
            continue

        regions = index.setdefault(normalized_city, set())
        regions.add(normalized_region)
    return index


def normalize_region_name(value: str) -> str:
    """Приводит название региона к нормализованной форме для сравнения."""
    text = value.strip().replace("ё", "е").replace("Ё", "Е")
    text = _MULTISPACE_RE.sub(" ", text)
    return text.casefold()


def is_russian_city(value: str) -> bool:
    """Проверяет, что введённый город присутствует в справочнике городов РФ."""
    normalized = normalize_city_name(value)
    return bool(normalized) and normalized in _city_index()


def is_russian_region(value: str) -> bool:
    """Проверяет, что введённый регион присутствует в справочнике городов РФ."""
    normalized = normalize_region_name(value)
    return bool(normalized) and normalized in _region_index()


def suggest_cities(value: str, n: int = 3, cutoff: float = 0.72) -> list[str]:
    """Возвращает список похожих названий городов для подсказки при ошибке."""
    idx = _city_index()
    normalized = normalize_city_name(value)
    matches = get_close_matches(normalized, idx.keys(), n=n, cutoff=cutoff)
    return [idx[m] for m in matches]


def suggest_regions(value: str, n: int = 3, cutoff: float = 0.72) -> list[str]:
    """Возвращает список похожих названий регионов для подсказки при ошибке."""
    idx = _region_index()
    normalized = normalize_region_name(value)
    matches = get_close_matches(normalized, idx.keys(), n=n, cutoff=cutoff)
    return [idx[m] for m in matches]


def city_belongs_to_region(city: str, region: str) -> bool:
    """Проверяет, что город встречается в указанном регионе в справочнике."""
    normalized_city = normalize_city_name(city)
    normalized_region = normalize_region_name(region)

    if not normalized_city or not normalized_region:
        return False

    regions = _city_regions_index().get(normalized_city, set())
    return normalized_region in regions


def regions_for_city(city: str) -> list[str]:
    """Возвращает список регионов, в которых есть город из справочника."""
    normalized_city = normalize_city_name(city)
    if not normalized_city:
        return []

    region_index = _region_index()
    normalized_regions = sorted(_city_regions_index().get(normalized_city, set()))
    return [region_index[r] for r in normalized_regions if r in region_index]
