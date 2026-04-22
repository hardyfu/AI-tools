from ollama import chat

response = chat(
  model='qwen3.5:4b',
  messages=[{'role': 'user', 'content': '请用 Python 写一个简单的斐波那契数列生成器。'}],
  think=False,
  stream=False,
)

print('Thinking:\n', response.message.thinking)
print('Answer:\n', response.message.content)