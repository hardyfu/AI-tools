import json
import os
from pathlib import Path
from dataclasses import dataclass
from getpass import getpass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class QwenConfig:
    enabled: bool
    api_key: str
    base_url: str
    text_model: str
    vision_model: str
    timeout_seconds: int = 180
    max_tokens: int = 1200
    enable_thinking: bool = False


@dataclass(frozen=True)
class _ChatResult:
    content: str
    reasoning: str


def parse_json_text(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    if not content:
        raise ValueError("Qwen returned an empty response.")
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


def _resolve_api_key(profile: dict[str, Any]) -> str:
    model_runtime = profile.get("model_runtime", {})
    dashscope = model_runtime.get("dashscope", {})
    api_key = str(dashscope.get("api_key", "")).strip()
    if api_key:
        return api_key

    api_json = Path('/Users/ryan/Desktop/API.json')
    if api_json.exists():
        try:
            payload = json.loads(api_json.read_text())
            api_key = str(payload.get('QWEN', '')).strip()
            if api_key:
                return api_key
        except Exception:
            pass

    api_key = str(os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if api_key:
        return api_key
    if os.isatty(0):
        print("未在 /Users/ryan/Desktop/API.json 中找到 QWEN，也未配置 DASHSCOPE_API_KEY。请输入阿里云百炼 API Key：", flush=True)
        return getpass("").strip()
    return ""


class QwenRuntime:
    def __init__(self, config: QwenConfig):
        self.config = config
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=config.timeout_seconds,
        )

    def ping(self) -> tuple[bool, str | None]:
        if not self.config.api_key:
            return False, "Missing DASHSCOPE_API_KEY."
        try:
            self.client.models.list()
            return True, None
        except Exception as exc:
            return False, str(exc)

    def _collect_stream(self, stream: Any) -> _ChatResult:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
            except Exception:
                continue
            reasoning_piece = getattr(delta, "reasoning_content", None)
            if reasoning_piece:
                reasoning_parts.append(str(reasoning_piece))
            content_piece = getattr(delta, "content", None)
            if content_piece:
                content_parts.append(str(content_piece))
        return _ChatResult(content="".join(content_parts).strip(), reasoning="".join(reasoning_parts).strip())

    def chat_text(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        images: list[Any] | None = None,
        temperature: float = 0.1,
        num_predict: int | None = None,
    ) -> str:
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if images:
            content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]
            for item in images:
                content.append({"type": "image_url", "image_url": {"url": str(item)}})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_prompt})

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=num_predict or self.config.max_tokens,
            extra_body={"enable_thinking": self.config.enable_thinking},
            stream=True,
        )
        result = self._collect_stream(stream)
        return result.content

    def chat_json(
        self,
        *,
        model: str,
        system_prompt: str,
        user_prompt: str,
        images: list[Any] | None = None,
        temperature: float = 0.1,
        num_predict: int | None = None,
    ) -> dict[str, Any]:
        json_system_prompt = (
            system_prompt + " Output valid JSON only. Do not use markdown fences or commentary."
        )
        content = self.chat_text(
            model=model,
            system_prompt=json_system_prompt,
            user_prompt=user_prompt,
            images=images,
            temperature=temperature,
            num_predict=num_predict,
        )
        return parse_json_text(content)


def build_ollama_runtime(profile: dict[str, Any]) -> tuple[QwenRuntime | None, dict[str, Any]]:
    config = profile.get("model_runtime", {})
    dashscope = config.get("dashscope", {})
    runtime_config = QwenConfig(
        enabled=bool(dashscope.get("enabled", True)),
        api_key=_resolve_api_key(profile),
        base_url=str(dashscope.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")),
        text_model=str(dashscope.get("text_model", "qwen3.5-plus")),
        vision_model=str(dashscope.get("vision_model", "qwen2.5-vl-72b-instruct")),
        timeout_seconds=int(dashscope.get("timeout_seconds", 180)),
        max_tokens=int(dashscope.get("max_tokens", 1200)),
        enable_thinking=bool(dashscope.get("enable_thinking", False)),
    )
    if not runtime_config.enabled:
        return None, {
            "provider": "dashscope",
            "enabled": False,
            "available": False,
            "skip_reason": "DashScope runtime disabled in project profile.",
            "text_model": runtime_config.text_model,
            "vision_model": runtime_config.vision_model,
            "base_url": runtime_config.base_url,
        }
    runtime = QwenRuntime(runtime_config)
    available, reason = runtime.ping()
    return runtime if available else None, {
        "provider": "dashscope",
        "enabled": True,
        "available": available,
        "skip_reason": reason,
        "text_model": runtime_config.text_model,
        "vision_model": runtime_config.vision_model,
        "base_url": runtime_config.base_url,
    }


OllamaRuntime = QwenRuntime
build_qwen_runtime = build_ollama_runtime
