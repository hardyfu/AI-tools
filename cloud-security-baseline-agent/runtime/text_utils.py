import json
import re
import subprocess
import unicodedata
from pathlib import Path
from typing import Any

from runtime.pdf_parser import PDFParser
from runtime.pdf_parser import _resolve_binary

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET_PATTERN = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+|[一二三四五六七八九十]+、|（[一二三四五六七八九十0-9]+）)")
KEYWORD_PRIORITIES = {
    "must": "mandatory",
    "shall": "mandatory",
    "required": "mandatory",
    "ensure": "mandatory",
    "should": "recommended",
    "建议": "recommended",
    "必须": "mandatory",
    "确保": "mandatory",
    "应": "mandatory",
    "need": "mandatory",
}
CATEGORY_KEYWORDS = {
    "identity": ["identity", "iam", "ram", "账号", "身份", "权限", "access"],
    "logging": ["log", "audit", "trail", "日志", "审计"],
    "network": ["network", "vpc", "security group", "公网", "网络", "acl"],
    "encryption": ["encrypt", "kms", "key", "加密", "密钥"],
    "monitoring": ["monitor", "alert", "告警", "监控", "检测"],
    "configuration": ["config", "baseline", "harden", "配置", "基线", "加固"],
    "data protection": ["data", "backup", "retention", "数据", "备份", "保留"],
}
SERVICE_KEYWORDS = {
    "ECS": ["ecs", "elastic compute service"],
    "OSS": ["oss", "object storage service"],
    "RAM": ["ram", "resource access management"],
    "ActionTrail": ["actiontrail"],
    "Cloud Config": ["config", "cloud config"],
    "KMS": ["kms", "key management service"],
    "VPC": ["vpc", "virtual private cloud"],
    "Security Center": ["security center"],
}
STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "into", "your", "have", "will",
    "must", "shall", "should", "required", "need", "need to", "of", "on", "in", "to", "a",
    "is", "are", "be", "by", "or", "as", "an", "it", "ensure", "use", "all", "not",
    "必须", "应", "确保", "使用", "所有", "以及", "进行", "相关", "要求", "控制"
}
PAGE_NUMBER_PATTERNS = [
    re.compile(r"^\s*\d+\s*/\s*\d+\s*$"),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^\s*Page\s+\d+\s*$", re.IGNORECASE),
]
TOC_NOISE_PATTERNS = [
    re.compile(r"^\s*contents\s*$", re.IGNORECASE),
    re.compile(r"^\s*table of contents\s*$", re.IGNORECASE),
    re.compile(r"^\s*recommendation definitions\s*$", re.IGNORECASE),
    re.compile(r"^\s*overview\s*$", re.IGNORECASE),
]
CHECKBOX_GLYPHS = {"", "", "□", "■", "▪"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)



def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")



def read_text_files(directory: Path) -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = []
    if not directory.exists():
        return files
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.suffix.lower() in {".md", ".txt", ".text"}:
            files.append((path, path.read_text(encoding="utf-8")))
    return files


def extract_pdf_text(source: Path) -> str:
    parser = PDFParser()
    text = parser.extract_text(source)
    text = clean_pdf_layout_text(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def render_pdf_pages(source: Path, output_dir: Path, max_pages: int = 3) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = output_dir / source.stem
    pdftoppm_bin = _resolve_binary("pdftoppm")
    subprocess.run(
        [
            pdftoppm_bin,
            "-png",
            "-f",
            "1",
            "-l",
            str(max_pages),
            str(source),
            str(prefix),
        ],
        check=True,
        capture_output=True,
    )
    return sorted(output_dir.glob(f"{source.stem}-*.png"))



def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def clean_statement_noise(text: str) -> str:
    cleaned = normalize_line(text.replace("\f", " "))
    cleaned = re.sub(r"\s+\.\.+\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s+\.\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\s+\.\.\s*\d+\s*$", "", cleaned)
    cleaned = re.sub(r"\bCLOUD SECURITY STANDARD\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bApproved Internal\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"ConO\s*trol", "Control", cleaned)
    cleaned = re.sub(r"requireM\s*ments", "requirements", cleaned)
    cleaned = re.sub(r"Anti-DDosaccess", "Anti-DDoS access", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"DDosaccess", "DDoS access", cleaned)
    cleaned = re.sub(r"DDos", "DDoS", cleaned)
    cleaned = re.sub(r"([A-Za-z])([A-Z][a-z]+access)", r"\1 \2", cleaned)
    cleaned = re.sub(
        r"([a-z])([A-Z])\s+([a-z]{2,})",
        lambda m: m.group(1) + m.group(2).lower() + m.group(3),
        cleaned,
    )
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -;:,")


def normalize_security_terms(text: str) -> str:
    normalized = clean_statement_noise(text)
    normalized = re.sub(r"Anti-DD[oO]S\s*access", "Anti-DDoS access", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"Anti-DD[oO]Saccess", "Anti-DDoS access", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"Anti-DDosaccess", "Anti-DDoS access", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bDD[oO]S\b", "DDoS", normalized, flags=re.IGNORECASE)
    return normalized

def _is_page_noise_line(line: str) -> bool:
    if not line.strip():
        return True
    return any(pattern.match(line) for pattern in PAGE_NUMBER_PATTERNS)


def _is_toc_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if re.match(r"^\s*[1-9](?:\.\d+)+\s+(?:Ensure|Avoid)\b", stripped):
        return False
    if any(pattern.match(stripped) for pattern in TOC_NOISE_PATTERNS):
        return True
    if re.match(r"^\s*[1-9](?:\.[0-9]+)*\s+[A-Za-z].*\.{4,}\s*\d+\s*$", stripped):
        return True
    return False


def clean_pdf_layout_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    cleaned_lines: list[str] = []
    for raw_line in normalized.splitlines():
        line = normalize_line(raw_line.replace("\f", " "))
        if not line:
            cleaned_lines.append("")
            continue
        if _is_page_noise_line(line) or _is_toc_noise_line(line):
            continue
        if any(glyph in line for glyph in CHECKBOX_GLYPHS):
            continue
        line = re.sub(r"\s+\.{4,}\s*\d+\s*$", "", line)
        line = re.sub(r"\s+\.\s*\d+\s*$", "", line)
        line = re.sub(r"\s+\.\.\s*\d+\s*$", "", line)
        line = line.strip()
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)



def detect_priority(text: str) -> str:
    lowered = text.lower()
    for keyword, priority in KEYWORD_PRIORITIES.items():
        if keyword in lowered or keyword in text:
            return priority
    return "informational"



def categorize_text(text: str) -> str:
    lowered = text.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in lowered or keyword in text for keyword in keywords):
            return category
    return "general"



def detect_service(text: str) -> str:
    lowered = text.lower()
    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return service
    return "general"



def parse_requirement_lines(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current_section = "General"
    for raw_line in text.splitlines():
        line = normalize_line(raw_line)
        if not line:
            continue
        heading_match = HEADING_PATTERN.match(line)
        if heading_match:
            current_section = heading_match.group(2).strip()
            continue
        if BULLET_PATTERN.match(raw_line) or len(line) > 30 and detect_priority(line) != "informational":
            statement = BULLET_PATTERN.sub("", raw_line).strip()
            if len(statement) < 12:
                continue
            items.append(
                {
                    "section": current_section,
                    "statement": normalize_line(statement),
                    "category": categorize_text(statement),
                    "priority": detect_priority(statement),
                    "source_excerpt": normalize_line(statement)[:280],
                }
            )
    return dedupe_requirements(items)



def dedupe_requirements(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        key = re.sub(r"\W+", " ", item["statement"].lower()).strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped



def build_theme_summary(requirements: list[dict[str, str]], field_name: str) -> list[dict[str, str]]:
    counts: dict[str, int] = {}
    evidences: dict[str, str] = {}
    for requirement in requirements:
        theme = str(requirement.get(field_name, "general") or "general")
        counts[theme] = counts.get(theme, 0) + 1
        evidences.setdefault(theme, requirement.get("statement", "unknown"))
    return [
        {
            "theme": theme,
            "description": f"{counts[theme]} requirement(s) classified under {theme}.",
            "evidence": evidences[theme],
        }
        for theme in sorted(counts, key=lambda item: (-counts[item], item))
    ]



def tokenize(text: str) -> set[str]:
    normalized = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", " ", text.lower())
    return {token for token in normalized.split() if len(token) >= 2 and token not in STOPWORDS}



def score_overlap(left: str, right: str) -> float:
    left_tokens = tokenize(left)
    right_tokens = tokenize(right)
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = left_tokens & right_tokens
    return round(len(overlap) / max(len(left_tokens), len(right_tokens)), 4)


def overlap_tokens(left: str, right: str) -> set[str]:
    return tokenize(left) & tokenize(right)
