import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5:latest"


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


class OllamaClientError(RuntimeError):
    pass


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 120,
    ) -> None:
        load_env_file()
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        self.timeout = timeout

    def generate_text(self, prompt: str, *, system: str | None = None, format: str | None = None) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if format:
            payload["format"] = format
        response = self._post("/api/generate", payload)
        text = response.get("response", "")
        if not isinstance(text, str):
            raise OllamaClientError("Ollama returned a non-text response field.")
        return text.strip()

    def generate_json(self, prompt: str, *, system: str | None = None) -> dict[str, Any]:
        text = self.generate_text(prompt, system=system, format="json")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"Ollama returned invalid JSON: {exc}") from exc

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OllamaClientError(f"Ollama HTTP error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise OllamaClientError(f"Ollama connection error: {exc}") from exc
