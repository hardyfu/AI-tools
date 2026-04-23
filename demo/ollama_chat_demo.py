from openai import OpenAI

client = OpenAI(
    base_url='http://127.0.0.1:11434/v1/',
    api_key='ollama',  # required but ignored
)

chat_completion = client.chat.completions.create(
    messages=[
        {"role": "system", "content": "你是一个专业且简洁的 AI 编程助手。"},
        {"role": "user", "content": "请用 Python 写一个简单的斐波那契数列生成器。"}
    ],
    model='qwen3.5:4b',
)
print(chat_completion.choices[0].message.content)