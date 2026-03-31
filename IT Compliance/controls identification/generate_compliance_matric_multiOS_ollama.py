import time
import os
import re
import unicodedata
import platform
import importlib.util
from pathlib import Path

import requests
from pdf_parser import PDFParser, select_pdf_file

# ================= 配置区域 =================
BACKEND_MODE = "auto"   # 可选: auto / mlx / ollama

# MLX 配置（macOS Apple Silicon）
MLX_MODEL_PATH = "mlx-community/Qwen2.5-14B-Instruct-4bit"

# Ollama 配置（Windows 推荐）
OLLAMA_MODEL_NAME = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_TIMEOUT = 600

MAX_INPUT_TOKENS = 3000

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
PUNCTUATION_CLEAN_PATTERN = re.compile(r"[，。；：、“”‘’（）()【】《》,.;:\s]")
SKIP_CHAPTER_KEYWORDS = ("法律责任", "附 则", "附则")
# ===========================================


# ================= 后端适配层 =================
class BaseLLMBackend:
    name = "base"

    def initialize(self):
        raise NotImplementedError

    def count_tokens(self, text: str) -> int:
        raise NotImplementedError

    def build_prompt(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        raise NotImplementedError

    def cleanup(self):
        pass


class OllamaBackend(BaseLLMBackend):
    name = "ollama"

    def __init__(self, model_name: str, url: str, timeout: int = 600):
        self.model_name = model_name
        self.url = url
        self.timeout = timeout

    def initialize(self):
        print(f"\n🚀 正在检查 Ollama 模型: {self.model_name} ...")
        try:
            resp = requests.post(
                self.url,
                json={
                    "model": self.model_name,
                    "prompt": "你好",
                    "stream": False,
                    "options": {
                        "num_predict": 1,
                        "temperature": 0
                    }
                },
                timeout=60
            )
            resp.raise_for_status()
            print("✅ Ollama 服务和模型可用")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Ollama 调用失败。\n"
                f"请确认：\n"
                f"1. 已安装并启动 Ollama\n"
                f"2. 已执行: ollama pull {self.model_name}\n"
                f"3. 本地接口可访问: {self.url}\n"
                f"原始错误: {e}"
            )

    def count_tokens(self, text: str) -> int:
        # 近似估算，中文场景保守高估
        return int(len(text) * 1.2)

    def build_prompt(self, system_prompt: str, user_prompt: str) -> str:
        return f"""<SYSTEM>
{system_prompt}
</SYSTEM>

<USER>
{user_prompt}
</USER>

<ASSISTANT>
"""

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0
            }
        }

        resp = requests.post(self.url, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()


class MLXBackend(BaseLLMBackend):
    name = "mlx"

    def __init__(self, model_path: str):
        self.model_path = model_path
        self.mx = None
        self.load_fn = None
        self.generate_fn = None
        self.model = None
        self.tokenizer = None

    def initialize(self):
        print(f"\n🚀 正在加载 MLX 模型: {self.model_path} ...")
        import mlx.core as mx
        from mlx_lm import load, generate

        self.mx = mx
        self.load_fn = load
        self.generate_fn = generate

        self.model, self.tokenizer = self.load_fn(
            self.model_path,
            tokenizer_config={"trust_remote_code": True}
        )
        print("✅ MLX 模型加载完成")

    def count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))

    def build_prompt(self, system_prompt: str, user_prompt: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

    def generate(self, prompt: str, max_tokens: int = 2500) -> str:
        return self.generate_fn(
            self.model,
            self.tokenizer,
            prompt=prompt,
            max_tokens=max_tokens,
            verbose=False
        ).strip()

    def cleanup(self):
        try:
            if self.mx is not None:
                self.mx.metal.clear_cache()
        except Exception:
            pass


def is_module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def can_use_mlx() -> bool:
    return (
        platform.system() == "Darwin"
        and is_module_available("mlx")
        and is_module_available("mlx_lm")
    )


def select_backend():
    system_name = platform.system()

    if BACKEND_MODE == "mlx":
        if not can_use_mlx():
            raise RuntimeError("已强制指定 MLX，但当前环境不可用。请检查 macOS / Apple Silicon 及 mlx 依赖。")
        return MLXBackend(MLX_MODEL_PATH)

    if BACKEND_MODE == "ollama":
        return OllamaBackend(OLLAMA_MODEL_NAME, OLLAMA_URL, OLLAMA_TIMEOUT)

    # auto 模式
    if system_name == "Darwin" and can_use_mlx():
        print("🧠 自动选择后端: MLX")
        return MLXBackend(MLX_MODEL_PATH)

    print("🧠 自动选择后端: Ollama")
    return OllamaBackend(OLLAMA_MODEL_NAME, OLLAMA_URL, OLLAMA_TIMEOUT)


# ===========================================


def read_skill_file(filename):
    path = SKILLS_DIR / filename
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def load_prompt_assets():
    skill_content = read_skill_file("auditor_skill.md")
    ref_content = read_skill_file("references/domain_standards.md")
    valid_domains = []

    for line in ref_content.splitlines():
        match = re.match(r"^\s*\d+\.\s*(.+?)\s*$", line)
        if match:
            valid_domains.append(match.group(1))

    if not valid_domains:
        raise ValueError("未能从 domain_standards.md 提取控制域")

    return f"{skill_content}\n\n---\n\n{ref_content}", set(valid_domains)


def save_intermediate_file(law_name, chapters_data):
    filename = BASE_DIR / f"{law_name}_parsed.txt"
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"解析时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"源文件: {law_name}\n")
            f.write("=" * 80 + "\n\n")

            for chapter_info in chapters_data:
                f.write("\n" + "=" * 80 + "\n")
                f.write(f"📂 {chapter_info['chapter']}\n")
                f.write("=" * 80 + "\n")

                for article in chapter_info["articles"]:
                    f.write(article + "\n")
                    f.write("-" * 40 + "\n")

        print(f"💾 解析后的法律原文已保存至: {filename}")
    except Exception as e:
        print(f"⚠️ 保存中间文件失败: {e}")


def extract_article_excerpt(article_text, article_ref, max_len=64):
    normalized = unicodedata.normalize("NFKC", article_text).replace("\n", "")
    body = re.sub(rf"^{re.escape(article_ref)}", "", normalized, count=1).strip()
    if len(body) > max_len:
        body = body[:max_len].rstrip() + "..."
    return f"【{article_ref}】{body}"


def extract_article_refs(text):
    normalized_text = unicodedata.normalize("NFKC", text)
    return set(ARTICLE_REF_PATTERN.findall(normalized_text))


def normalize_for_match(text):
    normalized = unicodedata.normalize("NFKC", text)
    return PUNCTUATION_CLEAN_PATTERN.sub("", normalized)


def build_chapter_overview(chapter_info):
    overview_lines = []
    article_meta = chapter_info.get("article_meta", [])

    for idx, article in enumerate(chapter_info["articles"]):
        meta = article_meta[idx] if idx < len(article_meta) else {}
        article_ref = meta.get("article_ref") or next(iter(extract_article_refs(article)), "")
        subject_type = meta.get("subject_type", "unknown")
        paragraph_count = meta.get("paragraph_count", 1)

        if article_ref:
            overview_lines.append(
                f"- {extract_article_excerpt(article, article_ref, max_len=80)} "
                f"[主体={subject_type}; 段落={paragraph_count}]"
            )
        else:
            trimmed = unicodedata.normalize("NFKC", article).replace("\n", " ")
            overview_lines.append(
                f"- {trimmed[:80].rstrip()}... [主体={subject_type}; 段落={paragraph_count}]"
            )

    return "\n".join(overview_lines)


def build_condensed_chapter_overview(chapter_info, current_index, window_size=2):
    article_meta = chapter_info.get("article_meta", [])
    overview_lines = []
    start = max(0, current_index - window_size)
    end = min(len(chapter_info["articles"]), current_index + window_size + 1)

    for idx in range(start, end):
        article = chapter_info["articles"][idx]
        meta = article_meta[idx] if idx < len(article_meta) else {}
        article_ref = meta.get("article_ref") or next(iter(extract_article_refs(article)), "")
        subject_type = meta.get("subject_type", "unknown")
        marker = "当前条文" if idx == current_index else "邻近条文"

        if article_ref:
            overview_lines.append(
                f"- [{marker}] {extract_article_excerpt(article, article_ref, max_len=48)} [主体={subject_type}]"
            )
        else:
            trimmed = unicodedata.normalize("NFKC", article).replace("\n", " ")
            overview_lines.append(
                f"- [{marker}] {trimmed[:48].rstrip()}... [主体={subject_type}]"
            )

    return "\n".join(overview_lines)


def build_auditor_prompt(backend, law_name, chapter_title, chapter_overview, article_text, system_prompt):
    article_ref = next(iter(extract_article_refs(article_text)), "未识别条款")

    user_prompt = f"""你正在分析 **《{law_name}》** 的 **【{chapter_title}】**。

请先理解本章整体内容，再分析当前条文。

本章条文导览：
{chapter_overview}

当前需要细看并输出控制点的条文：
{article_text}

要求：
1. 先基于本章导览理解当前条文在本章中的作用。
2. 再只针对当前条文 `{article_ref}` 输出控制点。
3. 请严格参照 System Prompt 中的规则。
4. 只输出符合要求的 markdown 表格行；不要输出解释、标题、前言、结语。
5. 不适用时返回空白。"""

    return backend.build_prompt(system_prompt, user_prompt)


def build_prompt_with_budget(backend, law_name, chapter_title, chapter_info, article_index, article_text, system_prompt):
    overview_candidates = [
        build_chapter_overview(chapter_info),
        build_condensed_chapter_overview(chapter_info, article_index, window_size=2),
        build_condensed_chapter_overview(chapter_info, article_index, window_size=1),
        "请仅结合当前条文进行分析。"
    ]

    for level, overview in enumerate(overview_candidates, start=1):
        prompt = build_auditor_prompt(
            backend, law_name, chapter_title, overview, article_text, system_prompt
        )
        prompt_tokens = backend.count_tokens(prompt)
        if prompt_tokens <= MAX_INPUT_TOKENS:
            return prompt, prompt_tokens, level

    return None, None, None


def split_markdown_row(line):
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    return cells if len(cells) == 5 else None


def build_article_map(articles):
    article_map = {}
    for article in articles:
        refs = extract_article_refs(article)
        if refs:
            article_map[sorted(refs)[0]] = article
    return article_map


def is_actionable_article(article_text, chapter_title):
    if any(keyword in chapter_title for keyword in SKIP_CHAPTER_KEYWORDS):
        return False

    normalized = unicodedata.normalize("NFKC", article_text)
    has_target_entity = any(keyword in normalized for keyword in TARGET_ENTITY_KEYWORDS)
    has_non_enterprise_subject = any(keyword in normalized for keyword in NON_ENTERPRISE_SUBJECT_KEYWORDS)
    has_obligation = any(keyword in normalized for keyword in OBLIGATION_KEYWORDS)

    if not has_obligation:
        return False
    if has_non_enterprise_subject and not has_target_entity:
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

    if not any(keyword in control_point for keyword in EVIDENCE_KEYWORDS):
        return False, "控制点缺少明确审计证据", None

    canonical_requirement = extract_article_excerpt(source_article, cited_ref)

    normalized_line = "| " + " | ".join([
        domain,
        control_target,
        canonical_requirement,
        control_point,
        row_type
    ]) + " |"

    return True, "", normalized_line


def write_review_entry(file_path, chapter_title, batch_index, reason, line):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"## 章节: {chapter_title} / 批次: {batch_index}\n")
        f.write(f"- 原因: {reason}\n")
        f.write(f"- 原文: {line}\n\n")


def append_to_file(file_path, text):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def extract_valid_table_lines(response_text):
    valid_candidate_lines = []
    for raw_line in response_text.strip().split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if "|" not in line:
            continue
        if "---" in line:
            continue
        if "涉及领域" in line or "控制目标" in line or "法律要求" in line:
            continue
        valid_candidate_lines.append(line)
    return valid_candidate_lines


def main():
    print("Step 1: 请选择 PDF 文件...")
    pdf_path = select_pdf_file()
    if not pdf_path:
        print("⚠️ 未选择文件，程序结束。")
        return

    law_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_file = BASE_DIR / f"{law_name}_合规矩阵.md"
    review_file = BASE_DIR / f"{law_name}_复核清单.md"

    parser = PDFParser()
    chapters_data = parser.extract_content(pdf_path)
    if not chapters_data:
        print("⚠️ 未能从 PDF 提取有效内容，程序结束。")
        return

    save_intermediate_file(law_name, chapters_data)

    system_prompt, valid_domains = load_prompt_assets()
    backend = select_backend()
    backend.initialize()

    header = "| 涉及领域 | 控制目标 | 法律要求 | 控制点 | 类型 |\n| :--- | :--- | :--- | :--- | :--- |"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# 合规审计底稿\n**源文件**: {law_name}\n\n{header}\n")

    with open(review_file, "w", encoding="utf-8") as f:
        f.write(f"# 复核清单\n**源文件**: {law_name}\n\n")

    print(f"💾 结果将实时写入: {output_file}")
    print(f"🧾 异常输出将写入: {review_file}")
    print(f"⚡️ 开始智能分析 (当前后端: {backend.name})...")

    for chapter_info in chapters_data:
        chapter_title = chapter_info["chapter"]
        articles = chapter_info["articles"]

        if chapter_title == "未归类章节" or not articles:
            print(f"\n⏭️ 跳过章节: {chapter_title}")
            continue

        if any(keyword in chapter_title for keyword in SKIP_CHAPTER_KEYWORDS):
            print(f"\n⏭️ 跳过章节: {chapter_title} (默认不从处罚/附则章节抽取)")
            continue

        print(f"\n📚 章节: {chapter_title} (共 {len(articles)} 条)")
        chapter_article_map = build_article_map(articles)

        for idx, article in enumerate(articles):
            article_ref = next(iter(extract_article_refs(article)), f"第{idx + 1}条(未识别)")

            if not is_actionable_article(article, chapter_title):
                print(f"      -> 跳过条文 {article_ref}: 不属于企业义务")
                continue

            prompt, prompt_tokens, prompt_level = build_prompt_with_budget(
                backend, law_name, chapter_title, chapter_info, idx, article, system_prompt
            )

            if prompt is None:
                print(f"      -> 跳过条文 {article_ref}: 多级缩减后仍超出 token 限制")
                write_review_entry(
                    review_file,
                    chapter_title,
                    idx + 1,
                    "多级缩减后仍超出 token 限制",
                    article_ref
                )
                continue

            print(
                f"      -> 条文 {article_ref} ({idx + 1}/{len(articles)})..."
                f" 使用导览级别 {prompt_level}, tokens≈{prompt_tokens}"
            )

            try:
                response = backend.generate(prompt, max_tokens=2500)
            except Exception as e:
                print(f"         ❌ 模型调用失败: {e}")
                write_review_entry(
                    review_file,
                    chapter_title,
                    idx + 1,
                    f"模型调用失败: {e}",
                    article_ref
                )
                continue
            finally:
                backend.cleanup()

            valid_lines = []
            invalid_count = 0

            for line in extract_valid_table_lines(response):
                is_valid, reason, normalized_line = validate_output_row(
                    line, valid_domains, chapter_title, chapter_article_map
                )
                if is_valid:
                    valid_lines.append(normalized_line)
                else:
                    invalid_count += 1
                    write_review_entry(review_file, chapter_title, idx + 1, reason, line)

            if valid_lines:
                append_to_file(output_file, "\n".join(valid_lines))
                print(f"         ✅ 通过校验 {len(valid_lines)} 个控制点")
            else:
                print("         ℹ️ 未产出通过校验的控制点")

            if invalid_count:
                print(f"         ⚠️ {invalid_count} 个结果进入复核清单")

            if backend.name == "ollama":
                time.sleep(0.2)

    print(f"\n🎉 完成！请查看: {output_file}")
    print(f"🧾 复核清单: {review_file}")


if __name__ == "__main__":
    main()