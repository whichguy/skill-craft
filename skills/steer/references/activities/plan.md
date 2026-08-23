The spec is **frozen**. Read `{{SPEC_MD}}` (details) and `{{SPEC_JSON}}` (machine keys). Do not rewrite the spec.

Call the installed **backchain** skill **once** to write the sequence DAG. Include, when the frozen spec implies them, **prep**, **intermediate deploy**, and **cleanup** as real DAG steps (postconditions), not as a second spec.

Persist the backchain document to `{{BACKCHAIN_JSON}}` (canonical). Then write:

- `{{PLAN_MD}}` with a labeled line `done_sentence: {{DONE_SENTENCE}}` (must equal spec JSON)
- `{{PLAN_JSON}}` wrapper: `done_sentence` identical to spec JSON, `backchain` path, `step_ids` copy

Do not vendor backchain. Do not exec a live packager. Missing backchain root is a Missing line — then `--to blocked --resume-to plan`.
