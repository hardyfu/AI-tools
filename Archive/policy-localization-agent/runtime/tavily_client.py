import json
import os
from pathlib import Path
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - dependency guard
    requests = None

try:
    import certifi
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    certifi = None


TAVILY_SEARCH_URL = "https://api.tavily.com/search"


def load_env_file() -> None:
    candidates = [
        Path(__file__).resolve().parent / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for path in candidates:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


class TavilyClientError(RuntimeError):
    pass


class TavilyClient:
    def __init__(self, api_key: str | None = None, timeout: int = 30) -> None:
        load_env_file()
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        self.timeout = timeout
        if not self.api_key:
            raise TavilyClientError("Missing TAVILY_API_KEY environment variable.")

    def search(
        self,
        query: str,
        *,
        topic: str = "general",
        max_results: int = 5,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
        include_domains: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
        }
        if include_domains:
            payload["include_domains"] = include_domains
        if requests is None:
            raise TavilyClientError("Missing Python dependency: requests. Install it before using Tavily HTTP fallback.")
        try:
            verify = certifi.where() if certifi is not None else True
            response = requests.post(TAVILY_SEARCH_URL, json=payload, timeout=self.timeout, verify=verify)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            detail = exc.response.text if exc.response is not None else str(exc)
            raise TavilyClientError(f"Tavily HTTP error: {detail}") from exc
        except requests.RequestException as exc:
            raise TavilyClientError(f"Tavily connection error: {exc}") from exc
