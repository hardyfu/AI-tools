---
name: policy-parse
description: Use this skill when a global policy markdown file must be parsed into structured control items. This skill reads the provided policy file and the case working `scope_profile.json`, extracts distinct requirements without changing policy intent, and outputs a consistent `parsed_controls.json` structure for downstream use.
---

# Policy Parse

Use this skill only for policy parsing.

## Goal

Convert a policy markdown file into a stable JSON list of control items with source traceability.

## Inputs

- `policy_file_path` provided at runtime
- `working/scope_profile.json` from the current case

## Output

- `working/parsed_controls.json`
- `scripts/agent01_runner.py` is the skill-specific executor

## Rules

- Always use the provided `policy_file_path`.
- Derive the case directory from the provided `policy_file_path`.
- Always read `scope_profile.json` from the same case `working/` directory.
- If the provided policy file is a PDF, convert it to Markdown first and save it in `cases/<case_name>/input/global_policy/`.
- Use scope information for context only. Do not override policy text.
- If `scope_profile.json.source_policy.source_file_path_or_reference` is known, validate it against `policy_file_path`.
- If the paths do not match, stop and surface a handoff mismatch.
- Parse requirements into structured control items.
- Do not write guidance.
- Do not perform legal or regulatory analysis.
- Do not modify original policy intent.
- Output must be valid JSON only.
- Keep the structure consistent across all control items.

## Procedure

1. Derive the case directory from `policy_file_path`.
2. If the provided policy file is a PDF, call `runtime/pdf_to_markdown.py` and save the converted Markdown in `cases/<case_name>/input/global_policy/`.
3. Load the markdown policy file.
4. Load `cases/<case_name>/working/scope_profile.json`.
5. If `source_policy.source_file_path_or_reference` is known, validate it against `policy_file_path`.
6. Walk the document by headings and requirement boundaries.
7. Use headings as hints for `control_domain`.
8. Treat bullets or requirement sentences as candidate control boundaries.
9. Create one control item per distinct requirement.
10. Preserve traceability with `source_section` and `source_text`.
11. If a field is unavailable, use the schema default such as `"unknown"` or `""`.
12. Write `cases/<case_name>/working/parsed_controls.json` using the template structure.

## Control Item Rules

Every control item must include:

- `control_id`
- `control_domain`
- `requirement_title`
- `requirement_text`
- `applicability`
- `priority`
- `source_section`
- `source_text`
- `notes`
- `status`

Additional rules:

- Default rule: one bullet maps to one control item.
- Do not merge distinct requirements.
- Do not split one requirement unless the policy clearly expresses separate obligations.
- Exception: if a single bullet contains multiple independent `must` obligations that could stand alone operationally, splitting is allowed.
- Keep `requirement_text` clear and faithful to the source.
- Keep `source_text` original or near-original.
- Prefer near-source phrasing for `applicability`.
- If applicability is ambiguous, use `"unknown"`.
- Avoid unnecessary normalization in `applicability`.
- Set `status` to `"confirmed"`.

## Quality Bar

A good parse result is:

- requirement-granular
- structurally consistent
- easy to trace back to source text
- reusable by downstream agents without reformatting

## Guardrails

If scope and policy text appear inconsistent:

- preserve the policy text
- do not rewrite the requirement based on scope
- use notes only when necessary

If a priority cannot be derived cleanly:

- choose a stable best-effort `high`, `medium`, or `low`
- keep the parsing consistent across items

If the policy contains descriptive text without a requirement:

- do not force it into a control item unless it carries a clear obligation
