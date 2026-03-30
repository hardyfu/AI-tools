import argparse
from collections import Counter
from pathlib import Path
from typing import Any

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)

from runtime.text_utils import clean_statement_noise, load_json


def _render_global_refs(refs: list[dict[str, Any]]) -> str:
    if not refs:
        return "none"
    parts: list[str] = []
    for item in refs:
        source_id = str(item.get("global_source_requirement_id") or item.get("global_requirement_id") or "").strip()
        statement = clean_statement_noise(str(item.get("global_statement", "")))
        if source_id and statement:
            parts.append(f"{source_id}: {statement}")
        elif source_id:
            parts.append(source_id)
    return "; ".join(parts) if parts else "none"


def build_control_item(index: int, candidate: dict[str, Any]) -> str:
    lines = [
        f"### BL-{index:03d} {candidate.get('category', 'general')} / {candidate.get('service', 'general')}",
        f"- Source benchmark: {candidate.get('source_benchmark_requirement_id', '')}",
        f"- Benchmark source requirement: {candidate.get('source_benchmark_source_requirement_id', '')}",
        f"- Candidate priority: {candidate.get('candidate_priority', '')}",
        f"- Extension type: {candidate.get('extension_type', '')}",
        f"- Proposed control: {clean_statement_noise(str(candidate.get('proposed_control_statement', '')))}",
        f"- Related Global Standard requirements: {_render_global_refs(candidate.get('related_global_requirements', []))}",
        f"- Inclusion rationale: {clean_statement_noise(str(candidate.get('reason_for_inclusion', '')))}",
    ]
    return "\n".join(lines)


def build_report(
    case_name: str,
    org_data: dict[str, Any],
    benchmark_data: dict[str, Any],
    standard_coverage: dict[str, Any],
    benchmark_extensions: dict[str, Any],
    baseline_candidates: dict[str, Any],
) -> str:
    coverage_summary = standard_coverage.get("summary", {})
    extension_summary = benchmark_extensions.get("summary", {})
    candidate_summary = baseline_candidates.get("summary", {})
    coverage_rows = standard_coverage.get("rows", [])
    extension_rows = benchmark_extensions.get("rows", [])
    candidate_rows = baseline_candidates.get("rows", [])

    uncovered_examples = "\n".join(
        f"- {row['global_source_requirement_id']} {clean_statement_noise(row['global_statement'])}"
        for row in coverage_rows
        if row.get("coverage_status") == "not_addressed_by_benchmark"
    ) or "- None"
    uncovered_examples = "\n".join(uncovered_examples.splitlines()[:10])

    org_specific_examples = "\n".join(
        f"- {row['global_source_requirement_id']} {clean_statement_noise(row['global_statement'])}"
        for row in coverage_rows
        if row.get("coverage_status") == "organization_specific"
    ) or "- None"
    org_specific_examples = "\n".join(org_specific_examples.splitlines()[:10])

    extension_by_type = Counter(row.get("extension_type", "unknown") for row in extension_rows)
    extension_lines = "\n".join(
        f"- {kind}: {count}"
        for kind, count in extension_by_type.most_common()
    ) or "- None"

    candidate_lines = "\n".join(
        f"- {row['source_benchmark_source_requirement_id']} {clean_statement_noise(row['proposed_control_statement'])}"
        for row in candidate_rows[:12]
    ) or "- None"

    return (
        "# Baseline Report\n\n"
        "## Executive Summary\n"
        f"The {case_name} case evaluated how the Global Standard is reflected in the benchmark and where the benchmark extends beyond the current Global Standard. "
        f"Covered Global Standard requirements: {coverage_summary.get('covered', 0)}; partially covered: {coverage_summary.get('partially_covered', 0)}; "
        f"not addressed by benchmark: {coverage_summary.get('not_addressed_by_benchmark', 0)}; organization-specific: {coverage_summary.get('organization_specific', 0)}. "
        f"Benchmark extensions identified: {extension_summary.get('total_extensions', 0)}; baseline candidates created: {candidate_summary.get('total_candidates', 0)}.\n\n"
        "## Inputs Reviewed\n"
        f"- Global Policy files: {', '.join(org_data.get('source_files', [])) or 'none'}\n"
        f"- Third-Party Standard files: {', '.join(benchmark_data.get('source_files', [])) or 'none'}\n\n"
        "## Method\n"
        "- Parse the Global Policy into structured requirements.\n"
        "- Parse the Third-Party Standard into structured benchmark requirements.\n"
        "- Evaluate which Global Standard requirements are represented in the benchmark.\n"
        "- Identify benchmark controls that introduce platform-specific, stronger, or entirely new control content.\n"
        "- Promote benchmark extensions into baseline candidates for Alibaba Cloud implementation review.\n\n"
        "## Standard Coverage Summary\n"
        f"- Covered: {coverage_summary.get('covered', 0)}\n"
        f"- Partially covered: {coverage_summary.get('partially_covered', 0)}\n"
        f"- Not addressed by benchmark: {coverage_summary.get('not_addressed_by_benchmark', 0)}\n"
        f"- Organization-specific: {coverage_summary.get('organization_specific', 0)}\n\n"
        "## Global Standard Requirements Not Addressed By Benchmark\n"
        f"{uncovered_examples}\n\n"
        "## Organization-Specific Requirements\n"
        f"{org_specific_examples}\n\n"
        "## Benchmark Extension Summary\n"
        f"{extension_lines}\n\n"
        "## Candidate Controls For Baseline Inclusion\n"
        f"{candidate_lines}\n\n"
        "## Next Actions\n"
        "- Review organization-specific requirements to confirm they should remain outside the cloud benchmark mapping scope.\n"
        "- Review baseline candidates with Cloud Platform Engineering and IAM owners.\n"
        "- Separate benchmark extensions that are reference-only from those that must become mandatory platform controls.\n"
    )


def build_cn_recommendations(
    case_name: str,
    standard_coverage: dict[str, Any],
    benchmark_extensions: dict[str, Any],
    baseline_candidates: dict[str, Any],
) -> str:
    coverage_summary = standard_coverage.get("summary", {})
    extension_summary = benchmark_extensions.get("summary", {})
    candidate_summary = baseline_candidates.get("summary", {})
    candidate_rows = baseline_candidates.get("rows", [])

    grouped: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": []}
    for row in candidate_rows:
        grouped.setdefault(str(row.get("candidate_priority", "P2")), []).append(row)

    def render_group(items: list[dict[str, Any]]) -> str:
        if not items:
            return "- 无\n"
        lines = [
            f"- `{row['source_benchmark_source_requirement_id']}` {clean_statement_noise(row['proposed_control_statement'])}"
            for row in items
        ]
        return "\n".join(lines) + "\n"

    org_specific_lines = "\n".join(
        f"- `{row['global_source_requirement_id']}` {clean_statement_noise(row['global_statement'])}"
        for row in standard_coverage.get("rows", [])
        if row.get("coverage_status") == "organization_specific"
    ) or "- 无"
    org_specific_lines = "\n".join(org_specific_lines.splitlines()[:10])

    return (
        "# Alibaba Cloud Baseline 优先级建议\n\n"
        "## 结论\n"
        f"- Case: {case_name}\n"
        f"- Global Standard 覆盖情况：covered {coverage_summary.get('covered', 0)}，partially covered {coverage_summary.get('partially_covered', 0)}，"
        f"not addressed by benchmark {coverage_summary.get('not_addressed_by_benchmark', 0)}，organization specific {coverage_summary.get('organization_specific', 0)}。\n"
        f"- benchmark 扩展项数量：{extension_summary.get('total_extensions', 0)}；当前生成 baseline candidates：{candidate_summary.get('total_candidates', 0)}。\n"
        "- 建议不要把全部 benchmark 扩展项直接视为内部强制基线，而应先区分组织特有要求、平台细化要求和新增控制领域。\n\n"
        "## P0 应优先评审并纳入候选基线\n"
        f"{render_group(grouped.get('P0', []))}\n"
        "## P1 应由平台团队评估是否纳入后续版本\n"
        f"{render_group(grouped.get('P1', []))}\n"
        "## P2 可按服务实际使用范围决定\n"
        f"{render_group(grouped.get('P2', []))}\n"
        "## 组织特有要求\n"
        f"{org_specific_lines}\n\n"
        "## 建议动作\n"
        "- 先由云平台团队确认 P0 candidates 是否应进入 Alibaba Cloud baseline。\n"
        "- 对 benchmark_extensions 中的 platform_specific_detail 项，优先补齐平台级实施标准。\n"
        "- 对 organization_specific 项，不要求 benchmark 强制映射，但应保留在组织治理体系中。\n"
    )


def run(case_name: str) -> tuple[Path, Path, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    org_path = working_dir / "organizational_requirements.json"
    benchmark_path = working_dir / "benchmark_requirements.json"
    standard_coverage_path = working_dir / "standard_coverage.json"
    benchmark_extensions_path = working_dir / "benchmark_extensions.json"
    baseline_candidates_path = working_dir / "baseline_candidates.json"
    controls_path = working_dir / "baseline_controls.md"
    report_path = working_dir / "baseline_report.md"
    recommendations_cn_path = working_dir / "baseline_priority_recommendations_cn.md"

    org_data = load_json(org_path)
    benchmark_data = load_json(benchmark_path)
    standard_coverage = load_json(standard_coverage_path)
    benchmark_extensions = load_json(benchmark_extensions_path)
    baseline_candidates = load_json(baseline_candidates_path)

    control_lines = [
        "# Baseline Controls",
        "",
        "## Baseline Metadata",
        f"- Case: {case_name}",
        "- Scope: Alibaba Cloud",
        "- Primary source: Global Standard",
        "- Reference benchmark: Third-Party Standard",
        "",
        "## Candidate Control List",
    ]
    for index, item in enumerate(baseline_candidates.get("rows", []), start=1):
        control_lines.append(build_control_item(index, item))
        control_lines.append("")

    controls_path.write_text("\n".join(control_lines).strip() + "\n", encoding="utf-8")
    report_path.write_text(
        build_report(case_name, org_data, benchmark_data, standard_coverage, benchmark_extensions, baseline_candidates),
        encoding="utf-8",
    )
    recommendations_cn_path.write_text(
        build_cn_recommendations(case_name, standard_coverage, benchmark_extensions, baseline_candidates),
        encoding="utf-8",
    )
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
