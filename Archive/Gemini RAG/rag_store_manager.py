# rag_store_manager.py
"""
模块用途：
负责管理 Gemini File Search Store (知识库)。
包括创建 Store、上传文件到 Store、等待索引完成以及资源清理。
"""
import os
import time
from google import genai
from google.genai.errors import APIError
from typing import Optional, Tuple


def create_and_upload_to_store(client: genai.Client, file_path: str, store_display_name: str) -> Optional[str]:
    """
    创建 File Search Store，上传文件并等待索引完成。
    返回 Store 的唯一名称 (store_name)。
    """
    if not os.path.exists(file_path):
        print(f"❌ 错误: 文件未找到于 {file_path}")
        return None

    file_search_store = None
    store_name = None
    operation = None

    try:
        # 步骤 A: 创建 File Search Store
        print("\n--- 1. 创建 File Search Store ---")
        file_search_store = client.file_search_stores.create(
            config={"display_name": store_display_name}
        )
        store_name = file_search_store.name
        print(f"✅ Store 创建成功: {store_name}")

        # 步骤 B: 上传文件并导入 Store
        print("\n--- 2. 上传文件并导入 Store ---")

        # 使用 client.file_search_stores.upload_to_file_search_store 简化操作
        operation = client.file_search_stores.upload_to_file_search_store(
            file=file_path,
            file_search_store_name=store_name,
            config={"display_name": os.path.basename(file_path)}  # 使用文件名作为显示名称
        )

        print(f"⏳ 正在等待文件索引完成 (Operation: {operation.name})...")

        # 等待索引操作完成
        while not operation.done:
            time.sleep(5)
            # 使用 client.operations.get 来获取操作状态
            operation = client.operations.get(operation)
            print("   索引中...")

        print("✅ 文件索引完成!")
        return store_name

    except APIError as e:
        print(f"❌ 文件或 Store 操作失败: {e}")
        # 如果在出错前创建了 Store，也需要返回 Store 名称以便清理
        return store_name
    except Exception as e:
        print(f"❌ 发生未知错误: {e}")
        return store_name


def cleanup_store(client: genai.Client, store_name: Optional[str]):
    """
    🗑️ 删除 File Search Store 以清除存储。
    """
    if not store_name:
        return

    try:
        print(f"\n--- 4. 清理 Store ({store_name}) ---")
        # 必须指定 force=True 才能删除带有内容的 Store
        client.file_search_stores.delete(
            name=store_name, config={"force": True}
        )
        print(f"✅ Store ({store_name}) 清理完成。")
    except Exception as e:
        print(f"⚠️ 清理 Store 失败: {e}. 请手动删除 Store: {store_name}")