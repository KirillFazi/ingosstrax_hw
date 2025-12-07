from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama



class OpenRouterLLMClient:
    """Factory that reads OPENROUTER_API_KEY and returns ChatOpenAI bound to OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.0,
        top_p: float = 0.0001,
        max_tokens: int | None = None,
        referer: str | None = None,
        app_title: str | None = None,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        self.model = model
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.referer = referer
        self.app_title = app_title

    def get_model(self) -> Any:
        # OpenRouter exposes an OpenAI-compatible API
        default_headers: dict[str, str] = {}
        if self.referer:
            default_headers["HTTP-Referer"] = self.referer
        if self.app_title:
            default_headers["X-Title"] = self.app_title

        return ChatOpenAI(
            model=self.model,
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=self.temperature,
            top_p=self.top_p,
            max_tokens=self.max_tokens,
            default_headers=default_headers or None,
        )


class OllamaLLMClient:
    """LangChain LLM client for a local Ollama model."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434") -> None:
        self.model = model
        self.base_url = base_url

    def get_model(self) -> Any:
        return ChatOllama(model=self.model, base_url=self.base_url)