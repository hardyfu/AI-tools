---
name: baseline-writer
description: Use this skill when Stage 2 analysis is complete and the project must render review artifacts from Global Standard coverage, benchmark extensions, and baseline candidates.
---

# Baseline Writer

Use this skill only for final baseline generation.

## Goal

Produce the review artifact set that the team can inspect and iterate: a candidate control list, a concise report, and Chinese recommendations.

## Inputs

- `cases/<case_name>/working/project_profile.json`
- `cases/<case_name>/working/organizational_requirements.json`
- `cases/<case_name>/working/benchmark_requirements.json`
- `cases/<case_name>/working/standard_coverage.json`
- `cases/<case_name>/working/benchmark_extensions.json`
- `cases/<case_name>/working/baseline_candidates.json`

## Output

- `cases/<case_name>/working/baseline_controls.md`
- `cases/<case_name>/working/baseline_report.md`
- `cases/<case_name>/working/baseline_priority_recommendations_cn.md`
- `scripts/agent04_runner.py` is the skill-specific executor

## Rules

- Baseline controls must remain traceable to benchmark and Global Standard evidence.
- Distinguish Global Standard coverage from benchmark extensions.
- Keep organization-specific requirements visible rather than forcing them into benchmark coverage.
- Do not collapse all extensions into mandatory controls without preserving rationale.

## Procedure

1. Load Stage 2 artifacts.
2. Render candidate controls from `baseline_candidates.json`.
3. Summarize Global Standard coverage and benchmark extensions in `baseline_report.md`.
4. Write `baseline_priority_recommendations_cn.md`.
