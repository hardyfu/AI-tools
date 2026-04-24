---
name: regulatory-research
description: Use this skill when a policy localization case needs current local legal and regulatory inputs. This skill uses `scope_profile.json` plus Tavily-based research to collect only relevant laws, regulations, industry rules, standards, and other binding documents in their official original/full-text form, then saves both structured context and a Markdown research artifact.
---

# Regulatory Research

Use this skill only for local law and regulation research.

## Goal

Discover and structure the local legal and regulatory requirements relevant to the current localization case.

## Inputs

- `cases/<case_name>/working/scope_profile.json`
- optional `cases/<case_name>/input/local_regulations/*.md`
- Tavily research capability

## Output

- `cases/<case_name>/working/regulatory_context.json`
- `cases/<case_name>/working/regulatory_research.md`
- `scripts/agent02_runner.py` is the skill-specific executor

## Rules

- Use `scope_profile.json` to drive jurisdiction, audience, and topic selection.
- Tavily research is the default discovery mechanism.
- Local regulation Markdown files are optional supporting inputs.
- Search only for official, primary-source laws, regulations, industry rules, standards, specifications, guidance, and other binding documents in their original/full-text form.
- Prefer jurisdiction-relevant government or regulator domains when available.
- Exclude commentary, news, blogs, white papers, summaries, and secondary analysis.
- Do not make localization or drafting decisions in this skill.
- Do not present uncertain legal interpretation as settled fact.
- Keep source traceability explicit.

## Procedure

1. Load `scope_profile.json`.
2. Derive focused search topics from:
   - jurisdiction
   - policy type or title
   - target audience
   - localization objective
3. Load any user-provided local regulation Markdown files.
4. Use Tavily to search only for relevant official laws and regulations in their original/full-text form, including any laws and regulations related to the global policy topic.
5. Filter and dedupe low-value or clearly irrelevant results.
6. Write `regulatory_context.json` with:
   - jurisdiction
   - research date
   - reviewed local files
   - web sources
   - relevant obligations
   - open issues
   - notes
7. Write `regulatory_research.md` as a readable research log.

## Quality Bar

A good research result is:

- jurisdiction-specific
- limited to official laws and regulations in original/full-text form
- explicit about relevant obligations
- explicit about uncertainty
- directly usable by downstream drafting work

## Guardrails

If no local regulation files are provided:

- continue with Tavily research
- record that no uploaded local files were reviewed

If sources conflict:

- preserve the conflict
- do not silently resolve it

If only non-authoritative sources are found:

- record that limitation clearly
- avoid overstating certainty
