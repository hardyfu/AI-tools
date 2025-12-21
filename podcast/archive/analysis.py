# -*- coding: utf-8 -*-
import os
import sys
import time
from google import genai
from google.genai.errors import APIError

# 强制环境使用 UTF-8 编码
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ----------------------------------------------------
# 🎯 代理和文件配置
# ----------------------------------------------------
proxy_address = "127.0.0.1:7897"
os.environ['http_proxy'] = f"http://{proxy_address}"
os.environ['https_proxy'] = f"http://{proxy_address}"

# 输入文件
TRANSCRIPT_FILE = "AI_is_coming_for_your_job._Now_what_transcript.txt"
PROMPT_FILE = "prompt.md"
# 输出文件
OUTPUT_MD_FILE = "analysis_result.md"


def load_file_content(filepath):
    if not os.path.exists(filepath):
        print(f"❌ 错误：未找到文件 -> {filepath}")
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def get_api_key_interactively():
    print("-" * 60)
    api_key = input("🔑 请输入您的 Gemini API Key：\n> ")
    print("-" * 60)
    return api_key.strip()


def analyze_and_save():
    print("=" * 60)
    print(f"🌍 代理状态: {proxy_address}")

    # 1. 加载指令
    analysis_prompt = load_file_content(PROMPT_FILE)
    if not analysis_prompt: return

    # 2. 获取 API Key
    gemini_api_key = get_api_key_interactively()
    if not gemini_api_key: return

    # 3. 初始化客户端
    model_name = 'gemini-2.5-flash'
    client = genai.Client(api_key=gemini_api_key)
    uploaded_file = None

    try:
        # 4. 使用 File API 上传大文本
        print(f"⬆️ 正在上传转录文本...")
        start_upload = time.time()

        # *** 修复点：将 path= 改为 file= ***
        uploaded_file = client.files.upload(file=TRANSCRIPT_FILE)

        print(f"✅ 上传成功 (耗时: {time.time() - start_upload:.2f}s)")

        # 5. 调用模型 (后台流式获取，防止连接中断)
        print(f"🚀 Gemini 正在深度分析中，请稍候...")

        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=[analysis_prompt, uploaded_file]
        )

        full_content = ""
        # 即使不打印，也通过迭代流来保持连接活跃
        for chunk in response_stream:
            if chunk.text:
                full_content += chunk.text
                # 打印一个点表示进度，避免界面看起来像卡住了
                print(".", end="", flush=True)

        print("\n" + "-" * 60)

        # 6. 保存为 Markdown 文件
        with open(OUTPUT_MD_FILE, "w", encoding="utf-8") as md_file:
            md_file.write(f"# Gemini 分析报告\n\n")
            md_file.write(f"- **分析时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            md_file.write(f"- **源文件**: {TRANSCRIPT_FILE}\n\n---\n\n")
            md_file.write(full_content)

        print(f"🎉 分析完成并已保存！")
        print(f"📄 结果文件: {OUTPUT_MD_FILE}")
        print("-" * 60)

    except Exception as e:
        print(f"\n❌ 处理失败: {e}")

    finally:
        # 7. 清理云端临时文件
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                print("✨ 云端临时文件已清理。")
            except:
                pass


if __name__ == "__main__":
    analyze_and_save()