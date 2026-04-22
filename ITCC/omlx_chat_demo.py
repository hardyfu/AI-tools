from openai import OpenAI
import time

# 初始化客户端，指向本地 oMLX 服务
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="510918123Fu!"  # oMLX 在本地运行，不需要真实的 API Key，填入任意非空字符串即可
)

# 你的模型名称（需替换为 oMLX 中实际加载的模型目录名或别名，例如 "Qwen3.5-9B"）
# MODEL_NAME = "gemma-4-e4b-it-4bit"
MODEL_NAME = "Qwen3.5-9B-MLX-4bit"


def chat_with_omlx():
    print(f"正在调用 oMLX 模型: {MODEL_NAME} ...\n")

    try:
        start_time = time.perf_counter()

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "你是一个专业且简洁的 AI 编程助手。"},
                {"role": "user", "content": "请用 Python 写一个简单的斐波那契数列生成器。"}
            ],
            temperature=0.3,
            # max_tokens=8182
        )

        elapsed = time.perf_counter() - start_time

        # 打印模型的回复
        print("🤖 模型回复：")
        print(response.choices[0].message.content)
        print(f"\n⏱️ {MODEL_NAME} 本次调用耗时: {elapsed:.3f} 秒")

    except Exception as e:
        print(f"调用失败: {e}")


if __name__ == "__main__":
    chat_with_omlx()

# import os
#
# def get_env_value(*names):
#     for name in names:
#         value = os.getenv(name, "")
#         if value:
#             return value
#     return ""
#
# DEEPSEEK_API_KEY = get_env_value("DEEPSEEK_API_KEY")
# QWEN_API_KEY = get_env_value("DASHSCOPE_API_KEY")
#
# print(QWEN_API_KEY)