import logging
from typing import Any

from duckduckgo_search import DDGS

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DuckDuckGoClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._max_results = settings.duckduckgo_max_results

    def search_text(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        result_size = max_results or self._max_results

        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=result_size))
        except Exception:
            logger.exception("DuckDuckGo search failed for query: %s", query)
            return []

        normalized: list[dict[str, Any]] = []
        for item in results:
            normalized.append(
                {
                    "title": item.get("title", ""),
                    "href": item.get("href", ""),
                    "body": item.get("body", ""),
                }
            )
        return normalized
