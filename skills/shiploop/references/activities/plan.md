The spec is **frozen**. Read `{{SPEC_MD}}` (done sentence, checkable, and
the three placement answers) and `{{ENV_MD}}` (frozen survey). Do not
rewrite either.

Call the installed **backchain** skill **once** to write the sequence DAG.
Place work from those answers — do not invent a second spec or a second
copy of the same step:

- **prep** — if the spec named **deploy preparation before the walk**, that
  *is* the early prep step. If it said none, omit deploy-prep; still add
  other implied prep.
- **intermediate deploy** — if the spec named **deploy/publish** as
  **dag**, that *is* the deploy/publish sequence step. If it named
  **outer-loop**, do **not** put that publish in the DAG — residual owns
  it after the walk. If it said **none**, omit a deploy/publish step.
- **cleanup** — when implied, as a real DAG step (postcondition).
- A **quality `/goal` on outer-loop completion** is never a DAG step.

Include a **README create or revise** as a **late DAG successor** after the
feature work it documents — same grain as cleanup, not a new state-machine
phase. It must record what the app is, how to run it, and what this
increment changed; it must never contain machine JSON, handles, tokens, MCP
inventory, or session hashes (those stay in `{{ENV_MD}}`).

Every seed step must carry a nonempty `prompt` — the exact string the host
will paste into that step's inner loop (newlines allowed, no control chars
other than newline). `statement` stays the short diagnosis
label; `prompt` is what gets pasted, not composed later. Every **seed**
step's `prompt` must cite the concrete practice references from `{{ENV_MD}}`
(`references[].path` URLs or repo paths) that that step must use, so
implement reprints them; `dest implement` refuses a DAG whose stored seed
`prompt` omits any of those paths. `inject-step`'s own discovered steps
still need a nonempty `prompt` (same missing-prompt gate) but are exempt
from that citation requirement — they are ad-hoc mid-implement fixes, not
researched practice work; see `implement.md`.

Persist the backchain document to `{{BACKCHAIN_JSON}}` (canonical). Then
write:

- `{{PLAN_MD}}` with a labeled line `done_sentence: {{DONE_SENTENCE}}` (must
  equal the spec)
- `{{PLAN_JSON}}` wrapper: `done_sentence` identical to the spec, `backchain`
  path, `step_ids` copy

Do not vendor backchain. Do not exec a live packager. Missing backchain root
is a Missing line — then `/shiploop complete --blocked --resume-to plan`.
