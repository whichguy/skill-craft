# State files (`.shiploop/`)

Everything below lives under the **run dir** (default: walked from cwd to
`.shiploop`), never inside the `shiploop` skill package.

| File | Written during | Source of truth for |
|------|-----------------|----------------------|
| `state.json` | every command | phase, hashes, `dep_roots`, blocked/resume, `terminal` |
| `prompt.md` | `init` | the original ask |
| `environment.md` | `validate-spec` (survey + practices) | session survey: prose brief + `## machine` fenced JSON (`exclusive` is the session writer map); practice references and practice prose live here, hashed with the file. Session-wide union of `dont_use`; a row's `use` in another row's `dont_use` is a dest-plan gap (split the session). Artifact-scoped `Writes:` is a follow-up, not this increment. |
| `spec.md` | `validate-spec` | labeled `done_sentence:` and `checkable: true\|false` (each exactly once); `ask_user:` when `checkable: false` |
| `backchain/plan.json` | `plan` | canonical sequence DAG (steps carry `statement`, `prompt`, `produces`, `inputs`, `origin`; every seed `prompt` cites `environment.md` `references[].path` and a `Tools:` block) |
| `plan.md` | `plan` | sequence pointer with labeled `done_sentence:` (must equal `spec.md` at dest implement; same fence-skip labels as spec.md). Not hashed into `plan_sha256` — a post-bind edit does not fail-closed on `next`. dest residual may store `state.bound_plan_hash = sha256(plan.md)`. May lag the DAG after `inject-step`. |
| `steps/<id>.json` | `implement` | per-step receipt (`status`, `plan_sha256`, `worktree`, `branch`, `base_sha`) |
| `history.jsonl` | every command | append-only event log |
| `recap.html` | dest done / dest halted | harness-written walk-back HTML (intent, original spec, accomplished, changed, end result, outcome, verified) |

There is **no** `environment.json`, `spec.json`, `implement.json`, or
host-authored `plan.json`. Each artifact above has exactly one file as
its source of truth; the script never writes a JSON twin next to a `.md`
SoT. Leftover `plan.json` wrappers are inert — dest implement and
`inject-step` ignore them; `init --force` still unlinks them. The DAG in
`backchain/plan.json` is canonical.

## Hashes (fail-closed drift)

- `environment_sha256 = sha256(environment.md)`
- `spec_sha256 = sha256(spec.md)`
- `plan_sha256 = sha256(backchain/plan.json)`

`dest plan` **writes** `environment_sha256` / `spec_sha256` when empty (first
bind — including `blocked → plan`) and **verifies** them when already set.
Editing either file after bind requires dest blocked → validate-spec; rewrite
environment.md; → plan (do not hand-edit backchain/plan.json)
(this clears all three hashes and any receipts). Once `phase != validate-spec
and != plan`, any command that reads state re-checks these hashes and fails
closed (exit 2) on drift. An empty `environment_sha256` (a pre-0.7 run, or a
run that never survived to `dest plan`) is grandfathered — not enforced —
until the next `validate-spec`.

**Residual bind (not fail-closed):** dest residual may set
`state.bound_plan_hash = sha256(plan.md)` when it auto-binds a plan that
already has `## Review Coverage`. A later byte change does **not**
`die(EXIT_BLOCKED)`; `plan_waiver()` returns None and the ledger may
read `foreign`. Do not merge `plan.md` into a file that keeps receiving
post-bind edits.

## Product `README.md`

Not a `.shiploop/` state file — it lives in the bound repo tree. Survey reads
it (if present) and cites it in `environment.md.references`; `validate-spec`
never writes it. The spec's final product duty is a README create/revise as
a late DAG successor (see `plan.md`, `survey.md`). It must never contain
machine JSON, handles, tokens, MCP inventory, or session hashes — those stay
in `environment.md`. `init --force` never deletes it.

## End-of-run `recap.html`

The harness writes this file on dest `done` and dest `halted` from the run
files (prompt, frozen spec, DAG/receipts, plan, survey prose, history,
ledger). dest appends `history.jsonl` first, then rewrites the recap so
**Materially changed** includes the dest event. The top of the page is a
reveal: key accomplishments and a diagram of implementation outcomes
(starting facts → each step's `produces` → frozen done_sentence).
**Verified** reports review-coverage status and that quality `/goal` /
outer-loop publish are host-owned (not harness-verified). Not hashed.
`--force` unlinks it. The script refuses dest `done` when the file is
missing, empty, not HTML, or missing the briefing words `intent`,
`accomplish`, `changed`, `outcome`, `verif`, `original spec`, and
`end result`. The host does not hand-author it.

## `state.json` `terminal`

Unset (`null`) until dest `done` or dest `halted`. This is the
review-coverage close mode, not a claim that quality `/goal` or
outer-loop publish ran:

| Value | Meaning |
|-------|---------|
| `success` | dest `done`; review-coverage complete and landed |
| `waived` | dest `done`; review-coverage waived on the bound plan |
| `halted` | dest `halted`; bound residual ledger is `stopped (...)` |

Quality `/goal` and outer-loop publish stay host-owned on every row.
Packet Diagnosis and recap Verified say that; `terminal` does not
witness them.
