# Adapter schema and campaign state

An adapter is a manifest (`closed-loop-adapter/1`) of **pinned argument lists** that `closed_loop.py` runs, plus whatever those
commands call. The orchestrator reads only their JSON. `scripts/closed_loop.py --help` lists every verb; `adapter-check` validates a
manifest.

## Manifest

```json
{
  "contract": "closed-loop-adapter/1",
  "subject": {"name": "fake", "mission": ["clauses a reviewer can cite"]},
  "execution": {"cwd": ".", "env_allow": ["HOME"], "capability": "writes-worktree", "cleanup": ["python3", "adapter.py", "cleanup"]},
  "commands": {"cases": [...], "records": [...], "identity": [...], "step": [...], "probe": [...]},
  "claims": {"cases.runs:A1": {"effect": "effectful"}, "grading.scores": {"effect": "effectful"}},
  "dimensions": ["style"],
  "quiet_window": 2,
  "evaluation_class": "scripted",
  "authority": {"routine": ["run cases"], "owner_only": ["hosted cases"], "owner_only_requires": ["hosted"]},
  "not_covered": {"style=gamma": "needs a hosted org; the owner decides"}
}
```

- **`commands`**: argument lists, never shell strings. `cases`, `records`, `identity` and `step` are required; `probe` is required when
  `claims` is non-empty. `argv[0]` has no whitespace. The orchestrator appends the verb's arguments.
- **`execution`** is the execution boundary the owner ratifies. Only `PATH` and the names in `env_allow` reach the child, plus
  `CLOSED_LOOP_WORKSPACE` (the subject's working directory) and `CLOSED_LOOP_CAMPAIGN`. `capability` is `read-only`,
  `writes-worktree` or `hosted`. `cwd` is relative to the manifest. `cleanup` is the owned-cleanup argument list.
- **`dimensions`** name the properties of a case that coverage is judged on (for example `style`); a case lists `dimensions` as
  `{name: value}`. A scope's *values* are `name=value` strings.
- **`quiet_window`** is K, default 2. **`evaluation_class`** is `scripted`, `scripted+judge` or `judge-only`; `judge-only` needs
  `judge_reliability` (kappa and noise) recorded.
- **`authority.owner_only_requires`**: a case whose `requires` (or `hosted: true`) meets this list is owner-gated: the campaign will
  not widen to it until `approve --case ID --yes-owner-approved`.
- **`not_covered`** may override the default reason for a catalog value a scope leaves out.

The **boundary hash** (`boundary_sha256`) covers `commands`, `execution`, `authority`, `claims` and `evaluation_class`; the owner
ratifies that hash. A manifest edited after `init` is refused (its identity differs).

## Adapter verbs

Each prints one JSON object and exits 0. A non-zero exit or output that is not a JSON object is an error the orchestrator reports.

| verb | prints |
| --- | --- |
| `cases` | `{"cases": [{"id", "dimensions", "cost", "requires": [], "hosted": false}]}` |
| `records` | `{"records": [{"id", "title", "material", "target": "subject"\|"adapter", "status", "evidence", "reopen_when", "cases": []}]}` |
| `identity` | `{"scoring": token, "build": token}`: the evaluator and the subject as they are now |
| `probe CLAIM` | `{"state", "evidence"}` with a state from that claim's ladder ([readiness.md](readiness.md)) |
| `step start --key K --scope S --cases A,B --mode iterate\|sweep --base TIP --out DIR` | `{"handle", "status", "iteration"?}`; **idempotent on K**: a second start with the same key returns the same handle and launches nothing |
| `step poll --handle H` | `{"status": "running"\|"done"\|"failed"\|"cancelled", "iteration"?, "error"?}` |
| `step cancel --handle H` | `{"status": "cancelled"}` |

Record `status` values the orchestrator understands: `verified`; `dropped`, `refuted`, `rejected` (resolved only with `evidence`);
`open`, `admitted`, `promoted`, `undecided` (actionable); `deferred`, `owner`, `unknown` (owner-gated). A `target: adapter` record
belongs to the evaluator, is listed in the report and never blocks a subject certificate.

An **`iteration`** object (what a finished step reports):
`build_before`, `build_after`, `scoring`; `cases {id: {ran, floors_met, baseline: "comparable"|"none"|"unknown"}}`;
`review {valid, complete}`, `judge {valid, complete}`; `discoveries [{id, material, repeat}]`;
`candidate {id, hash, outcome: PROMOTE|DROP|UNDECIDED}` or null; `invalid [...]`; `cleanup {verified, receipt}`;
`tier {green, build}` (a quick-tier receipt for the build); `acceptance {candidate, evidence}` or null; `consumed {name: amount}`.
Queries (`cases`, `records`, `identity`, `probe`) must not write inside the workspace: they run as exit checks, and a check that
changed the workspace would invalidate its own recorded run.

## Campaign state (`closed-loop-campaign/1`)

`campaign.json` in the campaign folder, written atomically under `campaign.lock`. Never recreated silently: a missing or corrupt
file is an error and is left untouched.

`id`, `subject`, `workspace`, `manifest {path, sha256, boundary_sha256}`, `ratification {boundary_sha256, at, note}` or null,
`budget` and `consumed` (aggregate across scopes), `quiet_window`, `scopes [{id, cases, values, not_covered, reason, sweep_pending}]`,
`scope` (the current id), `tip` (the accepted build), `iterations` (the orchestrator's record of each finished step: the adapter's
facts plus `quiet` and `quiet_reasons`), `steps {key: {handle, status, ...}}`, `tasks`, `unknowns`, `approved_cases`, `events` (an
audit trail) and `stop`. Beside it: `journal.md` (append-only, one line per iteration), `runs/<step key>/` (what the adapter wrote),
`report.md` and `report.json`.

**Identities.** *Scoring identity* is the adapter's `scoring` token: results compare only under the same one. *Campaign identity* is
a hash of the manifest, this script and the boundary; a contract binds the script's hash, so a changed script fails its own checks.
