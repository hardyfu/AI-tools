def llm_call_streaming(prompt: str, client, model_id: str, provider_type: str, extra_config: dict = None) -> str:
    """
    调用 LLM API 生成内容，支持 OpenAI (Qwen) 和 Google GenAI (Gemini)
    """
    if client is None:
        raise Exception(f"LLM 客户端 ({provider_type}) 未提供或初始化失败。")

    print(f"  [LLM] 正在生成摘要 ({provider_type} 静默模式)...")

    full_summary = ""

    try:
        if provider_type == 'openai':
            messages = [
                {'role': 'system', 'content': '你是一位专业的中文摘要专家。'},
                {'role': 'user', 'content': prompt}
            ]
            completion = client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.3,
                extra_body=extra_config,
                stream=True
            )
            for chunk in completion:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    full_summary += delta.content

        elif provider_type == 'google':
            # Gemini Native SDK (google-genai)
            # extra_config 已经是 types.GenerateContentConfig
            response_stream = client.models.generate_content_stream(
                model=model_id,
                contents=prompt,
                config=extra_config
            )
            for chunk in response_stream:
                if chunk.text:
                    full_summary += chunk.text

    except Exception as e:
        import sys
        print(f"\n❌ LLM 处理中途发生错误: {e}", file=sys.stderr)
        return full_summary if full_summary else f"LLM 调用失败: {e}"

    return full_summary