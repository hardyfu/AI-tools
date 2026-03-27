# Python Orchestration Design

## Goal

Replace AI-interpreted gateway behavior with a Python-controlled workflow that calls LLM-backed skills in a fixed, auditable sequence.

The Python orchestrator is the source of truth for:

- execution order
- case initialization
- file and directory checks
- dependency validation
- tool invocation
- state transitions

The LLM is used only inside controlled step executors.

## Core Design Shift

Old model:

- AI reads `gateway.md`
- AI decides what to do next

New model:

- Python enforces workflow logic
- AI executes one bounded skill at a time

## System Layers

### 1. Orchestrator

Main entrypoint:

- `policy_localization.py`

Responsibilities:

- initialize and load a case
- determine current phase
- resolve the required skill from the skill registry
- validate prerequisites
- call the correct step executor
- persist artifacts and state
- stop on missing dependencies

### 2. Skill Contracts

Retain skill docs as behavior specifications:

- `skills/localization-intake/SKILL.md`
- `skills/policy-parse/SKILL.md`
- `skills/regulatory-research/SKILL.md`
- `skills/localization-design/SKILL.md`

These documents define what each step should do, but Python decides when each step runs.

### 3. Tools and Scripts

Reusable scripts remain in `runtime/`:

- `pdf_to_markdown.py`
- `search_results_to_markdown.py`
- `ollama_client.py`

Fallback runners may remain for development:

- `skills/policy-parse/scripts/agent01_runner.py`
- `skills/regulatory-research/scripts/agent02_runner.py`
- `skills/localization-design/scripts/agent03_runner.py`

### 4. Artifacts

Artifacts remain the workflow interface between steps:

- `scope_profile.json`
- `parsed_controls.json`
- `regulatory_context.json`
- `localization_plan.json`

## Shared Case Structure

Each case must use:

- `cases/<case_name>/input/`
- `cases/<case_name>/input/global_policy/`
- `cases/<case_name>/input/local_regulations/`
- `cases/<case_name>/working/`

## Workflow Phases

### Phase 0 - Case Bootstrap

Python creates or validates:

- case directory
- `input/`
- `input/global_policy/`
- `input/local_regulations/`
- `working/`

This is not Agent00 completion. It is only environment setup.

### Phase 1 - Agent00 Skill

Purpose:

- gather scope through controlled questioning

Inputs:

- initial user request
- any provided intake answers

Outputs:

- `working/scope_profile.json`

Important:

- Python should track whether intake is still awaiting user answers
- final artifact should not be written until the questioning contract is satisfied
- Python should persist the current intake round and outstanding questions

### Phase 2 - Agent01 Skill

Purpose:

- parse the global policy

Inputs:

- `working/scope_profile.json`
- global policy source path

Supporting tools:

- `pdf_to_markdown.py` when source is PDF
- `ollama_client.py` for policy parsing reasoning

Outputs:

- converted Markdown in `input/global_policy/` if needed
- `working/parsed_controls.json`

Suggested orchestrator action:

- `agent01_run`

### Phase 3 - Agent02 Skill

Purpose:

- perform regulatory research

Inputs:

- `working/scope_profile.json`
- optional files from `input/local_regulations/`

Required external capability:

- Tavily MCP in the Codex validation host

Supporting tools:

- `search_results_to_markdown.py`
- `tavily_mcp_client.py`
- `ollama_client.py`

Outputs:

- `working/regulatory_context.json`
- `working/regulatory_research.md`

Suggested orchestrator action:

- `agent02_run`

### Phase 4 - Agent03 Skill

Purpose:

- create localization decisions

Inputs:

- `working/scope_profile.json`
- `working/parsed_controls.json`
- `working/regulatory_context.json`

Outputs:

- `working/localization_plan.json`

Supporting tools:

- `ollama_client.py`

Suggested orchestrator action:

- `agent03_run`

## State Model

The orchestrator should track an explicit workflow state.

Suggested statuses:

- `BOOTSTRAP_PENDING`
- `INTAKE_IN_PROGRESS`
- `INTAKE_COMPLETE`
- `POLICY_PARSE_READY`
- `POLICY_PARSE_COMPLETE`
- `REGULATORY_RESEARCH_READY`
- `REGULATORY_RESEARCH_COMPLETE`
- `LOCALIZATION_DESIGN_READY`
- `LOCALIZATION_DESIGN_COMPLETE`
- `BLOCKED`

Suggested state file:

- `cases/<case_name>/working/workflow_state.json`

Suggested intake state fields:

- `intake_round`
- `awaiting_user_answers`
- `asked_questions`
- `pending_questions`
- `last_intake_summary`

## Orchestrator Rules

- never infer missing prerequisite files
- never skip an earlier phase
- treat artifacts as contracts, not suggestions
- stop early on missing dependencies
- persist clear state after every step
- separate bootstrap success from skill completion

## LLM Boundary

Python controls:

- step order
- file paths
- state
- dependency checks
- tool selection

LLM controls only:

- bounded reasoning inside a specific skill
- structured output generation for that phase

Recommended LLM integration:

- local host: Ollama
- shared runtime client: `runtime/ollama_client.py`
- Agent00 does not require LLM
- Agent01, Agent02, and Agent03 are LLM-backed skill steps

Implementation note:

- Agent01 should prefer Ollama-backed parsing.
- Agent02 should prefer Tavily MCP plus Ollama-backed synthesis, with the Tavily HTTP API used only as a development fallback.
- Agent02 should prompt the operator for a Tavily API key at run time unless a different secure secret-handling mechanism is introduced later.
- Agent03 should use Ollama-backed localization design, with a local fallback only for development testing.
- A local deterministic fallback may remain for development, but it is not the intended primary behavior.

## Recommended Next Implementation

1. Create `policy_localization.py`
2. Add workflow state helpers
3. Implement bootstrap and status inspection
4. Implement Agent00 interaction mode
5. Implement Agent01 execution mode
6. Implement Agent02 execution mode
7. Add Agent03 execution logic

## Agent00 Interaction Model

Agent00 should be split into two orchestrated actions:

### `agent00_start`

Purpose:

- initialize intake state
- generate the first-turn response contract

Behavior:

- create or validate case structure
- persist workflow state as `INTAKE_IN_PROGRESS`
- return:
  - understanding summary
  - 3-4 critical questions
  - explicit note that final artifact is not created yet

### `agent00_continue`

Purpose:

- accept user answers
- update intake state
- decide whether more questions are required

Behavior:

- append answers to intake history
- decide whether intake is complete
- if incomplete:
  - return next-round questions
- if complete:
  - write `scope_profile.json`
  - update workflow state to `POLICY_PARSE_READY`
