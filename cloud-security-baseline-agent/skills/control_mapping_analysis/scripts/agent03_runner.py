import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.text_utils import load_json, overlap_tokens, score_overlap, write_json



def choose_best_match(benchmark_item: dict[str, Any], org_requirements: list[dict[str, Any]]) -> dict[str, Any] | None:
    best_match: dict[str, Any] | None = None
    best_score = 0.0
    best_overlap: set[str] = set()
    for org_item in org_requirements:
        overlap = overlap_tokens(benchmark_item["statement"], org_item["statement"])
        score = score_overlap(benchmark_item["statement"], org_item["statement"])
        if benchmark_item.get("category") == org_item.get("category"):
            score += 0.2
        if benchmark_item.get("service") != "general" and benchmark_item.get("service") in org_item.get("statement", ""):
            score += 0.1
        if score > best_score:
            best_score = score
            best_match = org_item
            best_overlap = overlap
    if best_match is None or best_score < 0.2:
        return None
    return {
        "requirement": best_match,
        "score": round(best_score, 4),
        "overlap_tokens": sorted(best_overlap),
        "overlap_count": len(best_overlap),
    }



def decision_from_match(benchmark_item: dict[str, Any], matched: dict[str, Any] | None) -> str:
    if matched is None:
        return "gap"
    org_item = matched["requirement"]
    score = float(matched.get("score", 0.0))
    overlap_count = int(matched.get("overlap_count", 0))
    if overlap_count < 2:
        return "gap"
    if org_item.get("priority") == "mandatory" and score >= 0.55:
        return "aligned"
    if score >= 0.35:
        return "partial"
    return "gap"



def render_markdown(case_name: str, mapping: list[dict[str, Any]], org_themes: list[dict[str, Any]], benchmark_themes: list[dict[str, Any]], org_only: list[dict[str, Any]]) -> str:
    lines = [
        "# Mapping Analysis",
        "",
        "## Analysis Metadata",
        f"- Case: {case_name}",
        "- Organization standard: cloud security standard",
        "- Benchmark: CIS Alibaba Cloud Foundations Benchmark",
        "- Target cloud: Alibaba Cloud",
        "",
        "## Strategy Themes",
    ]
    lines.extend(f"- {item['theme']}: {item['description']}" for item in org_themes[:10])
    lines.extend(["", "## Benchmark Themes"])
    lines.extend(f"- {item['theme']}: {item['description']}" for item in benchmark_themes[:10])
    lines.extend(["", "## Requirement Mapping"])
    for item in mapping:
        benchmark = item["benchmark_requirement"]
        matched = item.get("matched_organizational_requirement")
        lines.append(f"- {benchmark['requirement_id']} [{item['decision']}] {benchmark['statement']}")
        if matched:
            lines.append(f"  - matched {matched['requirement_id']} ({item['match_score']}): {matched['statement']}")
        else:
            lines.append("  - matched none: organizational policy does not explicitly cover this benchmark item.")
    lines.extend(["", "## Gaps and Additions"])
    gap_count = sum(1 for item in mapping if item["decision"] == "gap")
    partial_count = sum(1 for item in mapping if item["decision"] == "partial")
    lines.append(f"- Benchmark gaps: {gap_count}")
    lines.append(f"- Partial matches: {partial_count}")
    lines.append(f"- Organization-only requirements: {len(org_only)}")
    if org_only:
        for item in org_only[:10]:
            lines.append(f"- {item['requirement_id']}: {item['statement']}")
    lines.extend([
        "",
        "## Baseline Decision Principles",
        "- Adopt controls where organizational policy and CIS benchmark align.",
        "- Adapt controls where CIS gives a stronger technical prescription than the organizational standard.",
        "- Flag benchmark gaps for review when the organization standard is silent.",
        "- Preserve organization-specific requirements that exceed CIS.",
        "",
        "## Open Issues",
        "- Review benchmark gaps with cloud platform owners before final sign-off.",
        "- Validate parser output when source documents rely on tables rather than bullets or sentences.",
    ])
    return "\n".join(lines) + "\n"



def run(case_name: str) -> tuple[Path, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    org_path = working_dir / "organizational_requirements.json"
    benchmark_path = working_dir / "benchmark_requirements.json"
    markdown_path = working_dir / "mapping_analysis.md"
    json_path = working_dir / "mapping_analysis.json"

    org_data = load_json(org_path)
    benchmark_data = load_json(benchmark_path)
    org_requirements = org_data.get("requirements", [])
    benchmark_requirements = benchmark_data.get("requirements", [])

    mapping: list[dict[str, Any]] = []
    matched_org_ids: set[str] = set()
    for benchmark_item in benchmark_requirements:
        matched = choose_best_match(benchmark_item, org_requirements)
        decision = decision_from_match(benchmark_item, matched)
        item = {
            "benchmark_requirement": benchmark_item,
            "decision": decision,
            "rationale": "Matched by category and keyword overlap." if matched else "No strong organizational requirement match detected.",
        }
        if matched:
            org_item = matched["requirement"]
            if decision != "gap":
                matched_org_ids.add(org_item["requirement_id"])
            item["matched_organizational_requirement"] = org_item
            item["match_score"] = matched["score"]
            item["overlap_tokens"] = matched["overlap_tokens"]
        mapping.append(item)

    org_only = [item for item in org_requirements if item["requirement_id"] not in matched_org_ids]
    analysis = {
        "case_name": case_name,
        "mapping": mapping,
        "org_only_requirements": org_only,
        "summary": {
            "aligned": sum(1 for item in mapping if item["decision"] == "aligned"),
            "partial": sum(1 for item in mapping if item["decision"] == "partial"),
            "gap": sum(1 for item in mapping if item["decision"] == "gap"),
            "organization_only": len(org_only),
        },
    }
    write_json(json_path, analysis)
    markdown_path.write_text(
        render_markdown(
            case_name,
            mapping,
            org_data.get("strategy_signals", []),
            benchmark_data.get("benchmark_themes", []),
            org_only,
        ),
        encoding="utf-8",
    )
    return markdown_path, json_path



def main() -> int:
    parser = argparse.ArgumentParser(description="Map organizational standard to CIS Alibaba Cloud")
    parser.add_argument("--case", required=True, dest="case_name")
    args = parser.parse_args()
    try:
        markdown_path, json_path = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(markdown_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
