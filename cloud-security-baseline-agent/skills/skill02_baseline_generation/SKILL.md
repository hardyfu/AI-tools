---
name: skill02-baseline-generation
description: Use this skill when structured parse artifacts already exist for a global policy and a third-party standard, and the workflow must classify overlaps, carry-forward obligations, platform-specific additions, and deferred items in order to generate a complete baseline package. This skill uses the parser outputs from skill01 as the primary input to Azure OpenAI, with deterministic matching used only to build candidate context and fallback behavior.
---

# Skill02 Baseline Generation

Use this skill only for baseline synthesis after parsing is complete.

## Goal

Consume the two parse artifacts and generate a complete baseline package with:
- requirement classification
- baseline analysis
- baseline controls
- baseline report
- priority recommendations

## Inputs

- `cases/<case_name>/working/global_policy_parse.json`
- `cases/<case_name>/working/third_party_standard_parse.json`
- `cases/<case_name>/working/project_profile.json`

## Outputs

- `cases/<case_name>/working/baseline_analysis.json`
- `cases/<case_name>/working/baseline_controls.md`
- `cases/<case_name>/working/baseline_report.md`
- `cases/<case_name>/working/baseline_priority_recommendations_cn.md`
- script entrypoint: `scripts/run_baseline_generation.py`

## Rules

- Treat the global policy as the baseline governance source.
- Treat the third-party standard as the platform or industry augmentation source.
- Use the parser outputs from skill01 as the primary analysis input.
- Use deterministic similarity matching only to provide candidate matches and fallback behavior.
- Classify each third-party requirement as one of:
  - `carry_forward`
  - `adapt_for_platform`
  - `new_baseline_control`
- Keep traceability to both source artifacts.
- Generate the full baseline package in this skill.

## Procedure

1. Load both parse artifacts.
2. Build candidate alignments between third-party requirements and global policy requirements.
3. Send the parser outputs and candidate alignments to the configured Azure OpenAI deployment, using `gpt-5.4-mini` for classification.
4. Let the LLM produce the baseline action and rationale for each requirement.
5. Generate analysis and reporting artifacts.
6. Write the baseline outputs.

## References

- Classification guidance: `references/classification.md`
- Output package guidance: `references/output_package.md`
