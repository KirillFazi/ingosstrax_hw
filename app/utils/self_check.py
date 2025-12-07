from __future__ import annotations

from typing import Tuple

from app.core.models import LLMClient, ReasoningResult, ReasoningStep

TIME_RANGE = (0.5, 600.0)
BRIDGE_RANGE = (20.0, 1000.0)
SPEED_RANGE = (5.0, 100.0)


def _check_range(
    value: float, min_v: float, max_v: float, description: str, units: str
) -> ReasoningStep:
    ok = min_v <= value <= max_v
    status = "ok" if ok else "fail"
    return ReasoningStep(
        description=description,
        data={
            "value": value,
            "min": min_v,
            "max": max_v,
            "units": units,
            "status": status,
        },
    )


def _llm_self_check(result: ReasoningResult, llm_client: LLMClient | None) -> ReasoningStep | None:
    if llm_client is None:
        return None
    try:
        llm = llm_client.get_model()
        prompt = (
            "Оцени корректность результата пересечения моста:\n"
            f"{result.model_dump()}\n"
            "Ответь кратко, до 2 предложений, укажи 'ok' или 'warning'."
        )
        opinion = llm.invoke(prompt)
        return ReasoningStep(
            description="LLM self-check (opinion)",
            data={"comment": str(opinion)},
        )
    except Exception as exc:  # noqa: BLE001
        return ReasoningStep(
            description="LLM self-check failed", data={"error": str(exc)}
        )


def self_check_result(
    result: ReasoningResult, llm_client: LLMClient | None = None
) -> Tuple[bool, list[ReasoningStep]]:
    """Validate the result for sanity and return extra steps."""
    steps: list[ReasoningStep] = []
    time_step = _check_range(
        result.time_seconds,
        TIME_RANGE[0],
        TIME_RANGE[1],
        "Проверка времени пересечения",
        "секунды",
    )
    bridge_step = _check_range(
        result.bridge.length_meters,
        BRIDGE_RANGE[0],
        BRIDGE_RANGE[1],
        "Проверка длины моста",
        "метры",
    )
    speed_step = _check_range(
        result.animal.speed_m_s,
        SPEED_RANGE[0],
        SPEED_RANGE[1],
        "Проверка скорости гепарда",
        "м/с",
    )
    steps.extend([time_step, bridge_step, speed_step])
    ok = all(step.data and step.data.get("status") == "ok" for step in steps)
    steps.append(
        ReasoningStep(
            description="Итог self-check",
            data={
                "ok": ok,
                "note": "При ok=False результат сомнителен. TODO: пересчитать с альтернативными источниками при необходимости.",
            },
        )
    )
    llm_step = _llm_self_check(result, llm_client)
    if llm_step:
        steps.append(llm_step)
    return ok, steps
