from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class LLMClient(Protocol):
    """Protocol for LLM clients used in agent and self-check."""
    
    def get_model(self) -> Any:
        """Return the underlying LLM model instance."""
        ...


class CrossingEstimate(BaseModel):
    """Structured result of a crossing time estimation."""

    cheetah_speed_mps: float
    bridge_length_m: float
    crossing_time_seconds: float


class ReasoningTrace(BaseModel):
    """Intermediate reasoning steps for transparency."""

    steps: list[str]


class WikipediaSearchResult(BaseModel):
    """Single Wikipedia search result."""

    page_id: int
    title: str
    snippet: str | None = None


class WikipediaPageSummary(BaseModel):
    """Summary details for a Wikipedia page."""

    page_id: int
    title: str
    extract: str
    description: str | None = None


class BridgeInfo(BaseModel):
    """Information about a bridge."""

    name: str
    length_meters: float
    source: str


class AnimalSpeed(BaseModel):
    """Speed characteristics of an animal."""

    name: str
    speed_m_s: float
    source: str
    speed_km_h: float | None = None

    @classmethod
    def from_kmh(cls, name: str, speed_km_h: float, source: str) -> "AnimalSpeed":
        return cls(
            name=name,
            speed_m_s=kmh_to_ms(speed_km_h),
            source=source,
            speed_km_h=speed_km_h,
        )


class ReasoningStep(BaseModel):
    """Single reasoning step."""

    description: str
    data: dict[str, Any] | None = None


class ReasoningResult(BaseModel):
    """Final reasoning result."""

    bridge: BridgeInfo
    animal: AnimalSpeed
    time_seconds: float
    time_human_readable: str
    steps: list[ReasoningStep]


def kmh_to_ms(speed_km_h: float) -> float:
    """Convert speed from km/h to m/s."""
    return speed_km_h / 3.6


def format_seconds(seconds: float) -> str:
    """Format seconds into a human-readable string."""
    if seconds < 60:
        return f"{seconds:.1f} секунд"
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    if remainder < 0.1:
        return f"{minutes} минут"
    return f"{minutes} минут {remainder:.1f} секунд"
