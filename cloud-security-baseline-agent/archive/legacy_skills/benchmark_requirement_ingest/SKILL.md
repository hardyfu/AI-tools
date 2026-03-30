---
name: benchmark-requirement-ingest
description: Use this skill when a cloud security baseline project needs to parse CIS Alibaba Cloud benchmark content into a structured set of benchmark requirements and benchmark themes for downstream mapping and baseline design.
---

# Benchmark Requirement Ingest

Use this skill only for the CIS Alibaba Cloud benchmark parsing stage.

## Goal

Create a structured benchmark artifact that captures actionable CIS Alibaba Cloud requirements, target services, and benchmark themes.

## Inputs

- `cases/<case_name>/working/project_profile.json`
- source files under `cases/<case_name>/input/cis_alibaba_cloud/`

## Output

- `cases/<case_name>/working/benchmark_requirements.json`
- `scripts/agent02_runner.py` is the skill-specific executor

## Rules

- Treat the CIS benchmark as the industry best-practice baseline, not the final internal baseline.
- Preserve benchmark traceability to the source text.
- Capture service hints when present.
- Do not make adoption decisions in this skill.

## Procedure

1. Load `project_profile.json`.
2. Read benchmark source files from the case input directory.
3. Extract benchmark requirements and infer service/category metadata.
4. Build benchmark themes from recurring categories.
5. Write `benchmark_requirements.json`.
