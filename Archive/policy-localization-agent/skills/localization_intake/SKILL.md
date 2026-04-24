---
name: localization-intake
description: Use this skill when starting a policy localization case and you need to clarify scope with the user before any downstream work. This skill asks structured intake questions, captures only confirmed information, marks unknowns explicitly, and produces a `scope_profile.json` artifact while preparing collection of the source global policy file.
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
- `scripts/intake_helpers.py` contains the deterministic intake helper logic used by the orchestrator

## Rules

- Human-in-the-loop is required.
- Ask clarifying questions before finalizing the artifact.
- Start with an understanding summary and ask the user to confirm or correct it.
- Use staged iterative questioning.
- Ask no more than 5 questions in one turn.
- Prioritize the highest-impact missing fields first.
- Establish a stable `case_name` before finalizing the handoff artifact.
- Do not create the final `scope_profile.json` from the user's initial request alone.
- Ask intake questions first, receive user answers, and only then finalize the artifact.
- Never fabricate policy, jurisdiction, organizational, or deadline details.
- Mark unresolved values as `"unknown"`.
- Allow conservative inference when a value is strongly supported by the user's context, but label it as `inferred`.
- Keep the scope aligned to practical guidance documents, not audits.

## Procedure

1. First response requirements:
   - provide a short understanding summary
   - ask 3-4 critical intake questions
   - explicitly say that the final `scope_profile.json` will be created only after the user answers
   - do not create the final artifact yet
2. Summarize the current understanding in a short, explicit block.
3. Ask the user to confirm or correct that summary.
4. Stage 1: ask only 3-4 critical questions for the highest-impact missing fields. Typical priorities are:
   - source policy identity
   - target team or business unit
   - exact jurisdiction or scope boundary
   - localization objective
5. Record the user's answers and classify each captured field as:
   - `confirmed`
   - `inferred`
   - `unknown`
6. Stage 2: ask follow-up questions based on the user's answers.
7. Stage 3: check completeness and decide whether to continue asking questions.
8. Continue iteratively until the information is sufficient for a usable intake artifact or the remaining gaps are explicitly marked as `unknown`.
9. In each round:
   - avoid asking too many questions at once
   - prioritize the highest-impact remaining gaps
   - do not assume the process ends after two rounds
10. For every missing or unconfirmed field:
   - set the value to `"unknown"`
   - include the field in `missing_information`
   - add a concrete follow-up in `open_questions` if the gap matters
11. If a value is inferred:
   - keep the inferred value
   - label it as `inferred`
   - surface it for confirmation before treating it as settled
12. Do not produce the final `scope_profile.json` until the intake questions have been asked and the user has answered them.
13. Produce `scope_profile.json` from the template.
14. Write the artifact to `cases/<case_name>/working/scope_profile.json`.
15. If the source policy file path is known, record it in `source_policy.source_file_path_or_reference`.
16. Tell the user where to place:
   - the source global policy PDF or Markdown for policy normalization
   - any optional local law and regulation Markdown files for regulatory research
17. Stop after intake. Do not normalize the policy or draft the localized standard.

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
