---
name: regulatory-research
description: Use this skill when a policy localization case needs a structured view of relevant local laws and regulations. This skill reads `scope_profile.json`, optional local regulation markdown files, and Tavily MCP-based web research to produce `regulatory_context.json`.
---

# Regulatory Research

Use this skill only for local law and regulation research.

## Goal

Identify and structure the local legal and regulatory context relevant to the case, with explicit source traceability and uncertainty handling.

## Inputs

- `cases/<case_name>/working/scope_profile.json`
- `cases/<case_name>/input/local_regulations/*.md` when available
- Tavily MCP-based web research on relevant local laws or regulations

## Output

- `cases/<case_name>/working/regulatory_context.json`
- `cases/<case_name>/working/regulatory_research.md`
- `scripts/agent02_runner.py` is the skill-specific executor

## Rules

- Use `scope_profile.json` to determine jurisdiction, case context, and research scope.
- Tavily MCP-based web research is the default discovery mechanism.
- Local regulation markdown files are optional supporting inputs.
- Generate research topics and queries from the scope instead of broad unspecific searching.
- Use local regulation markdown files when provided.
- Use web research to discover, verify, or supplement current local legal or regulatory information.
- Prefer primary sources when available.
- Do not make localization implementation decisions.
- Do not present uncertain legal interpretation as settled fact.
- Keep the output structured and traceable.
- Validation runtime execution requires Tavily MCP to be available through the Codex validation host.
- The Python orchestrator may satisfy this by launching a local Tavily MCP stdio client.

## Procedure

1. Load `scope_profile.json`.
2. Derive research topics and search queries from the case scope.
3. Load all available markdown files from `input/local_regulations/` when present.
4. Use Tavily MCP-based web research to discover, verify, or supplement current local requirements.
5. Write `regulatory_context.json` with:
   - jurisdiction
   - research date
   - source list
   - relevant obligations
   - relevance topics or related control domains
   - uncertainty and open questions
6. Call `runtime/search_results_to_markdown.py` to save a Markdown research note file in `cases/<case_name>/working/`.

## Quality Bar

A good research result is:

- traceable to specific sources
- explicit about relevant local obligations
- explicit about uncertainty
- structured enough for a downstream localization decision agent to use directly

## Guardrails

If no local law files are provided:

- continue with web research
- record that local uploaded source files were unavailable

If local files are provided but appear incomplete:

- use them
- supplement with web research
- record the limitation in `regulatory_context.json`

If sources disagree:

- preserve the conflict in the output
- do not silently resolve it

## Runtime Note

- Preferred validation host: Codex validation thread
- Preferred regulatory search integration: Tavily MCP
- Local HTTP API code may be used only as a development fallback
