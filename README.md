# Agent: оценка времени пересечения Большого Каменного моста гепардом

Python-агент на LangChain, который получает данные из Википедии о длине Большого Каменного моста и скорости животных, рассчитывает время пересечения и выполняет самопроверку результата. Поддерживает OpenRouter и Ollama, есть HTTP API и минимальный A2A-слой.

## Архитектура

```text
app/
  core/
    config.py         — конфигурация (LLM, API URLs)
    llm.py            — LLM клиенты (OpenRouter, Ollama)
    models.py         — доменные модели и протоколы
  utils/
    wikipedia_client.py — запросы к Wikipedia API
    reasoning.py      — парсинг данных и расчет времени
    self_check.py     — валидация результатов
  agent.py            — LangChain агент с инструментами
  app.py              — FastAPI приложение /health, /solve
  a2a_server.py       — минимальный A2A-сервер (заглушка)

src/
  run_diagnostics.py  — скрипт диагностики системы
  run_agent_verbose.py — запуск агента с подробным выводом
  test_openrouter_api.py — проверка OpenRouter API
  test_a2a_client.py  — тестовый клиент для A2A сервера

tests/
  test_diagnostics.py — интеграционные тесты
  test_reasoning.py   — unit тесты для reasoning
```

## Установка

```bash
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows
pip install -r requirements.txt
```

**Примечание**: установка `a2a-sdk[http-server]` может занять некоторое время, так как включает зависимости для HTTP сервера.

Создайте файл `.env` с настройками:

```bash
# OpenRouter API ключ (если используете OpenRouter)
OPENROUTER_API_KEY=your_key_here
```

## Конфигурация LLM

Конфигурация использует Pydantic Settings с env-префиксом `AGENT_` и вложенностью через `__`.

### Автоматический выбор моделей по провайдеру

Достаточно изменить только `provider` — модели подберутся автоматически:

```bash
# OpenRouter (по умолчанию)
AGENT_LLM__PROVIDER=openrouter

# Или Ollama
AGENT_LLM__PROVIDER=ollama
```

Модели для каждого провайдера настроены в `app/core/config.py`:

- **OpenRouter**: `openai/gpt-oss-120b` для агента и self-check
- **Ollama**: `qwen2.5:7b` для агента, `deepseek-r1:8b` для self-check

### Переопределение моделей вручную

```bash
AGENT_LLM__PROVIDER=openrouter
AGENT_LLM__AGENT_MODEL=anthropic/claude-3.5-sonnet
AGENT_LLM__SELFCHECK_MODEL=openai/gpt-4o
AGENT_LLM__USE_LLM_SELFCHECK=true
```

### Настройка Ollama

```bash
# Установка и запуск Ollama
ollama serve

# Загрузка моделей
ollama pull qwen2.5:7b
ollama pull deepseek-r1:8b

# В .env
AGENT_LLM__PROVIDER=ollama
AGENT_LLM__OLLAMA_BASE_URL=http://localhost:11434
```

## Запуск

### Диагностика системы

```bash
python src/run_diagnostics.py
```

Проверяет:

- Wikipedia API (доступность и парсинг данных)
- Инициализацию LLM и агента
- Полный цикл работы агента end-to-end

### HTTP API сервер

```bash
python -m app.app
# или
uvicorn app.app:app --reload

# Эндпоинты:
# GET  http://localhost:8000/health
# POST http://localhost:8000/solve
#      Body: {"question": "Сколько времени зайцу нужно..."}
#      Question опционален, есть дефолтный запрос
```

### A2A сервер (официальный протокол)

```bash
python -m app.a2a_server
# Запускается на порту 8001

# Эндпоинты A2A:
# GET  /.well-known/agent-card.json  - AgentCard с описанием агента
# POST /                              - JSON-RPC методы (message/send, tasks/get, tasks/cancel)
```

Тестирование A2A сервера:

```bash
# Запустите сервер в одном терминале
python -m app.a2a_server

# В другом терминале запустите тестовый клиент
python src/test_a2a_client.py
```

Пример JSON-RPC запроса `message/send`:

```bash
curl -X POST http://localhost:8001 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [
          {
            "type": "text",
            "text": "Сколько времени гепарду нужно, чтобы пересечь мост?"
          }
        ]
      }
    },
    "id": 1
  }'
```

### Запуск агента напрямую

```bash
# С подробным выводом
python src/run_agent_verbose.py

# Из Python кода
from app.agent import run_agent
result = run_agent("Сколько времени гепарду...")
print(result.model_dump())
```

## A2A Протокол

Приложение реализует полноценный A2A (Agent-to-Agent) протокол с использованием официального `a2a-sdk`:

**Реализованные компоненты:**

- **AgentCard** (`/.well-known/agent-card.json`): описание агента, его навыков и возможностей
- **JSON-RPC методы**:
  - `message/send`: отправка сообщения агенту и получение ответа
  - `tasks/get`: получение статуса выполняемой задачи
  - `tasks/cancel`: отмена выполняемой задачи
- **AgentExecutor**: обертка вокруг `run_agent` для интеграции с A2A
- **Task/Artifact**: структурированные ответы с метаданными

**Особенности реализации:**

- Использует `InMemoryTaskStore` и `InMemoryQueueManager` для управления задачами
- Артефакты содержат как текстовый ответ, так и полные данные `ReasoningResult` в metadata
- Поддерживает обработку ошибок с корректными статусами задач

## Самопроверка (Self-check)

После расчета `ReasoningResult` автоматически выполняется валидация:

**Базовая проверка (rules-based):**

- Время пересечения: 0.5–600 секунд
- Длина моста: 20–1000 метров
- Скорость животного: 5–100 м/с

**LLM-проверка (опциональная):**

- Если `use_llm_selfcheck=true`, LLM анализирует результат
- Добавляет экспертное мнение о корректности

Результаты проверок добавляются в `steps` с флагом `ok`. При `ok=False` результат помечается как сомнительный.

## Тесты

```bash
# Все тесты
pytest

# Только unit тесты (без сети)
pytest tests/test_reasoning.py -v

# Только интеграционные тесты (требуют сеть и API ключ)
pytest -m integration

# С покрытием
pytest --cov=app --cov-report=html
```

## Ограничения и допущения

- **Парсинг данных**: использует regex для извлечения чисел из текста Wikipedia. Зависит от формата статей.
- **Fallback механизм**: при ошибках Wikipedia используются дефолтные значения (487м для моста, 90 км/ч для гепарда).
- **Языковая поддержка**: приоритет русской Wikipedia, при отсутствии данных переключается на английскую.
- **LLM**: требует сетевой доступ и API ключ для OpenRouter, или локальный Ollama.
- **A2A протокол**: использует официальный `a2a-sdk`, реализует JSON-RPC методы и `/.well-known/agent-card.json`.

## Структура данных

```python
class ReasoningResult(BaseModel):
    bridge: BridgeInfo          # название, длина, источник
    animal: AnimalSpeed         # название, скорость, источник
    time_seconds: float         # расчитанное время
    time_human_readable: str    # "X минут Y секунд"
    steps: list[ReasoningStep]  # цепочка рассуждений + проверки
```

## Пример использования

### Запрос

```python
from app.agent_cli import run_agent

result = run_agent("Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?")
print(result.model_dump())
```

### Ответ

```json
{
  "bridge": {
    "name": "Большой Каменный мост",
    "length_meters": 487.0,
    "source": "https://ru.wikipedia.org/?curid=95754"
  },
  "animal": {
    "name": "Гепард",
    "speed_m_s": 30.56,
    "source": "https://ru.wikipedia.org/?curid=9166",
    "speed_km_h": 110.0
  },
  "time_seconds": 15.94,
  "time_human_readable": "15.9 секунд",
  "steps": [
    {
      "description": "Получена длина моста",
      "data": {
        "name": "Большой Каменный мост",
        "length_meters": 487.0
      }
    },
    {
      "description": "Получена скорость животного",
      "data": {
        "name": "Гепард",
        "speed_m_s": 30.56,
        "speed_km_h": 110.0
      }
    },
    {
      "description": "Рассчитано время пересечения",
      "data": {
        "time_seconds": 15.94
      }
    },
    {
      "description": "Проверка времени пересечения",
      "data": {
        "value": 15.94,
        "min": 0.5,
        "max": 600.0,
        "units": "секунды",
        "status": "ok"
      }
    },
    {
      "description": "Проверка длины моста",
      "data": {
        "value": 487.0,
        "min": 20.0,
        "max": 1000.0,
        "units": "метры",
        "status": "ok"
      }
    },
    {
      "description": "Проверка скорости животного",
      "data": {
        "value": 30.56,
        "min": 5.0,
        "max": 100.0,
        "units": "м/с",
        "status": "ok"
      }
    },
    {
      "description": "Итог self-check",
      "data": {
        "ok": true,
        "note": "При ok=False результат сомнителен."
      }
    },
    {
      "description": "LLM self-check (opinion)",
      "data": {
        "comment": "ok."
      }
    }
  ]
}
```

### Особенности примера

- **Wikipedia API**: данные о гепарде и мосте успешно получены из русской Wikipedia
- **Расчет**: гепард со скоростью 110 км/ч (30.56 м/с) пересечет мост 487м за ~16 секунд
- **Self-check**: все базовые проверки прошли (`status: "ok"`)
- **LLM opinion**: модель подтвердила корректность расчета
- **Цепочка рассуждений**: полная трассировка от получения данных до финальной проверки

## License

MIT
