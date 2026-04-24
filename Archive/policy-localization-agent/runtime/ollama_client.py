import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

try:
    from ollama import Client, ResponseError
except ModuleNotFoundError:  # pragma: no cover - dependency guard
    Client = None
    ResponseError = None


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"
DEFAULT_OLLAMA_STARTUP_TIMEOUT = 20.0


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
        temperature: float | None = None,
        num_ctx: int | None = None,
    ) -> None:
        load_env_file()
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        self.timeout = timeout
        env_temperature = os.environ.get("OLLAMA_TEMPERATURE")
        env_num_ctx = os.environ.get("OLLAMA_NUM_CTX")
        self.temperature = temperature if temperature is not None else (float(env_temperature) if env_temperature else None)
        self.num_ctx = num_ctx if num_ctx is not None else (int(env_num_ctx) if env_num_ctx else None)
        self.startup_timeout = DEFAULT_OLLAMA_STARTUP_TIMEOUT
        self.client = Client(host=self.base_url) if Client is not None else None

    def generate_text(self, prompt: str, *, system: str | None = None, format: str | None = None) -> str:
        if self.client is None:
            raise OllamaClientError("Missing Python dependency: ollama. Install it before running LLM-backed skills.")
        self._ensure_service()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        options: dict[str, Any] = {}
        if self.temperature is not None:
            options["temperature"] = self.temperature
        if self.num_ctx is not None:
            options["num_ctx"] = self.num_ctx

        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                stream=False,
                format=format,
                options=options or None,
            )
        except Exception as exc:
            if ResponseError is not None and isinstance(exc, ResponseError):
                raise OllamaClientError(f"Ollama SDK error for model {self.model}: {exc}") from exc
            raise OllamaClientError(f"Ollama SDK connection error: {exc}") from exc

        try:
            content = response["message"]["content"]
        except Exception as exc:
            raise OllamaClientError("Ollama SDK returned an unexpected response shape.") from exc
        if not isinstance(content, str):
            raise OllamaClientError("Ollama SDK returned a non-text message content field.")
        return content.strip()

    def generate_json(self, prompt: str, *, system: str | None = None) -> dict[str, Any]:
        text = self.generate_text(prompt, system=system, format="json")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise OllamaClientError(f"Ollama returned invalid JSON: {exc}") from exc

    def _healthcheck(self) -> bool:
        try:
            from urllib.request import urlopen

            with urlopen(f"{self.base_url}/api/tags", timeout=3) as response:
                return response.status == 200
        except Exception:
            return False

    def _ensure_service(self) -> None:
        if self._healthcheck():
            return

        ollama_bin = shutil.which("ollama")
        if not ollama_bin:
            raise OllamaClientError("Ollama is not installed or not on PATH.")

        try:
            subprocess.Popen(
                [ollama_bin, "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except Exception as exc:
            raise OllamaClientError(f"Failed to start Ollama service: {exc}") from exc

        deadline = time.time() + self.startup_timeout
        while time.time() < deadline:
            if self._healthcheck():
                return
            time.sleep(0.5)

        raise OllamaClientError(
            f"Ollama service did not become ready within {self.startup_timeout:.0f}s at {self.base_url}."
        )
