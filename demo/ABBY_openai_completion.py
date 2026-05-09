from openai import OpenAI
import os

ABBY_BASE_URL = os.getenv("ABBY_BASE_URL")
print(ABBY_BASE_URL)
ABBY_API_KEY = os.getenv("ABBY_API_KEY")

client = OpenAI(
    api_key=ABBY_API_KEY,
    base_url=ABBY_BASE_URL
)

completion = client.chat.completions.create(
    model="gpt-5.4",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "使用python语言编写斐波那伽数列生成器"}
    ]
)

print(completion.choices[0].message.content)