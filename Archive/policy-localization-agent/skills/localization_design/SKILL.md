---
name: localization-design
description: Use this skill when the project must draft a localized standard document from the intake scope and an integrated requirements artifact. This skill produces a structured local standard draft with a fixed document framework rather than free-form prose.
---

# Localization Design

Use this skill only for localized standard drafting.

## Goal

Draft a localized standard document that integrates:

- integrated group and local requirements
- case scope and audience needs

The output must follow a fixed document framework.

## Inputs

- `cases/<case_name>/working/scope_profile.json`
- `cases/<case_name>/working/integrated_requirements.md`

## Output

- `cases/<case_name>/working/localized_standard_draft.md`
- `scripts/agent03_runner.py` is the skill-specific executor

## Rules

- Use `integrated_requirements.md` as the drafting baseline.
- Draft a standard document, not a decision list and not free-form commentary.
- Follow the fixed document structure.
- Keep traceability to the integrated requirements artifact.
- If a local requirement appears to add obligations, state them explicitly.
- If a local requirement appears to conflict with a global requirement, flag the conflict explicitly.
- Do not hide unknowns.

## Required Document Structure

The draft must contain these sections in order:

1. Document Metadata
2. Purpose
3. Scope and Audience
4. Global Standard Requirements
5. Local Regulatory Requirements
6. Localized Implementation Requirements
7. Roles and Responsibilities
8. Exceptions and Escalation
9. References
10. Open Issues and Unknowns

## Procedure

1. Load `scope_profile.json`.
2. Load `integrated_requirements.md`.
3. Use the integrated requirements as the drafting source.
4. Draft the localized standard in the fixed structure.
7. Write `localized_standard_draft.md`.

## Quality Bar

A good draft is:

- structured like a standard, not an essay
- explicit about what is mandatory
- explicit about local additions
- explicit about conflicts and unknowns
- readable by the target internal audience

## Guardrails

If `integrated_requirements.md` is missing:

- stop and surface the missing dependency

If the evidence for a local requirement is weak:

- include it under `Open Issues and Unknowns`
- do not write it as settled mandatory text
