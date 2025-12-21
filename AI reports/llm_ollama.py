import os
import json
import asyncio
import requests
import sys
from dotenv import load_dotenv

# 确保加载配置
load_dotenv()

# 从环境变量获取配置
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL')
OLLAMA_MODEL_NAME = os.getenv('OLLAMA_MODEL_NAME')


# ----------------- Ollama 核心同步调用 -----------------

def call_ollama_sync(prompt: str) -> str:
    """
    同步调用 Ollama 的 /api/generate 接口，并优化 JSON 输出和超时。
    """
    if not OLLAMA_BASE_URL or not OLLAMA_MODEL_NAME:
        raise ValueError("❌ 错误: OLLAMA_BASE_URL 或 OLLAMA_MODEL_NAME 未设置，请检查 .env 文件。")

    url = f"{OLLAMA_BASE_URL}/api/generate"

    # Ollama API 请求体
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json",  # <-- 强制 JSON 输出
        "options": {
            "temperature": 0.0,  # <-- 极低温度，提高结构化稳定性
        }
    }

    try:
        print(f"⚙️  正在向 Ollama 发送请求 (模型: {OLLAMA_MODEL_NAME})...")

        # 延长超时时间到 900 秒 (15 分钟)，解决 Read timed out 问题
        response = requests.post(url, json=payload, timeout=900)
        response.raise_for_status()

        result = response.json()

        # 确保提取的内容不包含 Ollama 的错误或聊天式的说明
        response_content = result.get('response', '').strip()

        # 如果 Ollama 强制输出 JSON 失败，它可能会在 response 中放错误信息
        if response_content and ("error" in response_content.lower() or "not a valid json" in response_content.lower()):
            print(f"❌ Ollama 返回内容似乎包含错误或解释: {response_content[:100]}...", file=sys.stderr)
            # 尝试返回原始内容，让 main_script 中的 extract_json 处理
            return response_content

        return response_content

    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(
            f"❌ 无法连接到 Ollama 服务器 ({OLLAMA_BASE_URL})。请确认 Ollama 已启动且模型已拉取。") from e
    except requests.exceptions.RequestException as e:
        print(f"❌ Ollama API 请求失败: {e}", file=sys.stderr)
        raise e


# ----------------- 异步包装 -----------------

async def llm_call(prompt: str) -> str:
    """
    异步调用 LLM 的主要接口。
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, call_ollama_sync, prompt)