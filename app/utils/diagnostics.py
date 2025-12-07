"""Диагностические функции для проверки работоспособности приложения."""

from __future__ import annotations

from typing import Any

from app.agent_cli import build_agent_executor, run_agent
from app.core.config import AppConfig
from app.utils.reasoning import get_animal_speed, get_bridge_info_big_stone_bridge
from app.utils.wikipedia_client import WikipediaClient


def check_wikipedia_client() -> dict[str, Any]:
    """
    Проверяет работу Wikipedia client.
    
    Возвращает словарь с информацией о мосте и животном.
    """
    client = WikipediaClient()
    
    # Получаем данные о мосте
    bridge = get_bridge_info_big_stone_bridge(client)
    bridge_data = {
        "name": bridge.name,
        "length_meters": bridge.length_meters,
        "source": bridge.source,
    }
    
    # Получаем данные о животном (гепард)
    animal = get_animal_speed(client, "Гепард")
    animal_data = {
        "name": animal.name,
        "speed_m_s": animal.speed_m_s,
        "speed_km_h": animal.speed_km_h,
        "source": animal.source,
    }
    
    return {
        "bridge": bridge_data,
        "animal": animal_data,
    }


def check_agent_initialization() -> dict[str, Any]:
    """
    Проверяет инициализацию агента и LLM.
    
    Возвращает информацию о типе агента и модели.
    """
    config = AppConfig()
    client = WikipediaClient()
    
    # Инициализируем LLM клиент
    if config.llm.provider == "ollama":
        from app.core.llm import OllamaLLMClient
        
        llm_client = OllamaLLMClient(
            model=config.llm.agent_model,
            base_url=str(config.llm.ollama_base_url),
        )
    elif config.llm.provider == "openrouter":
        from app.core.llm import OpenRouterLLMClient
        
        llm_client = OpenRouterLLMClient(model=config.llm.agent_model)
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm.provider}")
    
    # Создаем agent executor
    executor, _ = build_agent_executor(llm_client, client, verbose=False)
    
    return {
        "agent_executor_type": type(executor).__name__,
        "llm_provider": config.llm.provider,
        "llm_model": config.llm.agent_model,
        "use_llm_selfcheck": config.llm.use_llm_selfcheck,
        "selfcheck_model": config.llm.selfcheck_model if config.llm.use_llm_selfcheck else None,
    }


def check_agent_full(query: str | None = None) -> dict[str, Any]:
    """
    Запускает полный цикл работы агента.
    
    Args:
        query: Пользовательский запрос. По умолчанию используется стандартный.
    
    Возвращает результат работы агента в виде словаря.
    """
    if query is None:
        query = "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?"
    
    result = run_agent(query, verbose=False)
    
    return result.model_dump()

