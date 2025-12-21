import os
import sys
import re
from config import LLM_MODEL_ID  # 导入配置
from extractor import get_article  # 导入文章提取功能
from llm_service import llm_call_streaming  # 导入 LLM 调用功能
from datetime import datetime


def clean_and_summarize():
    """主流程：提取、清理并总结文章"""

    # 1. 提取文章内容
    article_data = get_article(input("输入需要总结的文章URL：\n"))
    # 🚨 移除：提取标题和文本验证的打印

    if not article_data or not article_data.get('text'):
        print("🔴 提取失败，无法继续总结。", file=sys.stderr)

        if article_data is None:
            return "无法提取文章内容，请检查 Diffbot 配置和网络连接。"
        else:
            return f"无法总结文章：{article_data.get('title', 'N/A')} (内容为空)"

    # 2. 清理文本
    text = article_data['text']
    url_pattern = r'https?://\S+|www\.\S+|ftp://\S+'
    cleaned_text = re.sub(url_pattern, ' [链接已移除] ', text)

    # 3. 读取提示词
    base_dir = os.path.dirname(os.path.abspath(__file__))
    prompt_path = os.path.join(base_dir, 'prompt.md')

    if not os.path.exists(prompt_path):
        print(f"🔴 错误: 缺少提示词文件 {prompt_path}，请创建。", file=sys.stderr)
        prompt = "请作为一位专业的中文摘要专家，根据以下文章内容，生成一份结构化、内容精炼的摘要。"
    else:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()

    # 4. 构造完整提示词
    summary_prompt = (
        f"{prompt}\n\n"
        f"文章内容：\n---\n{cleaned_text}"
    )

    # 5. 调用 LLM API (静默流式)
    try:
        summary = llm_call_streaming(prompt=summary_prompt, model_id=LLM_MODEL_ID)
        return summary
    except Exception as e:
        return f"LLM 总结失败: {e}"


# =========================================================================
# 主执行逻辑
# =========================================================================

if __name__ == "__main__":

    print("================ 文章抓取与 Qwen 静默总结启动 ================")

    # 运行主流程
    final_summary = clean_and_summarize()

    print("\n================ 最终总结写入文件 ================")

    # 路径构建：当前工作目录/summary/summary.md
    summary_dir = os.path.join(os.getcwd(), 'summary')

    # 确保目录存在
    os.makedirs(summary_dir, exist_ok=True)

    # 构建最终路径
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_path = os.path.join(summary_dir, f'{date} summary.md')

    try:
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(final_summary)
        print(f"✅ 摘要已保存到: {save_path}")
    except Exception as e:
        print(f"❌ 文件保存失败: {e}", file=sys.stderr)

    print("==================================================")

