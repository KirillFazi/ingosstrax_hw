from __future__ import annotations

import argparse
import json
from typing import Any

from langchain.agents import create_agent
from langchain.tools import tool

from app.core.config import AppConfig
from app.core.models import LLMClient, ReasoningResult, ReasoningStep
from app.utils.reasoning import (
    estimate_crossing_time,
    get_animal_speed,
    get_bridge_info_big_stone_bridge,
)
from app.utils.self_check import self_check_result
from app.utils.wikipedia_client import WikipediaClient


def _build_tools(client: WikipediaClient, cache: dict[str, Any]) -> list[Any]:
    @tool
    def bridge_info_tool(_: str = "") -> str:
        """Get information about the Big Stone Bridge (Bolshoy Kamenny Most) in Moscow, including its length in meters."""
        if "bridge" not in cache:
            cache["bridge"] = get_bridge_info_big_stone_bridge(client)
        bridge = cache["bridge"]
        return f"Bridge: {bridge.name}, Length: {bridge.length_meters} meters, Source: {bridge.source}"

    @tool
    def animal_speed_tool(animal: str) -> str:
        """Get the speed of an animal from Wikipedia. Input should be the animal name in Russian (e.g., 'Гепард' or 'Заяц')."""
        key = f"animal:{animal.lower()}"
        if key not in cache:
            cache[key] = get_animal_speed(client, animal)
        cache["animal"] = cache[key]
        animal_data = cache[key]
        return (
            f"Animal: {animal_data.name}, Speed: {animal_data.speed_m_s} m/s "
            f"({animal_data.speed_km_h} km/h), Source: {animal_data.source}"
        )

    return [bridge_info_tool, animal_speed_tool]


def build_agent_executor(
    llm_client: LLMClient, client: WikipediaClient, verbose: bool = False
) -> tuple[Any, dict[str, Any]]:
    tools_cache: dict[str, Any] = {}
    tools = _build_tools(client, tools_cache)
    llm = llm_client.get_model()

    system_prompt = (
        "Ты помощник, который использует инструменты для ответа. "
        "Всегда вызывай bridge_info_tool и animal_speed_tool (обязательный аргумент animal из запроса). "
        "Пример: Пользователь спрашивает 'Сколько времени зайцу нужно, чтобы перейти мост?'. "
        "Ты вызываешь animal_speed_tool с аргументом 'Заяц'. "
        "Если запрос: 'Гепард пересечет мост за сколько секунд?', вызываешь animal_speed_tool с аргументом 'Гепард'."
    )
    agent_graph = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    class _Executor:
        def __init__(self, graph: Any, cache: dict[str, Any]) -> None:
            self.graph = graph
            self.cache = cache

        def invoke(self, inputs: dict[str, Any]) -> dict[str, Any]:
            user_input = inputs.get("input", "")
            return self.graph.invoke({"messages": [{"role": "user", "content": user_input}]})

    return _Executor(agent_graph, tools_cache), tools_cache


def run_agent(
    query: str,
    llm_client: LLMClient | None = None,
    client: WikipediaClient | None = None,
    verbose: bool = True,
    max_tool_retries: int = 3,
) -> ReasoningResult:
    """Entry point to resolve the query via agent and produce ReasoningResult."""
    config = AppConfig()
    wikipedia_client = client or WikipediaClient()

    if llm_client is None:
        if config.llm.provider == "ollama":
            from app.core.llm import OllamaLLMClient

            llm_client = OllamaLLMClient(
                model=config.llm.agent_model, base_url=str(config.llm.ollama_base_url)
            )
        elif config.llm.provider == "openrouter":
            from app.core.llm import OpenRouterLLMClient

            llm_client = OpenRouterLLMClient(model=config.llm.agent_model)
        else:
            raise ValueError(f"Unknown LLM provider {config.llm.provider}")

    executor, tools_cache = build_agent_executor(llm_client, wikipedia_client, verbose=verbose)
    output: dict[str, Any] | None = None
    last_error: Exception | None = None
    bridge = tools_cache.get("bridge")
    animal = tools_cache.get("animal")

    for attempt in range(1, max_tool_retries + 1):
        if not bridge or not animal:
            try:
                output = executor.invoke({"input": query})
            except Exception as exc:  # noqa: PERF203, BLE001
                last_error = exc
                output = {"error": str(exc)}
            bridge = tools_cache.get("bridge")
            animal = tools_cache.get("animal")
            if verbose and (not bridge or not animal) and attempt < max_tool_retries:
                print(
                    f"Попытка {attempt} не вызвала все инструменты. "
                    f"Повторяем (макс {max_tool_retries})."
                )
        else:
            break

    print("RAW AGENT OUTPUT:", output)
    print("TOOLS CACHE:", tools_cache)
    
    # Agent must have called tools; retrieve data from cache
    bridge = tools_cache.get("bridge")
    animal = tools_cache.get("animal")

    
    if not bridge or not animal:
        error_hint = f" Последняя ошибка: {last_error}" if last_error else ""
        raise RuntimeError(
            "Agent did not call required tools after retries. "
            f"Bridge or animal data is missing.{error_hint}"
        )
    
    result = estimate_crossing_time(bridge, animal)
    
    llm_selfcheck_client: LLMClient | None = None
    if config.llm.use_llm_selfcheck:
        if config.llm.provider == "ollama":
            from app.core.llm import OllamaLLMClient

            llm_selfcheck_client = OllamaLLMClient(
                model=config.llm.selfcheck_model, base_url=str(config.llm.ollama_base_url)
            )
        elif config.llm.provider == "openrouter":
            from app.core.llm import OpenRouterLLMClient

            llm_selfcheck_client = OpenRouterLLMClient(model=config.llm.selfcheck_model)

    _, check_steps = self_check_result(result, llm_client=llm_selfcheck_client)
    result.steps.extend(check_steps)
    result.steps.append(
        ReasoningStep(description="Агентный ответ", data={"raw_agent_output": output})
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run agent_app via LangChain agent.")
    parser.add_argument(
        "--query",
        default="Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?",
        help="User query to process.",
    )
    args = parser.parse_args()
    result = run_agent(args.query)
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
