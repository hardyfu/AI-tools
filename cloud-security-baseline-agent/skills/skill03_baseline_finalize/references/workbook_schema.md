# Workbook Schema

The final workbook `final_baseline.xlsx` must contain exactly these sheets in order:

1. `Summary`
2. `Document Sections`
3. `Control Mapping`
4. `Pending Controls`
5. `Organizational Only`
6. `Recommendations CN`

## `Summary`

Columns:

- `Field`
- `Value`

Required rows:

- `case_name`
- `document_title`
- `target_platform`
- `finalization_model`
- `carry_forward_count`
- `adapt_for_platform_count`
- `new_baseline_control_count`
- `organizational_only_count`
- `llm_used`
- `provider`

## `Document Sections`

Columns:

- `Section`
- `Content`

Required section rows:

- `Title`
- `Purpose`
- `Scope`
- `Principles`
- `Governance`

Additional rows:

- `Domain Overview: <domain>`

## `Control Mapping`

Columns:

- `Domain`
- `Baseline Action`
- `Decision`
- `Benchmark Requirement ID`
- `Benchmark Source Requirement ID`
- `Benchmark Section`
- `Benchmark Statement`
- `Benchmark Category`
- `Benchmark Service`
- `Matched Global Requirement ID`
- `Matched Global Source Requirement ID`
- `Matched Global Section`
- `Matched Global Statement`
- `Match Score`
- `Trace`
- `Rationale`

Rows:

- One row per `baseline_mapping` item from `baseline_analysis.json`

## `Pending Controls`

Columns:

- `Benchmark Requirement ID`
- `Benchmark Source Requirement ID`
- `Benchmark Section`
- `Benchmark Statement`
- `Benchmark Category`
- `Benchmark Service`
- `Rationale`

Rows:

- Only items where `decision == gap`

## `Organizational Only`

Columns:

- `Global Requirement ID`
- `Global Source Requirement ID`
- `Global Section`
- `Global Statement`
- `Category`
- `Priority`

Rows:

- One row per item in `global_policy_only_requirements`

## `Recommendations CN`

Columns:

- `Section`
- `Content`

Rows:

- Ordered lines parsed from `baseline_priority_recommendations_cn.md`
- Ignore blank lines
- Preserve heading text and bullet text as separate rows
