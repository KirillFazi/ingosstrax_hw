from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

import pytest
from types import SimpleNamespace

from app.core.models import AnimalSpeed, BridgeInfo, kmh_to_ms
from app.utils.reasoning import (
    estimate_crossing_time,
    format_seconds,
    get_animal_speed,
    get_bridge_info_big_stone_bridge,
    _parse_length_meters,
    _parse_speed_kmh,
)
from app.utils.wikipedia_client import WikipediaClient


def test_kmh_to_ms_conversion() -> None:
    """
    Проверяет конвертацию скорости из км/ч в м/с.
    
    Тестирует формулу: м/с = км/ч / 3.6
    """
    assert kmh_to_ms(36.0) == pytest.approx(10.0)
    assert kmh_to_ms(72.0) == pytest.approx(20.0)


def test_parse_length_meters_picks_max_value() -> None:
    """
    Проверяет парсинг длины моста из текста.
    
    Когда в тексте несколько значений длины, функция должна
    выбрать максимальное (основная длина моста).
    """
    text = "Мост длиной 345,5 м построен рядом с 123 м переправой."
    assert _parse_length_meters(text) == pytest.approx(345.5)


def test_parse_length_meters_raises_when_absent() -> None:
    """
    Проверяет обработку ошибки при отсутствии длины моста в тексте.
    
    Функция должна выбросить ValueError, если в тексте нет
    упоминания длины в метрах.
    """
    with pytest.raises(ValueError):
        _parse_length_meters("В тексте нет данных о длине моста.")


def test_parse_speed_kmh_handles_variants() -> None:
    """
    Проверяет парсинг скорости из текста с разными форматами.
    
    Функция должна распознать "км/ч", "km/h" и другие варианты,
    а также выбрать максимальное значение скорости.
    """
    text = "Гепард развивает скорость до 100 км/ч, а иногда 95 km/h."
    assert _parse_speed_kmh(text) == pytest.approx(100.0)


def test_parse_speed_kmh_raises_when_absent() -> None:
    """
    Проверяет обработку ошибки при отсутствии скорости в тексте.
    
    Функция должна выбросить ValueError, если в тексте нет
    упоминания скорости в км/ч.
    """
    with pytest.raises(ValueError):
        _parse_speed_kmh("Здесь нет упоминания скорости.")


def test_format_seconds_outputs_human_readable_values() -> None:
    """
    Проверяет форматирование секунд в читаемый текст.
    
    Тестирует разные варианты: только секунды, только минуты,
    и комбинация минут с секундами.
    """
    assert format_seconds(45.12) == "45.1 секунд"
    assert format_seconds(120.0) == "2 минут"
    assert format_seconds(125.4) == "2 минут 5.4 секунд"


def test_estimate_crossing_time_requires_positive_speed() -> None:
    """
    Проверяет валидацию скорости животного.
    
    Функция должна выбросить ValueError при попытке рассчитать
    время с нулевой или отрицательной скоростью.
    """
    bridge = BridgeInfo(name="Any Bridge", length_meters=100.0, source="mock://bridge")
    animal = AnimalSpeed(name="Slow Animal", speed_m_s=0.0, source="mock://animal")
    with pytest.raises(ValueError, match="Скорость животного должна быть положительной"):
        estimate_crossing_time(bridge, animal)


def test_estimate_crossing_time_with_mock_data() -> None:
    """
    Проверяет расчет времени пересечения моста.
    
    Использует mock данные для проверки формулы: время = длина / скорость.
    200м / 25м/с = 8 секунд.
    """
    bridge = BridgeInfo(name="Mock Bridge", length_meters=200.0, source="mock://bridge")
    animal = AnimalSpeed(name="Mock Cheetah", speed_m_s=25.0, source="mock://cheetah")
    result = estimate_crossing_time(bridge, animal)
    assert result.time_seconds == pytest.approx(8.0)
    assert result.bridge.name == "Mock Bridge"
    assert result.animal.name == "Mock Cheetah"


def test_get_bridge_info_uses_fallback_on_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Проверяет fallback при ошибке Wikipedia API.
    
    Если Wikipedia недоступна или возвращает ошибку, функция должна
    вернуть дефолтные данные о мосте (487 метров).
    """
    class FailingClient(WikipediaClient):
        def __init__(self) -> None:
            self.base_url = "https://example.org/w/api.php"

        def search_page(self, title: str, lang: str = "ru"):
            raise RuntimeError("boom")

    bridge = get_bridge_info_big_stone_bridge(FailingClient())
    assert bridge.name.startswith("Большой Каменный мост")
    assert bridge.length_meters == pytest.approx(487.0)
    assert bridge.source.startswith("fallback:")


def test_get_animal_speed_tries_english_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Проверяет автоматический переход на английскую Wikipedia.
    
    Если животное не найдено в русской Wikipedia, функция должна
    попробовать найти его в английской версии.
    """
    def fake_search(self, title: str, lang: str = "ru"):
        if str(self.base_url).startswith("https://ru"):
            return None
        return SimpleNamespace(page_id=100, title=f"{title} (EN)")

    def fake_summary(self, page_id: int, lang: str = "ru", intro_only: bool = True):
        return SimpleNamespace(
            page_id=page_id,
            title="dummy",
            extract="Typical speed reaches 108 km/h.",
            description=None,
        )

    monkeypatch.setattr(WikipediaClient, "search_page", fake_search)
    monkeypatch.setattr(WikipediaClient, "get_page_summary", fake_summary)

    client = WikipediaClient(base_url="https://ru.wikipedia.org/w/api.php")
    animal = get_animal_speed(client, "Cheetah")

    assert animal.speed_m_s == pytest.approx(kmh_to_ms(108.0))
    assert animal.source.endswith("/?curid=100")
    assert animal.name.endswith("(EN)")


def test_get_animal_speed_returns_default_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    Проверяет fallback скорости животного при ошибке Wikipedia.
    
    Если Wikipedia недоступна, функция должна вернуть дефолтную
    скорость гепарда (90 км/ч).
    """
    def failing_search(self, title: str, lang: str = "ru"):
        raise RuntimeError("network down")

    monkeypatch.setattr(WikipediaClient, "search_page", failing_search)

    animal = get_animal_speed(WikipediaClient(base_url="https://ru.wikipedia.org/w/api.php"), "Гепард")

    assert animal.speed_m_s == pytest.approx(kmh_to_ms(90.0))
    assert "(fallback)" in animal.name
    assert animal.source.startswith("fallback:")


def test_high_level_functions_with_mocked_wikipedia(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Интеграционный тест с полностью замоканным Wikipedia клиентом.
    
    Проверяет работу функций get_bridge_info и get_animal_speed
    с контролируемыми mock данными, включая парсинг русскоязычного текста.
    """
    class DummyClient(WikipediaClient):
        def __init__(self) -> None:
            super().__init__(base_url="https://example.com")

        def search_page(self, title: str, lang: str = "ru"):
            class Obj:
                def __init__(self, page_id: int, title: str) -> None:
                    self.page_id = page_id
                    self.title = title
            # Разные page_id для разных запросов
            if "мост" in title.lower():
                return Obj(page_id=1, title=title)
            return Obj(page_id=2, title=title)

        def get_page_summary(self, page_id: int, lang: str = "ru", intro_only: bool = True):
            class Obj:
                def __init__(self, extract: str) -> None:
                    self.page_id = page_id
                    self.title = "dummy"
                    self.extract = extract
                    self.description = None
            if page_id == 1:
                return Obj("Длина моста 200 м.")
            return Obj("Гепард развивает скорость до 100 км/ч.")

    client = DummyClient()
    monkeypatch.setattr(WikipediaClient, "search_page", client.search_page)
    monkeypatch.setattr(WikipediaClient, "get_page_summary", client.get_page_summary)

    bridge = get_bridge_info_big_stone_bridge(client)
    animal = get_animal_speed(client, "Гепард")

    assert bridge.length_meters == pytest.approx(200.0)
    assert animal.speed_m_s == pytest.approx(kmh_to_ms(100.0))
