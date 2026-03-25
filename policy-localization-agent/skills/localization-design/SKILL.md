---
name: localization-design
description: Use this skill when parsed global policy controls must be evaluated against local scope and a prepared `regulatory_context.json` to produce structured localization decisions in `localization_plan.json`.
---

# Localization Design

Use this skill only for localization decision design.

## Goal

Determine how each parsed global control should be applied in the local context, with explicit traceability to both parsed controls and regulatory context.

## Inputs

- `cases/<case_name>/working/scope_profile.json`
- `cases/<case_name>/working/parsed_controls.json`
- `cases/<case_name>/working/regulatory_context.json`

## Output

- `cases/<case_name>/working/localization_plan.json`

## Rules

- Use `scope_profile.json` as context, not as a replacement for policy content.
- Use `parsed_controls.json` as the control inventory.
- Use `regulatory_context.json` as the local law and regulation input.
- Preserve original control intent unless a local requirement clearly justifies adaptation.
- Keep one localization decision item per parsed control.
- Do not write the final guidance document.
- Do not perform fresh legal research as the primary task.
- Do not present uncertain interpretation as settled fact.
- Keep the output structured and traceable.

## Procedure

1. Load `scope_profile.json`.
2. Load `parsed_controls.json`.
3. Load `regulatory_context.json`.
4. For each parsed control, decide whether it is:
   - `adopt`
   - `adapt`
   - `supplement`
   - `flag`
5. Write `localization_plan.json` with one decision item per control.

## Decision Item Rules

Every localization decision item must include:

- control traceability
- decision type
- local applicability
- rationale
- supporting local references
- unresolved issues
- status

Additional rules:

- Do not silently combine multiple controls.
- If a control has no local change, state that clearly.
- If local law creates extra implementation needs, capture them explicitly.
- If interpretation is uncertain, record the uncertainty instead of forcing a decision.

## Quality Bar

A good localization design result is:

- traceable to both global controls and local regulatory context
- explicit about where local adaptation is needed
- explicit about uncertainty
- structured enough for a downstream writing agent to use directly

## Guardrails

If `regulatory_context.json` is missing:

- stop and surface the missing dependency

If a local requirement appears to conflict with the global control:

- preserve both sides in the output
- explain the conflict
- flag the item instead of silently resolving it
