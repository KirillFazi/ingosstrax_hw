from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    __package__ = "agent_app"

from .agent_cli import run_agent
from app.core.models import ReasoningResult

DEFAULT_QUESTION = "Сколько понадобится времени гепарду, чтобы пересечь Москву-реку по Большому Каменному мосту?"


class SolveRequest(BaseModel):
    question: str | None = None


class SolveResponse(BaseModel):
    result: dict[str, Any]
    raw_answer: str


def _build_raw_answer(result: ReasoningResult) -> str:
    return (
        f"{result.animal.name} пересекает {result.bridge.name} длиной "
        f"{result.bridge.length_meters:.1f} м за {result.time_human_readable} "
        f"при скорости {result.animal.speed_m_s:.1f} м/с."
    )


def get_app() -> FastAPI:
    app = FastAPI(title="Agent HTTP API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/solve", response_model=SolveResponse)
    def solve(payload: SolveRequest) -> SolveResponse:
        question = payload.question or DEFAULT_QUESTION
        result = run_agent(question)
        return SolveResponse(result=result.model_dump(), raw_answer=_build_raw_answer(result))

    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(get_app(), host="0.0.0.0", port=8000)
