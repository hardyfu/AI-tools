# Finalization Guidance

The final artifact should:

- use formal English for workbook section summaries rather than free-form prose
- organize controls by domain instead of source order
- distinguish between:
  - controls already covered by the global policy
  - controls that require Alibaba Cloud-specific adaptation
  - controls that remain pending or should be explicitly added
- include short governance wording describing exceptions, ownership, and review cadence

Formatting and contract rules:

- The LLM may only generate section-level wording and domain summaries.
- Control rows, identifiers, decisions, traces, and counts must be rendered locally from structured data.
- The workbook schema is authoritative. If wording is present but the schema is invalid, the run must fail.

Use concise, formal English. Avoid repeating raw analysis noise or parser artifacts.
