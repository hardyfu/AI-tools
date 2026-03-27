import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from ollama_client import OllamaClient, OllamaClientError
from pdf_to_markdown import convert_pdf_to_markdown

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


def policy_markdown_path(case_name: str, policy_path: Path) -> Path:
    return PROJECT_ROOT / "cases" / case_name / "input" / "global_policy" / f"{policy_path.stem}.md"


def parse_controls_rule_fallback(markdown_text: str) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []
    current_section = "unknown"
    counter = 1
    for raw_line in markdown_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        if line.startswith("- "):
            source_text = line[2:].strip()
            title = re.sub(r"[^\w\s]", "", source_text).strip().split()
            requirement_title = " ".join(title[:6]) or "unknown"
            controls.append(
                {
                    "control_id": f"CTRL-{counter:03d}",
                    "control_domain": current_section,
                    "requirement_title": requirement_title,
                    "requirement_text": source_text,
                    "applicability": "unknown",
                    "priority": "medium",
                    "source_section": current_section,
                    "source_text": source_text,
                    "notes": "",
                    "status": "confirmed",
                }
            )
            counter += 1
    return controls


def build_agent01_prompt(markdown_text: str) -> str:
    return f"""
Parse the following policy markdown into structured control items.

Rules:
- Output valid JSON only.
- Return an object with one key: "controls".
- Each distinct requirement should become one control item.
- Default rule: one bullet maps to one control item.
- If a single bullet contains multiple independent "must" obligations that can stand alone operationally, splitting is allowed.
- Preserve source traceability.
- Do not generate guidance or legal analysis.
- Each control item must include:
  - control_domain
  - requirement_title
  - requirement_text
  - applicability
  - priority
  - source_section
  - source_text
  - notes
  - status
- Use "unknown" if applicability is ambiguous.
- Use one of: high, medium, low for priority.
- Use "confirmed" for status.

Policy markdown:

{markdown_text}
""".strip()


def normalize_control_item(item: dict[str, Any], counter: int) -> dict[str, Any]:
    return {
        "control_id": f"CTRL-{counter:03d}",
        "control_domain": str(item.get("control_domain", "unknown")) or "unknown",
        "requirement_title": str(item.get("requirement_title", "unknown")) or "unknown",
        "requirement_text": str(item.get("requirement_text", "unknown")) or "unknown",
        "applicability": str(item.get("applicability", "unknown")) or "unknown",
        "priority": str(item.get("priority", "medium")) or "medium",
        "source_section": str(item.get("source_section", "unknown")) or "unknown",
        "source_text": str(item.get("source_text", "unknown")) or "unknown",
        "notes": str(item.get("notes", "")),
        "status": "confirmed",
    }


def parse_controls_with_llm(markdown_text: str) -> list[dict[str, Any]]:
    client = OllamaClient()
    system = (
        "You are Agent01, a strict policy parser. "
        "Return only valid JSON that matches the requested schema. "
        "Do not include markdown fences or explanatory text."
    )
    payload = client.generate_json(build_agent01_prompt(markdown_text), system=system)
    controls = payload.get("controls")
    if not isinstance(controls, list):
        raise OllamaClientError("Agent01 LLM output did not contain a controls list.")
    normalized = []
    for index, item in enumerate(controls, start=1):
        if not isinstance(item, dict):
            raise OllamaClientError("Agent01 LLM output contains a non-object control item.")
        normalized.append(normalize_control_item(item, index))
    return normalized


def run(policy_file_path: str, *, allow_rule_fallback: bool = True) -> tuple[Path, Path | None]:
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

    converted_markdown_path: Path | None = None
    if policy_path.suffix.lower() == ".pdf":
        converted_markdown_path = policy_markdown_path(case_name, policy_path)
        convert_pdf_to_markdown(policy_path, converted_markdown_path)
        markdown_path = converted_markdown_path
    else:
        markdown_path = policy_path

    markdown_text = markdown_path.read_text(encoding="utf-8")
    try:
        controls = parse_controls_with_llm(markdown_text)
    except Exception:
        if not allow_rule_fallback:
            raise
        controls = parse_controls_rule_fallback(markdown_text)
    output = {
        "policy_file_path": str(markdown_path.relative_to(PROJECT_ROOT)),
        "scope_profile_path": str(scope_path.relative_to(PROJECT_ROOT)),
        "controls": controls,
    }
    output_path = case_dir / "working" / "parsed_controls.json"
    write_json(output_path, output)
    return output_path, converted_markdown_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Agent01 policy parsing.")
    parser.add_argument("--policy-file", required=True, dest="policy_file", help="Path to policy Markdown or PDF")
    parser.add_argument(
        "--no-rule-fallback",
        action="store_true",
        help="Fail instead of using the local rule-based fallback if Ollama parsing fails",
    )
    args = parser.parse_args()
    try:
        output_path, converted = run(args.policy_file, allow_rule_fallback=not args.no_rule_fallback)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    if converted:
        print(f"Converted PDF to Markdown: {converted}")
    print(f"Wrote parsed controls to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
