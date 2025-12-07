#!/usr/bin/env python3
"""Скрипт для диагностики работоспособности приложения."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Добавляем app в path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv()

from app.utils.diagnostics import check_agent_full, check_agent_initialization, check_wikipedia_client


def print_section(title: str) -> None:
    """Печатает заголовок секции."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def check_1_wikipedia() -> bool:
    """Проверка 1: Wikipedia API."""
    print_section("ПРОВЕРКА 1: Wikipedia API")
    
    try:
        data = check_wikipedia_client()
        
        bridge = data.get("bridge", {})
        animal = data.get("animal", {})
        
        print(f"✅ Мост: {bridge.get('name')}")
        print(f"   Длина: {bridge.get('length_meters')} метров")
        print(f"   Источник: {bridge.get('source')}")
        
        print(f"\n✅ Животное: {animal.get('name')}")
        print(f"   Скорость: {animal.get('speed_m_s')} м/с ({animal.get('speed_km_h')} км/ч)")
        print(f"   Источник: {animal.get('source')}")
        
        # Проверки
        if bridge.get("length_meters", 0) <= 0:
            print("❌ ОШИБКА: Длина моста не получена")
            return False
        if animal.get("speed_m_s", 0) <= 0:
            print("❌ ОШИБКА: Скорость животного не получена")
            return False
        
        print("\n✅ Wikipedia API работает корректно")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_2_agent_initialization() -> bool:
    """Проверка 2: Инициализация агента."""
    print_section("ПРОВЕРКА 2: Инициализация агента и LLM")
    
    # Проверяем API ключ
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️  ПРЕДУПРЕЖДЕНИЕ: OPENROUTER_API_KEY не установлен")
        print("   Для работы с OpenRouter необходимо установить переменную окружения")
        print("   Пропускаем эту проверку")
        return True  # Не считаем это ошибкой, так как можно использовать Ollama
    
    try:
        info = check_agent_initialization()
        
        print(f"✅ Agent executor: {info.get('agent_executor_type')}")
        print(f"✅ LLM Provider: {info.get('llm_provider')}")
        print(f"✅ Agent Model: {info.get('llm_model')}")
        print(f"✅ Self-check: {'Включен' if info.get('use_llm_selfcheck') else 'Выключен'}")
        if info.get('use_llm_selfcheck'):
            print(f"   Self-check model: {info.get('selfcheck_model')}")
        
        print("\n✅ Агент инициализирован корректно")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_3_full_run() -> bool:
    """Проверка 3: Полный запуск агента."""
    print_section("ПРОВЕРКА 3: Полный запуск агента")
    
    # Проверяем API ключ
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️  ПРЕДУПРЕЖДЕНИЕ: OPENROUTER_API_KEY не установлен")
        print("   Для работы с OpenRouter необходимо установить переменную окружения")
        print("   Пропускаем эту проверку")
        return True  # Не считаем это ошибкой
    
    try:
        query = "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?"
        print(f"📝 Запрос: {query}\n")
        
        result = check_agent_full(query)
        
        print(f"✅ Мост: {result.get('bridge', {}).get('name')}")
        print(f"   Длина: {result.get('bridge', {}).get('length_meters')} метров")
        
        print(f"\n✅ Животное: {result.get('animal', {}).get('name')}")
        print(f"   Скорость: {result.get('animal', {}).get('speed_m_s')} м/с")
        
        print(f"\n✅ Время пересечения: {result.get('time_seconds')} секунд")
        print(f"   ({result.get('time_human_readable')})")
        
        print(f"\n✅ Количество шагов reasoning: {len(result.get('steps', []))}")
        
        # Проверки
        if result.get("time_seconds", 0) <= 0:
            print("❌ ОШИБКА: Время пересечения не рассчитано")
            return False
        if result.get('bridge', {}).get("length_meters", 0) <= 0:
            print("❌ ОШИБКА: Длина моста не получена")
            return False
        
        print("\n✅ Агент отработал корректно")
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False


def main() -> None:
    """Основная функция диагностики."""
    print("\n" + "🔍" * 40)
    print("  ДИАГНОСТИКА ПРИЛОЖЕНИЯ")
    print("🔍" * 40)
    
    results = []
    
    # Запускаем проверки
    results.append(("Wikipedia API", check_1_wikipedia()))
    results.append(("Agent Initialization", check_2_agent_initialization()))
    results.append(("Full Agent Run", check_3_full_run()))
    
    # Итоговый отчет
    print_section("ИТОГОВЫЙ ОТЧЕТ")
    
    all_passed = True
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
        sys.exit(0)
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ")
        sys.exit(1)


if __name__ == "__main__":
    main()

