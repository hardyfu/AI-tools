# Workflow

`skill01-document-parse` supports two document roles:

- `global_policy`: parse internal policy / standard style documents where obligations are often numbered and grouped by control domains.
- `third_party_standard`: parse external benchmarks or standards where requirements appear as recommendation summaries.

Use the parser that matches the role rather than trying to force a single generic parser over both shapes.

This skill is parse-only. It should record extraction quality, but it should not use LLMs to classify, reason, or synthesize the baseline.
