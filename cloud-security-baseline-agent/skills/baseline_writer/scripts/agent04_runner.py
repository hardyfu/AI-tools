import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)

from runtime.text_utils import clean_statement_noise, load_json


P0_IDS = {
    "1.1", "1.2", "1.3", "1.4", "1.15", "1.16",
    "3.2", "3.5", "5.1", "5.2", "5.4", "5.7",
    "6.1", "6.2", "6.5",
    "7.5", "7.6", "7.7", "7.9",
    "8.1", "8.5", "8.7",
}
P1_IDS = {
    "1.5", "1.7", "1.8", "1.9", "1.10", "1.11", "1.12", "1.13", "1.14",
    "2.4", "2.5", "2.23",
    "3.1", "3.3", "3.4",
    "4.1", "4.3", "4.4", "4.5",
    "5.3", "5.5", "5.6", "5.8", "5.9",
    "6.3", "6.4", "6.6", "6.7", "6.8", "6.9",
    "7.1", "7.2", "7.4", "7.8",
    "8.3", "8.4", "8.6",
}



def build_control_item(index: int, mapping_item: dict[str, Any]) -> str:
    benchmark = mapping_item["benchmark_requirement"]
    matched = mapping_item.get("matched_organizational_requirement")
    decision = mapping_item["decision"]
    if decision == "aligned":
        action = "adopted"
        rationale = "Organizational standard already covers this CIS expectation."
    elif decision == "partial":
        action = "adapted"
        rationale = "Organizational direction exists, but CIS provides a stronger or more explicit benchmark expression."
    else:
        action = "deferred"
        rationale = "No explicit organizational requirement match. Review with control owners before adoption."

    lines = [
        f"### BL-{index:03d} {benchmark['category']} / {benchmark['service']}",
        f"- Decision: {action}",
        f"- Benchmark source: {benchmark['requirement_id']}",
        f"- Benchmark statement: {clean_statement_noise(benchmark['statement'])}",
        f"- Organizational trace: {matched['requirement_id'] if matched else 'none'}",
        f"- Rationale: {rationale}",
    ]
    if matched:
        lines.append(f"- Organization statement: {clean_statement_noise(matched['statement'])}")
    return "\n".join(lines)



def build_report(case_name: str, analysis: dict[str, Any], org_data: dict[str, Any], benchmark_data: dict[str, Any]) -> str:
    summary = analysis["summary"]
    mapping = analysis.get("mapping", [])
    gap_items = [item for item in mapping if item["decision"] == "gap"]
    partial_items = [item for item in mapping if item["decision"] == "partial"]
    gap_by_category = Counter(item["benchmark_requirement"].get("category", "general") for item in gap_items)
    top_gap_lines = "\n".join(
        f"- {item['benchmark_requirement']['source_requirement_id']} {clean_statement_noise(item['benchmark_requirement']['statement'])}"
        for item in gap_items[:10]
    ) or "- None"
    gap_area_lines = "\n".join(
        f"- {category}: {count}"
        for category, count in gap_by_category.most_common(8)
    ) or "- None"
    partial_lines = "\n".join(
        f"- {item['benchmark_requirement']['source_requirement_id']} {clean_statement_noise(item['benchmark_requirement']['statement'])}"
        for item in partial_items[:10]
    ) or "- None"
    return (
        "# Baseline Report\n\n"
        "## Executive Summary\n"
        f"The {case_name} case produced an Alibaba Cloud baseline by comparing the organizational cloud security standard against the CIS Alibaba Cloud Foundations Benchmark. "
        f"This run uses conservative matching to avoid overstating coverage. Aligned items: {summary['aligned']}; partial items: {summary['partial']}; benchmark gaps: {summary['gap']}; organization-only items: {summary['organization_only']}.\n\n"
        "## Inputs Reviewed\n"
        f"- Organization policy files: {', '.join(org_data.get('source_files', [])) or 'none'}\n"
        f"- CIS benchmark files: {', '.join(benchmark_data.get('source_files', [])) or 'none'}\n\n"
        "## Method\n"
        "- Parse organization policy into structured requirements and strategy themes.\n"
        "- Parse CIS Alibaba Cloud benchmark into structured benchmark requirements.\n"
        "- Match by category and keyword overlap.\n"
        "- Apply conservative thresholds so generic governance requirements do not automatically satisfy service-specific CIS controls.\n"
        "- Convert mapping results into adopted, adapted, and deferred baseline controls.\n\n"
        "## Key Alignment Findings\n"
        f"- Strongest organizational theme: {org_data.get('strategy_signals', [{}])[0].get('theme', 'unknown')}\n"
        f"- Strongest benchmark theme: {benchmark_data.get('benchmark_themes', [{}])[0].get('theme', 'unknown')}\n"
        "- The organizational standard strongly covers governance-level logging, encryption, and workload hardening requirements.\n"
        "- The largest remaining gaps are Alibaba Cloud-specific IAM password policy controls and service-specific configuration controls.\n\n"
        "## Baseline Summary\n"
        f"- Adopted controls: {summary['aligned']}\n"
        f"- Adapted controls: {summary['partial']}\n"
        f"- Deferred controls: {summary['gap']}\n\n"
        "## Major Gap Areas\n"
        f"{gap_area_lines}\n\n"
        "## Representative Gaps\n"
        f"{top_gap_lines}\n\n"
        "## Representative Partial Matches\n"
        f"{partial_lines}\n\n"
        "## Residual Gaps\n"
        "- PDF table extraction still leaves some broken words and mixed explanatory text in the organizational source artifact.\n"
        "- Benchmark gaps need human review before being treated as mandatory internal controls.\n"
        "- Some gaps may be covered operationally outside the standard, but that evidence is not in the current source documents.\n\n"
        "## Next Actions\n"
        "- Review gap items with cloud platform engineering and IAM owners first.\n"
        "- Decide which Alibaba Cloud-specific CIS controls should be adopted into the internal baseline versus handled as platform exceptions.\n"
        "- Refine source documents into markdown with stable headings and bullets for better extraction quality.\n"
    )


def classify_priority(source_requirement_id: str) -> str:
    if source_requirement_id in P0_IDS:
        return "P0"
    if source_requirement_id in P1_IDS:
        return "P1"
    return "P2"


def build_cn_recommendations(case_name: str, analysis: dict[str, Any]) -> str:
    mapping = analysis.get("mapping", [])
    gaps = [item for item in mapping if item["decision"] == "gap"]
    partials = [item for item in mapping if item["decision"] == "partial"]
    grouped: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": []}
    for item in gaps:
        grouped[classify_priority(item["benchmark_requirement"]["source_requirement_id"])].append(item)

    def render_group(items: list[dict[str, Any]]) -> str:
        if not items:
            return "- 无\n"
        lines: list[str] = []
        for item in items:
            req = item["benchmark_requirement"]
            lines.append(f"- `{req['source_requirement_id']}` {clean_statement_noise(req['statement'])}")
        return "\n".join(lines) + "\n"

    partial_lines = "\n".join(
        f"- `{item['benchmark_requirement']['source_requirement_id']}` {clean_statement_noise(item['benchmark_requirement']['statement'])}"
        for item in partials[:15]
    ) or "- 无"

    return (
        "# Alibaba Cloud Baseline 优先级建议\n\n"
        "## 结论\n"
        f"- Case: {case_name}\n"
        f"- 当前 conservative 分析结果：aligned {analysis['summary']['aligned']}，partial {analysis['summary']['partial']}，gap {analysis['summary']['gap']}。\n"
        "- 建议不要把全部 CIS 项直接等同为内部强制基线，而是分层纳管。\n"
        "- P0 为应优先纳入的高价值控制；P1 为应尽快补齐的服务级控制；P2 为结合实际云服务范围决定是否纳入的控制。\n\n"
        "## P0 应优先纳入 Internal Baseline\n"
        f"{render_group(grouped['P0'])}\n"
        "## P1 应在后续版本补齐\n"
        f"{render_group(grouped['P1'])}\n"
        "## P2 可按平台范围和实际服务使用情况决定\n"
        f"{render_group(grouped['P2'])}\n"
        "## Partial 项处理建议\n"
        f"{partial_lines}\n\n"
        "## 建议动作\n"
        "- 先由 IAM 与 Cloud Platform Owner 审核 P0 项，确认直接纳入 Alibaba Cloud baseline。\n"
        "- P1 项按域拆分给平台团队：日志、网络、OSS、RDS、ACK、安全中心。\n"
        "- Partial 项不要视为已覆盖，应补平台级实现标准、配置基线或检测规则。\n"
    )



def run(case_name: str) -> tuple[Path, Path, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    org_path = working_dir / "organizational_requirements.json"
    benchmark_path = working_dir / "benchmark_requirements.json"
    analysis_path = working_dir / "mapping_analysis.json"
    controls_path = working_dir / "baseline_controls.md"
    report_path = working_dir / "baseline_report.md"
    recommendations_cn_path = working_dir / "baseline_priority_recommendations_cn.md"

    org_data = load_json(org_path)
    benchmark_data = load_json(benchmark_path)
    analysis = load_json(analysis_path)

    mapping = analysis.get("mapping", [])
    adopted = [item for item in mapping if item["decision"] == "aligned"]
    adapted = [item for item in mapping if item["decision"] == "partial"]
    deferred = [item for item in mapping if item["decision"] == "gap"]

    control_lines = [
        "# Baseline Controls",
        "",
        "## Baseline Metadata",
        f"- Case: {case_name}",
        "- Scope: Alibaba Cloud",
        "- Source strategy: cloud security standard",
        "- Source benchmark: CIS Alibaba Cloud Foundations Benchmark",
        "",
        "## Control List",
    ]
    for index, item in enumerate(adopted + adapted + deferred, start=1):
        control_lines.append(build_control_item(index, item))
        control_lines.append("")
    control_lines.extend(["## Deferred Items"])
    if deferred:
        control_lines.extend(
            f"- {item['benchmark_requirement']['requirement_id']}: {clean_statement_noise(item['benchmark_requirement']['statement'])}"
            for item in deferred
        )
    else:
        control_lines.append("- None")

    controls_path.write_text("\n".join(control_lines) + "\n", encoding="utf-8")
    report_path.write_text(build_report(case_name, analysis, org_data, benchmark_data), encoding="utf-8")
    recommendations_cn_path.write_text(build_cn_recommendations(case_name, analysis), encoding="utf-8")
    return controls_path, report_path, recommendations_cn_path



def main() -> int:
    parser = argparse.ArgumentParser(description="Write baseline controls and report")
    parser.add_argument("--case", required=True, dest="case_name")
    args = parser.parse_args()
    try:
        controls_path, report_path, recommendations_cn_path = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(controls_path)
    print(report_path)
    print(recommendations_cn_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
