---
name: baseline-writer
description: Use this skill when mapping analysis is complete and the project must output a usable Alibaba Cloud security baseline, including a baseline control list and a concise report that explains why each control is adopted, adapted, or deferred.
---

# Baseline Writer

Use this skill only for final baseline generation.

## Goal

Produce the baseline artifact set that the team can review and iterate: a control list and a short report.

## Inputs

- `cases/<case_name>/working/project_profile.json`
- `cases/<case_name>/working/organizational_requirements.json`
- `cases/<case_name>/working/benchmark_requirements.json`
- `cases/<case_name>/working/mapping_analysis.json`

## Output

- `cases/<case_name>/working/baseline_controls.md`
- `cases/<case_name>/working/baseline_report.md`
- `scripts/agent04_runner.py` is the skill-specific executor

## Rules

- Baseline controls must be traceable to source requirements.
- Distinguish adopted, adapted, and deferred controls.
- Prefer organization-mandated controls when they exceed CIS.
- Keep unresolved items visible.

## Procedure

1. Load the analysis artifacts.
2. Convert mapping results into baseline decisions.
3. Write `baseline_controls.md`.
4. Write `baseline_report.md`.
