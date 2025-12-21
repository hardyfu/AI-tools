import sys
from config import client, LLM_API_URL  # 导入客户端实例和 URL


def llm_call_streaming(prompt: str, model_id: str) -> str:
    """
    调用 LLM API 生成内容，不在控制台实时打印，只返回完整的摘要文本。
    """
    if client is None:
        raise Exception("LLM 客户端未初始化成功，无法进行调用。")

    print("  [LLM] 正在生成摘要 (静默模式)...")  # 仅保留过程状态提示

    messages = [
        {'role': 'system', 'content': '你是一位专业的中文摘要专家。'},
        {'role': 'user', 'content': prompt}
    ]

    try:
        completion = client.chat.completions.create(
            model=model_id,
            messages=messages,
            temperature=0.3,
            extra_body={"enable_thinking": False},  # 虽然不显示，但仍可启用
            stream=True
        )
    except Exception as e:
        raise Exception(f'LLM API 调用失败: 请检查 API 密钥、URL 或网络连接。原始错误: {e}')

    # --- 静默流式处理逻辑 ---
    full_summary = ""

    try:
        for chunk in completion:
            delta = chunk.choices[0].delta

            # 仅收集内容，不再打印思考过程或回复
            if hasattr(delta, "content") and delta.content:
                content = delta.content
                full_summary += content

    except Exception as e:
        print(f"\n❌ LLM 流式处理中途发生错误: {e}", file=sys.stderr)
        return full_summary if full_summary else "LLM 流式调用失败或中断。"

    return full_summary  # 返回完整的摘要