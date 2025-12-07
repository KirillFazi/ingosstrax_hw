#!/usr/bin/env python3
"""Тест агента с подробным выводом цепочки размышлений."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Добавляем корень проекта в path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agent_cli import run_agent
from app.core.config import AppConfig
from app.utils.wikipedia_client import WikipediaClient


def main() -> None:
    """Запускает агента с verbose=True для просмотра цепочки размышлений."""
    
    config = AppConfig()
    wikipedia_client = WikipediaClient()
    
    # Выбираем LLM провайдер
    llm_client = None
    if config.llm.provider == "ollama":
        from app.core.llm import OllamaLLMClient
        
        llm_client = OllamaLLMClient(
            model=config.llm.agent_model,
            base_url=str(config.llm.ollama_base_url)
        )
    elif config.llm.provider == "openrouter":
        from app.core.llm import OpenRouterLLMClient
        
        llm_client = OpenRouterLLMClient(model=config.llm.agent_model)
    
    query = "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?"
    print(f"\n🔍 ЗАПРОС: {query}\n")
    print("=" * 80)
    
    result = run_agent(query, llm_client=llm_client, client=wikipedia_client, verbose=True)
    
    print("\n" + "=" * 80)
    print("ФИНАЛЬНЫЙ РЕЗУЛЬТАТ")
    print("=" * 80)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
