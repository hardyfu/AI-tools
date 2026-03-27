import argparse
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.ollama_client import OllamaClient, OllamaClientError


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def build_prompt(scope: dict[str, Any], global_policy_markdown: str, regulatory_context: dict[str, Any], template_markdown: str) -> str:
    return f"""
Create an integrated requirements document in Markdown.

Rules:
- Output Markdown only.
- Start the document with exactly this title line: `# Integrated Requirements`
- Follow the exact section order and headings from the provided template.
- Do not draft the final localized standard.
- Treat the global policy as the mandatory group baseline.
- Treat regulatory_context as the source of local legal and regulatory requirements.
- Show overlaps, local additions, conflicts, and unknowns explicitly.
- Keep requirement statements concise and traceable.

Template:
{template_markdown}

Scope profile:
{json.dumps(scope, ensure_ascii=True, indent=2)}

Normalized global policy markdown:
{global_policy_markdown}

Regulatory context:
{json.dumps(regulatory_context, ensure_ascii=True, indent=2)}
""".strip()


REQUIRED_HEADINGS = [
    "## Integration Metadata",
    "## Global Mandatory Requirements",
    "## Local Legal and Regulatory Requirements",
    "## Integrated Requirement Mapping",
    "## Local Additions",
    "## Conflicts and Constraints",
    "## Open Issues and Unknowns",
    "## Source References",
]


def normalize_markdown(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("markdown"):
            text = text[8:].strip()
    if text.startswith("## "):
        text = "# Integrated Requirements\n\n" + text
    return text.strip()


def validate_markdown(text: str) -> None:
    if not text.strip():
        raise OllamaClientError("Integrated requirements output was empty. See integrated_requirements.raw.txt for the raw model response.")
    if not text.startswith("# Integrated Requirements"):
        raise OllamaClientError("Integrated requirements output did not start with the required title.")
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        raise OllamaClientError(f"Integrated requirements output is missing required sections: {', '.join(missing)}")


def build_fallback_document(scope: dict[str, Any], regulatory_context: dict[str, Any]) -> str:
    policy_title = str(scope.get("source_policy", {}).get("document_title", "unknown")) or "unknown"
    jurisdiction = str(scope.get("localization_scope", {}).get("target_country_or_region", "unknown")) or "unknown"
    audience = str(scope.get("localization_scope", {}).get("target_audience", "unknown")) or "unknown"
    open_issues = regulatory_context.get("open_issues", []) if isinstance(regulatory_context.get("open_issues", []), list) else []
    references = regulatory_context.get("web_sources", []) if isinstance(regulatory_context.get("web_sources", []), list) else []
    open_issue_lines = "\n".join(
        f"- {str(item.get('issue', 'unknown'))}: {str(item.get('reason', 'unknown'))}"
        for item in open_issues[:5]
        if isinstance(item, dict)
    ) or "- No confirmed local legal source text was integrated."
    reference_lines = "\n".join(
        f"- {str(item.get('source_title', 'unknown'))}: {str(item.get('source_link_or_reference', 'unknown'))}"
        for item in references[:10]
        if isinstance(item, dict)
    ) or "- No confirmed official source reference available."
    return f"""# Integrated Requirements

## Integration Metadata
- Policy title: {policy_title}
- Jurisdiction: {jurisdiction}
- Audience: {audience}
- Integration mode: fallback_structure_due_to_empty_llm_output

## Global Mandatory Requirements
- Use the normalized global policy markdown as the mandatory group baseline.
- Extract implementation requirements from the global standard during downstream drafting.

## Local Legal and Regulatory Requirements
- No confirmed local legal or regulatory requirement text was integrated in this run.

## Integrated Requirement Mapping
- Mapping could not be completed because no confirmed local regulatory source text was available.

## Local Additions
- No validated local additions identified in this run.

## Conflicts and Constraints
- No direct conflict analysis completed because local regulatory source text was not confirmed.

## Open Issues and Unknowns
{open_issue_lines}

## Source References
{reference_lines}
""".strip()


def run(case_name: str) -> Path:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    scope_path = working_dir / "scope_profile.json"
    policy_parse_result_path = working_dir / "policy_parse_result.json"
    regulatory_context_path = working_dir / "regulatory_context.json"
    template_path = PROJECT_ROOT / "templates" / "integrated_requirements.template.md"

    for path in (scope_path, policy_parse_result_path, regulatory_context_path, template_path):
        if not path.exists():
            raise FileNotFoundError(f"Missing required input: {path}")

    scope = load_json(scope_path)
    policy_parse_result = load_json(policy_parse_result_path)
    regulatory_context = load_json(regulatory_context_path)
    normalized_policy_path = PROJECT_ROOT / policy_parse_result["normalized_markdown_path"]
    if not normalized_policy_path.exists():
        raise FileNotFoundError(f"Missing normalized global policy markdown: {normalized_policy_path}")

    client = OllamaClient()
    system = (
        "You are a strict requirements integrator. "
        "Return Markdown only. Do not include commentary outside the document."
    )
    raw = client.generate_text(
        build_prompt(scope, load_text(normalized_policy_path), regulatory_context, load_text(template_path)),
        system=system,
    )
    raw_output_path = working_dir / "integrated_requirements.raw.txt"
    raw_output_path.write_text(raw + "\n", encoding="utf-8")
    normalized = normalize_markdown(raw)
    if not normalized:
        normalized = build_fallback_document(scope, regulatory_context)
    validate_markdown(normalized)

    output_path = working_dir / "integrated_requirements.md"
    output_path.write_text(normalized + "\n", encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate integrated requirements markdown.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    args = parser.parse_args()
    try:
        output_path = run(args.case_name)
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Wrote integrated requirements to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
