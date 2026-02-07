import time
import os
import mlx.core as mx
from mlx_lm import load, generate
from pdf_parser import PDFParser, select_pdf_file

# ================= 配置区域 =================
MODEL_PATH = "mlx-community/Qwen2.5-14B-Instruct-4bit"
MAX_INPUT_TOKENS = 3000
SKILLS_DIR = "skills"


# ===========================================

def load_ai_model():
    print(f"\n🚀 正在加载 AI 模型: {MODEL_PATH} ...")
    model, tokenizer = load(MODEL_PATH, tokenizer_config={"trust_remote_code": True})
    return model, tokenizer


def count_tokens(tokenizer, text):
    return len(tokenizer.encode(text))


def smart_batching_by_token(tokenizer, articles, max_tokens):
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


def read_skill_file(filename):
    path = os.path.join(SKILLS_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"⚠️ 找不到文件: {path}")
        return ""


# =================================================================
# 【已恢复】保存解析后的中间文件 (txt)
# =================================================================
def save_intermediate_file(law_name, chapters_data):
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


# =================================================================
# 构建 Auditor Prompt
# =================================================================
def build_auditor_prompt(tokenizer, law_name, chapter_title, articles_batch):
    # 1. 读取主 Skill
    skill_content = read_skill_file("auditor_skill.md")
    # 2. 读取 13个控制域列表
    ref_content = read_skill_file("references/domain_standards.md")

    # 3. 拼接 System Prompt
    full_system = f"{skill_content}\n\n---\n\n{ref_content}"

    # 4. 构建 User Prompt
    context_text = "\n\n".join(articles_batch)

    user_prompt = f"""你正在分析 **《{law_name}》** 的 **【{chapter_title}】**。

以下是待分析的原文片段：
{context_text}

请严格参照 System Prompt 中的【成功案例】格式，输出表格行："""

    messages = [{"role": "system", "content": full_system}, {"role": "user", "content": user_prompt}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


def append_to_file(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def main():
    print("Step 1: 请选择 PDF 文件...")
    pdf_path = select_pdf_file()
    if not pdf_path: return

    law_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = f"{law_name}_合规矩阵.md"

    parser = PDFParser()
    chapters_data = parser.extract_content(pdf_path)
    if not chapters_data: return

    # 【已恢复】调用保存中间文件函数
    save_intermediate_file(law_name, chapters_data)

    model, tokenizer = load_ai_model()

    header = "| 涉及领域 | 控制目标 | 法律要求 | 控制点 | 类型 |\n| :--- | :--- | :--- | :--- | :--- |"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 合规审计底稿\n**源文件**: {law_name}\n\n{header}\n")

    print(f"💾 结果将实时写入: {output_file}")
    print("⚡️ 开始智能分析 (Few-Shot 增强版)...")

    for chapter_info in chapters_data:
        chapter_title = chapter_info['chapter']
        articles = chapter_info['articles']
        if not articles: continue

        print(f"\n📚 章节: {chapter_title} (共 {len(articles)} 条)")

        batches = smart_batching_by_token(tokenizer, articles, MAX_INPUT_TOKENS)

        for idx, batch in enumerate(batches):
            print(f"      -> 批次 {idx + 1}/{len(batches)}...")

            prompt = build_auditor_prompt(tokenizer, law_name, chapter_title, batch)

            response = generate(model, tokenizer, prompt=prompt, max_tokens=2500, verbose=False)

            clean_lines = [line for line in response.strip().split('\n') if
                           "|" in line and "---" not in line and "涉及领域" not in line]
            if clean_lines:
                append_to_file(output_file, "\n".join(clean_lines))
                print(f"         ✅ 生成 {len(clean_lines)} 个控制点")

            mx.metal.clear_cache()

    print(f"\n🎉 完成！请查看: {output_file}")


if __name__ == "__main__":
    main()