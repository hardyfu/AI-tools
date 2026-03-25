---
name: localization-intake
description: Use this skill when starting a policy localization case and you need to clarify scope with the user before any parsing or drafting work. This skill asks structured intake questions, captures only confirmed information, marks unknowns explicitly, and produces a `scope_profile.json` artifact for downstream localization work.
---

# Localization Intake

Use this skill only for the intake and scope-clarification stage of the policy localization workflow.

## Goal

Create a complete enough `scope_profile.json` for downstream work without assuming missing facts.

## Inputs

- User request
- Optional notes about the local team, country, or policy set
- Optional file names or document references supplied by the user

## Output

- `scope_profile.json`

## Rules

- Human-in-the-loop is required.
- Ask clarifying questions before finalizing the artifact.
- Start with an understanding summary and ask the user to confirm or correct it.
- Use staged iterative questioning.
- Ask no more than 5 questions in one turn.
- Prioritize the highest-impact missing fields first.
- Establish a stable `case_name` before finalizing the handoff artifact.
- Never fabricate policy, jurisdiction, organizational, or deadline details.
- Mark unresolved values as `"unknown"`.
- Allow conservative inference when a value is strongly supported by the user's context, but label it as `inferred`.
- Keep the scope aligned to practical guidance documents, not audits.

## Procedure

1. Summarize the current understanding in a short, explicit block.
2. Ask the user to confirm or correct that summary.
3. Stage 1: ask only 3-4 critical questions for the highest-impact missing fields. Typical priorities are:
   - source policy identity
   - target team or business unit
   - exact jurisdiction or scope boundary
   - localization objective
4. Record the user's answers and classify each captured field as:
   - `confirmed`
   - `inferred`
   - `unknown`
5. Stage 2: ask follow-up questions based on the user's answers.
6. Stage 3: check completeness and decide whether to continue asking questions.
7. Continue iteratively until the information is sufficient for a usable intake artifact or the remaining gaps are explicitly marked as `unknown`.
8. In each round:
   - avoid asking too many questions at once
   - prioritize the highest-impact remaining gaps
   - do not assume the process ends after two rounds
9. For every missing or unconfirmed field:
   - set the value to `"unknown"`
   - include the field in `missing_information`
   - add a concrete follow-up in `open_questions` if the gap matters
10. If a value is inferred:
   - keep the inferred value
   - label it as `inferred`
   - surface it for confirmation before treating it as settled
11. Produce `scope_profile.json` from the template.
12. Write the artifact to `cases/<case_name>/working/scope_profile.json`.
13. If the source policy file path is known, record it in `source_policy.source_file_path_or_reference`.
14. Tell the user where to place:
   - the markdown global policy file for Agent01
   - the markdown local law and regulation files for Agent02
15. Stop after intake. Do not parse the policy or draft guidance.

## Quality Bar

A good intake artifact is:

- specific enough for downstream design work
- explicit about gaps
- explicit about field status: confirmed, inferred, or unknown
- easy to inspect by a human reviewer
- stored as structured JSON rather than prose-only notes
- paired with clear next-step file placement instructions for downstream agents

## Guardrails

If the user gives partial answers:

- keep the known values
- mark the rest as `"unknown"`
- do not silently fill gaps

If the user provides enough context to support a likely value:

- you may mark it as `inferred`
- do not upgrade it to `confirmed` without user confirmation

If the user asks to skip clarification:

- explain that intake requires explicit confirmation
- still capture only confirmed details

If the request starts drifting into policy parsing or drafting:

- note that those belong to later agents
- finish the intake artifact first
