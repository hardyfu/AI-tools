import argparse
import re
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.ollama_runtime import build_ollama_runtime
from runtime.text_utils import clean_statement_noise, load_json, write_json


DOMAIN_TITLES = {
    "identity": "Identity and Access Management",
    "logging": "Logging and Monitoring",
    "network": "Network Security",
    "encryption": "Encryption and Key Management",
    "data protection": "Data Protection",
    "general": "General Platform Security",
}

SHEET_ORDER = [
    "Summary",
    "Document Sections",
    "Control Mapping",
    "Pending Controls",
    "Organizational Only",
    "Recommendations CN",
]

SECTION_FIELDS = ["title", "purpose", "scope", "principles", "governance", "domain_overviews"]


def _bucket(mapping: list[dict[str, Any]], decision: str) -> list[dict[str, Any]]:
    return [item for item in mapping if item.get("decision") == decision]


def _title(category: str) -> str:
    return DOMAIN_TITLES.get(category, "Other Controls")


def _render_trace(item: dict[str, Any]) -> str:
    trace: list[str] = []
    matched = item.get("matched_global_policy_requirement")
    benchmark = item.get("third_party_requirement", {})
    if matched:
        trace.append(str(matched.get("source_requirement_id") or matched.get("requirement_id") or "").strip())
    trace.append(str(benchmark.get("source_requirement_id") or benchmark.get("requirement_id") or "").strip())
    trace = [value for value in trace if value]
    return ", ".join(trace)


def _normalize_text_list(value: Any) -> list[str]:
    if isinstance(value, str):
        cleaned = clean_statement_noise(value)
        return [cleaned] if cleaned else []
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    char_buffer: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        candidate = clean_statement_noise(item)
        if not candidate:
            continue
        if len(candidate) == 1:
            char_buffer.append(candidate)
            continue
        if char_buffer:
            merged = clean_statement_noise("".join(char_buffer))
            if merged:
                normalized.append(merged)
            char_buffer = []
        normalized.append(candidate)
    if char_buffer:
        merged = clean_statement_noise("".join(char_buffer))
        if merged:
            normalized.append(merged)
    return normalized


def _join_lines(lines: list[str]) -> str:
    return "\n".join(line for line in lines if line).strip()


def _group_active_controls(analysis: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in analysis.get("baseline_mapping", []):
        if item.get("decision") == "gap":
            continue
        category = item.get("third_party_requirement", {}).get("category", "general")
        grouped.setdefault(category, []).append(item)
    return grouped


def _validate_final_payload(payload: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in SECTION_FIELDS if field not in payload]
    if missing:
        raise RuntimeError(f"LLM finalization output missing fields: {', '.join(missing)}")

    title = clean_statement_noise(str(payload.get("title", "")).strip()) or "Alibaba Cloud Security Baseline Final"
    normalized = {
        "title": title,
        "purpose": _normalize_text_list(payload.get("purpose", [])),
        "scope": _normalize_text_list(payload.get("scope", [])),
        "principles": _normalize_text_list(payload.get("principles", [])),
        "governance": _normalize_text_list(payload.get("governance", [])),
        "domain_overviews": [],
    }
    if not all(normalized[key] for key in ("purpose", "scope", "principles", "governance")):
        raise RuntimeError("LLM finalization output must provide non-empty purpose, scope, principles, and governance sections.")

    domain_overviews = payload.get("domain_overviews", [])
    if not isinstance(domain_overviews, list) or not domain_overviews:
        raise RuntimeError("LLM finalization output must provide at least one domain overview.")
    for item in domain_overviews:
        if not isinstance(item, dict):
            continue
        domain = clean_statement_noise(str(item.get("domain", "")).strip())
        summary = clean_statement_noise(str(item.get("summary", "")).strip())
        if domain and summary:
            normalized["domain_overviews"].append({"domain": domain, "summary": summary})
    if not normalized["domain_overviews"]:
        raise RuntimeError("LLM finalization output did not contain usable domain_overviews.")
    return normalized


def _set_sheet_style(sheet: Any, widths: list[tuple[str, float]]) -> None:
    header_fill = PatternFill("solid", start_color="D9EAF7", end_color="D9EAF7")
    for cell in sheet[1]:
        cell.font = Font(name="Arial", bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.font = Font(name="Arial")
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for column, width in widths:
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"


def _markdown_lines_to_rows(text: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    current_section = "General"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_section = clean_statement_noise(line.lstrip("#").strip()) or current_section
            continue
        if line.startswith("-"):
            content = clean_statement_noise(line[1:].strip())
        else:
            content = clean_statement_noise(line)
        if content:
            rows.append((current_section, content))
    return rows


def _build_workbook(
    output_path: Path,
    *,
    case_name: str,
    final_payload: dict[str, Any],
    analysis: dict[str, Any],
    recommendations_text: str,
    finalization_model: str,
    runtime_status: dict[str, Any],
    used_llm: bool,
) -> None:
    workbook = Workbook()
    workbook.remove(workbook.active)

    summary_sheet = workbook.create_sheet("Summary")
    summary_sheet.append(["Field", "Value"])
    summary_sheet_rows = [
        ("case_name", case_name),
        ("document_title", final_payload["title"]),
        ("target_platform", "Alibaba Cloud"),
        ("finalization_model", finalization_model),
        ("carry_forward_count", analysis["summary"]["carry_forward"]),
        ("adapt_for_platform_count", analysis["summary"]["adapt_for_platform"]),
        ("new_baseline_control_count", analysis["summary"]["new_baseline_control"]),
        ("organizational_only_count", analysis["summary"]["global_policy_only"]),
        ("llm_used", str(bool(used_llm))),
        ("provider", runtime_status.get("provider", "unknown")),
    ]
    for row in summary_sheet_rows:
        summary_sheet.append(list(row))
    _set_sheet_style(summary_sheet, [("A", 28), ("B", 90)])

    sections_sheet = workbook.create_sheet("Document Sections")
    sections_sheet.append(["Section", "Content"])
    sections_sheet.append(["Title", final_payload["title"]])
    sections_sheet.append(["Purpose", _join_lines(final_payload["purpose"])])
    sections_sheet.append(["Scope", _join_lines(final_payload["scope"])])
    sections_sheet.append(["Principles", _join_lines(final_payload["principles"])])
    sections_sheet.append(["Governance", _join_lines(final_payload["governance"])])
    for item in final_payload["domain_overviews"]:
        sections_sheet.append([f"Domain Overview: {item['domain']}", item["summary"]])
    _set_sheet_style(sections_sheet, [("A", 30), ("B", 120)])

    mapping_sheet = workbook.create_sheet("Control Mapping")
    mapping_sheet.append([
        "Domain",
        "Baseline Action",
        "Decision",
        "Benchmark Requirement ID",
        "Benchmark Source Requirement ID",
        "Benchmark Section",
        "Benchmark Statement",
        "Benchmark Category",
        "Benchmark Service",
        "Matched Global Requirement ID",
        "Matched Global Source Requirement ID",
        "Matched Global Section",
        "Matched Global Statement",
        "Match Score",
        "Trace",
        "Rationale",
    ])
    for item in analysis.get("baseline_mapping", []):
        benchmark = item.get("third_party_requirement", {})
        matched = item.get("matched_global_policy_requirement", {})
        mapping_sheet.append([
            _title(str(benchmark.get("category", "general"))),
            item.get("baseline_action", ""),
            item.get("decision", ""),
            benchmark.get("requirement_id", ""),
            benchmark.get("source_requirement_id", ""),
            benchmark.get("section", ""),
            clean_statement_noise(str(benchmark.get("statement", ""))),
            benchmark.get("category", ""),
            benchmark.get("service", ""),
            matched.get("requirement_id", ""),
            matched.get("source_requirement_id", ""),
            matched.get("section", ""),
            clean_statement_noise(str(matched.get("statement", ""))),
            item.get("match_score", ""),
            _render_trace(item),
            clean_statement_noise(str(item.get("rationale", ""))),
        ])
    _set_sheet_style(
        mapping_sheet,
        [("A", 26), ("B", 20), ("C", 16), ("D", 18), ("E", 22), ("F", 24), ("G", 56), ("H", 18),
         ("I", 18), ("J", 18), ("K", 22), ("L", 24), ("M", 56), ("N", 12), ("O", 24), ("P", 48)],
    )

    pending_sheet = workbook.create_sheet("Pending Controls")
    pending_sheet.append([
        "Benchmark Requirement ID",
        "Benchmark Source Requirement ID",
        "Benchmark Section",
        "Benchmark Statement",
        "Benchmark Category",
        "Benchmark Service",
        "Rationale",
    ])
    for item in _bucket(analysis.get("baseline_mapping", []), "gap"):
        benchmark = item.get("third_party_requirement", {})
        pending_sheet.append([
            benchmark.get("requirement_id", ""),
            benchmark.get("source_requirement_id", ""),
            benchmark.get("section", ""),
            clean_statement_noise(str(benchmark.get("statement", ""))),
            benchmark.get("category", ""),
            benchmark.get("service", ""),
            clean_statement_noise(str(item.get("rationale", ""))),
        ])
    _set_sheet_style(pending_sheet, [("A", 18), ("B", 22), ("C", 24), ("D", 68), ("E", 18), ("F", 18), ("G", 48)])

    org_only_sheet = workbook.create_sheet("Organizational Only")
    org_only_sheet.append([
        "Global Requirement ID",
        "Global Source Requirement ID",
        "Global Section",
        "Global Statement",
        "Category",
        "Priority",
    ])
    for item in analysis.get("global_policy_only_requirements", []):
        org_only_sheet.append([
            item.get("requirement_id", ""),
            item.get("source_requirement_id", ""),
            item.get("section", ""),
            clean_statement_noise(str(item.get("statement", ""))),
            item.get("category", ""),
            item.get("priority", ""),
        ])
    _set_sheet_style(org_only_sheet, [("A", 18), ("B", 22), ("C", 24), ("D", 68), ("E", 18), ("F", 12)])

    rec_sheet = workbook.create_sheet("Recommendations CN")
    rec_sheet.append(["Section", "Content"])
    for row in _markdown_lines_to_rows(recommendations_text):
        rec_sheet.append(list(row))
    _set_sheet_style(rec_sheet, [("A", 30), ("B", 110)])

    if workbook.sheetnames != SHEET_ORDER:
        raise RuntimeError(f"Workbook schema mismatch. Expected sheets: {', '.join(SHEET_ORDER)}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)


def validate_workbook(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing final workbook: {path}")
    workbook = load_workbook(path, read_only=True)
    if workbook.sheetnames != SHEET_ORDER:
        raise RuntimeError(f"Workbook schema mismatch. Expected sheets: {', '.join(SHEET_ORDER)}, got {', '.join(workbook.sheetnames)}")
    expected_headers = {
        "Summary": ["Field", "Value"],
        "Document Sections": ["Section", "Content"],
        "Control Mapping": [
            "Domain",
            "Baseline Action",
            "Decision",
            "Benchmark Requirement ID",
            "Benchmark Source Requirement ID",
            "Benchmark Section",
            "Benchmark Statement",
            "Benchmark Category",
            "Benchmark Service",
            "Matched Global Requirement ID",
            "Matched Global Source Requirement ID",
            "Matched Global Section",
            "Matched Global Statement",
            "Match Score",
            "Trace",
            "Rationale",
        ],
        "Pending Controls": [
            "Benchmark Requirement ID",
            "Benchmark Source Requirement ID",
            "Benchmark Section",
            "Benchmark Statement",
            "Benchmark Category",
            "Benchmark Service",
            "Rationale",
        ],
        "Organizational Only": [
            "Global Requirement ID",
            "Global Source Requirement ID",
            "Global Section",
            "Global Statement",
            "Category",
            "Priority",
        ],
        "Recommendations CN": ["Section", "Content"],
    }
    for sheet_name, headers in expected_headers.items():
        sheet = workbook[sheet_name]
        actual = list(next(sheet.iter_rows(min_row=1, max_row=1, values_only=True)))
        if actual != headers:
            raise RuntimeError(f"Workbook sheet {sheet_name} header mismatch. Expected {headers}, got {actual}")


def run(case_name: str) -> tuple[Path, Path]:
    working_dir = PROJECT_ROOT / "cases" / case_name / "working"
    profile_path = working_dir / "project_profile.json"
    analysis_path = working_dir / "baseline_analysis.json"
    controls_path = working_dir / "baseline_controls.md"
    report_path = working_dir / "baseline_report.md"
    recommendations_path = working_dir / "baseline_priority_recommendations_cn.md"
    for required in (profile_path, analysis_path, controls_path, report_path, recommendations_path):
        if not required.exists():
            raise FileNotFoundError(f"Missing skill03 input artifact: {required}")

    profile = load_json(profile_path)
    analysis = load_json(analysis_path)
    controls_text = controls_path.read_text(encoding="utf-8")
    report_text = report_path.read_text(encoding="utf-8")
    recommendations_text = recommendations_path.read_text(encoding="utf-8")

    runtime, runtime_status = build_ollama_runtime(profile)
    dashscope = profile.get("model_runtime", {}).get("dashscope", {})
    finalization_model = str(dashscope.get("finalization_model", "qwen3-max"))

    used_llm = False
    fallback_reason = ""
    if runtime is None:
        fallback_reason = f"DashScope runtime unavailable: {runtime_status.get('skip_reason')}"
        debug_path = working_dir / "skill03_debug.json"
        write_json(
            debug_path,
            {
                "case_name": case_name,
                "provider": runtime_status.get("provider", "unknown"),
                "available": bool(runtime_status.get("available", False)),
                "finalization_model": finalization_model,
                "used_llm": False,
                "fallback_reason": fallback_reason,
                "source_artifacts": {
                    "baseline_analysis": str(analysis_path.relative_to(PROJECT_ROOT)),
                    "baseline_controls": str(controls_path.relative_to(PROJECT_ROOT)),
                    "baseline_report": str(report_path.relative_to(PROJECT_ROOT)),
                    "priority_recommendations_cn": str(recommendations_path.relative_to(PROJECT_ROOT)),
                },
            },
        )
        raise RuntimeError(f"skill03 requires LLM runtime, but it is unavailable: {runtime_status.get('skip_reason')}")

    system_prompt = (
        "You are an enterprise cloud security standards editor. "
        "Produce a formal, review-ready English baseline document structure from the approved baseline analysis. "
        "Do not redo the mapping analysis. Do not convert gap or deferred controls into covered controls. "
        "Return JSON only. Do not return Markdown or commentary."
    )
    user_prompt = (
        "Generate the JSON structure for a formal English document titled 'Alibaba Cloud Security Baseline Final'.\n"
        "Requirements:\n"
        "1. The JSON fields must be: title, purpose, scope, principles, governance, domain_overviews.\n"
        "2. domain_overviews must be an array of objects with fields: domain, summary.\n"
        "3. Write only document-level formal wording and domain summaries. Do not rewrite each control and do not emit pending control details.\n"
        "4. Control details will be rendered locally. Your job is to provide formal English section wording and domain overviews.\n"
        "5. Use concise, formal English. Avoid parser noise.\n\n"
        f"[baseline_analysis.json]\n{analysis}\n\n"
        f"[baseline_controls.md]\n{controls_text[:12000]}\n\n"
        f"[baseline_report.md]\n{report_text[:8000]}\n\n"
        f"[baseline_priority_recommendations_cn.md]\n{recommendations_text[:8000]}"
    )

    try:
        final_payload_raw = runtime.chat_json(
            model=finalization_model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            num_predict=2200,
        )
        final_payload = _validate_final_payload(final_payload_raw)
        used_llm = True
    except Exception as exc:
        fallback_reason = str(exc)
        debug_path = working_dir / "skill03_debug.json"
        write_json(
            debug_path,
            {
                "case_name": case_name,
                "provider": runtime_status.get("provider", "unknown"),
                "available": bool(runtime_status.get("available", False)),
                "finalization_model": finalization_model,
                "used_llm": False,
                "fallback_reason": fallback_reason,
                "source_artifacts": {
                    "baseline_analysis": str(analysis_path.relative_to(PROJECT_ROOT)),
                    "baseline_controls": str(controls_path.relative_to(PROJECT_ROOT)),
                    "baseline_report": str(report_path.relative_to(PROJECT_ROOT)),
                    "priority_recommendations_cn": str(recommendations_path.relative_to(PROJECT_ROOT)),
                },
            },
        )
        raise RuntimeError(f"skill03 requires usable LLM output, but finalization failed: {fallback_reason}")

    output_path = working_dir / "final_baseline.xlsx"
    _build_workbook(
        output_path,
        case_name=case_name,
        final_payload=final_payload,
        analysis=analysis,
        recommendations_text=recommendations_text,
        finalization_model=finalization_model,
        runtime_status=runtime_status,
        used_llm=used_llm,
    )

    debug_path = working_dir / "skill03_debug.json"
    write_json(
        debug_path,
        {
            "case_name": case_name,
            "provider": runtime_status.get("provider", "unknown"),
            "available": bool(runtime_status.get("available", False)),
            "finalization_model": finalization_model,
            "used_llm": used_llm,
            "fallback_reason": fallback_reason,
            "source_artifacts": {
                "baseline_analysis": str(analysis_path.relative_to(PROJECT_ROOT)),
                "baseline_controls": str(controls_path.relative_to(PROJECT_ROOT)),
                "baseline_report": str(report_path.relative_to(PROJECT_ROOT)),
                "priority_recommendations_cn": str(recommendations_path.relative_to(PROJECT_ROOT)),
                "final_baseline_xlsx": str(output_path.relative_to(PROJECT_ROOT)),
            },
        },
    )
    return output_path, debug_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run skill03 baseline finalization")
    parser.add_argument("--case", required=True, dest="case_name")
    args = parser.parse_args()
    try:
        outputs = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
