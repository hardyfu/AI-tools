import argparse
import json
import re
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.ollama_client import OllamaClient, OllamaClientError


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_prompt(scope: dict[str, Any], integrated_requirements_markdown: str, template_markdown: str) -> str:
    return f"""
Draft a localized internal standard document in Markdown.

Rules:
- Output Markdown only.
- Start the document with exactly this title line: `# Localized Standard Draft`
- Follow the exact section order and headings from the provided template.
- Write a standard document, not a decision list and not free-form prose.
- Use the integrated requirements document as the drafting baseline.
- If a local requirement adds obligations, state them explicitly.
- If a local requirement conflicts with a global requirement, flag the conflict explicitly.
- If evidence is weak or unclear, record it under "Open Issues and Unknowns".
- Keep references traceable to the provided integrated requirements document.
- Keep the writing practical for the target internal audience.

Template:
{template_markdown}

Scope profile:
{json.dumps(scope, ensure_ascii=True, indent=2)}

Integrated requirements:
{integrated_requirements_markdown}
""".strip()


REQUIRED_HEADINGS = [
    "## Document Metadata",
    "## Purpose",
    "## Scope and Audience",
    "## Global Standard Requirements",
    "## Local Regulatory Requirements",
    "## Localized Implementation Requirements",
    "## Roles and Responsibilities",
    "## Exceptions and Escalation",
    "## References",
    "## Open Issues and Unknowns",
]


def normalize_draft(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    if not text.startswith("# "):
        first_heading = text.find("## ")
        if first_heading > 0:
            text = text[first_heading:].strip()
    if text.startswith("## "):
        text = "# Localized Standard Draft\n\n" + text
    return text.strip()


def validate_draft(draft: str) -> None:
    if not draft.startswith("# "):
        raise OllamaClientError("Localization draft did not return a Markdown document.")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in draft]
    if missing:
        raise OllamaClientError(f"Localization draft is missing required sections: {', '.join(missing)}")


def run(case_name: str) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    scope_path = working_dir / "scope_profile.json"
    integrated_requirements_path = working_dir / "integrated_requirements.md"
    template_path = PROJECT_ROOT / "templates" / "localized_standard.template.md"

    for path in (scope_path, integrated_requirements_path, template_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    scope = load_json(scope_path)

    client = OllamaClient()
    system = (
        "You are a strict policy localization drafter. "
        "Return Markdown only. Do not include commentary outside the document."
    )
    raw_draft = client.generate_text(
        build_prompt(
            scope,
            load_text(integrated_requirements_path),
            load_text(template_path),
        ),
        system=system,
    ).strip()
    raw_output_path = working_dir / "localized_standard_draft.raw.txt"
    raw_output_path.write_text(raw_draft + "\n", encoding="utf-8")
    draft = normalize_draft(raw_draft)
    validate_draft(draft)

    output_path = working_dir / "localized_standard_draft.md"
    output_path.write_text(draft + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Draft a localized standard document.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    args = parser.parse_args()
    try:
        output_path = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Wrote localized standard draft to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
