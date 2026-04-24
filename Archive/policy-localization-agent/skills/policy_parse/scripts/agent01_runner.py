import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.pdf_to_markdown import convert_pdf_to_markdown


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def derive_case_name(policy_path: Path) -> str:
    parts = policy_path.parts
    if "cases" not in parts:
        raise ValueError(f"Policy file is not inside cases/: {policy_path}")
    index = parts.index("cases")
    return parts[index + 1]


def normalized_markdown_path(case_name: str, policy_path: Path) -> Path:
    stem = policy_path.stem.replace(" ", "_")
    return PROJECT_ROOT / "cases" / case_name / "input" / "global_policy" / f"{stem}.normalized.md"


def detect_markdown_quality_warnings(markdown_text: str) -> list[str]:
    warnings: list[str] = []
    lines = markdown_text.splitlines()
    page_heading_count = sum(1 for line in lines if line.strip().startswith("## Page "))
    dashed_line_count = sum(1 for line in lines if re.fullmatch(r"[-_=\s]{4,}", line.strip() or ""))
    short_line_count = sum(1 for line in lines if 0 < len(line.strip()) < 24)
    if page_heading_count >= 3:
        warnings.append("Input markdown appears to be page-oriented PDF extraction rather than native markdown.")
    if dashed_line_count > 0:
        warnings.append("Input markdown contains divider noise lines.")
    if short_line_count > max(12, len(lines) // 3):
        warnings.append("Input markdown contains many short broken lines, suggesting PDF fragmentation.")
    return warnings


def normalize_markdown_text(markdown_text: str) -> tuple[str, list[str]]:
    warnings = detect_markdown_quality_warnings(markdown_text)
    text = markdown_text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[-_=]{4,}\n", "\n", text)
    return text.strip() + "\n", warnings


def run(policy_file_path: str) -> tuple[Path, Path]:
    policy_path = Path(policy_file_path).resolve()
    if not policy_path.exists():
        raise FileNotFoundError(f"Missing policy file: {policy_path}")

    case_name = derive_case_name(policy_path)
    case_dir = PROJECT_ROOT / "cases" / case_name
    scope_path = case_dir / "working" / "scope_profile.json"
    if not scope_path.exists():
        raise FileNotFoundError(f"Missing scope profile: {scope_path}")

    scope = load_json(scope_path)
    source_reference = scope.get("source_policy", {}).get("source_file_path_or_reference", "unknown")
    relative_policy_path = str(policy_path.relative_to(PROJECT_ROOT))
    if source_reference != "unknown" and source_reference != relative_policy_path:
        raise ValueError(f"Policy path mismatch: scope has {source_reference}, runner got {relative_policy_path}")

    output_markdown_path = normalized_markdown_path(case_name, policy_path)
    output_markdown_path.parent.mkdir(parents=True, exist_ok=True)

    if policy_path.suffix.lower() == ".pdf":
        convert_pdf_to_markdown(policy_path, output_markdown_path)
        raw_text = output_markdown_path.read_text(encoding="utf-8")
    else:
        raw_text = policy_path.read_text(encoding="utf-8")

    normalized_text, warnings = normalize_markdown_text(raw_text)
    output_markdown_path.write_text(normalized_text, encoding="utf-8")

    metadata = {
        "case_name": case_name,
        "source_policy_path": relative_policy_path,
        "scope_profile_path": str(scope_path.relative_to(PROJECT_ROOT)),
        "normalized_markdown_path": str(output_markdown_path.relative_to(PROJECT_ROOT)),
        "source_format": policy_path.suffix.lower().lstrip(".") or "unknown",
        "normalization_mode": "pdf_to_markdown" if policy_path.suffix.lower() == ".pdf" else "markdown_cleanup",
        "normalization_warnings": warnings,
        "notes": "Policy parse completed as normalization only. No control extraction was performed.",
    }
    metadata_path = case_dir / "working" / "policy_parse_result.json"
    write_json(metadata_path, metadata)
    return metadata_path, output_markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a global policy file into case-local Markdown.")
    parser.add_argument("--policy-file", required=True, dest="policy_file", help="Path to policy Markdown or PDF")
    args = parser.parse_args()
    try:
        metadata_path, markdown_path = run(args.policy_file)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Wrote normalized markdown to {markdown_path}")
    print(f"Wrote normalization metadata to {metadata_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
