import os
import re
import unicodedata
from pathlib import Path
from openai import OpenAI
from pdf_parser import PDFParser, select_pdf_file

# ================= 测试模式配置 =================
TEST_MODE = True  # 设置为True时只处理前2章
MAX_CHAPTERS_IN_TEST = 2
# ===============================================

# ================= 配置区域 =================
# 固定使用本地 oMLX OpenAI-compatible 服务
OMLX_BASE_URL = "http://localhost:8000/v1"
OMLX_API_KEY = "510918123Fu!"
OMLX_MODEL_NAME = "MLX-Qwen3.5-9B-Claude-4.6-Opus-Reasoning-Distilled-v2-8bit"

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "skills"

EVIDENCE_KEYWORDS = (
    "截图", "报表", "记录", "日志", "台账", "配置", "工单", "审批", "清单",
    "文件", "证据", "报告", "任命书", "纪要", "演练", "告警", "策略"
)

TARGET_ENTITY_KEYWORDS = (
    "网络运营者", "关键信息基础设施的运营者", "关键信息基础设施运营者",
    "运营者", "网络产品、服务的提供者", "网络产品和服务的提供者",
    "电子信息发送服务提供者", "应用软件下载服务提供者", "任何个人和组织"
)

NON_ENTERPRISE_SUBJECT_KEYWORDS = (
    "国家", "国务院", "人民政府", "网信部门", "有关部门", "公安机关",
    "国家安全机关", "行业组织", "大众传播媒介", "国家网信部门"
)

OBLIGATION_KEYWORDS = (
    "应当", "必须", "不得"
)

ARTICLE_REF_PATTERN = re.compile(r"第[一二三四五六七八九十百零〇两0-9]{1,10}条")
SKIP_CHAPTER_KEYWORDS = ("法律责任", "附 则", "附则")
# ===========================================


# ================= 后端适配层 =================
class BaseLLMBackend:
    name = "base"

    def initialize(self):
        raise NotImplementedError

    def build_messages(self, system_prompt: str, user_prompt: str):
        raise NotImplementedError

    def generate(self, messages, max_tokens: int = 2500) -> str:
        raise NotImplementedError

    def cleanup(self):
        pass


class OMLXBackend(BaseLLMBackend):
    name = "omlx"

    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.client: OpenAI | None = None

    def initialize(self):
        print(f"\n🚀 正在连接 oMLX 服务: {self.base_url} / {self.model_name} ...")
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
        print("✅ oMLX 客户端初始化完成")

    def build_messages(self, system_prompt: str, user_prompt: str):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def generate(self, messages, max_tokens: int = 2500) -> str:
        if self.client is None:
            raise RuntimeError("oMLX 客户端尚未初始化，请先调用 initialize()")

        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=0.0,
            max_tokens=max_tokens
        )

        content = response.choices[0].message.content
        if content is None:
            return ""
        return content.strip()


def select_backend():
    print("🧠 固定使用后端: oMLX")
    return OMLXBackend(OMLX_BASE_URL, OMLX_API_KEY, OMLX_MODEL_NAME)


# ===========================================


def read_skill_file(filename):
    return (SKILLS_DIR / filename).read_text(encoding="utf-8")


def load_prompt_assets():
    """Deprecated: use load_auditor_skill instead"""
    skill_content = read_skill_file("auditor/SKILL.md")
    ref_content = read_skill_file("shared/references/domain_standards.md")
    valid_domains = []

    for line in ref_content.splitlines():
        match = re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if match:
            valid_domains.append(match.group(1))

    if not valid_domains:
        raise ValueError("未能从 domain_standards.md 提取控制域")

    return f"{skill_content}\n\n---\n\n{ref_content}", set(valid_domains)


def load_auditor_skill():
    """Load auditor skill content and extract valid domains"""
    skill_content = read_skill_file("auditor/SKILL.md")
    ref_content = read_skill_file("shared/references/domain_standards.md")
    valid_domains = []

    for line in ref_content.splitlines():
        match = re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if match:
            valid_domains.append(match.group(1))

    if not valid_domains:
        raise ValueError("未能从 domain_standards.md 提取控制域")

    return skill_content, set(valid_domains)


def load_analyst_skill():
    """Load analyst skill content"""
    return read_skill_file("analyst/SKILL.md")


def load_reviewer_skill():
    """Load reviewer skill content"""
    return read_skill_file("reviewer/SKILL.md")





def extract_article_excerpt(article_text, article_ref, max_len=64):
    normalized = unicodedata.normalize("NFKC", article_text).replace("\n", "")
    body = re.sub(rf"^{re.escape(article_ref)}", "", normalized, count=1).strip()
    return f"【{article_ref}】{body[:max_len].rstrip() + '...' if len(body) > max_len else body}"


def extract_article_refs(text):
    normalized_text = unicodedata.normalize("NFKC", text)
    return set(ARTICLE_REF_PATTERN.findall(normalized_text))





def build_chapter_overview(chapter_info, current_index=None, window_size=None):
    article_meta = chapter_info.get("article_meta", [])
    articles = chapter_info["articles"]
    is_windowed_view = current_index is not None
    start_index = max(0, current_index - (window_size or 2)) if is_windowed_view else 0
    end_index = min(len(articles), current_index + (window_size or 2) + 1) if is_windowed_view else len(articles)

    overview_lines = []
    for idx in range(start_index, end_index):
        article = articles[idx]
        meta = article_meta[idx] if idx < len(article_meta) else {}
        article_ref = meta.get("article_ref") or next(iter(extract_article_refs(article)), "")
        subject_type = meta.get("subject_type", "unknown")
        paragraph_count = meta.get("paragraph_count", 1)
        excerpt_limit = 48 if is_windowed_view else 80
        prefix = f"- [{'当前条文' if idx == current_index else '邻近条文'}] " if is_windowed_view else "- "
        suffix = f" [主体={subject_type}]" if is_windowed_view else f" [主体={subject_type}; 段落={paragraph_count}]"

        if article_ref:
            excerpt = extract_article_excerpt(article, article_ref, max_len=excerpt_limit)
        else:
            excerpt = unicodedata.normalize("NFKC", article).replace("\n", "")[:excerpt_limit].rstrip() + "..."

        overview_lines.append(f"{prefix}{excerpt}{suffix}")

    return "\n".join(overview_lines)


def build_analysis_messages(backend, law_name, chapter_title, chapter_summary, article_text, system_prompt, chapter_analysis=""):
    article_ref = next(iter(extract_article_refs(article_text)), "未识别条款")

    # Incorporate analyst summary if available
    analysis_context = ""
    if chapter_analysis:
        analysis_context = f"\n本章合规画像（分析师摘要）：\n{chapter_analysis}\n"

    user_prompt = f"""你正在分析 **《{law_name}》** 的 **【{chapter_title}】**。

请先理解本章整体内容，再分析当前条文。

本章条文导览：
{chapter_summary}{analysis_context}
当前需要细看并输出控制点的条文：
{article_text}

要求：
1. 先基于本章导览理解当前条文在本章中的作用。
2. 再只针对当前条文 `{article_ref}` 输出控制点。
3. 请严格参照 System Prompt 中的规则。
4. 只输出符合要求的 markdown 表格行；不要输出解释、标题、前言、结语。
5. 不适用时返回空白。"""

    return backend.build_messages(system_prompt, user_prompt)


def build_analysis_messages_with_context(backend, law_name, chapter_title, chapter_info, article_index, article_text, system_prompt, chapter_analysis=""):
    chapter_summary = build_chapter_overview(chapter_info, current_index=article_index, window_size=2)
    messages = build_analysis_messages(backend, law_name, chapter_title, chapter_summary, article_text, system_prompt, chapter_analysis)
    return messages, len(chapter_summary), 1


def split_markdown_row(line):
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return cells if len(cells) == 5 and line.strip().startswith("|") and line.strip().endswith("|") else None


def build_article_map(articles):
    return {
        next(iter(sorted(extract_article_refs(article)))): article
        for article in articles
        if extract_article_refs(article)
    }


def is_actionable_article(article_text, chapter_title):
    if any(keyword in chapter_title for keyword in SKIP_CHAPTER_KEYWORDS):
        return False

    normalized = unicodedata.normalize("NFKC", article_text)
    return (
        any(keyword in normalized for keyword in OBLIGATION_KEYWORDS)
        and (
            any(keyword in normalized for keyword in TARGET_ENTITY_KEYWORDS)
            or not any(keyword in normalized for keyword in NON_ENTERPRISE_SUBJECT_KEYWORDS)
        )
    )


def validate_output_row(line, valid_domains, chapter_title, article_map):
    cells = split_markdown_row(line)
    if not cells:
        return False, "列数不是 5 列", None

    domain, control_target, legal_requirement, control_point, row_type = cells
    if domain not in valid_domains:
        return False, f"控制域不在标准列表内: {domain}", None
    if row_type != "强制":
        return False, f"类型不是强制: {row_type}", None

    cited_refs = extract_article_refs(legal_requirement)
    if len(cited_refs) != 1:
        return False, "法律要求必须且只能引用一个条款", None

    cited_ref = next(iter(cited_refs))
    source_article = article_map.get(cited_ref)
    if not source_article:
        return False, f"当前批次不存在引用条款: {cited_ref}", None
    if not is_actionable_article(source_article, chapter_title):
        return False, "引用条款不属于适合转控制点的企业义务", None
    if not any(keyword in control_point for keyword in EVIDENCE_KEYWORDS):
        return False, "控制点缺少明确审计证据", None

    normalized_line = "| " + " | ".join([
        domain,
        control_target,
        extract_article_excerpt(source_article, cited_ref),
        control_point,
        row_type
    ]) + " |"
    return True, "", normalized_line


def write_review_entry(file_path, chapter_title, batch_index, reason, line):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"## 章节: {chapter_title} / 批次: {batch_index}\n- 原因: {reason}\n- 原文: {line}\n\n")


def append_to_file(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{text}\n")


def extract_valid_table_lines(response_text):
    return [
        line
        for line in (raw_line.strip() for raw_line in response_text.splitlines())
        if line
        and "|" in line
        and "---" not in line
        and "涉及领域" not in line
        and "控制目标" not in line
        and "法律要求" not in line
    ]


def main():
    print("Step 1: 请选择 PDF 文件...")
    source_pdf_path = select_pdf_file()
    if not source_pdf_path:
        print("⚠️ 未选择文件，程序结束。")
        return

    law_name = os.path.splitext(os.path.basename(source_pdf_path))[0]
    output_file_path = BASE_DIR / f"{law_name}_合规矩阵.md"
    review_file_path = BASE_DIR / f"{law_name}_复核清单.md"

    parser = PDFParser()
    chapters_data = parser.extract_content(source_pdf_path)
    if not chapters_data:
        print("⚠️ 未能从 PDF 提取有效内容，程序结束。")
        return




    # Load skills
    analyst_system_prompt = load_analyst_skill()
    auditor_system_prompt, valid_domains = load_auditor_skill()
    reviewer_system_prompt = load_reviewer_skill()
    backend = select_backend()
    backend.initialize()

    header = "| 涉及领域 | 控制目标 | 法律要求 | 控制点 | 类型 |\n| :--- | :--- | :--- | :--- | :--- |"

    with open(output_file_path, "w", encoding="utf-8") as output_file:
        output_file.write(f"# 合规审计底稿\n**源文件**: {law_name}\n\n{header}\n")

    with open(review_file_path, "w", encoding="utf-8") as review_file:
        review_file.write(f"# 复核清单\n**源文件**: {law_name}\n\n")

    print(f"💾 结果将实时写入: {output_file_path}")
    print(f"🧾 异常输出将写入: {review_file_path}")
    print(f"⚡️ 开始智能分析 (当前后端: {backend.name})...")

    processed_chapters = 0
    for chapter_info in chapters_data:
        chapter_title = chapter_info["chapter"]
        articles = chapter_info["articles"]

        # 测试模式限制
        if TEST_MODE and processed_chapters >= MAX_CHAPTERS_IN_TEST:
            print(f"\n⏭️ 测试模式：已处理 {MAX_CHAPTERS_IN_TEST} 章，跳过剩余章节")
            break

        if chapter_title == "未归类章节" or not articles:
            print(f"\n⏭️ 跳过章节: {chapter_title}")
            continue

        if any(keyword in chapter_title for keyword in SKIP_CHAPTER_KEYWORDS):
            print(f"\n⏭️ 跳过章节: {chapter_title} (默认不从处罚/附则章节抽取)")
            continue

        processed_chapters += 1
        print(f"\n📚 章节: {chapter_title} (共 {len(articles)} 条)")
        article_lookup = build_article_map(articles)

        # Step 1: Analyst phase - generate chapter summary
        print(f"      📋 分析师阶段: 生成章节摘要...")
        analyst_messages = backend.build_messages(
            analyst_system_prompt,
            f"请分析 **《{law_name}》** 的 **【{chapter_title}】**。"
        )
        try:
            chapter_analysis = backend.generate(analyst_messages, max_tokens=300)
            print(f"      ✅ 章节摘要生成完成 ({len(chapter_analysis)} 字符)")
        except Exception as e:
            print(f"      ❌ 分析师阶段失败: {e}")
            chapter_analysis = ""

        for article_index, article_text in enumerate(articles):
            article_ref = next(iter(extract_article_refs(article_text)), f"第{article_index + 1}条(未识别)")

            if not is_actionable_article(article_text, chapter_title):
                print(f"      -> 跳过条文 {article_ref}: 不属于企业义务")
                continue

            messages, prompt_size, prompt_level = build_analysis_messages_with_context(
                backend, law_name, chapter_title, chapter_info, article_index, article_text, auditor_system_prompt, chapter_analysis
            )

            print(
                f"      -> 条文 {article_ref} ({article_index + 1}/{len(articles)})..."
                f" 使用导览级别 {prompt_level}, size≈{prompt_size}"
            )

            try:
                response_text = backend.generate(messages, max_tokens=2500)
            except Exception as error:
                print(f"         ❌ 模型调用失败: {error}")
                write_review_entry(
                    review_file_path,
                    chapter_title,
                    article_index + 1,
                    f"模型调用失败: {error}",
                    article_ref
                )
                continue
            finally:
                backend.cleanup()

            valid_lines = []
            review_lines = []
            invalid_count = 0

            for line in extract_valid_table_lines(response_text):
                # Step 3: Reviewer phase - quality check
                reviewer_messages = backend.build_messages(
                    reviewer_system_prompt,
                    f"""请审查以下控制点：

控制点表格行：
{line}

对应法律条文原文：
{article_text}

章节标题：{chapter_title}
法律名称：{law_name}

请基于评审员技能中的标准进行严格审查。"""
                )
                try:
                    reviewer_response = backend.generate(reviewer_messages, max_tokens=500)

                    # Clean and parse reviewer response
                    reviewer_response = reviewer_response.strip()

                    # Enhanced parsing with multiple possible formats
                    if reviewer_response.startswith("PASS") or "| PASS |" in reviewer_response:
                        # Extract the actual line if reviewer returned modified version
                        if "|" in reviewer_response and reviewer_response.count("|") >= 4:
                            # Try to extract the table line from reviewer response
                            parts = reviewer_response.split("|")
                            if len(parts) >= 6:
                                # Reconstruct table line from reviewer response
                                extracted_line = "|" + "|".join(parts[1:6]) + "|"
                                line = extracted_line

                        is_valid, reason, normalized_line = validate_output_row(
                            line, valid_domains, chapter_title, article_lookup
                        )
                        if is_valid:
                            valid_lines.append(normalized_line)
                        else:
                            invalid_count += 1
                            write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)

                    elif reviewer_response.startswith("REVIEW") or "| REVIEW |" in reviewer_response:
                        review_lines.append(line)
                        reason = "需人工复核"
                        if "|" in reviewer_response:
                            parts = reviewer_response.split("|")
                            if len(parts) > 5:
                                reason = parts[-1].strip()
                        write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)

                    elif reviewer_response.startswith("FAIL") or "| FAIL |" in reviewer_response:
                        invalid_count += 1
                        reason = "评审不通过"
                        if "|" in reviewer_response:
                            parts = reviewer_response.split("|")
                            if len(parts) > 5:
                                reason = parts[-1].strip()
                        write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)

                    else:
                        # Fallback: check if response contains pass/fail/review keywords
                        response_lower = reviewer_response.lower()
                        if any(keyword in response_lower for keyword in ["pass", "通过", "保留"]):
                            is_valid, reason, normalized_line = validate_output_row(
                                line, valid_domains, chapter_title, article_lookup
                            )
                            if is_valid:
                                valid_lines.append(normalized_line)
                            else:
                                invalid_count += 1
                                write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)
                        elif any(keyword in response_lower for keyword in ["review", "复核", "review"]):
                            review_lines.append(line)
                            write_review_entry(review_file_path, chapter_title, article_index + 1, "需人工复核", line)
                        elif any(keyword in response_lower for keyword in ["fail", "丢弃", "不通过"]):
                            invalid_count += 1
                            write_review_entry(review_file_path, chapter_title, article_index + 1, "评审不通过", line)
                        else:
                            # Final fallback to original validation
                            is_valid, reason, normalized_line = validate_output_row(
                                line, valid_domains, chapter_title, article_lookup
                            )
                            if is_valid:
                                valid_lines.append(normalized_line)
                            else:
                                invalid_count += 1
                                write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)

                except Exception as e:
                    print(f"         ⚠️ 评审阶段失败: {e}")
                    # Fallback to original validation
                    is_valid, reason, normalized_line = validate_output_row(
                        line, valid_domains, chapter_title, article_lookup
                    )
                    if is_valid:
                        valid_lines.append(normalized_line)
                    else:
                        invalid_count += 1
                        write_review_entry(review_file_path, chapter_title, article_index + 1, reason, line)

            if valid_lines:
                append_to_file(output_file_path, "\n".join(valid_lines))
                print(f"         ✅ 通过评审 {len(valid_lines)} 个控制点")
            if review_lines:
                print(f"         ⚠️ {len(review_lines)} 个控制点需人工复核")
            if not valid_lines and not review_lines:
                print("         ℹ️ 未产出通过评审的控制点")

            if invalid_count:
                print(f"         ❌ {invalid_count} 个结果评审不通过")

    print(f"\n🎉 完成！请查看: {output_file_path}")
    print(f"🧾 复核清单: {review_file_path}")


if __name__ == "__main__":
    main()
