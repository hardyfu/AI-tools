import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def render_markdown(data: dict[str, Any]) -> str:
    jurisdiction = data.get("jurisdiction", "unknown")
    research_date = data.get("research_date", "unknown")
    lines = [
        f"# Regulatory Research Notes - {jurisdiction}",
        "",
        f"- Research date: {research_date}",
        "",
        "## Sources",
        "",
    ]

    for source in data.get("web_sources", []):
        title = source.get("source_title", "unknown")
        link = source.get("source_link_or_reference", "unknown")
        relevance = source.get("relevance", "unknown")
        origin = source.get("source_origin", "unknown")
        excerpt = source.get("content_excerpt", "unknown")
        lines.append(f"- {title} ({origin})")
        lines.append(f"  - Reference: {link}")
        lines.append(f"  - Relevance: {relevance}")
        lines.append(f"  - Content excerpt: {excerpt}")

    lines.extend(["", "## Relevant Obligations", ""])
    for item in data.get("relevant_obligations", []):
        topic = item.get("topic", "unknown")
        summary = item.get("requirement_summary", "unknown")
        reference = item.get("source_reference", "unknown")
        lines.append(f"### {topic}")
        lines.append("")
        lines.append(summary)
        lines.append("")
        lines.append(f"Source: {reference}")
        lines.append("")

    open_issues = data.get("open_issues", [])
    lines.extend(["## Open Issues", ""])
    if open_issues:
        for issue in open_issues:
            lines.append(f"- {issue}")
    else:
        lines.append("- None recorded")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert regulatory_context.json to Markdown notes.")
    parser.add_argument("--input", required=True, dest="input_path", help="Input regulatory_context.json path")
    parser.add_argument("--output", required=True, dest="output_path", help="Output Markdown file path")
    args = parser.parse_args()

    input_path = Path(args.input_path)
    output_path = Path(args.output_path)
    if not input_path.exists():
        print(f"ERROR: Missing input JSON: {input_path}")
        return 1

    try:
        data = load_json(input_path)
        markdown = render_markdown(data)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1

    print(f"Wrote Markdown to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
