import os
import json
from google import genai
from google.genai import types

SYSTEM_PROMPT = """
你是一名专业的费曼学习法教练。你的目标是通过让用户向你解释概念，来帮助他们发现知识盲点。

## 行为准则：
1. **角色定位**：你是一个逻辑严密、但没有相关背景知识的学生。
2. **渐进引导**：
   - 第一步：请用户说出他们想解释的概念。
   - 第二步：倾听解释。如果用户使用术语，请追问：“对不起，我是外行，你能用更通俗的例子解释[术语]吗？”
   - 第三步：针对逻辑断层进行反问。例如：“如果 A 导致了 B，那中间发生了什么？”
3. **识别盲点**：在对话过程中，暗中记录用户解释不清晰或回避的地方。
4. **结束条件**：当用户输入“总结”、“结束”或解释已经足够完美时，生成结构化的 Markdown 报告。
"""

# --- 1. 配置加载 ---
def load_config():
    with open("/Users/ryan/Desktop/API.json", "r") as f:
        api_data = json.load(f)

    # 获取 API Key
    api_key = os.getenv('GEMINI_API_KEY', api_data.get("GEMINI"))
    model_id = os.getenv('GEMINI_MODEL_ID', 'gemini-3-flash-preview')  # 建议使用稳定版或你指定的 flash 预览版
    proxy = 'http://127.0.0.1:7890'

    # 初始化 Client (设置环境变量以支持代理)
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy

    client = genai.Client(api_key=api_key)
    return client, model_id


# --- 2. 核心交互函数 ---
def run_feynman_session():
    client, model_id = load_config()

    # 初始化对话上下文
    # 注意：最新的 SDK 中，系统指令通常在 generate_content 的 config 中传入
    chat = client.chats.create(model=model_id, config=types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.7
    ))

    print(">>> 费曼学习教练已上线。输入 '总结' 或 '退出' 结束对话并生成报告。\n")
    print("AI: 你好！今天你想教会我哪一个复杂的概念？")

    history_log = []

    while True:
        user_input = input("\n你: ").strip()
        if not user_input: continue

        # 判断是否结束
        if user_input.lower() in ['总结', 'exit', 'quit', '结束']:
            generate_final_report(chat)
            break

        # 流式获取响应
        print("\nAI: ", end="", flush=True)
        response_stream = chat.send_message_stream(user_input)

        current_response = ""
        for chunk in response_stream:
            if chunk.text:
                print(chunk.text, end="", flush=True)
                current_response += chunk.text
        print("\n")


# --- 3. 生成报告并保存 ---
def generate_final_report(chat_session):
    print("\n--- 正在为您整理费曼学习报告... ---")

    summary_prompt = "现在请根据我们刚才的对话，输出一份 Markdown 格式的学习报告。要求包含：1. 核心概念 2. 你的简化版理解 3. 发现的知识盲点 4. 改进建议。"

    response = chat_session.send_message(summary_prompt)
    report_content = response.text

    # 自动保存
    file_path = "Feynman_Report.md"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"\n✅ 报告已生成！保存位置：{os.path.abspath(file_path)}")


if __name__ == "__main__":
    try:
        run_feynman_session()
    except Exception as e:
        print(f"发生错误: {e}")