# Runtime Notes

This directory contains local development runtime code.

Use these files in three categories:

## Shared utility scripts

These scripts are still useful even when the primary validation path uses Codex + Tavily MCP:

- `pdf_to_markdown.py`
- `search_results_to_markdown.py`
- `ollama_client.py`
- `tavily_mcp_client.py`

## Runtime utilities

These files remain under `runtime/` because they are shared utilities rather than skill-specific executors:

- `gateway_runner.py`
- `ollama_client.py`
- `pdf_to_markdown.py`
- `search_results_to_markdown.py`
- `tavily_client.py`
- `tavily_mcp_client.py`

## Skill executors

Skill-specific runner code now lives under each skill directory:

- `skills/localization-intake/scripts/`
- `skills/policy-parse/scripts/`
- `skills/regulatory-research/scripts/`
- `skills/localization-design/scripts/`

The main orchestrator now lives at the project root:

- `policy_localization.py`

## Model configuration

LLM-backed steps should use `ollama_client.py`.

Supported environment variables:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

Default assumptions:

- base URL: `http://localhost:11434`
- model: `qwen2.5:latest`

Skill notes:

- policy-parse should prefer Ollama-backed parsing.
- regulatory-research should use Tavily MCP plus Ollama-backed synthesis.
- localization-design should use Ollama-backed decision generation.

Development note:

- `policy_localization.py --action agent02_run` defaults to Tavily MCP and supports `--search-provider api` only as a local fallback.
- Each Agent02 run should prompt the operator to enter a Tavily API key for that run only.
- The key should remain in process memory only and should not be written to project files.
- `policy_localization.py --action agent03_run` uses the local Ollama-backed runner with a local fallback.
- The intended validation path for Agent02 remains Codex validation host + Tavily MCP.

Current Python-orchestrated actions:

- `agent00_start`
- `agent00_continue`
- `agent01_run`
- `agent02_run`
- `agent03_run`

They are not the preferred validation execution path.

Preferred validation path:

- host: Codex validation thread
- regulatory search provider: Tavily MCP

Any validation orchestration design should treat Codex + Tavily MCP as the primary runtime model.
