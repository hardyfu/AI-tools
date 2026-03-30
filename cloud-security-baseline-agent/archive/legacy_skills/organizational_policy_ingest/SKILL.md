---
name: organizational-policy-ingest
description: Use this skill when a cloud security baseline project needs to understand the organization's cloud security standard, extract strategy signals and mandatory requirements, and save a structured organizational requirements artifact for downstream mapping.
---

# Organizational Policy Ingest

Use this skill only for parsing the organization's source cloud security standard.

## Goal

Create a structured requirements artifact from the organization's cloud security standard so later skills can map it against CIS Alibaba Cloud requirements.

## Inputs

- `cases/<case_name>/working/project_profile.json`
- source files under `cases/<case_name>/input/organization_policy/`

## Output

- `cases/<case_name>/working/organizational_requirements.json`
- `scripts/agent01_runner.py` is the skill-specific executor

## Rules

- Preserve the source policy intent. Do not weaken organizational requirements.
- Extract both explicit requirements and higher-level strategy themes.
- Prefer deterministic parsing over free-form rewriting.
- Mark notes when the source file format is unsupported or thin.
- Do not map to CIS in this skill.

## Procedure

1. Load `project_profile.json`.
2. Read organization policy files from the case input directory.
3. Extract requirement candidates and classify them.
4. Build strategy themes from recurring categories.
5. Write `organizational_requirements.json`.
