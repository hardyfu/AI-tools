import json
import re
from pathlib import Path
from typing import Any

from runtime.ollama_runtime import OllamaRuntime
from runtime.text_utils import (
    build_theme_summary,
    categorize_text,
    clean_statement_noise,
    detect_priority,
    detect_service,
    extract_pdf_text,
    load_json,
    normalize_security_terms,
    overlap_tokens,
    render_pdf_pages,
    read_text_files,
    score_overlap,
    write_json,
)

QUALITY_SIGNAL_PATTERNS = {
    "table_artifacts": re.compile(r"\.{4,}\s*\d+|\bPage\s+\d+\b", re.IGNORECASE),
    "broken_uppercase": re.compile(r"(?:[A-Z]\s){4,}[A-Z]"),
    "control_chars": re.compile(r"\f"),
}

GLOBAL_POLICY_REQUIREMENT_START = re.compile(r"^\s*(2\.\d+\.\d+[A-Z]?)\.?\s+(.*)$")
GLOBAL_POLICY_SECTION = re.compile(r"^\s*2\.\d+\.\s+(.+?)\s*$")
GLOBAL_POLICY_STOP = re.compile(r"^\s*3\.\s+Additional information\b", re.IGNORECASE)
GLOBAL_POLICY_NOISE = [
    re.compile(r"^\s*STATUS\s+SECURITY LEVEL", re.IGNORECASE),
    re.compile(r"^\s*Approved\s+Internal", re.IGNORECASE),
    re.compile(r"^\s*DOCUMENT ID\.", re.IGNORECASE),
    re.compile(r"^\s*© Copyright", re.IGNORECASE),
    re.compile(r"^\s*PAGE\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+/\d+\s*$"),
]
GLOBAL_POLICY_TRAILING = re.compile(r"\b(?:[OMRPN/Ax]{1,3}\s+){3,}[OMRPN/Ax]{1,3}\s*$")
GLOBAL_POLICY_INLINE = re.compile(r"\b(?:[OMRPN/Ax]{1,3}\s+){4,}[OMRPN/Ax]{1,3}\b")

THIRD_PARTY_REC_START = re.compile(r"^\s*((?:[1-9])\.\d+)\s+((?:Ensure|Avoid) .*)$")
THIRD_PARTY_SECTION = re.compile(r"^\s*([1-9])\s+([A-Za-z].*?)(?:\.{2,}\s*\d+)?\s*$")
THIRD_PARTY_STOP = re.compile(r"^\s*(?:Appendix)\b", re.IGNORECASE)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def is_valid_global_policy_requirement(statement: str) -> bool:
    lowered = statement.lower()
    if len(statement) < 16:
        return False
    if "withdrawn" in lowered:
        return False
    if statement.count("...") > 0:
        return False
    return True


def is_valid_third_party_requirement(source_id: str, statement: str) -> bool:
    if not re.fullmatch(r"[1-9]\.\d+", source_id.strip()):
        return False
    if len(statement) < 24:
        return False
    if not statement.startswith(("Ensure ", "Avoid ")):
        return False
    if any(glyph in statement for glyph in {"", "", "□", "■", "▪"}):
        return False
    if re.search(r"\s+\.\.?\s*\d+\s*$", statement):
        return False
    return True



def normalize_global_policy_text(text: str) -> str:
    text = text.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"([A-Za-z])\-\n\s*([A-Za-z])", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text



def normalize_global_policy_statement(text: str) -> str:
    text = GLOBAL_POLICY_INLINE.sub(" ", text)
    text = normalize_security_terms(text)
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = GLOBAL_POLICY_TRAILING.sub("", text).strip()
    return text



def global_policy_line_is_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("CLOU D S ECUR IT Y STA NDARD") or stripped.startswith("Cloud Security Standard"):
        return True
    if set(stripped) <= {"-", ".", " "}:
        return True
    return any(pattern.search(stripped) for pattern in GLOBAL_POLICY_NOISE)



def parse_global_policy(text: str, source_name: str) -> dict[str, Any]:
    requirements: list[dict[str, Any]] = []
    section = "General"
    current_id: str | None = None
    current_lines: list[str] = []
    started = False
    notes: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_lines
        if not current_id or not current_lines:
            current_id = None
            current_lines = []
            return
        statement = normalize_global_policy_statement(" ".join(current_lines))
        if is_valid_global_policy_requirement(statement):
            requirements.append(
                {
                    "requirement_id": f"GP-{len(requirements) + 1:03d}",
                    "source_requirement_id": current_id,
                    "section": section,
                    "statement": statement,
                    "category": categorize_text(statement),
                    "priority": detect_priority(statement),
                    "source_excerpt": statement[:280],
                    "service": detect_service(statement),
                }
            )
        current_id = None
        current_lines = []

    for raw_line in normalize_global_policy_text(text).splitlines():
        line = raw_line.strip()
        if global_policy_line_is_noise(line):
            continue
        section_match = GLOBAL_POLICY_SECTION.match(line)
        if section_match and "....." not in line:
            if started:
                flush()
            started = True
            section = normalize_whitespace(section_match.group(1))
            continue
        if not started and GLOBAL_POLICY_REQUIREMENT_START.match(line):
            started = True
        if GLOBAL_POLICY_STOP.match(line) and requirements:
            flush()
            break
        if not started:
            continue
        requirement_match = GLOBAL_POLICY_REQUIREMENT_START.match(line)
        if requirement_match:
            flush()
            current_id = requirement_match.group(1)
            current_lines = [requirement_match.group(2)]
            continue
        if current_id:
            if line.startswith("Note"):
                continue
            if re.fullmatch(r"[PMROCINSAax/\s]+", line):
                continue
            if "Information type" in line or "Applicable for" in line:
                continue
            current_lines.append(line)
    flush()
    if not requirements:
        notes.append(f"No structured global policy requirements detected in {source_name}.")
    return {
        "document_role": "global_policy",
        "document_name": source_name,
        "requirements": requirements,
        "thematic_signals": build_theme_summary(requirements, "category"),
        "parsing_notes": notes,
        "parser_strategy": "numbered_global_policy_parser",
    }



def normalize_third_party_statement(text: str) -> str:
    text = text.replace("\f", " ")
    text = re.sub(r"\.{4,}\s*\d+\s*$", "", text)
    text = re.sub(r"\s+\(Automated\)\s*$", " (Automated)", text)
    text = re.sub(r"\s+\(Manual\)\s*$", " (Manual)", text)
    return normalize_security_terms(text)



def infer_third_party_category(section_name: str, statement: str) -> str:
    lowered = section_name.lower()
    if "identity" in lowered or "access" in lowered:
        return "identity"
    if "logging" in lowered or "monitor" in lowered:
        return "logging"
    if "network" in lowered:
        return "network"
    if "storage" in lowered:
        return "data protection"
    if "database" in lowered:
        return "data protection"
    return categorize_text(statement)



def infer_third_party_severity(statement: str) -> str:
    lowered = statement.lower()
    if "(automated)" in lowered:
        return "high"
    if "(manual)" in lowered:
        return "medium"
    return "low"



def parse_third_party_standard(text: str, source_name: str) -> dict[str, Any]:
    def build_requirement_records(raw_requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in raw_requirements:
            source_id = item["source_requirement_id"]
            if source_id in seen:
                continue
            seen.add(source_id)
            deduped.append(item)
        return deduped

    def parse_from_all_headings() -> list[dict[str, Any]]:
        parsed_requirements: list[dict[str, Any]] = []
        local_section = "General"
        local_id: str | None = None
        local_lines: list[str] = []

        def flush_local() -> None:
            nonlocal local_id, local_lines
            if not local_id or not local_lines:
                local_id = None
                local_lines = []
                return
            statement = normalize_third_party_statement(" ".join(local_lines))
            if is_valid_third_party_requirement(local_id, statement):
                parsed_requirements.append(
                    {
                        "requirement_id": f"TPS-{len(parsed_requirements) + 1:03d}",
                        "source_requirement_id": local_id,
                        "section": local_section,
                        "statement": statement,
                        "category": infer_third_party_category(local_section, statement),
                        "priority": detect_priority(statement),
                        "severity": infer_third_party_severity(statement),
                        "service": detect_service(statement),
                        "source_excerpt": statement[:280],
                    }
                )
            local_id = None
            local_lines = []

        for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            line = raw_line.replace("\f", "").strip()
            if not line:
                continue
            if THIRD_PARTY_STOP.match(line) and parsed_requirements:
                flush_local()
                break
            section_match = THIRD_PARTY_SECTION.match(line)
            if section_match and "Ensure " not in line and "Avoid " not in line:
                flush_local()
                local_section = normalize_whitespace(section_match.group(2))
                continue
            rec_match = THIRD_PARTY_REC_START.match(line)
            if rec_match:
                flush_local()
                local_id = rec_match.group(1)
                local_lines = [rec_match.group(2)]
                continue
            if local_id:
                if line.startswith(("Rationale", "Profile", "Description", "Audit Procedure", "Remediation Procedure", "Impact")):
                    flush_local()
                    continue
                if line and re.match(r"^[1-9]\.\d+\s+(?:Ensure|Avoid)\s+", line):
                    flush_local()
                    next_match = THIRD_PARTY_REC_START.match(line)
                    if next_match:
                        local_id = next_match.group(1)
                        local_lines = [next_match.group(2)]
                    continue
                local_lines.append(line)
        flush_local()
        return build_requirement_records(parsed_requirements)

    def parse_from_recommendation_summary() -> list[dict[str, Any]]:
        parsed_requirements: list[dict[str, Any]] = []
        local_section = "General"
        local_id: str | None = None
        local_lines: list[str] = []
        started = False

        def flush_local() -> None:
            nonlocal local_id, local_lines
            if not local_id or not local_lines:
                local_id = None
                local_lines = []
                return
            statement = normalize_third_party_statement(" ".join(local_lines))
            if is_valid_third_party_requirement(local_id, statement):
                parsed_requirements.append(
                    {
                        "requirement_id": f"TPS-{len(parsed_requirements) + 1:03d}",
                        "source_requirement_id": local_id,
                        "section": local_section,
                        "statement": statement,
                        "category": infer_third_party_category(local_section, statement),
                        "priority": detect_priority(statement),
                        "severity": infer_third_party_severity(statement),
                        "service": detect_service(statement),
                        "source_excerpt": statement[:280],
                    }
                )
            local_id = None
            local_lines = []

        for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            line = raw_line.replace("\f", "").strip()
            if not line:
                continue
            if line.startswith("Recommendations"):
                started = True
                continue
            if not started:
                continue
            if THIRD_PARTY_STOP.match(line) and parsed_requirements:
                flush_local()
                break
            section_match = THIRD_PARTY_SECTION.match(line)
            if section_match and "Ensure " not in line and "Avoid " not in line:
                flush_local()
                local_section = normalize_whitespace(section_match.group(2))
                continue
            rec_match = THIRD_PARTY_REC_START.match(line)
            if rec_match:
                flush_local()
                local_id = rec_match.group(1)
                local_lines = [rec_match.group(2)]
                continue
            if local_id:
                if line.startswith(("Rationale", "Profile", "Description")):
                    flush_local()
                    continue
                if line and re.match(r"^[1-9]\.\d+\s+(?:Ensure|Avoid)\s+", line):
                    flush_local()
                    next_match = THIRD_PARTY_REC_START.match(line)
                    if next_match:
                        local_id = next_match.group(1)
                        local_lines = [next_match.group(2)]
                    continue
                local_lines.append(line)
        flush_local()
        return build_requirement_records(parsed_requirements)

    requirements: list[dict[str, Any]] = []
    section = "General"
    current_id: str | None = None
    current_lines: list[str] = []
    notes: list[str] = []

    def flush() -> None:
        nonlocal current_id, current_lines
        if not current_id or not current_lines:
            current_id = None
            current_lines = []
            return
        statement = normalize_third_party_statement(" ".join(current_lines))
        if is_valid_third_party_requirement(current_id, statement):
            requirements.append(
                {
                    "requirement_id": f"TPS-{len(requirements) + 1:03d}",
                    "source_requirement_id": current_id,
                    "section": section,
                    "statement": statement,
                    "category": infer_third_party_category(section, statement),
                    "priority": detect_priority(statement),
                    "severity": infer_third_party_severity(statement),
                    "service": detect_service(statement),
                    "source_excerpt": statement[:280],
                }
            )
        current_id = None
        current_lines = []

    requirements = parse_from_all_headings()
    if len(requirements) < 50:
        notes.append(
            f"正文标题抓取仅识别 {len(requirements)} 条 requirement，已回退到 recommendation summary 混合解析。"
        )
        requirements = parse_from_recommendation_summary()
    if not requirements:
        notes.append(f"No structured third-party requirements detected in {source_name}.")
    return {
        "document_role": "third_party_standard",
        "document_name": source_name,
        "requirements": requirements,
        "thematic_signals": build_theme_summary(requirements, "category"),
        "parsing_notes": notes,
        "parser_strategy": "recommendation_summary_parser",
    }



def assess_text_quality(text: str) -> dict[str, Any]:
    line_count = len(text.splitlines())
    word_count = len(re.findall(r"\b\w+\b", text))
    table_artifacts = len(QUALITY_SIGNAL_PATTERNS["table_artifacts"].findall(text))
    broken_uppercase = len(QUALITY_SIGNAL_PATTERNS["broken_uppercase"].findall(text))
    control_chars = len(QUALITY_SIGNAL_PATTERNS["control_chars"].findall(text))
    score = 1.0
    reasons: list[str] = []
    if table_artifacts > 80:
        score -= 0.25
        reasons.append("Detected many table-of-contents or dotted leader artifacts.")
    if broken_uppercase > 10:
        score -= 0.25
        reasons.append("Detected many broken uppercase letter sequences suggesting PDF layout damage.")
    if control_chars > 0:
        score -= 0.1
        reasons.append("Detected form-feed control characters from PDF extraction.")
    if word_count < 200:
        score -= 0.2
        reasons.append("Extracted text is unusually short.")
    score = max(0.0, round(score, 2))
    return {
        "score": score,
        "line_count": line_count,
        "word_count": word_count,
        "table_artifact_count": table_artifacts,
        "broken_uppercase_count": broken_uppercase,
        "control_char_count": control_chars,
        "vision_assistance_recommended": score < 0.75 or table_artifacts > 250 or control_chars > 120,
        "vision_reasons": reasons,
    }



def ingest_source_document(source: Path, destination_dir: Path) -> tuple[Path, str, dict[str, Any]]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    normalized_path = destination_dir / f"{source.stem}.normalized.md"
    if source.suffix.lower() == ".pdf":
        text = extract_pdf_text(source)
        normalized_path.write_text(text, encoding="utf-8")
    else:
        text = source.read_text(encoding="utf-8")
        normalized_path.write_text(text, encoding="utf-8")
    quality = assess_text_quality(text)
    return normalized_path, text, quality


def _compact_requirements(requirements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in requirements:
        compact.append(
            {
                "source_requirement_id": item.get("source_requirement_id", ""),
                "section": item.get("section", "General"),
                "statement": item.get("statement", ""),
                "category": item.get("category", "general"),
                "priority": item.get("priority", "informational"),
                "service": item.get("service", "general"),
            }
        )
    return compact


def _excerpt_for_llm(text: str, max_lines: int = 120, max_chars: int = 8000) -> str:
    selected: list[str] = []
    for line in text.splitlines():
        normalized = clean_statement_noise(line)
        if not normalized:
            continue
        if len(normalized) < 24:
            continue
        if normalized.startswith(("Rationale", "Description", "Profile")):
            continue
        selected.append(normalized)
        if len(selected) >= max_lines:
            break
    excerpt = "\n".join(selected)
    return excerpt[:max_chars]


ANCHOR_GROUPS = {
    "root": {"root"},
    "mfa": {"mfa", "multi", "factor", "authentication"},
    "password": {"password"},
    "access_key": {"access", "key", "keys"},
    "rotation": {"rotate", "rotation", "rotated", "days", "day"},
    "public_access": {"public", "anonymous", "internet", "公网"},
    "logging": {"log", "logs", "logging", "audit", "trail"},
    "alerting": {"alert", "alerts", "monitoring", "monitor"},
    "encryption": {"encrypt", "encrypted", "kms", "cmk", "tde"},
    "rbac": {"rbac", "role", "based"},
    "vulnerability": {"vulnerability", "scan", "security", "agent"},
}


def _anchor_hits(text: str) -> set[str]:
    tokens = overlap_tokens(text, text)
    hits: set[str] = set()
    for anchor, words in ANCHOR_GROUPS.items():
        if tokens & words:
            hits.add(anchor)
    return hits


def _anchor_compatibility(third_party_statement: str, global_statement: str) -> float:
    third_party_hits = _anchor_hits(third_party_statement)
    global_hits = _anchor_hits(global_statement)
    if not third_party_hits:
        return 0.0
    shared = third_party_hits & global_hits
    missing = third_party_hits - global_hits
    score = 0.08 * len(shared) - 0.1 * len(missing)
    if "public_access" in missing or "rotation" in missing or "root" in missing or "mfa" in missing:
        score -= 0.15
    return score


def merge_requirement_sets(
    primary: list[dict[str, Any]],
    secondary: list[dict[str, Any]],
    prefix: str,
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen_statement_keys: set[str] = set()
    seen_source_ids: set[str] = set()
    next_id = len(primary) + 1
    for item in primary + secondary:
        statement = normalize_whitespace(str(item.get("statement", "")))
        if len(statement) < 12:
            continue
        source_id = str(item.get("source_requirement_id", "")).strip()
        statement_key = re.sub(r"\W+", " ", statement.lower()).strip()
        if statement_key in seen_statement_keys:
            continue
        if source_id and source_id in seen_source_ids:
            continue
        normalized = dict(item)
        normalized["statement"] = statement
        if not normalized.get("section"):
            normalized["section"] = "General"
        if not normalized.get("category"):
            normalized["category"] = categorize_text(statement)
        if not normalized.get("priority"):
            normalized["priority"] = detect_priority(statement)
        if not normalized.get("service"):
            normalized["service"] = detect_service(statement)
        if not normalized.get("source_excerpt"):
            normalized["source_excerpt"] = statement[:280]
        if prefix == "TPS" and not is_valid_third_party_requirement(source_id or normalized.get("source_requirement_id", ""), statement):
            continue
        if prefix == "GP" and not is_valid_global_policy_requirement(statement):
            continue
        if not normalized.get("requirement_id"):
            normalized["requirement_id"] = f"{prefix}-{next_id:03d}"
            next_id += 1
        merged.append(normalized)
        seen_statement_keys.add(statement_key)
        if source_id:
            seen_source_ids.add(source_id)
    return merged


def llm_enhance_parse(
    *,
    runtime: OllamaRuntime | None,
    role: str,
    source: Path,
    text: str,
    quality: dict[str, Any],
    deterministic_requirements: list[dict[str, Any]],
    work_dir: Path,
) -> dict[str, Any]:
    result = {
        "used": False,
        "text_model_used": False,
        "vision_model_used": False,
        "notes": [],
        "added_requirements": [],
    }
    if runtime is None:
        result["notes"].append("Ollama runtime unavailable; parse stayed deterministic.")
        return result

    system_prompt = (
        "You extract security requirements from policy and standards documents. "
        "Return strict JSON with keys requirements and notes. "
        "Each requirement must contain source_requirement_id, section, statement, category, priority, service. "
        "Do not invent controls not grounded in the input."
    )
    excerpt_lines = _excerpt_for_llm(text, max_lines=90, max_chars=7000).splitlines()
    text_chunks = ["\n".join(excerpt_lines[i : i + 18]) for i in range(0, len(excerpt_lines), 18)]
    for chunk_index, excerpt in enumerate(text_chunks[:4], start=1):
        prompt_payload = {
            "document_role": role,
            "source_file": source.name,
            "quality": quality,
            "chunk_index": chunk_index,
            "existing_requirements": _compact_requirements(deterministic_requirements[:10]),
            "text_excerpt": excerpt,
        }
        user_prompt = (
            "Review the extracted text chunk and refine the requirement list. "
            "Add only missing or cleaner requirements from this chunk; do not restate every existing item.\n"
            f"{json.dumps(prompt_payload, ensure_ascii=False)}"
        )
        try:
            llm_text = runtime.chat_json(
                model=runtime.config.text_model,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                num_predict=450,
            )
            candidate_requirements = llm_text.get("requirements", [])
            if isinstance(candidate_requirements, list):
                result["added_requirements"].extend(candidate_requirements)
            notes = llm_text.get("notes", [])
            if isinstance(notes, list):
                result["notes"].extend(str(item) for item in notes if str(item).strip())
            result["used"] = True
            result["text_model_used"] = True
        except Exception as exc:
            result["notes"].append(f"Text-model parse enhancement skipped for chunk {chunk_index}: {exc}")
            break

    if quality.get("vision_assistance_recommended") and source.suffix.lower() == ".pdf":
        try:
            image_dir = work_dir / "vision_cache" / role
            image_paths = render_pdf_pages(source, image_dir, max_pages=3)
            if image_paths:
                vision_payload = {
                    "document_role": role,
                    "source_file": source.name,
                    "task": "Recover missed controls or numbering from the page images.",
                    "existing_requirements": _compact_requirements(deterministic_requirements[:20]),
                }
                vision_prompt = (
                    "Read these page images and return strict JSON with keys requirements and notes. "
                    "Each requirement must contain source_requirement_id, section, statement, category, priority, service. "
                    "Only include requirements visible in the images."
                )
                llm_vision = runtime.chat_json(
                    model=runtime.config.vision_model,
                    system_prompt=vision_prompt,
                    user_prompt=json.dumps(vision_payload, ensure_ascii=False),
                    images=image_paths,
                    num_predict=700,
                )
                candidate_requirements = llm_vision.get("requirements", [])
                if isinstance(candidate_requirements, list):
                    result["added_requirements"].extend(candidate_requirements)
                notes = llm_vision.get("notes", [])
                if isinstance(notes, list):
                    result["notes"].extend(str(item) for item in notes if str(item).strip())
                result["used"] = True
                result["vision_model_used"] = True
        except Exception as exc:
            result["notes"].append(f"Vision-model assistance skipped: {exc}")
    return result



def classify_baseline_action(match: dict[str, Any] | None) -> str:
    if match is None:
        return "new_baseline_control"
    score = float(match.get("score", 0.0))
    overlap_count = int(match.get("overlap_count", 0))
    org_item = match["requirement"]
    overlap_tokens_list = {str(token).lower() for token in match.get("overlap_tokens", [])}
    if overlap_count < 2:
        return "new_baseline_control"
    if {"monitor", "alert", "change", "changes"} & overlap_tokens_list and score < 0.65:
        return "new_baseline_control"
    if {"mfa", "multi", "factor"} & overlap_tokens_list and score < 0.6:
        return "new_baseline_control"
    if org_item.get("priority") == "mandatory" and score >= 0.58:
        return "carry_forward"
    if score >= 0.4:
        return "adapt_for_platform"
    return "new_baseline_control"



def _intent_guard_penalty(third_party_statement: str, global_statement: str) -> float:
    third = third_party_statement.lower()
    global_text = global_statement.lower()
    penalty = 0.0
    if "ssh" in third and "mfa" in global_text:
        penalty -= 0.35
    if "publicly accessible" in third and "utc" in global_text:
        penalty -= 0.45
    if "access key" in third and "access rights" in global_text:
        penalty -= 0.4
    if "rotated every 90 days" in third and "reviewed at least every 90 days" in global_text:
        penalty -= 0.35
    if "security group" in third and "log all security related events" in global_text:
        penalty -= 0.2
    if "network access rule" in third and "role based access control" in global_text:
        penalty -= 0.3
    if ("monitor" in third or "alert" in third or "changes" in third) and "retention" in global_text:
        penalty -= 0.35
    if ("monitor" in third or "alert" in third) and "monitor" not in global_text and "alert" not in global_text:
        penalty -= 0.25
    if "mfa" in third and "mfa" not in global_text and "multi-factor" not in global_text:
        penalty -= 0.2
    if "console password" in third and "api" in global_text:
        penalty -= 0.2
    if "service key" in third and "must not be used for any other customers" in global_text:
        penalty -= 0.3
    return penalty



def _score_candidate_match(third_party_item: dict[str, Any], global_item: dict[str, Any]) -> tuple[float, set[str]]:
    overlap = overlap_tokens(third_party_item["statement"], global_item["statement"])
    score = score_overlap(third_party_item["statement"], global_item["statement"])
    if third_party_item.get("category") == global_item.get("category") and overlap:
        score += 0.2
    if (
        third_party_item.get("service") != "general"
        and third_party_item.get("service", "").lower() in global_item.get("statement", "").lower()
    ):
        score += 0.1
    score += _anchor_compatibility(third_party_item["statement"], global_item["statement"])
    score += _intent_guard_penalty(third_party_item["statement"], global_item["statement"])
    return score, overlap



def choose_best_global_match(third_party_item: dict[str, Any], global_requirements: list[dict[str, Any]]) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_score = 0.0
    best_overlap: set[str] = set()
    for global_item in global_requirements:
        score, overlap = _score_candidate_match(third_party_item, global_item)
        if score > best_score:
            best_score = score
            best_match = global_item
            best_overlap = overlap
    if best_match is None or best_score < 0.2 or len(best_overlap) == 0:
        return None
    return {
        "requirement": best_match,
        "score": round(best_score, 4),
        "overlap_tokens": sorted(best_overlap),
        "overlap_count": len(best_overlap),
    }



def choose_top_global_matches(
    third_party_item: dict[str, Any],
    global_requirements: list[dict[str, Any]],
    limit: int = 3,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    for global_item in global_requirements:
        score, overlap = _score_candidate_match(third_party_item, global_item)
        if score < 0.15:
            continue
        ranked.append(
            {
                "requirement": global_item,
                "score": round(score, 4),
                "overlap_tokens": sorted(overlap),
                "overlap_count": len(overlap),
            }
        )
    ranked.sort(key=lambda item: (-item["score"], -item["overlap_count"], item["requirement"]["requirement_id"]))
    return ranked[:limit]


def llm_classify_baseline_actions(
    *,
    runtime: OllamaRuntime | None,
    global_requirements: list[dict[str, Any]],
    third_party_requirements: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    debug_chunks: list[dict[str, Any]] = []
    if runtime is None:
        return {}, [{"status": "skipped", "reason": "Ollama runtime unavailable"}]

    candidates: list[dict[str, Any]] = []
    for third_party_item in third_party_requirements:
        top_matches = choose_top_global_matches(third_party_item, global_requirements, limit=3)
        deterministic_match = top_matches[0] if top_matches else None
        candidates.append(
            {
                "third_party_requirement_id": third_party_item.get("requirement_id"),
                "third_party_source_requirement_id": third_party_item.get("source_requirement_id"),
                "third_party_statement": third_party_item.get("statement"),
                "third_party_category": third_party_item.get("category"),
                "third_party_priority": third_party_item.get("priority"),
                "third_party_service": third_party_item.get("service"),
                "candidate_matches": [
                    {
                        "matched_global_policy_requirement_id": match["requirement"]["requirement_id"],
                        "matched_global_policy_source_requirement_id": match["requirement"].get("source_requirement_id"),
                        "matched_global_policy_section": match["requirement"].get("section"),
                        "matched_global_policy_statement": match["requirement"].get("statement"),
                        "matched_global_policy_category": match["requirement"].get("category"),
                        "matched_global_policy_priority": match["requirement"].get("priority"),
                        "match_score": match["score"],
                        "overlap_tokens": match["overlap_tokens"],
                    }
                    for match in top_matches
                ],
                "deterministic_action": classify_baseline_action(deterministic_match),
            }
        )

    indexed: dict[str, dict[str, Any]] = {}
    system_prompt = (
        "You classify third-party security requirements against a global policy baseline using parser outputs. "
        "Return strict JSON only. "
        "Use one top-level key named decisions. "
        "Each decision must contain third_party_requirement_id, baseline_action, rationale, matched_global_policy_requirement_id. "
        "Allowed baseline_action values are carry_forward, adapt_for_platform, new_baseline_control."
    )
    global_theme_summary = build_theme_summary(global_requirements, "category")[:8]
    for start in range(0, len(candidates), 1):
        chunk = candidates[start : start + 1]
        debug_entry: dict[str, Any] = {
            "chunk_start": start,
            "chunk_size": len(chunk),
            "candidate_ids": [item["third_party_requirement_id"] for item in chunk],
        }
        prompt_payload = {"global_policy_themes": global_theme_summary, "candidates": chunk}
        prompt_variants = [
            (
                "Analyze the candidate using parser outputs as primary evidence. "
                "carry_forward only if the same control intent is clearly covered. "
                "adapt_for_platform only if governance intent exists but platform detail is missing. "
                "new_baseline_control if coverage is weak or service-specific. "
                "Do not map SSH exposure to MFA, key rotation to access review, or public access to UTC logging. "
                "If coverage is weak, set matched_global_policy_requirement_id to an empty string.\n"
                f"{json.dumps(prompt_payload, ensure_ascii=False)}",
                420,
            ),
            (
                "Return JSON decisions for this candidate only. Prefer new_baseline_control when uncertain.\n"
                f"{json.dumps({'candidates': chunk}, ensure_ascii=False)}",
                260,
            ),
        ]
        response = None
        errors: list[str] = []
        for attempt, (user_prompt, num_predict) in enumerate(prompt_variants, start=1):
            try:
                response = runtime.chat_json(
                    model=runtime.config.text_model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    num_predict=num_predict,
                )
                debug_entry["status"] = "ok"
                debug_entry["attempt"] = attempt
                debug_entry["response_keys"] = sorted(response.keys()) if isinstance(response, dict) else []
                break
            except Exception as exc:
                errors.append(str(exc))
        if response is None:
            debug_entry["status"] = "error"
            debug_entry["error"] = " | ".join(errors)
            debug_chunks.append(debug_entry)
            continue
        decisions = response.get("decisions", [])
        if not isinstance(decisions, list):
            debug_entry["status"] = "invalid"
            debug_entry["reason"] = "Response missing decisions list"
            debug_chunks.append(debug_entry)
            continue
        debug_entry["decision_count"] = len(decisions)
        for item in decisions:
            requirement_id = str(item.get("third_party_requirement_id", "")).strip()
            action = str(item.get("baseline_action", "")).strip()
            if requirement_id and action in {"carry_forward", "adapt_for_platform", "new_baseline_control"}:
                indexed[requirement_id] = {
                    "baseline_action": action,
                    "rationale": str(item.get("rationale", "")).strip(),
                    "matched_global_policy_requirement_id": str(item.get("matched_global_policy_requirement_id", "")).strip(),
                }
        debug_chunks.append(debug_entry)
    return indexed, debug_chunks
