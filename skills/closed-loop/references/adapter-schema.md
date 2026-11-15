# Adapter schema and campaign state

An adapter is a manifest (`closed-loop-adapter/1`) of **pinned argument lists** that `closed_loop.py` runs, plus whatever those
commands call. The orchestrator reads only their JSON. `scripts/closed_loop.py --help` lists every verb; `adapter-check` validates a
manifest.

## Manifest

```json
{
  "contract": "closed-loop-adapter/1",
  "subject": {"name": "fake", "mission": ["clauses a reviewer can cite"]},
  "execution": {"cwd": ".", "env_allow": ["HOME"], "capability": "writes-worktree", "timeout_seconds": 3600,
                "cleanup": ["python3", "adapter.py", "cleanup"], "pin": ["adapter.py", "graders/"]},
  "commands": {"cases": [...], "records": [...], "identity": [...], "step": [...], "probe": [...]},
  "claims": {"cases.runs:A1": {"effect": "effectful"}, "grading.scores": {"effect": "effectful"}},
  "dimensions": ["style", "size"],
  "combinations": [["style", "size"]],
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
  **`timeout_seconds`** (default 3600) bounds every adapter call: a hung call is killed, reported as an error, and its time is
  charged to the budget. **`pin`** lists files or folders (relative to the manifest, or absolute) whose content the boundary hash
  covers: list the adapter's own program and every grader or check script, because an argument list alone does not say what the
  program it names will do. **`step_timeout_seconds`** (default 21600) bounds how long one step may stay running.
- **`dimensions`** name the properties of a case that coverage is judged on (for example `style`); a case lists `dimensions` as
  `{name: value}`. A scope's *values* are `name=value` strings. **`combinations`** list sets of two or more dimensions whose value
  *pairs* also count as coverage (`style=alpha&size=large`): a catalog of AX, BY and AY exposes AY only through the pair, so a
  scope that covers AX and BY still lists AY as not covered when `["style", "size"]` is declared, and widens to it.
- **`quiet_window`** is K, an integer of at least 1, default 2. **`evaluation_class`** is `scripted`, `scripted+judge` or
  `judge-only`; `judge-only` needs `judge_reliability` (kappa and noise) recorded.
- **`authority.owner_only_requires`**: a case whose `requires` (or `hosted: true`) meets this list is owner-gated: it cannot be in a
  scope, first or widened, until `approve --case ID --yes-owner-approved` (or `init --approve-case ID --yes-owner-approved`).
- **`not_covered`** may override the default reason for a catalog value a scope leaves out.

The **boundary hash** (`boundary_sha256`) covers `commands`, `execution`, `authority`, `claims`, `evaluation_class`, `combinations` and
the content of every `pin`ned file; the owner ratifies that hash. A manifest or pinned file edited after `init` is refused (its
identity differs, so start a new campaign). The pins are a guard against an unratified change, not a proof that the adapter is
honest: the certificate checks the evidence the adapter reports, and the owner's ratification is the trust in what it reports.

## Adapter verbs

Each prints one JSON object and exits 0. A non-zero exit, a timeout, or output that is not a JSON object is an error the
orchestrator reports (and charges for).

| verb | prints |
| --- | --- |
| `cases` | `{"cases": [{"id", "dimensions", "cost", "requires": [], "hosted": false}]}` |
| `records` | `{"records": [{"id", "title", "material", "target": "subject"\|"adapter", "status", "evidence", "reopen_when", "cases": []}]}` |
| `identity` | `{"scoring": token, "build": token}`: the evaluator and the subject as they are now |
| `probe CLAIM` | `{"state", "evidence", "consumed"?}` with a state from that claim's ladder ([readiness.md](readiness.md)) |
| `step start --key K --scope S --cases A,B --mode iterate\|sweep --base TIP --out DIR` | `{"handle", "status", "iteration"?}`; **idempotent on K**: a second start with the same key returns the same handle and launches nothing |
| `step poll --handle H` | `{"status": "running"\|"done"\|"failed"\|"cancelled", "iteration"?, "error"?}`; a failed poll may carry `iteration.consumed` so the failed step is charged |
| `step cancel --handle H` | `{"status": "cancelled"}` |

| `execution.cleanup … --keys K1,K2` | `{"verified": true, "receipt": text}` for the runs named by those step keys |

**A `step start` launches the run detached and returns.** Start it in its own session with its output redirected to files under
`--out`: a call returns only when the program and everything holding its output pipe has exited, and a call that outlives
`timeout_seconds` is killed together with its whole process group. Every adapter call runs with its standard input closed.

Record `status` values the orchestrator understands: `verified`; `dropped`, `refuted`, `rejected` (resolved only with non-empty
`evidence`; so is `verified`); `open`, `admitted`, `promoted`, `undecided` (actionable); anything else, such as `deferred`, `owner`,
`unknown` or a status it has never seen, keeps a material record unresolved and waits for the owner. A `target: adapter` record
belongs to the evaluator, is listed in the report and never blocks a subject certificate.

An **`iteration`** object (what a finished step reports) must have exactly this shape; the orchestrator validates it before the
evidence can count, and a report of any other shape is recorded as a failed step, never as a quiet iteration:
`build_before`, `build_after`, `scoring` (non-empty text); `cases {id: {ran: bool, floors_met: bool, baseline:
"comparable"|"none"|"unknown"}}` for **exactly** the cases the step was asked to run; `review {valid: bool, complete: bool}`,
`judge {valid, complete}`; `discoveries [{id, material: bool, repeat?}]`; `candidate {id, hash, outcome: PROMOTE|DROP|UNDECIDED}`
or null; `invalid [text]`; `cleanup {verified: bool, receipt}` (a receipt whenever verified); `tier {green: bool, build}` (a
quick-tier receipt for the build); `acceptance {candidate, evidence}` or null; `consumed {name: finite amount >= 0}`.
Queries (`cases`, `records`, `identity`, `probe`) must not write inside the workspace: they run as exit checks, and a check that
changed the workspace would invalidate its own recorded run.

## Campaign state (`closed-loop-campaign/1`)

`campaign.json` in the campaign folder, written atomically under `campaign.lock`, validated whenever it is read. A verb that changes state waits up to 30 s for the lock and then refuses with a message (look for a hung adapter call, which `execution.timeout_seconds` bounds); the read-only verbs (`status`, `next`, `certificate`, `coverage`, `contract`, `check`) never take it. Never recreated
silently: a missing, corrupt or malformed file is an error and is left untouched. **The campaign folder is a small Git repo that
`init` creates and that holds only campaign state**, so the Until Loop can fingerprint every change to the evidence the checks read.
Bulky files live in the sibling folder `<campaign>.work` (`runs/<step key>/` for what the adapter wrote, and the Until Loop's own
state, contract and receipt files), never inside the campaign folder or the subject workspace. The campaign folder and the subject
workspace must be separate, neither inside the other.

`id` (random, so two campaigns never share a step key), `subject`, `workspace`, `manifest {path, sha256, boundary_sha256}`,
`ratification {boundary_sha256, at, note}` or null, `readiness {at, boundary_sha256, scoring, start_ok, blocked, allowed_claims,
claims {claim: {state, evidence}}}` or null (a claim above the bottom of its ladder must carry evidence), `budget` and `consumed` (aggregate across scopes; a budget is mandatory), `quiet_window`, `scopes [{id, cases, values,
not_covered, reason, sweep_pending}]`, `scope` (the current id), `tip` (the accepted build), `iterations` (the orchestrator's record
of each finished step: the adapter's facts plus `quiet` and `quiet_reasons`; a failed or cancelled step is an invalid iteration
too), `steps {key: {handle, status, ...}}`, `launch_intents {key: {base, scope, cases, mode}}` (written, and saved, before the adapter
is called, and cleared when the step is recorded: a replay after a crash starts from the same base, and a launch whose outcome is
unknown stays here until `cleanup` covers it), `cleaned_launches {key: receipt}`, `start_failures` and `poll_failures {key:
[errors]}`, `tasks`, `unknowns`, `approved_cases`, `events` (an
audit trail) and `stop`. In the folder: `journal.md` (append-only, one line per iteration, idempotent on the step key),
`report.md` and `report.json`.

**Identities.** *Scoring identity* is the adapter's `scoring` token: results compare only under the same one. *Campaign identity* is
a hash of the manifest, this script and the boundary; a contract binds the script's hash, the scope and the campaign identity, so a
changed script, another scope or another campaign fails its own checks with exit 3.

**Budget.** `--budget seconds=3600,turns=400` is required at `init` and is checked before each step, so a step that finishes can
overshoot it by up to its own consumption. Everything a campaign spends is charged: each finished or failed step's `consumed`,
each probe's `consumed` (charged as each probe finishes, and even when its answer is refused, so a failing probe still pays for
the ones before it), each task's `--consumed`, and the wall time of adapter calls that failed or timed out (to `seconds`). A step in
flight spends `seconds` as it runs, because the adapter reports its cost only when it finishes: `seconds` is wall-clock time. Once
the budget is used `readiness` refuses to run a probe and a running step is **not polled again**: the campaign stops `incomplete`,
the step is left for `cancel` and `cleanup`, and the owner may reopen with a larger budget to let it finish. Separately, a step that
has run longer than `execution.step_timeout_seconds` (default 21600) ends the campaign, and three identical poll failures end it.
Exhaustion ends the *campaign* `incomplete`, never converged, though a scope certificate gathered before it can still read
converged; only the owner raises the budget, with `reopen --budget`.
