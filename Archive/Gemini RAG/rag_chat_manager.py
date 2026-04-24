# rag_chat_manager.py
"""
模块用途：
负责处理与 Gemini 模型的聊天会话逻辑。
使用 File Search Store (知识库) 作为 Tool 配置，实现多轮 RAG 对话。
"""
from typing import Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError


def create_rag_config(store_name: str) -> types.GenerateContentConfig:
    """
    创建包含 File Search Store 引用的配置对象。
    """
    # 强大的系统指令，约束模型的行为
    system_instruction = (
        "你是一个专门的文档分析助手。你的任务是严格基于用户提供的知识库 Store 内容来回答所有问题。 "
        "请务必使用检索到的信息进行回答。如果你无法从知识库中找到答案，你必须明确说明信息不在知识库中。"
    )

    # 配置 File Search 工具
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=[
            types.Tool(
                file_search=types.FileSearch(
                    file_search_store_names=[store_name]
                )
            )
        ]
    )
    return config


def start_chat_with_store(client: genai.Client, store_name: str) -> Optional[genai.Chat]:
    """
    💬 创建一个新的聊天会话，并将 Store 配置作为 RAG 上下文。
    """
    try:
        print(f"💬 正在创建聊天会话，并使用 Store {store_name} 作为 RAG 知识库...")

        rag_config = create_rag_config(store_name)

        # 在 ChatSession 中，config 用于设置整个会话的生成参数，包括 RAG 工具
        chat = client.chats.create(
            model="gemini-2.5-flash",
            config=rag_config
        )

        print(f"✅ 聊天会话创建成功。Store {store_name} 已激活为检索工具。")
        return chat
    except APIError as e:
        print(f"❌ 聊天会话创建失败: {e}")
        return None


def interactive_chat_session(chat_session: genai.Chat):
    """
    🚀 运行交互式多轮问答循环。
    """
    print("---" * 10)
    print("🚀 开始多轮 RAG 问答（输入 '退出' 或 'exit' 停止）")

    while True:
        user_input = input("您的问题 (或 '退出'): ").strip()

        if user_input.lower() in ["退出", "exit", "stop"]:
            break

        if not user_input:
            continue

        print("\n🤖 Gemini 正在思考...")
        try:
            # 关键：多轮聊天中，只需传入用户文本，File Search Store 配置在创建会话时已设置
            response = chat_session.send_message(user_input)

            # 打印回复
            print(f"👉 回复: {response.text}")

            # 打印引用信息 (Grounding Metadata)
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.grounding_chunks:
                    print("--- 📄 引用来源 ---")
                    # 只打印第一个引用的文件信息
                    first_chunk = metadata.grounding_chunks[0]
                    title = getattr(first_chunk.retrieved_context, 'title', 'N/A')
                    print(f"来源文件: {title} (共引用 {len(metadata.grounding_chunks)} 个片段)")
                else:
                    print("   (模型未使用知识库检索来生成回复。)")

        except APIError as e:
            print(f"❌ 消息发送失败: {e}")
            break

        print("---" * 10)