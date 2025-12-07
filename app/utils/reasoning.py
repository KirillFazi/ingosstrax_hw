from __future__ import annotations

import re

from app.core.models import (
    AnimalSpeed,
    BridgeInfo,
    ReasoningResult,
    ReasoningStep,
    format_seconds,
)
from app.utils.wikipedia_client import WikipediaClient


def _build_page_url(page_id: int, api_base: str) -> str:
    prefix = api_base.split("/w/")[0]
    return f"{prefix}/?curid={page_id}"


def _parse_length_meters(text: str) -> float:
    matches = re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:м|метр)", text, flags=re.IGNORECASE)
    if not matches:
        raise ValueError("Не удалось извлечь длину моста из текста")
    values = [float(item.replace(",", ".")) for item in matches]
    return max(values)


def _parse_speed_kmh(text: str) -> float:
    pattern = r"(\d+(?:[.,]\d+)?)\s*(?:км\s*/\s*ч|км\s*в\s*час|km/h|kmh)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches:
        raise ValueError("Не удалось извлечь скорость гепарда из текста")
    values = [float(item.replace(",", ".")) for item in matches]
    return max(values)


def get_bridge_info_big_stone_bridge(client: WikipediaClient) -> BridgeInfo:
    try:
        search = client.search_page("Большой Каменный мост")
        if not search:
            raise LookupError("Статья 'Большой Каменный мост' не найдена")
        summary = client.get_page_summary(search.page_id, intro_only=True)
        try:
            length_meters = _parse_length_meters(summary.extract)
        except ValueError:
            summary = client.get_page_summary(search.page_id, intro_only=False)
            length_meters = _parse_length_meters(summary.extract)
        return BridgeInfo(
            name=search.title,
            length_meters=length_meters,
            source=_build_page_url(search.page_id, client.base_url),
        )
    except Exception as exc:  # noqa: BLE001
        # Offline or request failure fallback
        return BridgeInfo(
            name="Большой Каменный мост (fallback)",
            length_meters=487.0,
            source=f"fallback:{exc}",
        )


def get_animal_speed(client: WikipediaClient, animal_name: str) -> AnimalSpeed:
    try:
        search = client.search_page(animal_name) or client.search_page(animal_name.capitalize())
        effective_client = client
        if not search and not client.base_url.startswith("https://en.wikipedia.org"):
            fallback = WikipediaClient(base_url="https://en.wikipedia.org/w/api.php")
            search = fallback.search_page(animal_name.capitalize())
            if search:
                effective_client = fallback
        if not search:
            raise LookupError(f"Статья про '{animal_name}' не найдена")

        summary = effective_client.get_page_summary(search.page_id, intro_only=True)
        try:
            speed_km_h = _parse_speed_kmh(summary.extract)
        except ValueError:
            summary = effective_client.get_page_summary(search.page_id, intro_only=False)
            speed_km_h = _parse_speed_kmh(summary.extract)

        return AnimalSpeed.from_kmh(
            name=search.title,
            speed_km_h=speed_km_h,
            source=_build_page_url(search.page_id, effective_client.base_url),
        )
    except Exception as exc:  # noqa: BLE001
        # Offline or request failure fallback
        speed_km_h = 90.0
        return AnimalSpeed.from_kmh(
            name=f"{animal_name} (fallback)",
            speed_km_h=speed_km_h,
            source=f"fallback:{exc}",
        )


def estimate_crossing_time(bridge: BridgeInfo, animal: AnimalSpeed) -> ReasoningResult:
    if animal.speed_m_s <= 0:
        raise ValueError("Скорость животного должна быть положительной")
    time_seconds = bridge.length_meters / animal.speed_m_s
    steps = [
        ReasoningStep(
            description="Получена длина моста",
            data={"name": bridge.name, "length_meters": bridge.length_meters},
        ),
        ReasoningStep(
            description="Получена скорость животного",
            data={
                "name": animal.name,
                "speed_m_s": animal.speed_m_s,
                "speed_km_h": animal.speed_km_h,
            },
        ),
        ReasoningStep(
            description="Рассчитано время пересечения",
            data={"time_seconds": time_seconds},
        ),
    ]
    return ReasoningResult(
        bridge=bridge,
        animal=animal,
        time_seconds=time_seconds,
        time_human_readable=format_seconds(time_seconds),
        steps=steps,
    )

