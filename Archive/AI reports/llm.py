import os
import json
import sys

import httpx
from typing import Optional


async def llm_call(prompt: str, model_id: Optional[str] = None) -> str:
    """
    调用 LLM API 生成内容 (兼容 OpenAI 标准协议)。

    :param prompt: 提示词内容
    :param model_id: 模型 ID (可选)
    :return: LLM 生成的内容
    :raises Exception: API 调用失败或响应异常
    """
    try:
        api_key = os.getenv('LLM_API_KEY')
        api_url = os.getenv('LLM_API_URL')
        model = model_id if model_id else os.getenv('LLM_MODEL_ID')

        if not api_key or not api_url or not model:
            raise Exception('LLM 配置不完整：缺少 LLM_API_KEY, LLM_API_URL, 或 LLM_MODEL_ID')

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        data = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'response_format': {'type': "json_object"},
            'temperature': 0.7,
            'enable_thinking': False,
        }

        timeout_seconds = 1200  # 20分钟超时

        print("   [LLM] 正在发送 API 请求...")

        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=data
            )
            response.raise_for_status()

            response_data = response.json()

            content = (response_data.get('choices', [{}])[0]
                       .get('message', {})
                       .get('content'))

            if not content:
                print("原始响应内容为空:", json.dumps(response_data, indent=2))
                raise Exception('API 返回数据格式异常或内容为空')

            return content

    except httpx.HTTPStatusError as e:
        error_details = json.dumps(e.response.json(), indent=2)
        print(f'\n❌ LLM API 调用失败: {e.response.status_code} 状态码错误')
        print(f'   错误详情: {error_details}', file=sys.stderr)
        raise
    except httpx.RequestError as e:
        print(f'\n❌ LLM API 调用失败: 请求错误 ({e})', file=sys.stderr)
        raise
    except Exception as error:
        print(f'\n❌ LLM API 调用失败: {error}', file=sys.stderr)
        raise