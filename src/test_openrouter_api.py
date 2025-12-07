from __future__ import annotations

import os
import sys
import textwrap

import requests
from dotenv import load_dotenv
load_dotenv()


def main() -> None:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("❌ Переменная окружения OPENROUTER_API_KEY не установлена")
        sys.exit(1)

    url = "https://openrouter.ai/api/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        # Эти два заголовка OpenRouter рекомендует, но можно сначала без них:
        "HTTP-Referer": "http://localhost",      # адрес твоего приложения / сайта
        "X-Title": "OpenRouter test script",     # любое название проекта
        "Content-Type": "application/json",
    }

    payload = {
        "model": "openai/gpt-4o-mini",  # или любая другая доступная тебе модель
        "messages": [
            {"role": "user", "content": "Привет! Ответь одной короткой фразой, чтобы проверить OpenRouter API."}
        ],
        "max_tokens": 50,
    }

    print("→ Делаем запрос к OpenRouter...")
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        print("❌ Ошибка соединения с OpenRouter:\n", e)
        sys.exit(1)

    print(f"HTTP статус: {resp.status_code}")
    if resp.status_code != 200:
        print("Тело ответа:")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        print("❌ Не удалось распарсить ответ:", e)
        print("Полный JSON ответа:")
        print(data)
        sys.exit(1)

    print("✅ OpenRouter API работает. Ответ модели:")
    print("-" * 80)
    print(textwrap.fill(content, width=80))
    print("-" * 80)


if __name__ == "__main__":
    main()