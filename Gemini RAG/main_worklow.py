# main_workflow.py
"""
模块用途：
主控制脚本，基于 File Search Store 模式实现多轮 RAG 对话。
负责设置代理、API Key、文件准备，并调用 'rag_store_manager' 和 'rag_chat_manager'。
"""
import os
import getpass
import time
from google import genai
from google.genai.errors import APIError
import traceback

# 导入功能模块
from rag_store_manager import create_and_upload_to_store, cleanup_store
from rag_chat_manager import start_chat_with_store, interactive_chat_session

# =======================================================
# !!! 请替换为您的代理地址和端口 !!!
PROXY_URL = "http://127.0.0.1:7890"
# !!! 请替换为您想要上传的 PDF/TXT 文件路径 !!!
SAMPLE_FILE_PATH = "/Users/ryan/Downloads/words.pdf"
STORE_DISPLAY_NAME = "用户知识库"


# =======================================================

def setup_environment():
    """配置代理环境变量并提示用户输入 Gemini API Key。"""
    print("--- 🔑 API Key 输入 & ⚙️ 代理配置 ---")

    # 代理配置
    print(f"设定代理环境变量: {PROXY_URL}")
    os.environ['HTTP_PROXY'] = PROXY_URL
    os.environ['http_proxy'] = PROXY_URL
    os.environ['HTTPS_PROXY'] = PROXY_URL
    os.environ['https_proxy'] = PROXY_URL

    # API Key 输入
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        api_key = getpass.getpass("请输入您的 Gemini API Key: ")
        os.environ['GEMINI_API_KEY'] = api_key

    if not os.environ.get('GEMINI_API_KEY'):
        print("❌ 错误：未设置 GEMINI_API_KEY。")
        return False

    print("✅ 环境配置完成。")
    print("-" * 30)
    return True


def main_rag_workflow():
    """执行整个文档问答流程的主函数。"""

    if not setup_environment():
        return

    client = None
    store_name = None

    try:
        # 1. 初始化客户端
        client = genai.Client()
        print("✅ Gemini 客户端初始化成功。")
    except Exception as e:
        print(f"❌ 客户端初始化失败: {e}")
        return

    try:
        # --- 步骤 1 & 2: 创建和上传文件到 Store ---
        store_name = create_and_upload_to_store(client, SAMPLE_FILE_PATH, STORE_DISPLAY_NAME)
        if not store_name:
            # 如果上传或创建失败，store_name 可能是 None 或已存在的名称
            return

            # --- 步骤 3: 创建基于 Store 的聊天会话 ---
        chat_session = start_chat_with_store(client, store_name)
        if not chat_session:
            return

        # --- 步骤 4: 多轮问答 ---
        interactive_chat_session(chat_session)

    except Exception as e:
        print(f"\n❌ 发生程序错误: {e}")
        traceback.print_exc()
    finally:
        # --- 步骤 5: 清理 File Search Store ---
        print("\n--- 问答流程结束，执行清理操作 ---")
        if store_name and client:
            cleanup_store(client, store_name)
        print("程序已安全退出。")


if __name__ == "__main__":
    main_rag_workflow()