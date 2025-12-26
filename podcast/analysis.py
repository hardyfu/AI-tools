# -*- coding: utf-8 -*-
import os
import sys
import time
import google
from google import genai

# 保持你原有的编码重定向
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')


def analyze_and_save(api_key, transcript_file, output_dir, prompt_file="prompt.md"):
    # 1. 代理配置
    proxy_address = "127.0.0.1:7890"
    os.environ['http_proxy'] = f"http://{proxy_address}"
    os.environ['https_proxy'] = f"http://{proxy_address}"

    # 2. 检查 prompt
    if not os.path.exists(prompt_file):
        print(f"❌ 错误：未找到 prompt 文件 -> {prompt_file}")
        return None
    with open(prompt_file, 'r', encoding='utf-8') as f:
        analysis_prompt = f.read()

    # 3. 设置输出路径
    base_name = os.path.basename(transcript_file).replace("_transcript.txt", "")
    output_md_file = os.path.join(output_dir, f"{base_name}.md")

    # 4. 初始化客户端 (使用你在原代码中指定的 model)
    client = genai.Client(api_key=api_key)
    model_name = 'gemini-2.5-flash'  # 或保持 'gemini-2.5-flash'
    uploaded_file = None

    try:
        print(f"⬆️ 正在上传转录文本: {os.path.basename(transcript_file)}")
        start_upload = time.time()

        # 还原：使用你确认没问题的 file= 参数
        uploaded_file = client.files.upload(file=transcript_file)
        print(f"✅ 上传成功 (耗时: {time.time() - start_upload:.2f}s)")

        print(f"🚀 Gemini 正在深度分析中", end="")

        # 还原：使用你原代码中的流式获取
        response_stream = client.models.generate_content_stream(
            model=model_name,
            contents=[analysis_prompt, uploaded_file]
        )

        full_content = ""
        for chunk in response_stream:
            if chunk.text:
                full_content += chunk.text
                print(".", end="", flush=True)

        # 还原：保存为 Markdown
        with open(output_md_file, "w", encoding="utf-8") as md_file:
            md_file.write(full_content)

        return output_md_file

    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        return None

    finally:
        # 还原：清理云端文件
        if uploaded_file:
            try:
                client.files.delete(name=uploaded_file.name)
                print("\n✨ 云端临时文件已清理。")
            except:
                pass

if __name__ == "__main__":
    # 简单测试
    api_key=input("请输入 Gemini API Key: ").strip()
    transcript_file="/Users/ryan/Desktop/pythoncode/podcast/temp/How_to_make_AI_a_force_for_good_in_climate_Amen_Ra_Mashariki_and_Manoush_Zomorodi_transcript.txt"
    output_dir="output"

    result = analyze_and_save(api_key, transcript_file, output_dir)
    if result:
        print(f"分析结果已保存至: {result}")
    else:
        print("分析失败。")
