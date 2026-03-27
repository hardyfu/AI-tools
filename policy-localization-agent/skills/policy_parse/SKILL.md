---
name: policy-parse
description: Use this skill when a global policy file must be normalized into Markdown for downstream localization work. This skill converts a source PDF or existing markdown policy file into a clean case-local Markdown artifact without generating control items or rewriting policy obligations.
---

# Policy Parse

Use this skill only for global policy normalization.

## Goal

Create a clean Markdown version of the global policy in the current case so downstream skills can read a stable source document.

## Inputs

- `policy_file_path` provided at runtime
- `cases/<case_name>/working/scope_profile.json`

## Output

- `cases/<case_name>/input/global_policy/<normalized_name>.md`
- `scripts/agent01_runner.py` is the skill-specific executor

## Rules

- Always use the provided `policy_file_path`.
- Always read `scope_profile.json` from the same case.
- If the source file is a PDF, convert it to Markdown and save it under `cases/<case_name>/input/global_policy/`.
- If the source file is already Markdown, normalize placement and file naming under `cases/<case_name>/input/global_policy/`.
- Preserve source meaning. Do not summarize, interpret, or rewrite policy obligations.
- Do not produce control items.
- Do not produce localization decisions.
- Do not perform legal or regulatory analysis.
- Make normalization provenance explicit.

## Procedure

1. Validate the case context and `scope_profile.json`.
2. Validate the provided source file path.
3. If the source file is a PDF, call `runtime/pdf_to_markdown.py`.
4. If the source file is Markdown, copy or normalize it into the case `input/global_policy/` directory.
5. Apply light cleanup only:
   - paragraph reflow
   - broken-word de-hyphenation
   - obvious divider removal
6. Write the normalized Markdown file into the case.
7. Record normalization metadata:
   - original source path
   - source format
   - normalized markdown path
   - normalization warnings

## Quality Bar

A good output is:

- faithful to the source policy
- readable as Markdown
- stable enough for downstream skill consumption
- explicit about conversion quality and warnings

## Guardrails

If the source file is low quality:

- preserve the text conservatively
- record warnings
- do not invent missing structure

If the source path and case context conflict:

- stop and surface the mismatch
