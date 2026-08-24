The spec is **frozen**. Read `{{SPEC_MD}}` (done sentence, checkable) and
`{{ENV_MD}}` (frozen survey). Do not rewrite either.

Call the installed **backchain** skill **once** to write the sequence DAG.
Include, when the frozen spec implies them, **prep**, **intermediate deploy**,
and **cleanup** as real DAG steps (postconditions), not as a second spec.
Include a **README create or revise** as a **late DAG successor** after the
feature work it documents — same grain as cleanup, not a new state-machine
phase. It must record what the app is, how to run it, and what this
increment changed; it must never contain machine JSON, handles, tokens, MCP
inventory, or session hashes (those stay in `{{ENV_MD}}`).

Every seed step must carry a nonempty `prompt` — the exact string the host
will paste into that step's inner loop (newlines allowed, no control chars
other than newline, no `/devloop`). `statement` stays the short diagnosis
label; `prompt` is what gets pasted, not composed later.

Persist the backchain document to `{{BACKCHAIN_JSON}}` (canonical). Then
write:

- `{{PLAN_MD}}` with a labeled line `done_sentence: {{DONE_SENTENCE}}` (must
  equal the spec)
- `{{PLAN_JSON}}` wrapper: `done_sentence` identical to the spec, `backchain`
  path, `step_ids` copy

Do not vendor backchain. Do not exec a live packager. Missing backchain root
is a Missing line — then `/shiploop complete --blocked --resume-to plan`.
