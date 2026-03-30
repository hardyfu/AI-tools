# Output Package

The finalization skill must emit a single production workbook:

- `final_baseline.xlsx`

The workbook is the final delivery artifact and must follow a fixed schema.
Do not rely on free-form narrative layout. All sheets, headers, and field meanings
must remain stable for downstream consumers.

Required sheets:

- `Summary`
- `Document Sections`
- `Control Mapping`
- `Pending Controls`
- `Organizational Only`
- `Recommendations CN`

The exact sheet and column contract is defined in:

- `references/workbook_schema.md`
