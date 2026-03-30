import argparse
import sys
from pathlib import Path

from runtime.project_root import resolve_project_root

PROJECT_ROOT = resolve_project_root(__file__)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.document_pipeline import (
    build_theme_summary,
    ingest_source_document,
    load_json,
    parse_global_policy,
    parse_third_party_standard,
    write_json,
)
from runtime.text_utils import clean_statement_noise


ROLE_CONFIG = {
    "global_policy": {
        "input_dir": "global_policy",
        "output": "global_policy_parse.json",
        "parser": parse_global_policy,
    },
    "third_party_standard": {
        "input_dir": "third_party_standard",
        "output": "third_party_standard_parse.json",
        "parser": parse_third_party_standard,
    },
}

VALID_DOCUMENT_ROLES = set(ROLE_CONFIG)
VALID_PRIORITIES = {"mandatory", "recommended", "informational"}


def _validate_requirement(item: dict, role: str, index: int) -> None:
    requirement_id = str(item.get("requirement_id", "")).strip()
    source_requirement_id = str(item.get("source_requirement_id", "")).strip()
    section = str(item.get("section", "")).strip()
    statement = clean_statement_noise(str(item.get("statement", "")))
    category = str(item.get("category", "")).strip()
    priority = str(item.get("priority", "")).strip()
    source_excerpt = clean_statement_noise(str(item.get("source_excerpt", "")))
    source_file = str(item.get("source_file", "")).strip()
    service = str(item.get("service", "")).strip()

    if not requirement_id:
        raise RuntimeError(f"skill01 {role} requirement #{index} missing requirement_id")
    if not source_requirement_id:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} missing source_requirement_id")
    if not section:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} missing section")
    if len(statement) < 12:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} has insufficient statement")
    if not category:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} missing category")
    if priority not in VALID_PRIORITIES:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} has invalid priority: {priority}")
    if len(source_excerpt) < 12:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} has insufficient source_excerpt")
    if not source_file:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} missing source_file")
    if not service:
        raise RuntimeError(f"skill01 {role} requirement {requirement_id} missing service")


def _validate_theme_summary(themes: list[dict], role: str) -> None:
    if not isinstance(themes, list):
        raise RuntimeError(f"skill01 {role} thematic_signals must be a list")
    for index, item in enumerate(themes, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"skill01 {role} thematic_signals row #{index} is not an object")
        theme = str(item.get("theme", "")).strip()
        description = clean_statement_noise(str(item.get("description", "")))
        evidence = clean_statement_noise(str(item.get("evidence", "")))
        if not theme or not description or not evidence:
            raise RuntimeError(f"skill01 {role} thematic_signals row #{index} is incomplete")


def _validate_source_quality(source_quality: list[dict], role: str) -> None:
    if not isinstance(source_quality, list) or not source_quality:
        raise RuntimeError(f"skill01 {role} source_quality must be a non-empty list")
    for index, item in enumerate(source_quality, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"skill01 {role} source_quality row #{index} is not an object")
        if not str(item.get("source_file", "")).strip():
            raise RuntimeError(f"skill01 {role} source_quality row #{index} missing source_file")
        if not str(item.get("normalized_text_file", "")).strip():
            raise RuntimeError(f"skill01 {role} source_quality row #{index} missing normalized_text_file")
        for numeric_field in ("score", "line_count", "word_count", "table_artifact_count", "broken_uppercase_count", "control_char_count"):
            if numeric_field not in item:
                raise RuntimeError(f"skill01 {role} source_quality row #{index} missing {numeric_field}")
        if "vision_assistance_recommended" not in item or "vision_reasons" not in item:
            raise RuntimeError(f"skill01 {role} source_quality row #{index} missing vision fields")


def _validate_artifact(artifact: dict, role: str, source_files: list[Path]) -> None:
    document_role = str(artifact.get("document_role", "")).strip()
    if document_role not in VALID_DOCUMENT_ROLES:
        raise RuntimeError(f"skill01 produced invalid document_role: {document_role}")
    if document_role != role:
        raise RuntimeError(f"skill01 artifact role mismatch: expected {role}, got {document_role}")
    if not str(artifact.get("document_name", "")).strip():
        raise RuntimeError(f"skill01 {role} missing document_name")

    artifact_source_files = artifact.get("source_files")
    normalized_files = artifact.get("normalized_text_files")
    if artifact_source_files != [path.name for path in source_files]:
        raise RuntimeError(f"skill01 {role} source_files do not match staged inputs")
    if not isinstance(normalized_files, list) or len(normalized_files) != len(source_files):
        raise RuntimeError(f"skill01 {role} normalized_text_files count mismatch")

    requirements = artifact.get("requirements")
    if not isinstance(requirements, list) or not requirements:
        raise RuntimeError(f"skill01 {role} requirements must be a non-empty list")
    seen_requirement_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    for index, item in enumerate(requirements, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"skill01 {role} requirement row #{index} is not an object")
        _validate_requirement(item, role, index)
        requirement_id = str(item.get("requirement_id", "")).strip()
        source_requirement_id = str(item.get("source_requirement_id", "")).strip()
        if requirement_id in seen_requirement_ids:
            raise RuntimeError(f"skill01 {role} duplicate requirement_id: {requirement_id}")
        if source_requirement_id in seen_source_ids:
            raise RuntimeError(f"skill01 {role} duplicate source_requirement_id: {source_requirement_id}")
        seen_requirement_ids.add(requirement_id)
        seen_source_ids.add(source_requirement_id)

    _validate_theme_summary(artifact.get("thematic_signals"), role)
    _validate_source_quality(artifact.get("source_quality"), role)

    parsing_notes = artifact.get("parsing_notes")
    if not isinstance(parsing_notes, list):
        raise RuntimeError(f"skill01 {role} parsing_notes must be a list")
    if not str(artifact.get("parser_strategy", "")).strip():
        raise RuntimeError(f"skill01 {role} missing parser_strategy")



def run(case_name: str, role: str) -> Path:
    if role not in ROLE_CONFIG:
        raise ValueError(f"Unsupported role: {role}")
    config = ROLE_CONFIG[role]
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    profile_path = working_dir / "project_profile.json"
    if not profile_path.exists():
        raise FileNotFoundError(f"Missing project profile: {profile_path}")
    load_json(profile_path)

    input_dir = case_dir / "input" / config["input_dir"]
    source_files = (
        sorted(
            path
            for path in input_dir.iterdir()
            if path.is_file() and not path.name.endswith(".normalized.md")
        )
        if input_dir.exists()
        else []
    )
    if not source_files:
        raise FileNotFoundError(f"No source files found in {input_dir}")

    requirements: list[dict] = []
    thematic_signals: list[dict] = []
    parsing_notes: list[str] = []
    source_quality: list[dict] = []
    normalized_files: list[str] = []
    parser_strategy = "unknown"

    for source in source_files:
        normalized_path, text, quality = ingest_source_document(source, input_dir)
        parsed = config["parser"](text, source.name)
        parser_strategy = parsed["parser_strategy"]
        for item in parsed["requirements"]:
            item["source_file"] = normalized_path.name
            requirements.append(item)
        thematic_signals.extend(build_theme_summary(parsed["requirements"], "category"))
        parsing_notes.extend(parsed["parsing_notes"])
        source_quality.append(
            {
                "source_file": source.name,
                "normalized_text_file": normalized_path.name,
                **quality,
            }
        )
        normalized_files.append(normalized_path.name)

    artifact = {
        "document_role": role,
        "document_name": role.replace("_", " "),
        "source_files": [path.name for path in source_files],
        "normalized_text_files": normalized_files,
        "source_quality": source_quality,
        "requirements": requirements,
        "thematic_signals": thematic_signals,
        "parsing_notes": parsing_notes,
        "parser_strategy": parser_strategy,
    }
    _validate_artifact(artifact, role, source_files)
    output_path = working_dir / config["output"]
    write_json(output_path, artifact)
    return output_path



def main() -> int:
    parser = argparse.ArgumentParser(description="Run skill01 document parse")
    parser.add_argument("--case", required=True, dest="case_name")
    parser.add_argument("--role", required=True, choices=sorted(ROLE_CONFIG))
    args = parser.parse_args()
    try:
        output_path = run(args.case_name, args.role)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
