import logging
import os
import re
import unicodedata
from pathlib import Path

from openai import OpenAI
from pdf_parser import PDFParser, select_pdf_file

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# ================= 测试模式配置 =================
TEST_MODE = False  # 设置为True时只处理前2章
MAX_CHAPTERS_IN_TEST = 2
# ===============================================

# ================= 配置区域 =================
# DeepSeek API 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com/beta"
DEEPSEEK_CHAT_MODEL_NAME = "deepseek-chat"
DEEPSEEK_REASONER_MODEL_NAME = "deepseek-reasoner"

# Qwen API 配置（阿里云百炼 OpenAI-compatible 模式）
QWEN_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
QWEN_MODEL_NAME = "qwen3.6-plus"

# 后端选择配置
DEFAULT_BACKEND = os.getenv(
    "LLM_BACKEND", "deepseek"
).lower()  # 可选: "deepseek" 或 "qwen"

BASE_DIR = Path(__file__).resolve().parent
SKILLS_DIR = BASE_DIR / "skills"


def get_env_value(*names):
    for name in names:
        value = os.getenv(name, "")
        if value:
            return value
    return ""


DEEPSEEK_API_KEY = get_env_value("DEEPSEEK_API_KEY")
QWEN_API_KEY = get_env_value("DASHSCOPE_API_KEY")

AUDITED_ORGANIZATION_NAME = "ABB"
AUDITED_ORGANIZATION_PROFILE = (
    "ABB 是工业技术与制造企业，当前合规矩阵面向 ABB 在中国运营的组织、系统、"
    "产品和服务场景。默认适用主体包括一般网络运营者、网络产品和服务提供者、"
    "数据处理者、个人信息处理者以及任何个人和组织。ABB 不默认视为关键信息基础设施运营者，"
    "但 ABB 的客户可能是关键信息基础设施运营者；当条文涉及网络产品/服务提供、采购、外包、"
    "技术支持、供应链或受托运维等场景时，应评估 ABB 作为 CII 客户供应商或服务提供方需要承接的合规要求。"
)

TARGET_ENTITY_KEYWORDS = (
    "网络运营者",
    "网络产品、服务的提供者",
    "网络产品和服务的提供者",
    "网络服务提供者",
    "数据处理者",
    "重要数据的处理者",
    "个人信息处理者",
    "电子信息发送服务提供者",
    "应用软件下载服务提供者",
    "任何个人和组织",
)

ENTERPRISE_APPLICABILITY_KEYWORDS = (
    "建设、运营网络",
    "通过网络提供服务",
    "网络产品、服务",
    "网络产品和服务",
    "网络关键设备",
    "网络安全专用产品",
    "销售或者提供",
    "方可销售",
    "用户信息",
    "个人信息",
    "网络接入",
    "域名注册",
    "入网手续",
    "信息发布",
    "即时通讯",
    "技术支持",
    "广告推广",
    "支付结算",
)

NON_ENTERPRISE_SUBJECT_KEYWORDS = (
    "国家",
    "国务院",
    "人民政府",
    "网信部门",
    "有关部门",
    "公安机关",
    "国家安全机关",
    "行业组织",
    "大众传播媒介",
    "国家网信部门",
)

CII_CONTEXT_KEYWORDS = ("关键信息基础设施的运营者", "关键信息基础设施运营者")

ARTICLE_REF_PATTERN = re.compile(r"第[一二三四五六七八九十百零〇两0-9]{1,10}条")
SKIP_CHAPTER_KEYWORDS = ("法律责任", "附 则", "附则")
NO_APPLICABLE_MARKERS = (
    "空响应",
    "空白",
    "无适用控制点",
    "无适用",
    "不适用",
    "不涉及",
    "无需输出",
    "不输出任何表格行",
    "返回空白",
)
# ===========================================


def normalize_for_keyword_match(text):
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))


def should_skip_chapter(chapter_title):
    normalized_title = normalize_for_keyword_match(chapter_title)
    return any(
        normalize_for_keyword_match(keyword) in normalized_title
        for keyword in SKIP_CHAPTER_KEYWORDS
    )


# ================= 后端适配层 =================
class BaseLLMBackend:
    name = "base"

    def initialize(self):
        raise NotImplementedError

    def build_messages(self, system_prompt: str, user_prompt: str):
        raise NotImplementedError

    def generate(self, messages, max_tokens: int = 2500, task: str = "default") -> str:
        raise NotImplementedError

    def cleanup(self):
        pass


class QwenBackend(BaseLLMBackend):
    name = "qwen"

    def __init__(self, base_url: str, api_key: str, model_name: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model_name = model_name
        self.client: OpenAI | None = None

    def initialize(self):
        print(f"\n🚀 正在连接 Qwen API: {self.base_url} / 模型:{self.model_name} ...")

        # 配置 SSL 验证
        http_client_kwargs = {}
        if not SSL_VERIFY:
            print("⚠️  SSL 验证已禁用（仅限测试环境使用）")
            http_client_kwargs["verify"] = False
        elif SSL_CERT_PATH:
            print(f"📄 使用自定义 SSL 证书: {SSL_CERT_PATH}")
            http_client_kwargs["verify"] = SSL_CERT_PATH

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client_kwargs=http_client_kwargs,
        )
        print("✅ Qwen 客户端初始化完成")

    def build_messages(self, system_prompt: str, user_prompt: str):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def enable_thinking_for_task(self, task: str) -> bool:
        return task == "control_generation"

    def generate(self, messages, max_tokens: int = 2500, task: str = "default") -> str:
        if self.client is None:
            raise RuntimeError("Qwen 客户端尚未初始化，请先调用 initialize()")

        enable_thinking = self.enable_thinking_for_task(task)
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                extra_body={"enable_thinking": enable_thinking},
                stream=True,
            )

            content_parts = []
            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    content_parts.append(content)
            return "".join(content_parts).strip()
        except Exception as e:
            print(f"❌ Qwen API 调用失败: {e}")
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                print("⚠️  请检查 DASHSCOPE_API_KEY 是否正确")
            raise


class DeepSeekBackend(BaseLLMBackend):
    name = "deepseek"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        chat_model_name: str,
        reasoner_model_name: str,
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.chat_model_name = chat_model_name
        self.reasoner_model_name = reasoner_model_name
        self.client: OpenAI | None = None

    def initialize(self):
        print(
            f"\n🚀 正在连接 DeepSeek API: {self.base_url} "
            f"/ 摘要:{self.chat_model_name} 控制点:{self.reasoner_model_name} ..."
        )

        # 配置 SSL 验证
        http_client_kwargs = {}
        if not SSL_VERIFY:
            print("⚠️  SSL 验证已禁用（仅限测试环境使用）")
            http_client_kwargs["verify"] = False
        elif SSL_CERT_PATH:
            print(f"📄 使用自定义 SSL 证书: {SSL_CERT_PATH}")
            http_client_kwargs["verify"] = SSL_CERT_PATH

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client_kwargs=http_client_kwargs,
        )
        print("✅ DeepSeek 客户端初始化完成")

    def build_messages(self, system_prompt: str, user_prompt: str):
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

    def model_for_task(self, task: str) -> str:
        if task == "control_generation":
            return self.reasoner_model_name
        return self.chat_model_name

    def generate(self, messages, max_tokens: int = 2500, task: str = "default") -> str:
        if self.client is None:
            raise RuntimeError("DeepSeek 客户端尚未初始化，请先调用 initialize()")

        model_name = self.model_for_task(task)
        try:
            response = self.client.chat.completions.create(
                model=model_name, messages=messages, max_tokens=max_tokens
            )

            content = response.choices[0].message.content
            if content is None:
                return ""
            return content.strip()
        except Exception as e:
            print(f"❌ DeepSeek API 调用失败: {e}")
            if "api_key" in str(e).lower() or "authentication" in str(e).lower():
                print("⚠️  请检查 DEEPSEEK_API_KEY 是否正确")
            raise


def prompt_backend_choice():
    default_choice = (
        DEFAULT_BACKEND if DEFAULT_BACKEND in {"deepseek", "qwen"} else "deepseek"
    )
    print("\n请选择本次运行使用的模型后端：")
    print(
        "  1. DeepSeek（章节摘要/评审: deepseek-chat；控制点生成: deepseek-reasoner）"
    )
    print("  2. Qwen（始终 qwen3.6-plus；仅控制点生成启用 thinking）")
    choice = input(f"请输入 1 或 2，直接回车默认 {default_choice}: ").strip().lower()

    if not choice:
        return default_choice
    if choice in {"1", "deepseek", "d"}:
        return "deepseek"
    if choice in {"2", "qwen", "q"}:
        return "qwen"

    print(f"⚠️ 无法识别选择 [{choice}]，使用默认后端: {default_choice}")
    return default_choice


def select_backend():
    backend_choice = prompt_backend_choice()

    if backend_choice == "deepseek":
        print("🧠 配置使用 DeepSeek 后端")
        if not DEEPSEEK_API_KEY:
            raise ValueError(
                "DeepSeek API Key 未设置，请设置 DEEPSEEK_API_KEY 环境变量"
            )
        return DeepSeekBackend(
            DEEPSEEK_BASE_URL,
            DEEPSEEK_API_KEY,
            DEEPSEEK_CHAT_MODEL_NAME,
            DEEPSEEK_REASONER_MODEL_NAME,
        )
    elif backend_choice == "qwen":
        print("🧠 配置使用 Qwen 后端")
        if not QWEN_API_KEY:
            raise ValueError("Qwen API Key 未设置，请设置 DASHSCOPE_API_KEY 环境变量")
        return QwenBackend(QWEN_BASE_URL, QWEN_API_KEY, QWEN_MODEL_NAME)
    else:
        raise ValueError(
            f"未知的后端配置: {backend_choice}，请设置为 'deepseek' 或 'qwen'"
        )


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

    return f"{skill_content}\n\n---\n\n{ref_content}", set(valid_domains)


def load_analyst_skill():
    """Load analyst skill content"""
    return read_skill_file("analyst/SKILL.md")


def load_reviewer_skill():
    """Load reviewer skill content"""
    skill_content = read_skill_file("reviewer/SKILL.md")
    ref_content = read_skill_file("shared/references/domain_standards.md")
    return f"{skill_content}\n\n---\n\n{ref_content}"


def extract_article_excerpt(article_text, article_ref, max_len=64):
    normalized = unicodedata.normalize("NFKC", article_text).replace("\n", "")
    ref_index = normalized.find(article_ref)
    body_source = normalized[ref_index:] if ref_index >= 0 else normalized
    body = re.sub(rf"^{re.escape(article_ref)}", "", body_source, count=1).strip()
    return f"【{article_ref}】{body[:max_len].rstrip() + '...' if len(body) > max_len else body}"


def extract_article_ref_list(text):
    normalized_text = unicodedata.normalize("NFKC", text)
    return ARTICLE_REF_PATTERN.findall(normalized_text)


def extract_article_refs(text):
    return set(extract_article_ref_list(text))


def extract_primary_article_ref(article_text):
    normalized_text = unicodedata.normalize("NFKC", article_text)
    for line in normalized_text.splitlines():
        stripped = line.strip()
        match = ARTICLE_REF_PATTERN.match(stripped)
        if match:
            return match.group(0)

    refs = extract_article_ref_list(normalized_text)
    return refs[0] if refs else ""


def build_chapter_overview(chapter_info, current_index=None, window_size=None):
    article_meta = chapter_info.get("article_meta", [])
    articles = chapter_info["articles"]
    is_windowed_view = current_index is not None
    start_index = max(0, current_index - (window_size or 2)) if is_windowed_view else 0
    end_index = (
        min(len(articles), current_index + (window_size or 2) + 1)
        if is_windowed_view
        else len(articles)
    )

    overview_lines = []
    for idx in range(start_index, end_index):
        article = articles[idx]
        meta = article_meta[idx] if idx < len(article_meta) else {}
        article_ref = meta.get("article_ref") or next(
            iter(extract_article_refs(article)), ""
        )
        subject_type = meta.get("subject_type", "unknown")
        paragraph_count = meta.get("paragraph_count", 1)
        excerpt_limit = 48 if is_windowed_view else 80
        prefix = (
            f"- [{'当前条文' if idx == current_index else '邻近条文'}] "
            if is_windowed_view
            else "- "
        )
        suffix = (
            f" [主体={subject_type}]"
            if is_windowed_view
            else f" [主体={subject_type}; 段落={paragraph_count}]"
        )

        if article_ref:
            excerpt = extract_article_excerpt(
                article, article_ref, max_len=excerpt_limit
            )
        else:
            excerpt = (
                unicodedata.normalize("NFKC", article)
                .replace("\n", "")[:excerpt_limit]
                .rstrip()
                + "..."
            )

        overview_lines.append(f"{prefix}{excerpt}{suffix}")

    return "\n".join(overview_lines)


def build_analysis_messages(
    backend,
    law_name,
    chapter_title,
    chapter_summary,
    article_text,
    system_prompt,
    chapter_analysis="",
):
    article_ref = extract_primary_article_ref(article_text) or "未识别条款"

    # Incorporate analyst summary if available
    analysis_context = ""
    if chapter_analysis:
        analysis_context = f"\n本章合规画像（分析师摘要）：\n{chapter_analysis}\n"

    user_prompt = f"""你正在分析 **《{law_name}》** 的 **【{chapter_title}】**。

当前被审计组织：
{AUDITED_ORGANIZATION_NAME}

组织适用性画像：
{AUDITED_ORGANIZATION_PROFILE}

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


def build_analysis_messages_with_context(
    backend,
    law_name,
    chapter_title,
    chapter_info,
    article_index,
    article_text,
    system_prompt,
    chapter_analysis="",
):
    chapter_summary = build_chapter_overview(
        chapter_info, current_index=article_index, window_size=2
    )
    messages = build_analysis_messages(
        backend,
        law_name,
        chapter_title,
        chapter_summary,
        article_text,
        system_prompt,
        chapter_analysis,
    )
    return messages, len(chapter_summary), 1


def split_markdown_row(line):
    stripped = line.strip()
    if "|" not in stripped:
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) != 5 or any(not cell for cell in cells):
        return None
    return cells


def build_article_map(articles):
    return {
        extract_primary_article_ref(article): article
        for article in articles
        if extract_primary_article_ref(article)
    }


def is_actionable_article(article_text, chapter_title):
    if should_skip_chapter(chapter_title):
        return False

    normalized = unicodedata.normalize("NFKC", article_text)
    has_target_entity = any(keyword in normalized for keyword in TARGET_ENTITY_KEYWORDS)
    has_enterprise_applicability = any(
        keyword in normalized for keyword in ENTERPRISE_APPLICABILITY_KEYWORDS
    )
    has_cii_context = any(keyword in normalized for keyword in CII_CONTEXT_KEYWORDS)
    has_non_enterprise_subject = any(
        keyword in normalized for keyword in NON_ENTERPRISE_SUBJECT_KEYWORDS
    )

    if has_target_entity:
        return True
    if has_enterprise_applicability:
        return True
    if has_cii_context:
        return True
    if has_non_enterprise_subject:
        return False

    return True


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

    normalized_line = (
        "| "
        + " | ".join(
            [
                domain,
                control_target,
                extract_article_excerpt(source_article, cited_ref),
                control_point,
                row_type,
            ]
        )
        + " |"
    )
    return True, "", normalized_line


def write_review_entry(file_path, chapter_title, batch_index, reason, line):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(
            f"## 章节: {chapter_title} / 批次: {batch_index}\n- 原因: {reason}\n- 原文: {line}\n\n"
        )


def append_to_file(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{text}\n")


def extract_valid_table_lines(response_text):
    valid_lines = []
    for raw_line in response_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if (
            "---" in line
            or "涉及领域" in line
            or "控制目标" in line
            or "法律要求" in line
        ):
            continue
        if is_no_applicable_response(line):
            continue
        # 使用 split_markdown_row 验证是否为有效的5列表格行
        cells = split_markdown_row(line)
        if cells is not None:
            valid_lines.append(line)
    return valid_lines


def is_no_applicable_response(response_text):
    normalized = normalize_for_keyword_match(response_text)
    if not normalized:
        return True
    return any(marker in normalized for marker in NO_APPLICABLE_MARKERS)


def main():
    print("Step 1: 请选择 PDF 文件...")
    source_pdf_path = select_pdf_file()
    if not source_pdf_path:
        print("⚠️ 未选择文件，程序结束。")
        return

    law_name = os.path.splitext(os.path.basename(source_pdf_path))[0]
    output_file_path = BASE_DIR / f"{law_name}_合规矩阵.md"
    review_file_path = BASE_DIR / f"{law_name}_复核清单.md"

    # Load skills
    analyst_system_prompt = load_analyst_skill()
    auditor_system_prompt, valid_domains = load_auditor_skill()
    reviewer_system_prompt = load_reviewer_skill()
    backend = select_backend()
    backend.initialize()

    print("\nStep 2: 正在解析 PDF 内容...")
    parser = PDFParser()
    chapters_data = parser.extract_content(source_pdf_path)
    if not chapters_data:
        print("⚠️ 未能从 PDF 提取有效内容，程序结束。")
        return

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

        if should_skip_chapter(chapter_title):
            print(f"\n⏭️ 跳过章节: {chapter_title} (默认不从处罚/附则章节抽取)")
            continue

        processed_chapters += 1
        print(f"\n📚 章节: {chapter_title} (共 {len(articles)} 条)")
        article_lookup = build_article_map(articles)

        # Step 1: Analyst phase - generate chapter summary
        print(f"      📋 分析师阶段: 生成章节摘要...")
        analyst_messages = backend.build_messages(
            analyst_system_prompt,
            f"""请分析 **《{law_name}》** 的 **【{chapter_title}】**。

当前被审计组织：
{AUDITED_ORGANIZATION_NAME}

组织适用性画像：
{AUDITED_ORGANIZATION_PROFILE}""",
        )
        try:
            chapter_analysis = backend.generate(
                analyst_messages, max_tokens=300, task="chapter_analysis"
            )
            print(f"      ✅ 章节摘要生成完成 ({len(chapter_analysis)} 字符)")
        except Exception as e:
            print(f"      ❌ 分析师阶段失败: {e}")
            chapter_analysis = ""

        for article_index, article_text in enumerate(articles):
            article_meta = chapter_info.get("article_meta", [])
            article_ref = (
                article_meta[article_index].get("article_ref")
                if article_index < len(article_meta)
                else ""
            )
            article_ref = (
                article_ref
                or extract_primary_article_ref(article_text)
                or f"第{article_index + 1}条(未识别)"
            )

            if not is_actionable_article(article_text, chapter_title):
                print(f"      -> 跳过条文 {article_ref}: 不属于企业义务")
                continue

            messages, prompt_size, prompt_level = build_analysis_messages_with_context(
                backend,
                law_name,
                chapter_title,
                chapter_info,
                article_index,
                article_text,
                auditor_system_prompt,
                chapter_analysis,
            )

            print(
                f"      -> 条文 {article_ref} ({article_index + 1}/{len(articles)})..."
                f" 使用导览级别 {prompt_level}, size≈{prompt_size}"
            )

            try:
                response_text = backend.generate(
                    messages, max_tokens=2500, task="control_generation"
                )
            except Exception as error:
                print(f"         ❌ 模型调用失败: {error}")
                write_review_entry(
                    review_file_path,
                    chapter_title,
                    article_index + 1,
                    f"模型调用失败: {error}",
                    article_ref,
                )
                continue

            valid_lines = []
            review_lines = []
            invalid_count = 0
            candidate_lines = extract_valid_table_lines(response_text)

            if not candidate_lines:
                raw_response = response_text.strip() or "<空响应>"
                if is_no_applicable_response(raw_response):
                    print("         ⏭️ Auditor 判断无适用控制点")
                else:
                    write_review_entry(
                        review_file_path,
                        chapter_title,
                        article_index + 1,
                        "Auditor 未返回可解析的 5 列 Markdown 表格行",
                        raw_response,
                    )
                    print(
                        "         ⚠️ Auditor 未返回可解析表格行，原始输出已写入复核清单"
                    )

            for line in candidate_lines:
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
当前被审计组织：{AUDITED_ORGANIZATION_NAME}
组织适用性画像：{AUDITED_ORGANIZATION_PROFILE}

请基于评审员技能中的标准进行严格审查。请只输出以下三个标签之一：PASS、REVIEW 或 FAIL，不要输出任何其他内容。""",
                )
                try:
                    reviewer_response = backend.generate(
                        reviewer_messages, max_tokens=50, task="review"
                    )
                    reviewer_response = reviewer_response.strip().upper()

                    # Simplified parsing - only check for PASS, REVIEW, or FAIL
                    if reviewer_response.startswith("PASS"):
                        is_valid, reason, normalized_line = validate_output_row(
                            line, valid_domains, chapter_title, article_lookup
                        )
                        if is_valid:
                            valid_lines.append(normalized_line)
                        else:
                            invalid_count += 1
                            write_review_entry(
                                review_file_path,
                                chapter_title,
                                article_index + 1,
                                reason,
                                line,
                            )
                    elif reviewer_response.startswith("REVIEW"):
                        review_lines.append(line)
                        write_review_entry(
                            review_file_path,
                            chapter_title,
                            article_index + 1,
                            "需人工复核",
                            line,
                        )
                    elif reviewer_response.startswith("FAIL"):
                        invalid_count += 1
                        write_review_entry(
                            review_file_path,
                            chapter_title,
                            article_index + 1,
                            "评审不通过",
                            line,
                        )
                    else:
                        # If reviewer returns unexpected response, treat as FAIL
                        invalid_count += 1
                        write_review_entry(
                            review_file_path,
                            chapter_title,
                            article_index + 1,
                            f"评审返回未知标签: {reviewer_response}",
                            line,
                        )

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
                        write_review_entry(
                            review_file_path,
                            chapter_title,
                            article_index + 1,
                            reason,
                            line,
                        )

            if valid_lines:
                append_to_file(output_file_path, "\n".join(valid_lines))
                print(f"         ✅ 通过评审 {len(valid_lines)} 个控制点")
            if review_lines:
                print(f"         ⚠️ {len(review_lines)} 个控制点需人工复核")
            if candidate_lines and not valid_lines and not review_lines:
                print("         ℹ️ 未产出通过评审的控制点")

            if invalid_count:
                print(f"         ❌ {invalid_count} 个结果评审不通过")

    print(f"\n🎉 完成！请查看: {output_file_path}")
    print(f"🧾 复核清单: {review_file_path}")
    backend.cleanup()


if __name__ == "__main__":
    main()
