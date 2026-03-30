---
name: skill03-baseline-finalize
description: Use this skill when baseline analysis and control artifacts already exist and the workflow needs a formal, review-ready English baseline document. This skill consumes skill02 outputs, uses `qwen3-max` as the finalization model, and emits the publication-oriented English baseline document without changing parser or mapping logic.
---

# Skill03 Baseline Finalize

Use this skill only after skill02 has completed.

## Goal

Consume the baseline package from skill02 and generate a production-ready Excel workbook with fixed sheets and a validated schema.

## Inputs

- `cases/<case_name>/working/baseline_analysis.json`
- `cases/<case_name>/working/baseline_controls.md`
- `cases/<case_name>/working/baseline_report.md`
- `cases/<case_name>/working/baseline_priority_recommendations_cn.md`

## Outputs

- `cases/<case_name>/working/final_baseline.xlsx`
- `cases/<case_name>/working/skill03_debug.json`
- script entrypoint: `scripts/run_finalize.py`

## Rules

- Do not re-parse source documents.
- Do not re-run alignment or similarity logic.
- Treat skill02 outputs as the approved analytical basis.
- Use `qwen3-max` for final English wording and workbook section summaries.
- Preserve conservative treatment of pending controls.
- Fail the run if the online model is unavailable or returns unusable output.
- Treat the workbook schema as fixed production contract. Do not add, remove, or rename sheets or columns without updating the references and validation logic together.

## Procedure

1. Load the baseline analysis and control artifacts.
2. Load the DashScope runtime configuration.
3. Use `qwen3-max` to produce validated section wording and domain summaries.
4. Render the fixed workbook schema locally from the approved analysis plus validated LLM wording.
5. Fail if the model is unavailable or returns unusable output.
6. Write the final production workbook and a small debug artifact on success.

## References

- Finalization guidance: `references/finalization.md`
- Output structure: `references/output_package.md`
- Workbook schema: `references/workbook_schema.md`
