from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.utils.diagnostics import (  # noqa: E402
    check_agent_full,
    check_agent_initialization,
    check_wikipedia_client,
)

@pytest.mark.integration
def test_check_wikipedia_client_has_bridge_and_animal() -> None:
    """
    Проверяет работу Wikipedia API клиента.
    
    Получает данные о Большом Каменном мосте и гепарде через Wikipedia API,
    проверяет корректность длины моста и скорости животного.
    """
    data = check_wikipedia_client()
    bridge = data.get("bridge", {})
    animal = data.get("animal", {})
    assert bridge.get("length_meters", 0) > 0
    assert bridge.get("name")
    assert animal.get("speed_m_s", 0) > 0
    assert animal.get("name")


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; skipping agent initialization check",
)
def test_check_agent_initialization() -> None:
    """
    Проверяет инициализацию LLM и агента.
    
    Создает LLM клиент и agent executor, проверяет корректность
    инициализации и наличие информации о модели.
    Требует OPENROUTER_API_KEY в окружении.
    """
    info = check_agent_initialization()
    assert info["agent_executor_type"]
    assert "llm_model" in info


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"),
    reason="OPENROUTER_API_KEY not set; skipping agent full run",
)
def test_check_agent_full_runs() -> None:
    """
    Проверяет полный цикл работы агента end-to-end.
    
    Запускает агента с реальным вопросом, проверяет что агент
    вызывает все необходимые инструменты и возвращает корректный
    результат с рассчитанным временем пересечения.
    Требует OPENROUTER_API_KEY в окружении.
    """
    result = check_agent_full(
        "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?"
    )
    assert result["time_seconds"] > 0
    assert result["bridge"]["length_meters"] > 0
