# Archive

This directory holds repository content that is no longer part of the active runtime path, but is being kept for traceability and historical reference.

## Active runtime path

The current production pipeline uses:

- `baseline_agent.py`
- `runtime/`
- `skills/skill01_document_parse`
- `skills/skill02_baseline_generation`
- `skills/skill03_baseline_finalize`
- `skills/baseline_writer`
- `templates/project_profile.template.json`
- `templates/baseline_controls.template.md`
- `templates/baseline_report.template.md`

## Archived content

### `legacy_skills/`

Older skill split that predates the current `skill01/02/03` pipeline:

- `organizational_policy_ingest`
- `benchmark_requirement_ingest`
- `control_mapping_analysis`

These are kept only for history/reference and are not called by `baseline_agent.py`.

### `legacy_templates/`

Templates associated with the older artifact naming and flow:

- `organizational_requirements.template.json`
- `benchmark_requirements.template.json`
- `mapping_analysis.template.md`

### `samples/`

Ad hoc demo input material no longer used by the active pipeline:

- `tmp_demo/`

### `build_artifacts/`

Intermediate build output that can be recreated by `build_app.sh`.

### `misc/`

Non-runtime cache or Finder metadata moved out of the repository root for cleanliness.
