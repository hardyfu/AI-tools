# Classification Guidance

Use conservative matching.

- `carry_forward`: the global policy already covers the requirement strongly enough.
- `adapt_for_platform`: the global policy has the intent, but the third-party standard adds platform-specific implementation detail.
- `new_baseline_control`: the global policy does not cover the control strongly enough; it should be added explicitly to the platform baseline.

Workflow rule:

- Start from parser outputs, not raw PDF text.
- Build a small candidate match set deterministically.
- Let the configured DashScope text model analyze the parser outputs and candidate matches to produce the final classification.
- Keep the final output traceable to both the candidate match data and the LLM rationale.

Output contract:

- `baseline_action` must be one of `carry_forward`, `adapt_for_platform`, `new_baseline_control`.
- `decision` must map exactly to `aligned`, `partial`, or `gap`.
- Every benchmark requirement must produce exactly one classified output row.
