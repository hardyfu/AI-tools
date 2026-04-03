import argparse
import sys
from pathlib import Path

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.document_pipeline import (
    choose_top_global_matches,
    llm_classify_baseline_actions,
    load_json,
    write_json,
)
from runtime.ollama_runtime import build_azure_openai_runtime
from runtime.text_utils import clean_statement_noise
from skills.baseline_writer.scripts.agent04_runner import run as run_baseline_writer

VALID_BASELINE_ACTIONS = {"carry_forward", "adapt_for_platform", "new_baseline_control"}
ACTION_TO_DECISION = {
    "carry_forward": "aligned",
    "adapt_for_platform": "partial",
    "new_baseline_control": "gap",
}
VALID_DECISIONS = set(ACTION_TO_DECISION.values())
VALID_COVERAGE_STATUSES = {"covered", "partially_covered", "not_addressed_by_benchmark", "organization_specific"}
VALID_EXTENSION_TYPES = {"platform_specific_detail", "implementation_enrichment", "stronger_control", "new_control_area"}


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

    classification_method = str(item.get("classification_method", "")).strip()
    if classification_method not in {"azure_openai_online", "qwen_online"}:
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


def _is_org_specific_requirement(global_item: dict) -> bool:
    text = " ".join(
        [
            str(global_item.get("statement", "")),
            str(global_item.get("section", "")),
            str(global_item.get("source_excerpt", "")),
        ]
    ).lower()
    org_specific_markers = [
        "abb",
        "azure active directory",
        "active directory",
        "abb-managed",
        "abbmanaged",
        "jump server",
        "pam solution",
        "internal",
        "organization",
    ]
    return any(marker in text for marker in org_specific_markers)


def _build_standard_coverage(
    *,
    global_requirements: list[dict],
    baseline_mapping: list[dict],
) -> list[dict[str, object]]:
    matched_by_global_id: dict[str, list[dict]] = {}
    for item in baseline_mapping:
        matched = item.get("matched_global_policy_requirement")
        if not isinstance(matched, dict):
            continue
        requirement_id = str(matched.get("requirement_id", "")).strip()
        if not requirement_id:
            continue
        matched_by_global_id.setdefault(requirement_id, []).append(item)

    coverage_rows: list[dict[str, object]] = []
    for global_item in global_requirements:
        global_id = str(global_item.get("requirement_id", "")).strip()
        matched_rows = matched_by_global_id.get(global_id, [])
        if any(row.get("decision") == "aligned" for row in matched_rows):
            coverage_status = "covered"
        elif any(row.get("decision") == "partial" for row in matched_rows):
            coverage_status = "partially_covered"
        elif _is_org_specific_requirement(global_item):
            coverage_status = "organization_specific"
        else:
            coverage_status = "not_addressed_by_benchmark"

        matched_benchmark_requirements = [
            {
                "requirement_id": row["third_party_requirement"].get("requirement_id", ""),
                "source_requirement_id": row["third_party_requirement"].get("source_requirement_id", ""),
                "section": row["third_party_requirement"].get("section", ""),
                "statement": clean_statement_noise(str(row["third_party_requirement"].get("statement", ""))),
                "decision": row.get("decision", ""),
            }
            for row in matched_rows
        ]
        if matched_rows:
            coverage_rationale = clean_statement_noise(
                " | ".join(str(row.get("rationale", "")).strip() for row in matched_rows if str(row.get("rationale", "")).strip())
            )
        elif coverage_status == "organization_specific":
            coverage_rationale = "This Global Standard requirement appears organization-specific and is not expected to have a direct benchmark counterpart."
        else:
            coverage_rationale = "No benchmark requirement was matched to this Global Standard requirement."

        coverage_rows.append(
            {
                "global_requirement_id": global_id,
                "global_source_requirement_id": str(global_item.get("source_requirement_id", "")).strip(),
                "global_section": str(global_item.get("section", "")).strip(),
                "global_statement": clean_statement_noise(str(global_item.get("statement", ""))),
                "category": str(global_item.get("category", "")).strip(),
                "priority": str(global_item.get("priority", "")).strip(),
                "service": str(global_item.get("service", "")).strip(),
                "matched_benchmark_requirements": matched_benchmark_requirements,
                "coverage_status": coverage_status,
                "coverage_rationale": coverage_rationale,
            }
        )
    return coverage_rows


def _infer_extension_type(item: dict) -> str:
    benchmark = item.get("third_party_requirement", {})
    candidate_matches = item.get("candidate_matches", [])
    benchmark_service = str(benchmark.get("service", "")).strip()
    statement = str(benchmark.get("statement", "")).lower()

    if item.get("decision") == "partial":
        return "platform_specific_detail"
    if benchmark_service and benchmark_service != "general":
        return "platform_specific_detail"
    if candidate_matches:
        top_score = candidate_matches[0].get("match_score")
        if top_score is not None and float(top_score) >= 0.45:
            if any(token in statement for token in ["must", "ensure", "required", "enabled", "rotated", "minimum length", "mfa"]):
                return "stronger_control"
            return "implementation_enrichment"
    return "new_control_area"


def _candidate_priority(source_requirement_id: str) -> str:
    try:
        major, minor = source_requirement_id.split(".", 1)
    except ValueError:
        return "P2"
    if major == "1" and minor in {"1", "2", "3", "4", "15", "16"}:
        return "P0"
    if major in {"3", "5", "6", "7", "8"} and minor in {"2", "5", "7", "9"}:
        return "P0"
    if major in {"1", "2", "3", "4", "5", "6", "7", "8"}:
        return "P1"
    return "P2"


def _build_benchmark_extensions(baseline_mapping: list[dict]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for item in baseline_mapping:
        if item.get("decision") == "aligned":
            continue
        benchmark = item.get("third_party_requirement", {})
        related_globals = []
        for candidate in item.get("candidate_matches", []):
            matched = candidate.get("matched_global_policy_requirement", {})
            requirement_id = str(matched.get("requirement_id", "")).strip()
            if not requirement_id:
                continue
            related_globals.append(
                {
                    "global_requirement_id": requirement_id,
                    "global_source_requirement_id": str(matched.get("source_requirement_id", "")).strip(),
                    "global_statement": clean_statement_noise(str(matched.get("statement", ""))),
                    "match_score": candidate.get("match_score"),
                }
            )
        extension_type = _infer_extension_type(item)
        rows.append(
            {
                "benchmark_requirement_id": str(benchmark.get("requirement_id", "")).strip(),
                "benchmark_source_requirement_id": str(benchmark.get("source_requirement_id", "")).strip(),
                "benchmark_section": str(benchmark.get("section", "")).strip(),
                "benchmark_statement": clean_statement_noise(str(benchmark.get("statement", ""))),
                "category": str(benchmark.get("category", "")).strip(),
                "service": str(benchmark.get("service", "")).strip(),
                "decision": str(item.get("decision", "")).strip(),
                "baseline_action": str(item.get("baseline_action", "")).strip(),
                "related_global_requirements": related_globals,
                "extension_type": extension_type,
                "extension_rationale": clean_statement_noise(str(item.get("rationale", ""))),
                "baseline_candidate": True,
                "candidate_priority": _candidate_priority(str(benchmark.get("source_requirement_id", "")).strip()),
            }
        )
    return rows


def _build_baseline_candidates(benchmark_extensions: list[dict[str, object]]) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for index, item in enumerate(benchmark_extensions, start=1):
        if not item.get("baseline_candidate"):
            continue
        candidates.append(
            {
                "candidate_id": f"BC-{index:03d}",
                "source_benchmark_requirement_id": item.get("benchmark_requirement_id", ""),
                "source_benchmark_source_requirement_id": item.get("benchmark_source_requirement_id", ""),
                "proposed_control_title": clean_statement_noise(str(item.get("benchmark_statement", "")))[:120],
                "proposed_control_statement": clean_statement_noise(str(item.get("benchmark_statement", ""))),
                "category": item.get("category", ""),
                "service": item.get("service", ""),
                "candidate_priority": item.get("candidate_priority", "P2"),
                "reason_for_inclusion": clean_statement_noise(str(item.get("extension_rationale", ""))),
                "related_global_requirements": item.get("related_global_requirements", []),
                "extension_type": item.get("extension_type", ""),
            }
        )
    return candidates


def _validate_harness_artifacts(
    *,
    standard_coverage: list[dict[str, object]],
    benchmark_extensions: list[dict[str, object]],
    baseline_candidates: list[dict[str, object]],
    global_requirements: list[dict],
    third_party_requirements: list[dict],
) -> None:
    if len(standard_coverage) != len(global_requirements):
        raise RuntimeError("skill02 standard_coverage row count mismatch.")
    seen_global_ids: set[str] = set()
    for row in standard_coverage:
        requirement_id = str(row.get("global_requirement_id", "")).strip()
        if not requirement_id:
            raise RuntimeError("skill02 standard_coverage missing global_requirement_id.")
        if requirement_id in seen_global_ids:
            raise RuntimeError(f"skill02 duplicate standard_coverage row: {requirement_id}")
        seen_global_ids.add(requirement_id)
        if str(row.get("coverage_status", "")).strip() not in VALID_COVERAGE_STATUSES:
            raise RuntimeError(f"skill02 invalid coverage_status for {requirement_id}")

    third_party_ids = {
        str(item.get("requirement_id", "")).strip()
        for item in third_party_requirements
        if str(item.get("requirement_id", "")).strip()
    }
    candidate_source_ids: set[str] = set()
    for row in benchmark_extensions:
        benchmark_id = str(row.get("benchmark_requirement_id", "")).strip()
        if not benchmark_id or benchmark_id not in third_party_ids:
            raise RuntimeError(f"skill02 invalid benchmark_extension benchmark id: {benchmark_id}")
        extension_type = str(row.get("extension_type", "")).strip()
        if extension_type not in VALID_EXTENSION_TYPES:
            raise RuntimeError(f"skill02 invalid extension_type for {benchmark_id}: {extension_type}")
    for row in baseline_candidates:
        candidate_id = str(row.get("candidate_id", "")).strip()
        if not candidate_id:
            raise RuntimeError("skill02 baseline_candidates missing candidate_id.")
        source_id = str(row.get("source_benchmark_requirement_id", "")).strip()
        if not source_id or source_id in candidate_source_ids:
            raise RuntimeError(f"skill02 invalid or duplicate baseline candidate source: {source_id}")
        candidate_source_ids.add(source_id)



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

def run(case_name: str) -> tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    global_path = working_dir / "global_policy_parse.json"
    third_party_path = working_dir / "third_party_standard_parse.json"
    if not global_path.exists() or not third_party_path.exists():
        raise FileNotFoundError("Missing parse artifacts. Run skill01 first for both document roles.")

    profile = load_json(working_dir / "project_profile.json")
    azure_runtime, runtime_status = build_azure_openai_runtime(profile)
    if azure_runtime is None:
        raise RuntimeError(f"skill02 requires LLM runtime, but it is unavailable: {runtime_status.get('skip_reason')}")
    global_data = load_json(global_path)
    third_party_data = load_json(third_party_path)
    global_requirements = global_data.get("requirements", [])
    third_party_requirements = third_party_data.get("requirements", [])
    global_by_id = {item["requirement_id"]: item for item in global_requirements}
    llm_decisions, llm_debug = llm_classify_baseline_actions(
        runtime=azure_runtime,
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
            "classification_method": "azure_openai_online",
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

    standard_coverage = _build_standard_coverage(
        global_requirements=global_requirements,
        baseline_mapping=baseline_mapping,
    )
    benchmark_extensions = _build_benchmark_extensions(baseline_mapping)
    baseline_candidates = _build_baseline_candidates(benchmark_extensions)
    _validate_harness_artifacts(
        standard_coverage=standard_coverage,
        benchmark_extensions=benchmark_extensions,
        baseline_candidates=baseline_candidates,
        global_requirements=global_requirements,
        third_party_requirements=third_party_requirements,
    )

    standard_coverage_path = working_dir / "standard_coverage.json"
    benchmark_extensions_path = working_dir / "benchmark_extensions.json"
    baseline_candidates_path = working_dir / "baseline_candidates.json"
    write_json(
        standard_coverage_path,
        {
            "case_name": case_name,
            "artifact_type": "standard_coverage",
            "global_policy_parse": str(global_path.relative_to(PROJECT_ROOT)),
            "third_party_standard_parse": str(third_party_path.relative_to(PROJECT_ROOT)),
            "rows": standard_coverage,
            "summary": {
                "covered": sum(1 for row in standard_coverage if row["coverage_status"] == "covered"),
                "partially_covered": sum(1 for row in standard_coverage if row["coverage_status"] == "partially_covered"),
                "not_addressed_by_benchmark": sum(1 for row in standard_coverage if row["coverage_status"] == "not_addressed_by_benchmark"),
                "organization_specific": sum(1 for row in standard_coverage if row["coverage_status"] == "organization_specific"),
            },
        },
    )
    write_json(
        benchmark_extensions_path,
        {
            "case_name": case_name,
            "artifact_type": "benchmark_extensions",
            "rows": benchmark_extensions,
            "summary": {
                "total_extensions": len(benchmark_extensions),
                "platform_specific_detail": sum(1 for row in benchmark_extensions if row["extension_type"] == "platform_specific_detail"),
                "implementation_enrichment": sum(1 for row in benchmark_extensions if row["extension_type"] == "implementation_enrichment"),
                "stronger_control": sum(1 for row in benchmark_extensions if row["extension_type"] == "stronger_control"),
                "new_control_area": sum(1 for row in benchmark_extensions if row["extension_type"] == "new_control_area"),
            },
        },
    )
    write_json(
        baseline_candidates_path,
        {
            "case_name": case_name,
            "artifact_type": "baseline_candidates",
            "rows": baseline_candidates,
            "summary": {
                "total_candidates": len(baseline_candidates),
                "p0": sum(1 for row in baseline_candidates if row["candidate_priority"] == "P0"),
                "p1": sum(1 for row in baseline_candidates if row["candidate_priority"] == "P1"),
                "p2": sum(1 for row in baseline_candidates if row["candidate_priority"] == "P2"),
            },
        },
    )

    debug_path = working_dir / "skill02_debug.json"
    write_json(
        debug_path,
        {
            "case_name": case_name,
            "llm_runtime": runtime_status,
            "chunk_debug": llm_debug,
            "llm_decision_count": len(llm_decisions),
            "fallback_count": len(third_party_requirements) - len(llm_decisions),
            "harness_artifacts": {
                "standard_coverage": str(standard_coverage_path.relative_to(PROJECT_ROOT)),
                "benchmark_extensions": str(benchmark_extensions_path.relative_to(PROJECT_ROOT)),
                "baseline_candidates": str(baseline_candidates_path.relative_to(PROJECT_ROOT)),
            },
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
    return (
        analysis_path,
        standard_coverage_path,
        benchmark_extensions_path,
        baseline_candidates_path,
        compatibility_path,
        controls_path,
        report_path,
        recommendations_path,
        debug_path,
    )



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
