---
name: control-mapping-analysis
description: Use this skill when both organizational requirements and CIS Alibaba Cloud benchmark requirements are ready and the project needs a traceable mapping, gap analysis, and baseline decision logic before generating the final baseline.
---

# Control Mapping Analysis

Use this skill only for mapping organizational strategy against the CIS Alibaba Cloud benchmark.

## Goal

Create a structured analysis that shows where the organization's cloud security standard aligns with, exceeds, or misses CIS Alibaba Cloud benchmark expectations.

## Inputs

- `cases/<case_name>/working/project_profile.json`
- `cases/<case_name>/working/organizational_requirements.json`
- `cases/<case_name>/working/benchmark_requirements.json`

## Output

- `cases/<case_name>/working/mapping_analysis.md`
- `cases/<case_name>/working/mapping_analysis.json`
- `scripts/agent03_runner.py` is the skill-specific executor

## Rules

- Keep traceability to both organizational and CIS requirement IDs.
- Be explicit about unmatched benchmark items and organizational-only items.
- Separate descriptive mapping from baseline decisions.
- Do not hide weak matches.

## Procedure

1. Load organizational and benchmark artifacts.
2. Match benchmark items to organizational requirements using category and text overlap.
3. Record alignment, additions, and gaps.
4. Derive baseline decision principles.
5. Write Markdown and JSON mapping outputs.
