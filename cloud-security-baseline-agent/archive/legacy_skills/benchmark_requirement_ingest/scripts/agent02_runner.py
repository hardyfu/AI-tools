import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.text_utils import build_theme_summary, categorize_text, detect_service, load_json, read_text_files, write_json


RECOMMENDATION_START = re.compile(r"^\s*((?:[1-8])\.\d+)\s+((?:Ensure|Avoid) .*)$")
APPENDIX_OR_SECTION = re.compile(r"^\s*(?:Appendix|Overview|Recommendation Definitions|Terms of Use|Table of Contents)\b", re.IGNORECASE)
TOP_LEVEL_SECTION = re.compile(r"^\s*([1-8])\s+([A-Za-z].*?)(?:\.{2,}\s*\d+)?\s*$")


def normalize_statement(text: str) -> str:
    text = text.replace("\f", " ")
    text = re.sub(r"\.{4,}\s*\d+\s*$", "", text)
    text = re.sub(r"\s+\(Automated\)\s*$", " (Automated)", text)
    text = re.sub(r"\s+\(Manual\)\s*$", " (Manual)", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_severity(statement: str) -> str:
    lowered = statement.lower()
    if "(automated)" in lowered:
        return "high"
    if "(manual)" in lowered:
        return "medium"
    return "low"


def infer_category(section_name: str, statement: str) -> str:
    lowered_section = section_name.lower()
    if "identity" in lowered_section or "access" in lowered_section:
        return "identity"
    if "logging" in lowered_section or "monitor" in lowered_section:
        return "logging"
    if "network" in lowered_section:
        return "network"
    if "storage" in lowered_section:
        return "data protection"
    return categorize_text(statement)


def extract_requirements(text: str) -> tuple[list[dict[str, str]], list[str]]:
    requirements: list[dict[str, str]] = []
    notes: list[str] = []
    current_section = "General"
    current_id: str | None = None
    current_lines: list[str] = []
    started = False

    def flush_current() -> None:
        nonlocal current_id, current_lines
        if not current_id or not current_lines:
            current_id = None
            current_lines = []
            return
        statement = normalize_statement(" ".join(current_lines))
        if len(statement) >= 20:
            requirements.append(
                {
                    "requirement_id": f"CIS-{len(requirements) + 1:03d}",
                    "source_requirement_id": current_id,
                    "section": current_section,
                    "statement": statement,
                    "category": infer_category(current_section, statement),
                    "service": detect_service(statement),
                    "severity": infer_severity(statement),
                    "source_excerpt": statement[:280],
                }
            )
        current_id = None
        current_lines = []

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        line = raw_line.replace("\f", "").strip()
        if not line:
            continue
        if APPENDIX_OR_SECTION.match(line) and started:
            flush_current()
            break
        if line.startswith("Recommendations"):
            started = True
            continue
        if not started:
            continue
        top_match = TOP_LEVEL_SECTION.match(line)
        if top_match and "Ensure " not in line and "Avoid " not in line:
            flush_current()
            current_section = normalize_statement(top_match.group(2))
            continue
        rec_match = RECOMMENDATION_START.match(line)
        if rec_match:
            flush_current()
            current_id = rec_match.group(1)
            current_lines = [rec_match.group(2)]
            continue
        if current_id:
            if re.fullmatch(r"\.{4,}\s*\d+", line) or re.fullmatch(r"Page\s+\d+", line, re.IGNORECASE):
                continue
            if line.startswith("Rationale") or line.startswith("Profile") or line.startswith("Description"):
                flush_current()
                continue
            if line[0].isdigit() and "Ensure " in line:
                flush_current()
                next_match = RECOMMENDATION_START.match(line)
                if next_match:
                    current_id = next_match.group(1)
                    current_lines = [next_match.group(2)]
                continue
            current_lines.append(line)

    flush_current()
    deduped: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for item in requirements:
        source_id = item["source_requirement_id"]
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        deduped.append(item)
    requirements = deduped
    if not requirements:
        notes.append("No CIS recommendation lines detected. Review PDF extraction quality.")
    return requirements, notes


def run(case_name: str) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    profile_path = working_dir / "project_profile.json"
    source_dir = case_dir / "input" / "cis_alibaba_cloud"
    output_path = working_dir / "benchmark_requirements.json"

    if not profile_path.exists():
        raise FileNotFoundError(f"Missing project profile: {profile_path}")
    load_json(profile_path)

    files = read_text_files(source_dir)
    if not files:
        raise FileNotFoundError(f"No readable CIS benchmark files found in {source_dir}")

    requirements: list[dict[str, str]] = []
    notes: list[str] = []
    for source_path, content in files:
        parsed, file_notes = extract_requirements(content)
        notes.extend(file_notes)
        for item in parsed:
            item["source_file"] = source_path.name
            requirements.append(item)

    if not requirements:
        raise ValueError("Unable to derive CIS benchmark requirements from provided source files.")

    output = {
        "document_name": "CIS Alibaba Cloud Foundations Benchmark",
        "source_files": [path.name for path, _ in files],
        "requirements": requirements,
        "benchmark_themes": build_theme_summary(requirements, "category"),
        "notes": notes,
    }
    write_json(output_path, output)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse CIS Alibaba Cloud benchmark")
    parser.add_argument("--case", required=True, dest="case_name")
    args = parser.parse_args()
    try:
        output_path = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
