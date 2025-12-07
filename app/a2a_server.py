"""A2A Server using official a2a-sdk."""

from __future__ import annotations

import sys
from pathlib import Path

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from a2a.utils import new_agent_text_message

# Добавляем корень проекта в path если запускаем напрямую
if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "app"

from app.agent_cli import run_agent
from app.core.models import ReasoningResult

# Конфигурация агента для A2A
CHEETAH_SKILL_ID = "estimate_crossing_time"

agent_card = AgentCard(
    name="Cheetah Bridge Time Estimator",
    description=(
        "Оценивает время, за которое гепард (или другое животное) "
        "пересечет Москву-реку по Большому Каменному мосту, используя Wikipedia и рассуждения."
    ),
    url="http://localhost:8001",
    version="0.1.0",
    # Обязательные поля по A2A спецификации
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(
        streaming=False,
    ),
    skills=[
        AgentSkill(
            id=CHEETAH_SKILL_ID,
            name="Estimate crossing time",
            description=(
                "Принимает текстовый запрос (обычно вопрос вроде "
                "'Сколько времени нужно гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?') "
                "и возвращает обоснованный ответ с шагами рассуждения."
            ),
            tags=["cheetah", "bridge", "moscow", "reasoning", "wikipedia"],
        ),
    ],
)


class CheetahAgentExecutor(AgentExecutor):
    """Обёртка вокруг run_agent для A2A протокола."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Обработка message/send и message/stream.
        
        Не создаём Task/Artifact вручную, а просто публикуем одно агентское сообщение
        с финальным текстом ответа через new_agent_text_message.
        """
        user_text = context.get_user_input() or ""

        try:
            reasoning_result: ReasoningResult = run_agent(user_text, verbose=False)

            final_text = (
                f"{reasoning_result.animal.name} пересекает {reasoning_result.bridge.name} "
                f"длиной {reasoning_result.bridge.length_meters:.1f} м "
                f"за {reasoning_result.time_human_readable} "
                f"при скорости {reasoning_result.animal.speed_m_s:.1f} м/с.\n\n"
                f"Источники:\n"
                f"- Мост: {reasoning_result.bridge.source}\n"
                f"- Животное: {reasoning_result.animal.source}"
            )
        except Exception as exc:
            final_text = f"Ошибка при выполнении агента: {exc!r}"

        # Создаём одно агентское сообщение (Role.agent, TextPart внутри)
        message = new_agent_text_message(
            final_text,
            context_id=context.context_id,
            task_id=context.task_id,
        )

        # Публикуем его в очередь событий
        await event_queue.enqueue_event(message)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """
        Обработка tasks/cancel.
        
        Для простого агента без долгих задач отмена не поддерживается.
        """
        # Можно выбросить MethodNotImplementedError или просто ничего не делать
        return


# Инфраструктура A2A сервера
task_store = InMemoryTaskStore()
agent_executor = CheetahAgentExecutor()

request_handler = DefaultRequestHandler(
    agent_executor=agent_executor,
    task_store=task_store,
)

# Строим FastAPI приложение по A2A протоколу
# - /.well-known/agent-card.json  -> agent_card
# - POST /                        -> JSON-RPC методы (message/send, tasks/get, ...)
app = A2AFastAPIApplication(
    agent_card=agent_card,
    http_handler=request_handler,
).build(
    agent_card_url="/.well-known/agent-card.json",
    rpc_url="/",  # стандартный JSON-RPC endpoint
)


def start_a2a_server() -> None:
    """Запуск A2A сервера на порту 8001 (чтобы не конфликтовать с основным API)."""
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    start_a2a_server()
