import argparse
import json
import sys
from getpass import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from ollama_client import OllamaClient, OllamaClientError
from search_results_to_markdown import render_markdown
from tavily_client import TavilyClient, TavilyClientError
from tavily_mcp_client import TavilyMCPClient, TavilyMCPError

def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def read_markdown_files(directory: Path) -> list[dict[str, str]]:
    if not directory.exists():
        return []
    files = []
    for path in sorted(directory.glob("*.md")):
        files.append({"file_name": path.name, "path": str(path), "content": path.read_text(encoding="utf-8")})
    return files


def derive_case_paths(case_name: str) -> dict[str, Path]:
    case_dir = PROJECT_ROOT / "cases" / case_name
    working_dir = case_dir / "working"
    return {
        "case_dir": case_dir,
        "working_dir": working_dir,
        "scope_profile": working_dir / "scope_profile.json",
        "local_regulations_dir": case_dir / "input" / "local_regulations",
        "output": working_dir / "regulatory_context.json",
    }


def build_queries(scope: dict[str, Any]) -> list[dict[str, str]]:
    jurisdiction = scope["localization_scope"].get("target_country_or_region", "unknown")
    policy_title = scope["source_policy"].get("document_title", "global policy")
    objective = scope["business_context"].get("localization_objective", "policy localization")
    team = scope["localization_scope"].get("target_team", "local team")
    topics = [
        f"{jurisdiction} laws regulations relevant to {policy_title}",
        f"{jurisdiction} regulatory requirements for {team}",
        f"{jurisdiction} cybersecurity data security requirements for {objective}",
    ]
    return [{"query": query, "topic": "news"} for query in topics if "unknown" not in query.lower()]


def infer_obligations(search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for result in search_results:
        query = result["query"]
        for item in result.get("results", [])[:2]:
            obligations.append(
                {
                    "topic": query,
                    "requirement_summary": item.get("content") or item.get("snippet") or "unknown",
                    "source_reference": item.get("url", "unknown"),
                    "related_topics_or_control_domains": [],
                    "status": "confirmed",
                }
            )
    return obligations or [
        {
            "topic": "unknown",
            "requirement_summary": "unknown",
            "source_reference": "unknown",
            "related_topics_or_control_domains": [],
            "status": "confirmed",
        }
    ]


def build_agent02_prompt(
    scope: dict[str, Any],
    local_files: list[dict[str, str]],
    search_results: list[dict[str, Any]],
) -> str:
    return f"""
Create a structured regulatory context from the provided case scope, optional local regulation files, and Tavily research results.

Rules:
- Output valid JSON only.
- Return an object with keys:
  - web_sources
  - relevant_obligations
  - open_issues
  - notes
- Preserve source traceability.
- Prefer near-source phrasing for obligation summaries.
- Do not make localization decisions.
- Do not hide uncertainty.
- web_sources items must include:
  - source_title
  - source_link_or_reference
  - source_type
  - source_origin
  - relevance
  - related_topics_or_control_domains
- relevant_obligations items must include:
  - topic
  - requirement_summary
  - source_reference
  - related_topics_or_control_domains
  - status
- Use "confirmed" for status.

Scope profile:
{json.dumps(scope, ensure_ascii=True, indent=2)}

Uploaded local regulation markdown files:
{json.dumps(local_files, ensure_ascii=True, indent=2)}

Tavily research results:
{json.dumps(search_results, ensure_ascii=True, indent=2)}
""".strip()


def normalize_web_sources(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "source_title": str(item.get("source_title", "unknown")) or "unknown",
                "source_link_or_reference": str(item.get("source_link_or_reference", "unknown")) or "unknown",
                "source_type": str(item.get("source_type", "unknown")) or "unknown",
                "source_origin": str(item.get("source_origin", "web")) or "web",
                "relevance": str(item.get("relevance", "unknown")) or "unknown",
                "related_topics_or_control_domains": item.get("related_topics_or_control_domains", [])
                if isinstance(item.get("related_topics_or_control_domains", []), list)
                else [],
            }
        )
    return normalized


def normalize_obligations(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    normalized = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "topic": str(item.get("topic", "unknown")) or "unknown",
                "requirement_summary": str(item.get("requirement_summary", "unknown")) or "unknown",
                "source_reference": str(item.get("source_reference", "unknown")) or "unknown",
                "related_topics_or_control_domains": item.get("related_topics_or_control_domains", [])
                if isinstance(item.get("related_topics_or_control_domains", []), list)
                else [],
                "status": "confirmed",
            }
        )
    return normalized


def synthesize_output_with_llm(
    scope: dict[str, Any],
    local_files: list[dict[str, str]],
    search_results: list[dict[str, Any]],
) -> dict[str, Any]:
    client = OllamaClient()
    system = (
        "You are Agent02, a strict regulatory research synthesizer. "
        "Return only valid JSON with the requested schema. "
        "Do not include markdown fences or commentary."
    )
    payload = client.generate_json(build_agent02_prompt(scope, local_files, search_results), system=system)
    return {
        "web_sources": normalize_web_sources(payload.get("web_sources", [])),
        "relevant_obligations": normalize_obligations(payload.get("relevant_obligations", [])),
        "open_issues": payload.get("open_issues", []) if isinstance(payload.get("open_issues", []), list) else [],
        "notes": str(payload.get("notes", "Generated by Agent02 LLM synthesis.")) or "Generated by Agent02 LLM synthesis.",
    }


def build_output(
    scope: dict[str, Any],
    local_files: list[dict[str, str]],
    search_results: list[dict[str, Any]],
    *,
    provider: str,
) -> dict[str, Any]:
    jurisdiction = scope["localization_scope"].get("target_country_or_region", "unknown")
    try:
        synthesized = synthesize_output_with_llm(scope, local_files, search_results)
    except Exception:
        synthesized = {
            "web_sources": [],
            "relevant_obligations": [],
            "open_issues": [],
            "notes": "Generated by Agent02 fallback synthesis.",
        }
    sources: list[dict[str, Any]] = normalize_web_sources(synthesized.get("web_sources", []))
    obligations = normalize_obligations(synthesized.get("relevant_obligations", []))
    if not sources:
        for file_info in local_files:
            sources.append(
                {
                    "source_title": file_info["file_name"],
                    "source_link_or_reference": file_info["path"],
                    "source_type": "uploaded_markdown",
                    "source_origin": "uploaded_file",
                    "relevance": "user-provided local regulation source",
                    "related_topics_or_control_domains": [],
                }
            )
        for result in search_results:
            for item in result.get("results", []):
                sources.append(
                    {
                        "source_title": item.get("title", "unknown"),
                        "source_link_or_reference": item.get("url", "unknown"),
                        "source_type": "web_search_result",
                        "source_origin": provider,
                        "relevance": result["query"],
                        "related_topics_or_control_domains": [],
                    }
                )
    if not obligations:
        obligations = infer_obligations(search_results)

    return {
        "jurisdiction": jurisdiction,
        "research_date": datetime.now(timezone.utc).date().isoformat(),
        "local_regulation_files_reviewed": [item["path"] for item in local_files],
        "web_sources": sources or [
            {
                "source_title": "unknown",
                "source_link_or_reference": "unknown",
                "source_type": "unknown",
                "source_origin": "web",
                "relevance": "unknown",
                "related_topics_or_control_domains": [],
            }
        ],
        "relevant_obligations": obligations,
        "open_issues": synthesized.get("open_issues", []) if isinstance(synthesized.get("open_issues", []), list) else [],
        "notes": str(synthesized.get("notes", f"Generated by Agent02 {provider}-based regulatory research runner."))
        or f"Generated by Agent02 {provider}-based regulatory research runner.",
    }


def search_with_tavily_mcp(queries: list[dict[str, str]], max_results: int, *, api_key: str) -> list[dict[str, Any]]:
    search_results = []
    with TavilyMCPClient(api_key=api_key) as client:
        for query_info in queries:
            response = client.search(query_info["query"], topic=query_info["topic"], max_results=max_results)
            search_results.append({"query": query_info["query"], "results": response.get("results", [])})
    return search_results


def search_with_tavily_api(queries: list[dict[str, str]], max_results: int, *, api_key: str) -> list[dict[str, Any]]:
    client = TavilyClient(api_key=api_key)
    search_results = []
    for query_info in queries:
        response = client.search(query_info["query"], topic=query_info["topic"], max_results=max_results)
        search_results.append({"query": query_info["query"], "results": response.get("results", [])})
    return search_results


def run(
    case_name: str,
    max_results: int,
    *,
    provider: str = "mcp",
    allow_api_fallback: bool = True,
    api_key: str,
) -> Path:
    paths = derive_case_paths(case_name)
    scope_path = paths["scope_profile"]
    if not scope_path.exists():
        raise FileNotFoundError(f"Missing scope profile: {scope_path}")

    scope = load_json(scope_path)
    queries = build_queries(scope)
    local_files = read_markdown_files(paths["local_regulations_dir"])
    selected_provider = provider
    try:
        if provider == "mcp":
            search_results = search_with_tavily_mcp(queries, max_results, api_key=api_key)
        else:
            search_results = search_with_tavily_api(queries, max_results, api_key=api_key)
    except (TavilyMCPError, TavilyClientError):
        if provider != "mcp" or not allow_api_fallback:
            raise
        selected_provider = "api_fallback"
        search_results = search_with_tavily_api(queries, max_results, api_key=api_key)

    output = build_output(scope, local_files, search_results, provider=selected_provider)
    write_json(paths["output"], output)
    markdown_path = paths["working_dir"] / "regulatory_research.md"
    markdown_path.write_text(render_markdown(output), encoding="utf-8")
    return paths["output"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Agent02 regulatory research with Tavily.")
    parser.add_argument("--case", required=True, dest="case_name", help="Case name under cases/<case_name>")
    parser.add_argument("--max-results", type=int, default=5, help="Max Tavily results per query")
    parser.add_argument(
        "--provider",
        choices=["mcp", "api"],
        default="mcp",
        help="Preferred Tavily provider. mcp is the standard path; api is local fallback.",
    )
    parser.add_argument(
        "--no-api-fallback",
        action="store_true",
        help="Fail instead of falling back to the Tavily HTTP API when MCP search is unavailable.",
    )
    args = parser.parse_args()
    try:
        api_key = getpass("Enter Tavily API key for this Agent02 run: ").strip()
        if not api_key:
            raise TavilyMCPError("Tavily API key input was empty.")
        output = run(
            args.case_name,
            args.max_results,
            provider=args.provider,
            allow_api_fallback=not args.no_api_fallback,
            api_key=api_key,
        )
    except (FileNotFoundError, TavilyClientError, TavilyMCPError, OllamaClientError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"Wrote regulatory context to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
