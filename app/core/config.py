from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings


class LLMConfig(BaseModel):
    """LLM configuration for agent and self-check."""

    provider: Literal["openrouter", "ollama"] = "openrouter"
    agent_model: str = ""
    selfcheck_model: str = ""
    use_llm_selfcheck: bool = True
    ollama_base_url: HttpUrl = "http://localhost:11434"
    
    PROVIDER_MODELS: ClassVar[dict[str, dict[str, str]]] = {
        "openrouter": {
            "agent_model": "openai/gpt-oss-120b",
            "selfcheck_model": "openai/gpt-oss-120b"
        },
        "ollama": {
            "agent_model": "qwen2.5:7b",
            "selfcheck_model": "deepseek-r1:8b"
        }
    }
    
    @model_validator(mode='after')
    def set_models_from_provider(self):
        """Автоматически устанавливает модели на основе провайдера, если не указаны явно."""
        if not self.agent_model:
            self.agent_model = self.PROVIDER_MODELS[self.provider]["agent_model"]
        if not self.selfcheck_model:
            self.selfcheck_model = self.PROVIDER_MODELS[self.provider]["selfcheck_model"]
        return self


class AppConfig(BaseSettings):
    """Base configuration for the agent."""

    wikipedia_api_base: HttpUrl = "https://ru.wikipedia.org/w/api.php"
    a2a_base_url: HttpUrl | None = None
    http_port: int = 8000
    llm: LLMConfig = Field(default_factory=LLMConfig)

    model_config = {
        "env_prefix": "AGENT_",
        "env_nested_delimiter": "__",
        "extra": "ignore",
        "env_file": ".env",
    }
