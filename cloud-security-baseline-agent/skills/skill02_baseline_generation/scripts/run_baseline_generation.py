import argparse
import sys
from pathlib import Path

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.document_pipeline import (
    choose_best_global_match,
    choose_top_global_matches,
    classify_baseline_action,
    llm_classify_baseline_actions,
    load_json,
    write_json,
)
from runtime.ollama_runtime import build_ollama_runtime
from runtime.text_utils import clean_statement_noise
from skills.baseline_writer.scripts.agent04_runner import run as run_baseline_writer

VALID_BASELINE_ACTIONS = {"carry_forward", "adapt_for_platform", "new_baseline_control"}
ACTION_TO_DECISION = {
    "carry_forward": "aligned",
    "adapt_for_platform": "partial",
    "new_baseline_control": "gap",
}
VALID_DECISIONS = set(ACTION_TO_DECISION.values())


def _validate_mapping_item(item: dict, global_requirement_ids: set[str]) -> None:
    benchmark = item.get("third_party_requirement")
    if not isinstance(benchmark, dict):
        raise RuntimeError("skill02 produced a mapping row without third_party_requirement.")
    benchmark_id = str(benchmark.get("requirement_id", "")).strip()
    if not benchmark_id:
        raise RuntimeError("skill02 produced a benchmark row without requirement_id.")

    action = str(item.get("baseline_action", "")).strip()
    if action not in VALID_BASELINE_ACTIONS:
        raise RuntimeError(f"skill02 produced invalid baseline_action for {benchmark_id}: {action}")

    decision = str(item.get("decision", "")).strip()
    expected_decision = ACTION_TO_DECISION[action]
    if decision != expected_decision:
        raise RuntimeError(
            f"skill02 produced inconsistent decision for {benchmark_id}: expected {expected_decision}, got {decision}"
        )

    rationale = clean_statement_noise(str(item.get("rationale", "")))
    if len(rationale) < 20:
        raise RuntimeError(f"skill02 produced an insufficient rationale for {benchmark_id}")

    if str(item.get("classification_method", "")).strip() != "qwen_online":
        raise RuntimeError(f"skill02 produced invalid classification_method for {benchmark_id}")

    candidate_matches = item.get("candidate_matches")
    if not isinstance(candidate_matches, list):
        raise RuntimeError(f"skill02 produced non-list candidate_matches for {benchmark_id}")

    matched = item.get("matched_global_policy_requirement")
    if action == "new_baseline_control":
        if matched is not None:
            raise RuntimeError(f"skill02 should not attach matched_global_policy_requirement for gap row {benchmark_id}")
    else:
        if not isinstance(matched, dict):
            raise RuntimeError(f"skill02 missing matched_global_policy_requirement for {benchmark_id}")
        matched_id = str(matched.get("requirement_id", "")).strip()
        if not matched_id or matched_id not in global_requirement_ids:
            raise RuntimeError(f"skill02 produced invalid matched_global_policy_requirement for {benchmark_id}")


def _validate_analysis(
    *,
    analysis: dict,
    third_party_requirements: list[dict],
    global_requirements: list[dict],
) -> None:
    mapping = analysis.get("baseline_mapping")
    if not isinstance(mapping, list):
        raise RuntimeError("skill02 baseline_analysis missing baseline_mapping list.")

    third_party_ids = [str(item.get("requirement_id", "")).strip() for item in third_party_requirements]
    if any(not item_id for item_id in third_party_ids):
        raise RuntimeError("skill02 input third_party_requirements contains empty requirement_id.")
    if len(mapping) != len(third_party_requirements):
        raise RuntimeError(
            f"skill02 baseline_mapping row count mismatch: expected {len(third_party_requirements)}, got {len(mapping)}"
        )

    global_requirement_ids = {
        str(item.get("requirement_id", "")).strip()
        for item in global_requirements
        if str(item.get("requirement_id", "")).strip()
    }
    seen_ids: set[str] = set()
    for item in mapping:
        _validate_mapping_item(item, global_requirement_ids)
        benchmark_id = str(item["third_party_requirement"]["requirement_id"]).strip()
        if benchmark_id in seen_ids:
            raise RuntimeError(f"skill02 produced duplicate mapping row for {benchmark_id}")
        seen_ids.add(benchmark_id)

    missing_ids = [item_id for item_id in third_party_ids if item_id not in seen_ids]
    if missing_ids:
        raise RuntimeError(f"skill02 baseline_mapping missing benchmark rows: {', '.join(missing_ids[:10])}")

    summary = analysis.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("skill02 baseline_analysis missing summary object.")
    expected_summary = {
        "carry_forward": sum(1 for item in mapping if item["baseline_action"] == "carry_forward"),
        "adapt_for_platform": sum(1 for item in mapping if item["baseline_action"] == "adapt_for_platform"),
        "new_baseline_control": sum(1 for item in mapping if item["baseline_action"] == "new_baseline_control"),
        "global_policy_only": len(analysis.get("global_policy_only_requirements", [])),
    }
    if summary != expected_summary:
        raise RuntimeError(f"skill02 summary mismatch: expected {expected_summary}, got {summary}")

    if analysis.get("baseline_actions") != mapping:
        raise RuntimeError("skill02 baseline_actions must be an exact alias of baseline_mapping.")


def _validate_compatibility_analysis(compatibility_analysis: dict, analysis: dict) -> None:
    mapping_rows = compatibility_analysis.get("mapping")
    if not isinstance(mapping_rows, list):
        raise RuntimeError("skill02 compatibility mapping must be a list.")
    if len(mapping_rows) != len(analysis.get("baseline_mapping", [])):
        raise RuntimeError("skill02 compatibility mapping row count does not match baseline_mapping.")

    for row in mapping_rows:
        benchmark = row.get("benchmark_requirement")
        if not isinstance(benchmark, dict) or not str(benchmark.get("requirement_id", "")).strip():
            raise RuntimeError("skill02 compatibility mapping row missing benchmark requirement id.")
        decision = str(row.get("decision", "")).strip()
        if decision not in VALID_DECISIONS:
            raise RuntimeError(f"skill02 compatibility mapping has invalid decision: {decision}")
        rationale = clean_statement_noise(str(row.get("rationale", "")))
        if len(rationale) < 20:
            raise RuntimeError("skill02 compatibility mapping has insufficient rationale.")

    summary = compatibility_analysis.get("summary")
    expected_summary = {
        "aligned": analysis["summary"]["carry_forward"],
        "partial": analysis["summary"]["adapt_for_platform"],
        "gap": analysis["summary"]["new_baseline_control"],
        "organization_only": analysis["summary"]["global_policy_only"],
    }
    if summary != expected_summary:
        raise RuntimeError(f"skill02 compatibility summary mismatch: expected {expected_summary}, got {summary}")



def _enforce_action_guards(
    third_party_item: dict,
    action: str,
    selected_match: dict | None,
    rationale: str,
) -> tuple[str, dict | None, str]:
    if selected_match is None:
        return action, selected_match, rationale

    third = str(third_party_item.get("statement", "")).lower()
    global_statement = str(selected_match.get("requirement", {}).get("statement", "")).lower()

    logging_specific = any(
        token in third
        for token in ["monitor", "alert", "changes", "change", "unauthorized api", "policy changes"]
    )
    third_has_resource_object = any(
        token in third
        for token in ["security group", "cloud firewall", "ram role", "vpc", "oss", "rds", "cmk", "api"]
    )
    global_has_specific_monitoring = any(
        token in global_statement
        for token in ["monitor", "alert", "changes", "change", "collecting tool"]
    )
    global_has_resource_object = any(
        token in global_statement
        for token in ["security group", "cloud firewall", "ram role", "vpc", "oss", "rds", "cmk", "api"]
    )

    if logging_specific and (not global_has_specific_monitoring or (third_has_resource_object and not global_has_resource_object)):
        if action == "carry_forward":
            return (
                "adapt_for_platform",
                selected_match,
                "Global policy requires security logging, but the benchmark expects platform-specific monitoring or alerting behavior.",
            )
        if action == "adapt_for_platform":
            return (
                "new_baseline_control",
                None,
                "Global policy logging language is too general to cover this benchmark's monitoring or alerting requirement.",
            )

    if any(token in third for token in ["security group changes", "cloud firewall changes", "ram role changes"]):
        return (
            "new_baseline_control",
            None,
            "This benchmark requires monitoring or alerting for a specific cloud resource change event, which is not explicitly defined in the global policy.",
        )

    return action, selected_match, rationale

def run(case_name: str) -> tuple[Path, Path, Path, Path, Path, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    global_path = working_dir / "global_policy_parse.json"
    third_party_path = working_dir / "third_party_standard_parse.json"
    if not global_path.exists() or not third_party_path.exists():
        raise FileNotFoundError("Missing parse artifacts. Run skill01 first for both document roles.")

    profile = load_json(working_dir / "project_profile.json")
    ollama_runtime, runtime_status = build_ollama_runtime(profile)
    if ollama_runtime is None:
        raise RuntimeError(f"skill02 requires LLM runtime, but it is unavailable: {runtime_status.get('skip_reason')}")
    global_data = load_json(global_path)
    third_party_data = load_json(third_party_path)
    global_requirements = global_data.get("requirements", [])
    third_party_requirements = third_party_data.get("requirements", [])
    global_by_id = {item["requirement_id"]: item for item in global_requirements}
    llm_decisions, llm_debug = llm_classify_baseline_actions(
        runtime=ollama_runtime,
        global_requirements=global_requirements,
        third_party_requirements=third_party_requirements,
    )
    missing_decisions = [
        item.get("requirement_id", "")
        for item in third_party_requirements
        if item.get("requirement_id", "") not in llm_decisions
    ]
    if missing_decisions:
        debug_path = working_dir / "skill02_debug.json"
        write_json(
            debug_path,
            {
                "case_name": case_name,
                "llm_runtime": runtime_status,
                "chunk_debug": llm_debug,
                "llm_decision_count": len(llm_decisions),
                "fallback_count": len(missing_decisions),
                "missing_requirement_ids": missing_decisions,
            },
        )
        raise RuntimeError(
            f"skill02 requires LLM decisions for all benchmark requirements. Missing {len(missing_decisions)} decisions."
        )

    baseline_mapping: list[dict] = []
    matched_global_ids: set[str] = set()
    for third_party_item in third_party_requirements:
        candidate_matches = choose_top_global_matches(third_party_item, global_requirements, limit=3)
        match = candidate_matches[0] if candidate_matches else None
        normalized_third_party_item = dict(third_party_item)
        normalized_third_party_item["statement"] = clean_statement_noise(str(third_party_item.get("statement", "")))
        normalized_third_party_item["source_excerpt"] = clean_statement_noise(str(third_party_item.get("source_excerpt", "")))
        llm_decision = llm_decisions.get(third_party_item.get("requirement_id", ""))
        action = llm_decision["baseline_action"]
        selected_match = match
        selected_id = llm_decision.get("matched_global_policy_requirement_id", "")
        if selected_id and selected_id in global_by_id:
            selected_match = next(
                (
                    candidate
                    for candidate in candidate_matches
                    if candidate["requirement"]["requirement_id"] == selected_id
                ),
                {
                    "requirement": global_by_id[selected_id],
                    "score": None,
                    "overlap_tokens": [],
                    "overlap_count": 0,
                },
            )
        rationale = llm_decision.get("rationale", "").strip()
        if not rationale:
            raise RuntimeError(f"skill02 received an empty rationale for {third_party_item.get('requirement_id', '')}")
        action, selected_match, rationale = _enforce_action_guards(
            third_party_item, action, selected_match, rationale
        )
        item = {
            "third_party_requirement": normalized_third_party_item,
            "baseline_action": action,
            "decision": ACTION_TO_DECISION[action],
            "rationale": rationale,
            "classification_method": "qwen_online",
        }
        if selected_match and action != "new_baseline_control":
            global_item = dict(selected_match["requirement"])
            global_item["statement"] = clean_statement_noise(str(global_item.get("statement", "")))
            global_item["source_excerpt"] = clean_statement_noise(str(global_item.get("source_excerpt", "")))
            matched_global_ids.add(global_item["requirement_id"])
            item["matched_global_policy_requirement"] = global_item
            item["match_score"] = selected_match.get("score")
            item["overlap_tokens"] = selected_match.get("overlap_tokens", [])
        item["candidate_matches"] = [
                {
                    "matched_global_policy_requirement": {
                        **candidate["requirement"],
                        "statement": clean_statement_noise(str(candidate["requirement"].get("statement", ""))),
                        "source_excerpt": clean_statement_noise(str(candidate["requirement"].get("source_excerpt", ""))),
                    },
                    "match_score": candidate.get("score"),
                    "overlap_tokens": candidate.get("overlap_tokens", []),
                }
            for candidate in candidate_matches
        ]
        baseline_mapping.append(item)

    global_policy_only = [item for item in global_requirements if item["requirement_id"] not in matched_global_ids]
    analysis = {
        "case_name": case_name,
        "global_policy_parse": str(global_path.relative_to(PROJECT_ROOT)),
        "third_party_standard_parse": str(third_party_path.relative_to(PROJECT_ROOT)),
        "baseline_mapping": baseline_mapping,
        "baseline_actions": baseline_mapping,
        "global_policy_only_requirements": global_policy_only,
        "summary": {
            "carry_forward": sum(1 for item in baseline_mapping if item["baseline_action"] == "carry_forward"),
            "adapt_for_platform": sum(1 for item in baseline_mapping if item["baseline_action"] == "adapt_for_platform"),
            "new_baseline_control": sum(1 for item in baseline_mapping if item["baseline_action"] == "new_baseline_control"),
            "global_policy_only": len(global_policy_only),
        },
        "llm_runtime": runtime_status,
    }
    _validate_analysis(
        analysis=analysis,
        third_party_requirements=third_party_requirements,
        global_requirements=global_requirements,
    )
    analysis_path = working_dir / "baseline_analysis.json"
    write_json(analysis_path, analysis)
    debug_path = working_dir / "skill02_debug.json"
    write_json(
        debug_path,
        {
            "case_name": case_name,
            "llm_runtime": runtime_status,
            "chunk_debug": llm_debug,
            "llm_decision_count": len(llm_decisions),
            "fallback_count": len(third_party_requirements) - len(llm_decisions),
        },
    )

    # Compatibility bridge so the existing baseline writer can render the package.
    compatibility_analysis = {
        "case_name": case_name,
        "mapping": [
            {
                "benchmark_requirement": item["third_party_requirement"],
                "decision": item["decision"],
                "rationale": item["rationale"],
                **({
                    "matched_organizational_requirement": item["matched_global_policy_requirement"],
                    "match_score": item.get("match_score"),
                    "overlap_tokens": item.get("overlap_tokens", []),
                } if "matched_global_policy_requirement" in item else {}),
            }
            for item in baseline_mapping
        ],
        "org_only_requirements": global_policy_only,
        "summary": {
            "aligned": analysis["summary"]["carry_forward"],
            "partial": analysis["summary"]["adapt_for_platform"],
            "gap": analysis["summary"]["new_baseline_control"],
            "organization_only": analysis["summary"]["global_policy_only"],
        },
    }
    _validate_compatibility_analysis(compatibility_analysis, analysis)
    compatibility_path = working_dir / "mapping_analysis.json"
    write_json(compatibility_path, compatibility_analysis)

    # Compatibility bridge for the existing baseline writer input names.
    write_json(working_dir / "organizational_requirements.json", {
        "document_name": global_data.get("document_name", "global policy"),
        "source_files": global_data.get("source_files", []),
        "requirements": global_requirements,
        "strategy_signals": global_data.get("thematic_signals", []),
        "notes": global_data.get("parsing_notes", []),
    })
    write_json(working_dir / "benchmark_requirements.json", {
        "document_name": third_party_data.get("document_name", "third party standard"),
        "source_files": third_party_data.get("source_files", []),
        "requirements": third_party_requirements,
        "benchmark_themes": third_party_data.get("thematic_signals", []),
        "notes": third_party_data.get("parsing_notes", []),
    })

    controls_path, report_path, recommendations_path = run_baseline_writer(case_name)
    return analysis_path, compatibility_path, controls_path, report_path, recommendations_path, debug_path



def main() -> int:
    parser = argparse.ArgumentParser(description="Run skill02 baseline generation")
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
