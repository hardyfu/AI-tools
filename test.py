# file_search_rag_demo_with_proxy.py

import os
import time
from google import genai
from google.genai import types
from google.genai.errors import APIError
import traceback

# --- 1. 配置代理和 API Key ---

# 替换为您的代理地址和端口
proxy_url = "http://127.0.0.1:7890"

# 适用于 HTTP 代理
os.environ['HTTP_PROXY'] = proxy_url
os.environ['http_proxy'] = proxy_url

# 适用于 HTTPS 代理 (推荐，因为 Gemini API 使用 HTTPS)
os.environ['HTTPS_PROXY'] = proxy_url
os.environ['https_proxy'] = proxy_url

# 设置您的 API Key (注意：在实际生产环境中，不建议将 Key 硬编码在代码中)
# 如果您已经通过 shell 设置了环境变量，可以省略这一行。
os.environ['GEMINI_API_KEY'] = ''  # **请将 YOUR_API_KEY_HERE 替换为您的实际密钥**

# 检查 API Key 是否设置
if not os.environ.get('GEMINI_API_KEY'):
    print("❌ 错误：请在脚本中设置 GEMINI_API_KEY 或通过环境变量设置。")
    exit()

# 初始化 Client (它将自动使用上述环境变量中的代理和 Key)
try:
    client = genai.Client()
except Exception as e:
    print(f"❌ 初始化 Gemini Client 失败: {e}")
    print("请检查网络连接、代理配置以及 GEMINI_API_KEY。")
    exit()

TEST_FILE_NAME = "rag_document_sample.txt"
STORE_DISPLAY_NAME = "我的专业知识库"
MODEL_NAME = "gemini-2.5-flash"


# --- 2. 准备文件 (虚拟文件创建) ---
def create_sample_file(filename):
    """创建用于演示的虚拟文本文件。"""
    content = (
        "核心安全规则：所有员工必须每年进行网络安全培训。\n"
        "AI 专家团队的职责包括：模型性能监控和恶意输入过滤。\n"
        "最新的季度报告显示，RAG 系统的准确率提升了 15%。\n"
        "会议记录：下次会议时间定于下周三下午 2 点，主题是：Gemini API 新功能 File Search 的应用。\n"
        "重要链接：查看 Gemini File Search 的官方文档：https://ai.google.dev/gemini-api/docs/file-search"
    )
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ 创建虚拟文件: {filename}")


# --- 3. 主要 RAG 增强流程函数 ---
def run_file_search_rag_demo():
    """执行 File Search Store 的创建、上传、查询和清理。"""

    create_sample_file(TEST_FILE_NAME)

    file_search_store = None
    store_name = None
    try:
        # 步骤 A: 创建 File Search Store
        print("\n--- 1. 创建 File Search Store ---")
        file_search_store = client.file_search_stores.create(
            config={"display_name": STORE_DISPLAY_NAME}
        )
        store_name = file_search_store.name
        print(f"✅ Store 创建成功: {store_name}")

        # 步骤 B: 上传文件并导入 Store
        print("\n--- 2. 上传文件并导入 Store ---")
        operation = client.file_search_stores.upload_to_file_search_store(
            file=TEST_FILE_NAME,
            file_search_store_name=store_name,
            config={"display_name": TEST_FILE_NAME}
        )
        print(f"⏳ 正在等待文件索引完成 (Operation: {operation.name})...")

        # 等待索引操作完成
        while not operation.done:
            time.sleep(5)
            operation = client.operations.get(operation)
            print("   索引中...")

        print("✅ 文件索引完成!")

        # 步骤 C: 使用 RAG 进行查询
        print("\n--- 3. 执行 RAG 增强查询 ---")
        user_prompt = "请用一句话概括最新的会议主题，并告诉我 RAG 系统的准确率提升了多少？"

        config = types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )
            ]
        )

        print(f"提问: {user_prompt}")
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=config
        )

        print("\n--- 🤖 Gemini 回复 ---")
        print(response.text)
        print("-" * 30)

        # 步骤 D: 打印引用信息 (Grounding Metadata)
        if response.candidates and response.candidates[0].grounding_metadata:
            metadata = response.candidates[0].grounding_metadata
            print("--- 📄 引用来源 (Citations) ---")

            if metadata.grounding_chunks:
                for i, chunk in enumerate(metadata.grounding_chunks, 1):
                    # 获取文件名/标题
                    title = getattr(chunk.retrieved_context, 'title', 'N/A')
                    print(f"来源文件: {title}")

                    # 安全获取检索到的文本片段。优先尝试 'text' 字段。
                    retrieved_content = getattr(chunk.retrieved_context, 'text', None)
                    if retrieved_content is None:
                        # 备用尝试访问 'content' 字段
                        retrieved_content = getattr(chunk.retrieved_context, 'content', '无法获取内容：请检查 SDK 版本。')

                    print(f"检索文本片段 ({i}): \"{retrieved_content}\"")

                    # 安全获取原始 URI (如果适用)
                    if getattr(chunk.retrieved_context, 'uri', None):
                        print(f"原始 URI (如果适用): {chunk.retrieved_context.uri}")

                    print("-" * 20)
            else:
                print("模型未使用检索到的块来生成回复 (没有 grounding_chunks)。")
        else:
            print("未找到引用元数据。")

    except APIError as e:
        print(f"❌ 发生 API 错误: {e}")
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        traceback.print_exc()

    finally:
        # 步骤 E: 清理资源
        if file_search_store and store_name:
            print(f"\n--- 4. 清理 Store ({store_name}) ---")
            try:
                client.file_search_stores.delete(
                    name=store_name, config={"force": True}
                )
                print("✅ Store 清理完成。")
            except Exception as e:
                print(f"⚠️ 清理 Store 失败: {e}. 请手动删除 Store: {store_name}")

        # 删除本地创建的演示文件
        if os.path.exists(TEST_FILE_NAME):
            os.remove(TEST_FILE_NAME)
            print(f"✅ 删除本地文件: {TEST_FILE_NAME}")


if __name__ == "__main__":
    run_file_search_rag_demo()