import os
from openai import OpenAI


def get_client():
    api_key = os.getenv("DASHSCOPE_API_KEY")

    if not api_key:
        api_key = input("Please enter your DASHSCOPE_API_KEY: ").strip()

    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1",
    )


def call_llm(prompt: str) -> str:
    client = get_client()

    response = client.responses.create(
        model="qwen3.6-plus",
        input=prompt,
        extra_body={
            "enable_thinking": True
        }
    )

    final_text = []

    for item in response.output:
        if item.type == "message":
            for content in item.content:
                if hasattr(content, "text"):
                    final_text.append(content.text)

    return "\n".join(final_text).strip()