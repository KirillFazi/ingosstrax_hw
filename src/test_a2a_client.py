#!/usr/bin/env python3
"""Тестовый клиент для проверки A2A сервера."""

from __future__ import annotations

import json

import requests
import pytest


def _is_a2a_server_available() -> bool:
    try:
        requests.get("http://localhost:8001/.well-known/agent-card.json", timeout=1.5)
        return True
    except requests.exceptions.RequestException:
        return False


SERVER_AVAILABLE = _is_a2a_server_available()


@pytest.mark.skipif(not SERVER_AVAILABLE, reason="A2A server is not running on localhost:8001")
def test_agent_card() -> None:
    """Проверка получения AgentCard."""
    print("=" * 80)
    print("Тест 1: Получение AgentCard")
    print("=" * 80)
    
    response = requests.get("http://localhost:8001/.well-known/agent-card.json")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        card = response.json()
        print(json.dumps(card, ensure_ascii=False, indent=2))
        print("\n✅ AgentCard получен успешно")
    else:
        print(f"❌ Ошибка: {response.text}")


@pytest.mark.skipif(not SERVER_AVAILABLE, reason="A2A server is not running on localhost:8001")
def test_message_send() -> None:
    """Проверка отправки сообщения через JSON-RPC."""
    print("\n" + "=" * 80)
    print("Тест 2: Отправка message/send")
    print("=" * 80)
    
    request_body = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",  # A2A использует kind, а не type
                        "text": "Сколько времени гепарду нужно, чтобы пересечь Большой Каменный мост?"
                    }
                ],
                "messageId": "msg-1"  # messageId обязателен в A2A
            },
            "metadata": {}
        },
        "id": 1
    }
    
    print("\nЗапрос:")
    print(json.dumps(request_body, ensure_ascii=False, indent=2))
    
    response = requests.post(
        "http://localhost:8001/",
        json=request_body,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\nОтвет:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\n✅ Сообщение отправлено (JSON-RPC ответ получен)")
    else:
        print(f"❌ Ошибка: {response.text}")


@pytest.mark.skipif(not SERVER_AVAILABLE, reason="A2A server is not running on localhost:8001")
def test_tasks_get() -> None:
    """Проверка получения статуса задачи через JSON-RPC."""
    print("\n" + "=" * 80)
    print("Тест 3: Получение tasks/get")
    print("=" * 80)
    
    # 1) Отправляем задачу
    send_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Сколько времени зайцу нужно, чтобы пересечь мост?"
                    }
                ],
                "messageId": "msg-2"
            },
            "metadata": {}
        },
        "id": 2
    }
    
    send_response = requests.post(
        "http://localhost:8001/",
        json=send_request,
        headers={"Content-Type": "application/json"}
    )
    
    if send_response.status_code != 200:
        print(f"❌ Ошибка при отправке задачи: {send_response.text}")
        return
    
    send_result = send_response.json()
    print("\nОтвет message/send:")
    print(json.dumps(send_result, ensure_ascii=False, indent=2))
    
    # В A2A result - это сразу Task или Message (без обертки "task")
    result_obj = send_result.get("result")
    if not isinstance(result_obj, dict):
        print("❌ Некорректный формат result")
        return
    
    # Проверяем, что это Task (kind == "task")
    if result_obj.get("kind") != "task":
        print("ℹ️ Агент вернул не Task, а Message или другой результат - tasks/get не нужен")
        return
    
    task_id = result_obj.get("id")
    if not task_id:
        print("❌ Не удалось получить task_id из result")
        return
    
    # 2) Получаем статус задачи
    get_request = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "params": {
            "id": task_id  # ВАЖНО: просто id, без обертки task_id
        },
        "id": 3
    }
    
    print(f"\nПолучаем статус задачи {task_id}...")
    
    get_response = requests.post(
        "http://localhost:8001/",
        json=get_request,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus: {get_response.status_code}")
    
    if get_response.status_code == 200:
        result = get_response.json()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("\n✅ Статус задачи получен успешно")
    else:
        print(f"❌ Ошибка: {get_response.text}")


def main() -> None:
    """Запуск всех тестов."""
    print("\n🔍 ТЕСТИРОВАНИЕ A2A СЕРВЕРА")
    print("Убедитесь, что сервер запущен: python -m app.a2a_server\n")
    
    try:
        test_agent_card()
        test_message_send()
        test_tasks_get()
        
        print("\n" + "=" * 80)
        print("🎉 ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ОШИБКА: Не удалось подключиться к серверу")
        print("Запустите сервер: python -m app.a2a_server")
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
