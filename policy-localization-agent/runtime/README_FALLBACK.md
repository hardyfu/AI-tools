# Runtime Notes

This directory contains local development runtime code.

Use these files in three categories:

## Shared utility scripts

These scripts are still useful even when the primary validation path uses Codex + Tavily MCP:

- `pdf_to_markdown.py`
- `search_results_to_markdown.py`
- `ollama_client.py`
- `tavily_mcp_client.py`
- `ollama_smoke_demo.py`

## Runtime utilities

These files remain under `runtime/` because they are shared utilities rather than skill-specific executors:

- `gateway_runner.py`
- `ollama_client.py`
- `pdf_to_markdown.py`
- `search_results_to_markdown.py`
- `tavily_client.py`
- `tavily_mcp_client.py`
- `ollama_smoke_demo.py`

## Skill executors

Skill-specific runner code now lives under each skill directory:

- `skills/localization_intake/scripts/`
- `skills/policy_parse/scripts/`
- `skills/regulatory_research/scripts/`
- `skills/requirements_integration/scripts/`
- `skills/localization_design/scripts/`

The main orchestrator now lives at the project root:

- `policy_localization.py`

## Model configuration

LLM-backed steps should use `ollama_client.py`.

Supported environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`
- `OLLAMA_TEMPERATURE`
- `OLLAMA_NUM_CTX`

Default assumptions:

- base URL: `http://localhost:11434`
- model: `qwen3.5:4b`
- temperature: unset unless configured
- num_ctx: unset unless configured
- Ollama service: if not already running, `ollama_client.py` will try to start it with `ollama serve`

Skill notes:

- policy-parse normalizes the global policy into case-local Markdown.
- `policy_parse_result.json` records source path, normalized markdown path, normalization mode, and warnings.
- regulatory-research should search only official, original/full-text laws, regulations, industry rules, standards, and other binding documents related to the global policy topic plus jurisdiction, then search the original/full-text content of discovered binding documents.
- regulatory-research should use Tavily MCP plus Ollama-backed synthesis.
- requirements-integration should use Ollama-backed integration of group requirements and local legal requirements into `integrated_requirements.md`.
- localization-design should use Ollama-backed localized standard drafting from `integrated_requirements.md`.
- `pdf_to_markdown.py` now does light cleanup of extracted text, including divider removal, paragraph reflow, and de-hyphenation of broken words.
- Agent02 query construction now prefers China official regulatory domains and filters/dedupes obvious non-regulatory results before synthesis.
- Agent03 now drafts `localized_standard_draft.md` from scope and integrated requirements.
- Agent02 now drops non-official results when official China regulatory sources are available in the search set.
- Agent02 now preserves source content excerpts in `regulatory_context.json` and `regulatory_research.md`.

Development note:

- `policy_localization.py --action agent02_run` defaults to Tavily MCP and supports `--search-provider api` only as a local fallback.
- `policy_localization.py --action agent04_run` writes `integrated_requirements.md`.
- Agent02 first tries to read `TAVILY` from `/Users/<user>/Desktop/API.json`.
- If no configured key is found there, the operator is prompted to enter a Tavily API key for that run.
- The key is not written back to the project.
- `policy_localization.py --action agent03_run` writes `localized_standard_draft.md`.
- The intended validation path for Agent02 remains Codex validation host + Tavily MCP.

Current Python-orchestrated actions:

- `run`
- `agent00_start`
- `agent00_continue`
- `agent01_run`
- `agent02_run`
- `agent04_run`
- `agent03_run`

Quick validation:

- `python3 runtime/ollama_smoke_demo.py --model qwen3.5:4b`

Run mode note:

- `policy_localization.py --action run` now checks for existing case results.
- If previous outputs exist, the operator must choose whether to resume, restart and delete prior results, or cancel.

They are not the preferred validation execution path.

Preferred validation path:

- host: Codex validation thread
- regulatory search provider: Tavily MCP

Any validation orchestration design should treat Codex + Tavily MCP as the primary runtime model.
