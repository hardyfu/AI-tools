# Cloud Security Baseline Agent Operations

## Purpose

This project converts:

- one organizational cloud security policy
- one third-party benchmark or standard

into a production baseline package for Alibaba Cloud.

The workflow is split into three stages:

1. `skill01`: parse source documents into structured JSON artifacts
2. `skill02`: classify mappings and generate baseline analysis artifacts
3. `skill03`: generate the final production workbook `final_baseline.xlsx`

## Case Layout

Each case lives under:

- `cases/<case_name>/`

Expected structure:

- `input/global_policy/`
- `input/third_party_standard/`
- `working/`

Key working artifacts:

- `global_policy_parse.json`
- `third_party_standard_parse.json`
- `baseline_analysis.json`
- `mapping_analysis.json`
- `baseline_controls.md`
- `baseline_report.md`
- `baseline_priority_recommendations_cn.md`
- `final_baseline.xlsx`
- `workflow_state.json`

## Command Reference

Convenience shell wrapper:

```bash
./baseline_cli.sh
```

Interactive mode options:

```bash
1. Open GUI
2. Bootstrap case
3. Stage global policy
4. Stage third-party standard
5. Run case pipeline
6. Validate single case
7. Validate all cases
```

Direct pass-through mode:

```bash
./baseline_cli.sh run --case <case_name>
```

Launch the desktop GUI:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py
```

Create a case scaffold:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py bootstrap --case <case_name>
```

Stage an input file:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py stage-input --case <case_name> --target global_policy --file /abs/path/to/file.pdf
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py stage-input --case <case_name> --target third_party_standard --file /abs/path/to/file.pdf
```

Run the full pipeline:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py run --case <case_name>
```

Validate one case without regenerating artifacts:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py validate-case --case <case_name>
```

Validate all cases under `cases/`:

```bash
/Users/ryan/Desktop/pythoncode/.venv/bin/python3 baseline_agent.py validate-all-cases
```

## GUI Mode

Running `baseline_agent.py` without arguments starts a desktop window.

Layout:

- top panel: live run log and stage output
- bottom panel: action buttons

Buttons:

- `New Instance`
  - prompts for `case_name`
  - prompts for one global policy file
  - prompts for one third-party standard file
  - automatically runs:
    - `bootstrap`
    - `stage-input` for global policy
    - `stage-input` for third-party standard
    - `run`
  - copies `final_baseline.xlsx` to `~/Downloads/<case_name>-final_baseline.xlsx`
  - reports the download path in the top log panel
- `Validate`
  - prompts for validating one case or all cases
  - writes validation output to the top log panel
- `Open Folder`
  - opens the current case working folder when available
  - otherwise opens `~/Downloads`

## Recommended Operating Sequence

For a new case:

1. Run `bootstrap`
2. Stage one organizational policy document
3. Stage one third-party benchmark document
4. Run `run`
5. Run `validate-case`

For regression checking after code changes:

1. Run `validate-all-cases`
2. Review any failed case before release

## Production Contract

This project treats output format as a strict contract, not a best-effort suggestion.

### Skill01 contract

- Parse artifacts must contain stable top-level fields
- Every requirement row must contain the required identifiers and metadata
- Duplicate requirement identifiers are not allowed
- Source quality metadata must be present

### Skill02 contract

- Every benchmark requirement must produce exactly one classified mapping row
- `baseline_action` is restricted to:
  - `carry_forward`
  - `adapt_for_platform`
  - `new_baseline_control`
- `decision` must match the action exactly:
  - `aligned`
  - `partial`
  - `gap`
- Summary counts must match row-level data

### Skill03 contract

- Final output must be `final_baseline.xlsx`
- Workbook sheet order and headers are fixed
- LLM output only provides section wording and domain summaries
- Workbook structure is rendered locally and validated before acceptance

## Final Workbook

The final workbook contains exactly these sheets:

1. `Summary`
2. `Document Sections`
3. `Control Mapping`
4. `Pending Controls`
5. `Organizational Only`
6. `Recommendations CN`

The authoritative workbook schema is defined in:

- `skills/skill03_baseline_finalize/references/workbook_schema.md`

## Validation Behavior

`validate-case` and `validate-all-cases` do not rerun the pipeline.

They only:

- read existing artifacts
- validate schema and consistency
- verify workbook structure
- verify `workflow_state.json` is consistent with files on disk

If validation fails, the command exits non-zero and reports the failing case or artifact.

## Notes

- The pipeline expects the Python virtual environment at:
  - `/Users/ryan/Desktop/pythoncode/.venv`
- Online model access is required for full `run`
- Validation commands are safe to use when you only want production acceptance checks
