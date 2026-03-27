import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
    ) -> dict[str, Any]:
        payload = {
            "api_key": self.api_key,
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_raw_content": include_raw_content,
        }
        request = Request(
            TAVILY_SEARCH_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TavilyClientError(f"Tavily HTTP error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise TavilyClientError(f"Tavily connection error: {exc}") from exc
