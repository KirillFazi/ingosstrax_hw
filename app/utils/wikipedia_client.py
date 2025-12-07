from __future__ import annotations

from typing import Any

import requests

from app.core.config import AppConfig
from app.core.models import WikipediaPageSummary, WikipediaSearchResult


class WikipediaClient:
    """Client for interacting with the Wikipedia API."""

    def __init__(self, base_url: str | None = None) -> None:
        config = AppConfig()
        self.base_url = base_url or str(config.wikipedia_api_base)
        self.headers = {
            "User-Agent": "AgentApp/1.0 (https://github.com/KirillFazi; contact@example.com)"
        }

    def search_page(self, title: str, lang: str = "ru") -> WikipediaSearchResult | None:
        """Search for a Wikipedia page by title."""
        params = {
            "action": "query",
            "list": "search",
            "srsearch": title,
            "srlimit": 1,
            "format": "json",
        }
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError("Failed to search Wikipedia") from exc

        data: Any = response.json()
        search_results = data.get("query", {}).get("search", [])
        if not search_results:
            return None

        first = search_results[0]
        return WikipediaSearchResult(
            page_id=int(first.get("pageid")),
            title=str(first.get("title")),
            snippet=first.get("snippet"),
        )

    def get_page_summary(
        self, page_id: int, lang: str = "ru", intro_only: bool = True
    ) -> WikipediaPageSummary:
        """Retrieve summary information for a page by ID."""
        params = {
            "action": "query",
            "prop": "extracts|pageprops",
            "pageids": page_id,
            "explaintext": 1,
            "ppprop": "description",
            "format": "json",
        }
        if intro_only:
            params["exintro"] = 1
        try:
            response = requests.get(self.base_url, params=params, headers=self.headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError("Failed to fetch page summary") from exc

        data: Any = response.json()
        pages = data.get("query", {}).get("pages", {})
        page_data = pages.get(str(page_id)) or next(iter(pages.values()), None)
        if not page_data or int(page_data.get("pageid", -1)) == -1:
            raise LookupError(f"Wikipedia page {page_id} not found")

        return WikipediaPageSummary(
            page_id=int(page_data.get("pageid")),
            title=str(page_data.get("title")),
            extract=page_data.get("extract", ""),
            description=page_data.get("pageprops", {}).get("description"),
        )
