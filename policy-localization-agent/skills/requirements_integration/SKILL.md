---
name: requirements-integration
description: Use this skill when the project has both a normalized global policy markdown file and local regulatory research, and needs a structured integration result that consolidates mandatory group requirements with local law and regulation requirements before drafting the final localized standard.
---

# Requirements Integration

Use this skill only for integrating global policy requirements with local legal and regulatory requirements.

## Goal

Create a structured integration artifact that:

- consolidates mandatory group requirements from the normalized global policy
- consolidates relevant local legal and regulatory requirements from `regulatory_context.json`
- identifies overlaps, local additions, conflicts, and unknowns
- prepares a stable drafting input for the final localized standard

## Inputs

- `cases/<case_name>/working/scope_profile.json`
- normalized global policy Markdown under `cases/<case_name>/input/global_policy/`
- `cases/<case_name>/working/regulatory_context.json`

## Output

- `cases/<case_name>/working/integrated_requirements.md`
- `scripts/agent04_runner.py` is the skill-specific executor

## Rules

- Treat the global policy as the mandatory group baseline.
- Treat `regulatory_context.json` as the source of local law and regulation requirements.
- Do not draft the final localized standard in this skill.
- Do not ignore conflicts or uncertainties.
- Keep the result structured and traceable.
- Prefer concise requirement statements over narrative prose.

## Required Integration Structure

The integration artifact must contain these sections in order:

1. Integration Metadata
2. Global Mandatory Requirements
3. Local Legal and Regulatory Requirements
4. Integrated Requirement Mapping
5. Local Additions
6. Conflicts and Constraints
7. Open Issues and Unknowns
8. Source References

## Procedure

1. Load `scope_profile.json`.
2. Load the normalized global policy Markdown.
3. Load `regulatory_context.json`.
4. Extract the group requirements relevant to the case scope.
5. Extract the local legal and regulatory requirements relevant to the same scope.
6. Produce a structured mapping of:
   - group requirement
   - corresponding local requirement
   - integration outcome
7. Record local additions that are not explicitly present in the group policy.
8. Record conflicts, constraints, and unknowns explicitly.
9. Write `integrated_requirements.md`.

## Quality Bar

A good integration artifact is:

- structured
- traceable
- explicit about mandatory requirements
- explicit about local additions
- explicit about conflicts and unresolved questions
- directly usable as drafting input

## Guardrails

If the normalized global policy Markdown is missing:

- stop and surface the missing dependency

If `regulatory_context.json` is missing:

- stop and surface the missing dependency

If evidence for a local requirement is weak:

- keep it out of settled mappings
- record it under `Open Issues and Unknowns`
