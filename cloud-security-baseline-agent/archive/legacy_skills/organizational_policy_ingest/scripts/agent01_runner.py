import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.text_utils import build_theme_summary, categorize_text, detect_priority, load_json, read_text_files, write_json


REQUIREMENT_START = re.compile(r"^\s*(2\.\d+\.\d+[A-Z]?)\.?\s+(.*)$")
SECTION_HEADING = re.compile(r"^\s*2\.\d+\.\s+(.+?)\s*$")
NOISE_PATTERNS = [
    re.compile(r"^\s*STATUS\s+SECURITY LEVEL", re.IGNORECASE),
    re.compile(r"^\s*Approved\s+Internal", re.IGNORECASE),
    re.compile(r"^\s*DOCUMENT ID\.", re.IGNORECASE),
    re.compile(r"^\s*© Copyright", re.IGNORECASE),
    re.compile(r"^\s*PAGE\s*$", re.IGNORECASE),
    re.compile(r"^\s*\d+/\d+\s*$"),
]
TRAILING_APPLICABILITY = re.compile(r"\b(?:[OMRPN/Ax]{1,3}\s+){3,}[OMRPN/Ax]{1,3}\s*$")
INLINE_APPLICABILITY = re.compile(r"\b(?:[OMRPN/Ax]{1,3}\s+){4,}[OMRPN/Ax]{1,3}\b")


def clean_text(text: str) -> str:
    text = text.replace("\f", "\n").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"([A-Za-z])-\n\s*([A-Za-z])", r"\1\2", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def normalize_statement(text: str) -> str:
    text = INLINE_APPLICABILITY.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    text = TRAILING_APPLICABILITY.sub("", text).strip()
    return text


def is_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith("CLOU D S ECUR IT Y STA NDARD") or stripped.startswith("Cloud Security Standard"):
        return True
    if set(stripped) <= {"-", ".", " "}:
        return True
    return any(pattern.search(stripped) for pattern in NOISE_PATTERNS)


def extract_requirements(text: str) -> list[dict[str, str]]:
    requirements: list[dict[str, str]] = []
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
        if len(statement) >= 12 and "withdrawn" not in statement.lower():
            requirements.append(
                {
                    "requirement_id": f"ORG-{len(requirements) + 1:03d}",
                    "source_requirement_id": current_id,
                    "section": current_section,
                    "statement": statement,
                    "category": categorize_text(statement),
                    "priority": detect_priority(statement),
                    "source_excerpt": statement[:280],
                }
            )
        current_id = None
        current_lines = []

    for raw_line in clean_text(text).splitlines():
        line = raw_line.strip()
        if is_noise(line):
            continue
        section_match = SECTION_HEADING.match(line)
        if section_match and "....." not in line:
            if started:
                flush_current()
            started = True
            current_section = normalize_statement(section_match.group(1))
            continue
        if not started and REQUIREMENT_START.match(line):
            started = True
        if re.match(r"^\s*3\.\s+Additional information\b", line, re.IGNORECASE) and requirements:
            flush_current()
            break
        if not started:
            continue
        requirement_match = REQUIREMENT_START.match(line)
        if requirement_match:
            flush_current()
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

    flush_current()
    return requirements


def run(case_name: str) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    profile_path = working_dir / "project_profile.json"
    source_dir = case_dir / "input" / "organization_policy"
    output_path = working_dir / "organizational_requirements.json"

    if not profile_path.exists():
        raise FileNotFoundError(f"Missing project profile: {profile_path}")
    load_json(profile_path)

    files = read_text_files(source_dir)
    if not files:
        raise FileNotFoundError(f"No readable organization policy files found in {source_dir}")

    requirements: list[dict[str, str]] = []
    notes: list[str] = []
    for source_path, content in files:
        parsed = extract_requirements(content)
        if not parsed:
            notes.append(f"No numbered requirement rows detected in {source_path.name}. Review source formatting.")
            continue
        for item in parsed:
            item["source_file"] = source_path.name
            requirements.append(item)

    if not requirements:
        raise ValueError("Unable to derive organizational requirements from provided source files.")

    output = {
        "document_name": "cloud security standard",
        "source_files": [path.name for path, _ in files],
        "requirements": requirements,
        "strategy_signals": build_theme_summary(requirements, "category"),
        "notes": notes,
    }
    write_json(output_path, output)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse organizational cloud security standard")
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
