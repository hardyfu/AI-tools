import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from ollama_client import OllamaClient, OllamaClientError

def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def build_prompt(scope: dict[str, Any], parsed_controls: dict[str, Any], regulatory_context: dict[str, Any]) -> str:
    return f"""
Create a localization decision plan from the provided inputs.

Rules:
- Output valid JSON only.
- Return an object with one key: "localization_decisions".
- Create exactly one decision item per control in parsed_controls.
- Preserve the original control intent unless local context clearly requires adaptation.
- Use one of these decision types: adopt, adapt, supplement, flag.
- Each decision item must include:
  - control_id
  - control_domain
  - requirement_title
  - requirement_text
  - source_section
  - decision_type
  - local_applicability
  - decision_summary
  - decision_rationale
  - local_references
  - implementation_notes
  - unresolved_issues
  - status
- Use "confirmed" for status.
- If uncertainty exists, include it in unresolved_issues instead of hiding it.

Scope profile:
{json.dumps(scope, ensure_ascii=True, indent=2)}

Parsed controls:
{json.dumps(parsed_controls, ensure_ascii=True, indent=2)}

Regulatory context:
{json.dumps(regulatory_context, ensure_ascii=True, indent=2)}
""".strip()


def normalize_decision(item: dict[str, Any], control: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_id": control.get("control_id", "unknown"),
        "control_domain": control.get("control_domain", "unknown"),
        "requirement_title": control.get("requirement_title", "unknown"),
        "requirement_text": control.get("requirement_text", "unknown"),
        "source_section": control.get("source_section", "unknown"),
        "decision_type": str(item.get("decision_type", "adopt")) or "adopt",
        "local_applicability": str(item.get("local_applicability", "unknown")) or "unknown",
        "decision_summary": str(item.get("decision_summary", "unknown")) or "unknown",
        "decision_rationale": str(item.get("decision_rationale", "unknown")) or "unknown",
        "local_references": item.get("local_references", []) if isinstance(item.get("local_references", []), list) else [],
        "implementation_notes": str(item.get("implementation_notes", "unknown")) or "unknown",
        "unresolved_issues": item.get("unresolved_issues", []) if isinstance(item.get("unresolved_issues", []), list) else [],
        "status": "confirmed",
    }


def fallback_decisions(parsed_controls: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = []
    for control in parsed_controls.get("controls", []):
        decisions.append(
            {
                "control_id": control.get("control_id", "unknown"),
                "control_domain": control.get("control_domain", "unknown"),
                "requirement_title": control.get("requirement_title", "unknown"),
                "requirement_text": control.get("requirement_text", "unknown"),
                "source_section": control.get("source_section", "unknown"),
                "decision_type": "adopt",
                "local_applicability": "unknown",
                "decision_summary": "Adopt the global control unless local regulatory review requires change.",
                "decision_rationale": "Fallback decision generated because LLM-backed localization design was unavailable.",
                "local_references": [],
                "implementation_notes": "Review against regulatory_context.json before downstream writing.",
                "unresolved_issues": [],
                "status": "confirmed",
            }
        )
    return decisions


def generate_decisions_with_llm(
    scope: dict[str, Any],
    parsed_controls: dict[str, Any],
    regulatory_context: dict[str, Any],
) -> list[dict[str, Any]]:
    client = OllamaClient()
    system = (
        "You are Agent03, a strict localization designer. "
        "Return only valid JSON. Do not include markdown fences or commentary."
    )
    payload = client.generate_json(build_prompt(scope, parsed_controls, regulatory_context), system=system)
    raw_items = payload.get("localization_decisions")
    controls = parsed_controls.get("controls", [])
    if not isinstance(raw_items, list):
        raise OllamaClientError("Agent03 LLM output did not contain a localization_decisions list.")
    if len(raw_items) != len(controls):
        raise OllamaClientError("Agent03 LLM output count does not match parsed controls count.")
    normalized = []
    for item, control in zip(raw_items, controls, strict=True):
        if not isinstance(item, dict):
            raise OllamaClientError("Agent03 LLM output contains a non-object decision item.")
        normalized.append(normalize_decision(item, control))
    return normalized


def run(case_name: str, *, allow_fallback: bool = True) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    scope_path = working_dir / "scope_profile.json"
    parsed_controls_path = working_dir / "parsed_controls.json"
    regulatory_context_path = working_dir / "regulatory_context.json"

    for path in (scope_path, parsed_controls_path, regulatory_context_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    scope = load_json(scope_path)
    parsed_controls = load_json(parsed_controls_path)
    regulatory_context = load_json(regulatory_context_path)

    try:
        decisions = generate_decisions_with_llm(scope, parsed_controls, regulatory_context)
    except Exception:
        if not allow_fallback:
            raise
        decisions = fallback_decisions(parsed_controls)

    output = {
        "case_name": case_name,
        "jurisdiction": scope.get("localization_scope", {}).get("target_country_or_region", "unknown"),
        "scope_profile_path": str(scope_path.relative_to(PROJECT_ROOT)),
        "parsed_controls_path": str(parsed_controls_path.relative_to(PROJECT_ROOT)),
        "regulatory_context_path": str(regulatory_context_path.relative_to(PROJECT_ROOT)),
        "localization_decisions": decisions,
    }
    output_path = working_dir / "localization_plan.json"
    write_json(output_path, output)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Agent03 localization design.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Fail instead of using the local fallback if Ollama generation fails",
    )
    args = parser.parse_args()
    try:
        output_path = run(args.case_name, allow_fallback=not args.no_fallback)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Wrote localization plan to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
