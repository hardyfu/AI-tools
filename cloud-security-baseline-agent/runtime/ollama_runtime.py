import json
import os
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any

from openai import AzureOpenAI


DEFAULT_AZURE_OPENAI_ENDPOINT = "https://elisecamea.cognitiveservices.azure.com/"
DEFAULT_AZURE_OPENAI_API_VERSION = "2024-12-01-preview"
DEFAULT_DEPLOYMENT = "gpt-5.4-mini"

_INTERACTIVE_CACHE: dict[str, str] = {}


@dataclass(frozen=True)
class AzureOpenAIConfig:
    enabled: bool
    api_key: str
    endpoint: str
    api_version: str
    deployment: str
    text_model: str
    vision_model: str
    finalization_model: str
    timeout_seconds: int = 180
    max_completion_tokens: int = 1200


@dataclass(frozen=True)
class _ChatResult:
    content: str
    reasoning: str


def parse_json_text(text: str) -> dict[str, Any]:
    content = (text or "").strip()
    if not content:
        raise ValueError("Azure OpenAI returned an empty response.")
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
    cached = _INTERACTIVE_CACHE.get("api_key", "").strip()
    if cached:
        return cached

    model_runtime = profile.get("model_runtime", {})
    for key in ("azure_openai", "dashscope"):
        runtime_config = model_runtime.get(key, {})
        api_key = str(runtime_config.get("api_key", "")).strip()
        if api_key:
            _INTERACTIVE_CACHE["api_key"] = api_key
            return api_key

    for env_name in ("AZURE_OPENAI_API_KEY", "OPENAI_API_KEY", "DASHSCOPE_API_KEY"):
        api_key = str(os.getenv(env_name) or "").strip()
        if api_key:
            _INTERACTIVE_CACHE["api_key"] = api_key
            return api_key

    prompt = "未在项目配置或环境变量中找到 Azure OpenAI API Key，请手动输入： "
    if os.isatty(0):
        while True:
            api_key = getpass(prompt).strip()
            if api_key:
                _INTERACTIVE_CACHE["api_key"] = api_key
                return api_key
            prompt = "API Key 不能为空，请重新输入： "
    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        try:
            while True:
                api_key = simpledialog.askstring(
                    "Azure OpenAI API Key",
                    prompt,
                    parent=root,
                    show="*",
                )
                api_key = str(api_key or "").strip()
                if api_key:
                    _INTERACTIVE_CACHE["api_key"] = api_key
                    return api_key
                prompt = "API Key 不能为空，请重新输入： "
        finally:
            root.destroy()
    except Exception:
        pass
    return ""


def _resolve_config_value(
    runtime_config: dict[str, Any],
    legacy_config: dict[str, Any],
    key: str,
    env_names: tuple[str, ...],
    default: str,
) -> str:
    value = str(runtime_config.get(key, "")).strip()
    if value:
        return value
    value = str(legacy_config.get(key, "")).strip()
    if value:
        return value
    for env_name in env_names:
        value = str(os.getenv(env_name) or "").strip()
        if value:
            _INTERACTIVE_CACHE[key] = value
            return value

    cached = _INTERACTIVE_CACHE.get(key, "").strip()
    if cached:
        return cached
    return default


def _resolve_deployment(profile: dict[str, Any]) -> str:
    model_runtime = profile.get("model_runtime", {})
    azure_openai = model_runtime.get("azure_openai", {})
    legacy = model_runtime.get("dashscope", {})

    value = str(azure_openai.get("deployment", "")).strip()
    if value:
        return value

    for key in ("text_model", "finalization_model", "vision_model"):
        value = str(azure_openai.get(key, "")).strip()
        if value:
            return value
        value = str(legacy.get(key, "")).strip()
        if value:
            return value

    for env_name in ("AZURE_OPENAI_DEPLOYMENT", "AZURE_OPENAI_TEXT_MODEL", "AZURE_OPENAI_FINALIZATION_MODEL", "AZURE_OPENAI_VISION_MODEL"):
        value = str(os.getenv(env_name) or "").strip()
        if value:
            _INTERACTIVE_CACHE["deployment"] = value
            return value

    cached = _INTERACTIVE_CACHE.get("deployment", "").strip()
    if cached:
        return cached
    return DEFAULT_DEPLOYMENT


class AzureOpenAIRuntime:
    def __init__(self, config: AzureOpenAIConfig):
        self.config = config
        self.client = AzureOpenAI(
            api_key=config.api_key,
            azure_endpoint=config.endpoint,
            api_version=config.api_version,
            timeout=config.timeout_seconds,
        )

    def ping(self) -> tuple[bool, str | None]:
        if not self.config.api_key:
            return False, "Missing Azure OpenAI API key."
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
            max_completion_tokens=num_predict or self.config.max_completion_tokens,
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


def build_azure_openai_runtime(profile: dict[str, Any]) -> tuple[AzureOpenAIRuntime | None, dict[str, Any]]:
    config = profile.get("model_runtime", {})
    azure_openai = config.get("azure_openai", {})
    legacy = config.get("dashscope", {})
    deployment = _resolve_deployment(profile)
    runtime_config = AzureOpenAIConfig(
        enabled=bool(azure_openai.get("enabled", legacy.get("enabled", True))),
        api_key=_resolve_api_key(profile),
        endpoint=_resolve_config_value(
            azure_openai,
            legacy,
            "endpoint",
            ("AZURE_OPENAI_ENDPOINT",),
            DEFAULT_AZURE_OPENAI_ENDPOINT,
        ),
        api_version=_resolve_config_value(
            azure_openai,
            legacy,
            "api_version",
            ("AZURE_OPENAI_API_VERSION",),
            DEFAULT_AZURE_OPENAI_API_VERSION,
        ),
        deployment=deployment,
        text_model=deployment,
        vision_model=deployment,
        finalization_model=deployment,
        timeout_seconds=int(azure_openai.get("timeout_seconds", legacy.get("timeout_seconds", 180))),
        max_completion_tokens=int(
            azure_openai.get("max_completion_tokens", legacy.get("max_completion_tokens", 1200))
        ),
    )
    if not runtime_config.enabled:
        return None, {
            "provider": "azure_openai",
            "enabled": False,
            "available": False,
            "skip_reason": "Azure OpenAI runtime disabled in project profile.",
            "deployment": runtime_config.deployment,
            "text_model": runtime_config.text_model,
            "vision_model": runtime_config.vision_model,
            "finalization_model": runtime_config.finalization_model,
            "endpoint": runtime_config.endpoint,
            "api_version": runtime_config.api_version,
        }
    runtime = AzureOpenAIRuntime(runtime_config)
    available, reason = runtime.ping()
    return runtime if available else None, {
        "provider": "azure_openai",
        "enabled": True,
        "available": available,
        "skip_reason": reason,
        "deployment": runtime_config.deployment,
        "text_model": runtime_config.text_model,
        "vision_model": runtime_config.vision_model,
        "finalization_model": runtime_config.finalization_model,
        "endpoint": runtime_config.endpoint,
        "api_version": runtime_config.api_version,
    }


OllamaRuntime = AzureOpenAIRuntime
build_ollama_runtime = build_azure_openai_runtime
build_qwen_runtime = build_azure_openai_runtime
