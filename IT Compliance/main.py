import time
import os
import mlx.core as mx
from mlx_lm import load, generate
from onnxruntime.transformers.huggingface_models import MODELS

from pdf_parser import PDFParser, select_pdf_file

# ================= 配置区域 =================
# MODEL_PATH = "mlx-community/Qwen2.5-7B-Instruct-4bit"
MODEL_PATH = "mlx-community/Qwen2.5-14B-Instruct-4bit"

# 智能分批的 Token 阈值
MAX_INPUT_TOKENS = 3000

# 【核心控制域】(保持你的定制列表)
CONTROL_DOMAINS = """
- 日志管理
- 漏洞管理
- 访问控制
- 备份与加密
- 采取防范危害网络安全行为的措施
- 网络安全管理制度
- 网络安全管理机构
- 网络安全等级保护
- 国际专线/VPN使用
- 网站APP备案
- 数据保护
- 第三方服务商管理
- 云服务安全责任划分
"""


# ===========================================

def load_ai_model():
    print(f"\n🚀 正在加载 AI 模型: {MODEL_PATH} ...")
    model, tokenizer = load(MODEL_PATH, tokenizer_config={"trust_remote_code": True})
    return model, tokenizer


def count_tokens(tokenizer, text):
    return len(tokenizer.encode(text))


def smart_batching_by_token(tokenizer, articles, max_tokens):
    """基于Token的贪婪装箱分批算法"""
    batches = []
    current_batch = []
    current_tokens = 0

    for article in articles:
        article_tokens = count_tokens(tokenizer, article)
        if current_tokens + article_tokens > max_tokens and current_batch:
            batches.append(current_batch)
            current_batch = []
            current_tokens = 0
        current_batch.append(article)
        current_tokens += article_tokens

    if current_batch:
        batches.append(current_batch)
    return batches


def build_prompt(tokenizer, law_name, chapter_title, articles_batch, is_partial=False):
    """
    【Prompt 深度优化版】
    - 移除编号列
    - 法律要求改为总结+出处
    - 控制点强调“审计证明力”
    """
    context_text = "\n\n".join(articles_batch)

    context_intro = f"你正在分析 **《{law_name}》** 的 **【{chapter_title}】**。"
    if is_partial:
        context_intro += "（注：这是该章节的拆分片段）。"

    system_prompt = f"""你是一名资深网络安全合规审计师（CISA/ISO27001 Lead Auditor）。
{context_intro}
你的任务是编制一份【合规审计底稿】。

请严格遵循以下列定义：

1. **涉及领域**：必须从以下列表选择最匹配的一项：
{CONTROL_DOMAINS}

2. **控制目标**：一句话概括该条款的安全目的（例如：保障数据的机密性与完整性）。

3. **法律要求（总结）**：
   - **不要**大段复制原文。
   - 请用精炼的语言总结法律的核心义务。
   - **必须**在开头标注具体条款位置。
   - 格式示例：`【第21条第1款】要求网络运营者制定内部安全管理制度和操作规程。`

4. **控制点（审计标准）**：
   - 这是最关键的一列。请思考：**“企业必须具体做什么，才能证明完全满足了上述法律要求？”**
   - 描述必须周全、严谨，具备**可审计性**。
   - 涵盖层面：制度规范、人员职责、技术配置、过程记录。
   - 示例：`建立并发布正式的网络安全管理制度体系，明确各级人员安全职责，并保留制度发布审批记录及员工培训签到表。`

5. **类型**：
   - **强制**：原文含“应”、“应当”、“必须”、“不得”。
   - **推荐**：原文含“宜”、“建议”、“可”。

输出格式：Markdown表格行，**无表头**。
列顺序：| 涉及领域 | 控制目标 | 法律要求 | 控制点 | 类型 |
"""

    user_prompt = f"原文片段：\n\n{context_text}\n\n请输出表格行："

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def append_to_file(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def save_intermediate_file(law_name, chapters_data):
    """保存解析后的中间文件 (txt)"""
    filename = f"{law_name}_parsed.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"解析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"源文件: {law_name}\n")
            f.write("=" * 80 + "\n\n")

            for chapter_info in chapters_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"📂 {chapter_info['chapter']}\n")
                f.write("=" * 80 + "\n")

                for article in chapter_info['articles']:
                    f.write(article + "\n")
                    f.write("-" * 40 + "\n")

        print(f"💾 解析后的法律原文已保存至: {filename}")
    except Exception as e:
        print(f"⚠️ 保存中间文件失败: {e}")


def main():
    print("Step 1: 请选择 PDF 文件...")
    pdf_path = select_pdf_file()
    if not pdf_path: return

    # 提取法律名称
    law_name = os.path.splitext(os.path.basename(pdf_path))[0]
    print(f"📖 识别到法律名称: 《{law_name}》")

    # 动态生成输出文件名
    output_file = f"{law_name}_合规矩阵.md"

    parser = PDFParser()
    chapters_data = parser.extract_content(pdf_path)

    if not chapters_data:
        print("❌ 解析失败")
        return

    # 保存中间 txt 文件
    save_intermediate_file(law_name, chapters_data)

    # 加载模型
    model, tokenizer = load_ai_model()

    # 【修改点：更新表头】
    # 移除了“控制点编号”，调整了“法律要求”和“控制点”的说明
    header = "| 涉及领域 | 控制目标 | 法律要求（条款摘要） | 控制点（审计标准） | 类型 |\n| :--- | :--- | :--- | :--- | :--- |"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 合规控制矩阵\n**源文件**: {law_name}\n\n{header}\n")

    print(f"💾 结果将实时写入: {output_file}")
    print("⚡️ 开始分析...")

    for chapter_info in chapters_data:
        chapter_title = chapter_info['chapter']
        articles = chapter_info['articles']

        if not articles: continue

        print(f"\n📚 章节: {chapter_title} (共 {len(articles)} 条)")

        batches = smart_batching_by_token(tokenizer, articles, MAX_INPUT_TOKENS)

        for idx, batch in enumerate(batches):
            print(f"      -> 批次 {idx + 1}/{len(batches)}...")

            is_partial = len(batches) > 1

            prompt = build_prompt(tokenizer, law_name, chapter_title, batch, is_partial=is_partial)

            # 使用默认参数生成 (无 temperature)
            response = generate(
                model,
                tokenizer,
                prompt=prompt,
                max_tokens=2500,
                verbose=False
            )

            # 清洗结果，只保留表格行
            # 过滤条件：必须包含 |，不是表头分割线 ---，且不包含表头关键词“涉及领域”
            clean_lines = [line for line in response.strip().split('\n') if
                           "|" in line and "---" not in line and "涉及领域" not in line]
            if clean_lines:
                append_to_file(output_file, "\n".join(clean_lines))
                print(f"         ✅ 生成 {len(clean_lines)} 个控制点")

            mx.metal.clear_cache()

    print(f"\n🎉 完成！请查看: {output_file}")


if __name__ == "__main__":
    main()