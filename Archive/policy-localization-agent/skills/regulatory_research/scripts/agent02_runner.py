import argparse
import json
from getpass import getpass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[3]

from runtime.ollama_client import OllamaClient, OllamaClientError
from runtime.search_results_to_markdown import render_markdown
from runtime.tavily_client import TavilyClient, TavilyClientError
from runtime.tavily_mcp_client import TavilyMCPClient, TavilyMCPError

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


OFFICIAL_CHINA_REGULATORY_DOMAINS = [
    "gov.cn",
    "cac.gov.cn",
    "miit.gov.cn",
    "samr.gov.cn",
    "beian.gov.cn",
]

REGULATORY_KEYWORDS = [
    "law",
    "regulation",
    "rules",
    "measures",
    "provisions",
    "decision",
    "notice",
    "regulatory",
    "cybersecurity",
    "data security",
    "personal information",
    "critical information infrastructure",
    "government",
    "ministry",
    "网信",
    "网络安全",
    "数据安全",
    "个人信息",
    "industry standard",
    "industry regulation",
    "specification",
    "standard",
    "guideline",
    "标准",
    "规范",
    "指引",
    "导则",
]

PRIMARY_TEXT_KEYWORDS = [
    "全文",
    "原文",
    "正式文本",
    "official text",
    "full text",
    "text of",
]

NON_PRIMARY_SOURCE_KEYWORDS = [
    "news",
    "article",
    "blog",
    "commentary",
    "analysis",
    "interpretation",
    "white paper",
    "report",
    "press release",
    "媒体",
    "解读",
    "评论",
    "白皮书",
    "报道",
    "新闻",
]

LAW_TITLE_KEYWORDS = [
    "法",
    "条例",
    "规定",
    "办法",
    "通知",
    "决定",
    "细则",
    "标准",
    "规范",
    "导则",
    "指引",
    "measures",
    "provisions",
    "rules",
    "regulation",
    "law",
    "notice",
    "standard",
    "specification",
    "guideline",
]


def build_discovery_queries(scope: dict[str, Any]) -> list[dict[str, Any]]:
    jurisdiction = scope["localization_scope"].get("target_country_or_region", "unknown")
    policy_title = scope["source_policy"].get("document_title", "global policy")
    objective = str(scope.get("business_context", {}).get("localization_objective", "") or "")
    audience = str(scope.get("localization_scope", {}).get("target_audience", "") or "")
    thematic_terms = "云安全 网络安全 数据安全 个人信息 关键信息基础设施 cloud security cybersecurity data security personal information critical information infrastructure"
    queries: list[dict[str, Any]] = [
        {
            "query": f"{jurisdiction} 与 {policy_title} 相关的 官方 法律 法规 行业规定 标准 规范 指引 办法 通知 原文 全文",
            "topic": "general",
            "include_domains": OFFICIAL_CHINA_REGULATORY_DOMAINS,
            "intent": "official_original_binding_documents_related_to_policy",
        },
        {
            "query": f"{jurisdiction} binding laws regulations industry standards related to {policy_title} official original full text",
            "topic": "general",
            "include_domains": OFFICIAL_CHINA_REGULATORY_DOMAINS,
            "intent": "official_full_text_binding_sources_related_to_policy",
        },
        {
            "query": f"{jurisdiction} 与 {policy_title} 和 {thematic_terms} 相关的 官方 法律 法规 行业规定 标准 规范 指引 办法 通知 原文 全文 {audience}",
            "topic": "general",
            "include_domains": OFFICIAL_CHINA_REGULATORY_DOMAINS,
            "intent": "official_original_thematic_binding_documents_related_to_policy",
        },
        {
            "query": f"{jurisdiction} official binding laws regulations standards specifications related to {policy_title} {thematic_terms} original full text {objective}",
            "topic": "general",
            "include_domains": OFFICIAL_CHINA_REGULATORY_DOMAINS,
            "intent": "official_full_text_thematic_binding_sources_related_to_policy",
        },
    ]
    return [item for item in queries if "unknown" not in str(item["query"]).lower()]


def build_detail_queries(jurisdiction: str, discovery_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for result in discovery_results:
        for item in result.get("results", [])[:3]:
            title = str(item.get("title", "")).strip()
            url = str(item.get("url", "")).strip()
            if not title or not url or not is_official_domain(url):
                continue
            query = f"{jurisdiction} {title} 原文 全文 official full text"
            if query in seen:
                continue
            seen.add(query)
            queries.append(
                {
                    "query": query,
                    "topic": "general",
                    "include_domains": OFFICIAL_CHINA_REGULATORY_DOMAINS,
                    "intent": "law_content",
                    "seed_title": title,
                    "seed_url": url,
                }
            )
    return queries


def infer_obligations(search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    obligations: list[dict[str, Any]] = []
    for result in search_results:
        query = result["query"]
        for item in result.get("results", [])[:2]:
            obligations.append(
                {
                    "topic": result.get("intent", query),
                    "requirement_summary": item.get("snippet") or item.get("content") or "unknown",
                    "source_reference": item.get("url", "unknown"),
                    "related_topics_or_control_domains": result.get("related_topics_or_control_domains", []),
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


def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def is_official_domain(url: str) -> bool:
    domain = extract_domain(url)
    return any(domain == allowed or domain.endswith(f".{allowed}") for allowed in OFFICIAL_CHINA_REGULATORY_DOMAINS)


def result_is_relevant(item: dict[str, Any]) -> bool:
    url = str(item.get("url", ""))
    haystack = " ".join(
        str(item.get(key, "")) for key in ("title", "content", "snippet")
    ).lower()
    if any(keyword in haystack for keyword in NON_PRIMARY_SOURCE_KEYWORDS):
        return False
    if not is_official_domain(url):
        return False
    has_regulatory_signal = any(keyword in haystack for keyword in REGULATORY_KEYWORDS)
    has_law_title_signal = any(keyword in haystack for keyword in LAW_TITLE_KEYWORDS)
    has_primary_text_signal = any(keyword in haystack for keyword in PRIMARY_TEXT_KEYWORDS)
    return (has_regulatory_signal or has_law_title_signal) and has_primary_text_signal


def filter_and_dedupe_results(items: list[dict[str, Any]], max_items: int) -> list[dict[str, Any]]:
    filtered = [item for item in items if isinstance(item, dict) and result_is_relevant(item)]
    if any(is_official_domain(str(item.get("url", ""))) for item in filtered):
        filtered = [item for item in filtered if is_official_domain(str(item.get("url", "")))]
    ranked = sorted(
        filtered,
        key=lambda item: (0 if is_official_domain(str(item.get("url", ""))) else 1, str(item.get("title", ""))),
    )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in ranked:
        url = str(item.get("url", "")).strip()
        title = str(item.get("title", "")).strip()
        key = url or title
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


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
- Only use official laws, regulations, rules, measures, and notices that appear in the search results.
- Exclude commentary, white papers, summaries, blog posts, and media coverage.
- Prefer original/full-text law and regulation pages only.
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
  - content_excerpt
  - related_topics_or_control_domains
- relevant_obligations items must include:
  - topic
  - requirement_summary
  - source_reference
  - related_topics_or_control_domains
  - status
- Prefer obligations that quote or paraphrase the actual content of the law or regulation, not just search-result titles.
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
                "content_excerpt": str(item.get("content_excerpt", "unknown")) or "unknown",
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
                    "content_excerpt": (file_info.get("content") or "")[:600] or "unknown",
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
                        "relevance": result.get("intent", result["query"]),
                        "content_excerpt": item.get("raw_content") or item.get("content") or item.get("snippet") or "unknown",
                        "related_topics_or_control_domains": result.get("related_topics_or_control_domains", []),
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
                "content_excerpt": "unknown",
                "related_topics_or_control_domains": [],
            }
        ],
        "relevant_obligations": obligations,
        "open_issues": synthesized.get("open_issues", []) if isinstance(synthesized.get("open_issues", []), list) else [],
        "research_strategy": "search official laws/regulations by policy title + jurisdiction, then search the content of discovered laws/regulations",
        "notes": str(synthesized.get("notes", f"Generated by Agent02 {provider}-based regulatory research runner."))
        or f"Generated by Agent02 {provider}-based regulatory research runner.",
    }


def search_with_tavily_mcp(queries: list[dict[str, Any]], max_results: int, *, api_key: str) -> list[dict[str, Any]]:
    search_results = []
    with TavilyMCPClient(api_key=api_key) as client:
        for query_info in queries:
            response = client.search(
                query_info["query"],
                topic=query_info.get("topic", "general"),
                max_results=max_results,
                include_domains=query_info.get("include_domains"),
                include_raw_content=True,
            )
            search_results.append(
                {
                    "query": query_info["query"],
                    "intent": query_info.get("intent", "unknown"),
                    "related_topics_or_control_domains": query_info.get("related_topics_or_control_domains", []),
                    "results": filter_and_dedupe_results(response.get("results", []), max_results),
                }
            )
    return search_results


def search_with_tavily_api(queries: list[dict[str, Any]], max_results: int, *, api_key: str) -> list[dict[str, Any]]:
    client = TavilyClient(api_key=api_key)
    search_results = []
    for query_info in queries:
        response = client.search(
            query_info["query"],
            topic=query_info.get("topic", "general"),
            max_results=max_results,
            include_domains=query_info.get("include_domains"),
            include_raw_content=True,
        )
        search_results.append(
            {
                "query": query_info["query"],
                "intent": query_info.get("intent", "unknown"),
                "related_topics_or_control_domains": query_info.get("related_topics_or_control_domains", []),
                "results": filter_and_dedupe_results(response.get("results", []), max_results),
            }
        )
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
    discovery_queries = build_discovery_queries(scope)
    local_files = read_markdown_files(paths["local_regulations_dir"])
    selected_provider = provider
    try:
        if provider == "mcp":
            discovery_results = search_with_tavily_mcp(discovery_queries, max_results, api_key=api_key)
        else:
            discovery_results = search_with_tavily_api(discovery_queries, max_results, api_key=api_key)
    except (TavilyMCPError, TavilyClientError) as exc:
        if provider != "mcp" or not allow_api_fallback:
            raise
        print(f"Tavily MCP unavailable ({exc}). Falling back to Tavily HTTP API.")
        selected_provider = "api_fallback"
        discovery_results = search_with_tavily_api(discovery_queries, max_results, api_key=api_key)

    jurisdiction = scope["localization_scope"].get("target_country_or_region", "unknown")
    detail_queries = build_detail_queries(jurisdiction, discovery_results)
    if detail_queries:
        if selected_provider in {"mcp", "api_fallback"} and provider == "mcp":
            detail_results = search_with_tavily_api(detail_queries, max_results, api_key=api_key) if selected_provider == "api_fallback" else search_with_tavily_mcp(detail_queries, max_results, api_key=api_key)
        else:
            detail_results = search_with_tavily_api(detail_queries, max_results, api_key=api_key)
    else:
        detail_results = []

    search_results = discovery_results + detail_results

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
