# State files (`.shiploop/`)

Everything below lives under the **run dir** (default: walked from cwd to
`.shiploop`), never inside the `shiploop` skill package.

| File | Written during | Source of truth for |
|------|-----------------|----------------------|
| `state.json` | every command | phase, hashes, `dep_roots`, blocked/resume |
| `prompt.md` | `init` | the original ask |
| `environment.md` | `validate-spec` (survey + practices) | session survey: prose brief + `## machine` fenced JSON; practice references live here |
| `spec.md` | `validate-spec` | labeled `done_sentence:` and `checkable: true\|false` (each exactly once); `ask_user:` when `checkable: false` |
| `backchain/plan.json` | `plan` | canonical sequence DAG (steps carry `statement`, `prompt`, `produces`, `inputs`, `origin`) |
| `plan.md` / `plan.json` | `plan` | pointer + thin wrapper (`done_sentence`, `backchain` path, `step_ids` — not SoT, recomputed from the DAG) |
| `steps/<id>.json` | `implement` | per-step receipt (`status`, `plan_sha256`, `worktree`, `branch`, `base_sha`) |
| `history.jsonl` | every command | append-only event log |
| `recap.html` | dest done / dest halted | harness-written walk-back HTML (intent, original spec, accomplished, changed, end result, outcome, verified) |

There is **no** `environment.json`, `spec.json`, or `implement.json`. Each
artifact above has exactly one file as its source of truth; the script never
writes a JSON twin next to a `.md` SoT. (`plan.json`/`plan.md` are a wrapper
pair, not a twin — the DAG in `backchain/plan.json` is still canonical.)

## Hashes (fail-closed drift)

- `environment_sha256 = sha256(environment.md)`
- `spec_sha256 = sha256(spec.md)`
- `plan_sha256 = sha256(backchain/plan.json)`

`dest plan` **writes** `environment_sha256` / `spec_sha256` when empty (first
bind — including `blocked → plan`) and **verifies** them when already set.
Editing either file after bind requires `blocked → validate-spec` to rebind
(this clears all three hashes and any receipts). Once `phase != validate-spec
and != plan`, any command that reads state re-checks these hashes and fails
closed (exit 2) on drift. An empty `environment_sha256` (a pre-0.7 run, or a
run that never survived to `dest plan`) is grandfathered — not enforced —
until the next `validate-spec`.

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
ledger). Not hashed. `--force` unlinks it. The script refuses dest `done`
when the file is missing, empty, not HTML, or missing the briefing words
`intent`, `accomplish`, `changed`, `outcome`, `verif`, `original spec`, and
`end result`. The host does not hand-author it.
