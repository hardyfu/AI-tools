import openai
import httpx
import os

http_client = httpx.Client(verify=False, follow_redirects=True)
ABB_QWEN_API_KEY = os.getenv("ABB_QWEN_API_KEY")

client = openai.OpenAI(
    api_key=ABB_QWEN_API_KEY,
    base_url="https://is-ai.abb.com.cn/v1",
    http_client=http_client
)

response = client.chat.completions.create(
    model="qwen3.5",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "使用python语言编写斐波那契额数列生成器"}
    ],
    temperature=0.3,
    top_p=0.95,
    max_tokens=8192,
    extra_body={
        "chat_template_kwargs": {"enable_thinking": False}
    }
)

print(response.choices[0].message.content)