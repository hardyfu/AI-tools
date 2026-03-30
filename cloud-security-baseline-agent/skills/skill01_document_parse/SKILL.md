---
name: skill01-document-parse
description: Use this skill when the workflow receives a global policy document or a third-party standard and must parse it into a structured requirement artifact. This skill normalizes text with `pdf_parser`, evaluates extraction quality, and produces role-specific parse artifacts for downstream baseline generation. It does not perform LLM reasoning or baseline judgment.
---

# Skill01 Document Parse

Use this skill only for document parsing and normalization.

## Goal

Turn a source `global policy` or `third-party standard` into a structured parse artifact with:
- normalized text
- extraction quality metadata
- structured requirements and thematic signals

## Inputs

- `cases/<case_name>/working/project_profile.json`
- source files under:
  - `cases/<case_name>/input/global_policy/`
  - `cases/<case_name>/input/third_party_standard/`

## Outputs

- `cases/<case_name>/working/global_policy_parse.json`
- `cases/<case_name>/working/third_party_standard_parse.json`
- script entrypoint: `scripts/run_parse.py`

## Rules

- Parse the two document roles separately.
- Always preserve traceability to source file names and source requirement identifiers.
- Always evaluate extraction quality and preserve those diagnostics in the artifact.
- Use deterministic parsing only in this skill.
- Do not generate the final baseline in this skill.
- Do not perform classification, gap analysis, or policy reasoning in this skill.

## Procedure

1. Load the case profile.
2. Normalize text from the target document set.
3. Assess extraction quality.
4. Run the deterministic role-appropriate parser.
5. Write the role-specific parse artifact.

## References

- Parsing workflow: `references/workflow.md`
- Output schema guidance: `references/output_schema.md`
