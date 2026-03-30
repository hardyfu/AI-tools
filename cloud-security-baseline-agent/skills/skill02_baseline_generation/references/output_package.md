# Output Package

The complete baseline package should contain:

- a machine-readable analysis artifact
- a human-readable baseline control list
- a summary report
- a prioritized recommendation document for review

Do not stop at similarity mapping only. The workflow must synthesize a usable baseline package.

Format contract rules:

- `baseline_analysis.json` is the authoritative machine-readable artifact and must remain schema-stable.
- `baseline_controls.md`, `baseline_report.md`, and `baseline_priority_recommendations_cn.md` must keep fixed top-level section structure so downstream finalization can parse them safely.
- Downstream workbook generation depends on stable field names, decisions, trace identifiers, and summary counts.
