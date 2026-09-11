# Durable run files (`.shiploop/`)

Everything below belongs to a run directory, normally `<repo>/.shiploop`,
not to the installed ShipLoop package. Markdown is the authoritative state.
Each structured record has one `shiploop-state` JSON fence inside its Markdown
file. There is no writable JSON mirror.

| File or directory | Authority / purpose |
|---|---|
| `state.md` | Current phase, stage, action, revision, frozen hashes, active step, and completed-action replay digests. |
| `run.md` | Persistent marker that identifies Markdown state authority and prevents accidental reinitialization/resurrection. |
| `prompt.md` | Original user request captured at initialization. |
| `preflight.md`, `approach.md` | Baseline facts and the initial delivery approach. |
| `environment.md` | Survey and research-facing environment brief. Its prose is human-readable; its single `## machine` JSON fence is the validated environment contract. |
| `research.md` | Sources, uncertainty resolution, and assumptions used before freezing the spec. |
| `spec.md` | Checkable `done_sentence:` and `checkable: true`; the product contract. |
| `lifecycle.md` | Whether preparation, quality, and publication belong in the DAG or outer loop, plus acceptance criteria and rationale. |
| `plan.md` | Human-readable sequence plan, including matching `done_sentence:` and the bound Review Coverage section. |
| `backchain/plan.md` | Canonical dependency DAG in a Markdown record. The JSON fence is authoritative for steps, dependencies, prompts, produces, and unresolved facts. |
| `steps/<id>.md` | Per-step receipt: allocation, branch/worktree, implementation evidence, Improve iterations, final check, plan review, and merge result. |
| `results/<action>.md` | Immutable submitted result for a completed action. |
| `checks/<action>.md` | Manifest plus verified check evidence for that action. |
| `manifests/<step-or-outer>.md` | Last accepted manifest for change detection and required verification reason. |
| `check-attempts/<action>-<id>.md` | Every verification attempt, including failures, timeout evidence, and manifest-change reason. |
| `logs/<action>/` | Raw stdout/stderr logs named by check; evidence, not Markdown authority or prompt payload. |
| `history-pages/<action>-<skip>.md` | Persisted pages of full Git commit bodies read for an Improve review. |
| `history.md` | Append-only command/action history. |
| `shiploop-improvements.md` | Deduplicated generic ShipLoop improvement proposals with provenance; proposal-only. |
| `preparation.md`, `coverage.md`, `quality.md`, `delivery.md`, `handoff.md` | Outer-loop evidence and final handoff records. |
| `migration.md`, `legacy-backup/` | Explicit legacy-migration marker and copied pre-0.9 records. |
| `transaction.md` | Short-lived write-ahead transaction journal. The next locked command rolls it forward deterministically. |

`recap.html` from an older run may remain as a historical view, but it is not
the source of truth for the 0.9 protocol. Inspect `handoff.md`, checks,
receipts, history, and the journal for current evidence.

## Authority and safety rules

- Do not create or edit `state.json`, `plan.json`, `steps/*.json`, or
  `history.jsonl`. They are legacy inputs only, never state authority once a
  Markdown run exists.
- The script rejects a legacy `state.json` until explicit `migrate`; it does
  not silently convert or resurrect JSON.
- `migrate` saves source JSON under `legacy-backup/`, creates
  `migration.md`, preserves code/branches/worktrees, and makes planning pass
  new evidence gates. It does not certify historical assertions.
- A state mutation writes one transaction intent before targets. If an
  interruption leaves `transaction.md`, the next locked command recovers it.
  Do not hand-delete it to make a run appear healthy.
- A result is action-bound. The same action plus byte-equivalent structured
  result is replay-safe; a different result for an already consumed action is
  rejected.
- Worktrees live below `<repo>/.worktrees/shiploop/<run-id>/<step-id>` and
  branches are retained after merge. The session checkout is the local merge
  destination; unrelated dirty files are preserved and block an implicit
  merge rather than being swept in.
- Results, check-attempt records, and raw logs can retain exact host-provided
  content. Do not include credentials or secrets; storage permissions reduce
  accidental exposure but do not promise perfect redaction.

## Frozen planning contracts

`environment.md`, `spec.md`, and `backchain/plan.md` are hashed when their
stage completes. Drift fails closed rather than being silently reinterpreted.
The only plan change path is the completed step's `post-inner` action: it can
replace `plan.md` and `backchain/plan.md` together after candidate validation,
and only change pending steps while retaining goal, initial state, completed
receipts, and the running receipt.

`environment.md` retains the valuable survey contract:

- The prose brief records scope, existing repository facts, research, writer
  and platform constraints, deferred tools, and non-secret readiness facts.
- Its `## machine` JSON object records inventory fields such as `kind`,
  `augment`, `references`, `tools`, `mcp`, `mcp_considered`, `exclusive`,
  `handles`, `initiation`, and UI information.
- When an exclusive destination writer exists, retain the validated
  `layout`/`routing` contract: product files do not enter reserved trees,
  writer lint/validation is the syntax authority, and live writer list/status
  is the identity authority.
- Never persist credentials, signed-in account addresses, or live delivery
  URLs as state. Reference a safe probe or expected account role instead.

The DAG must keep the same protections: safe unique IDs; nonempty exact
`produces`; valid dependency edges and no cycles; a complete seed prompt with
its `Tools:` contract; cited environment references; reserved-path and
exclusive-writer restrictions; and an early design-producing seed feeding
another seed for human-facing UI work. A discovered need after planning is
not a license to hand-edit the DAG: record it in post-inner learning and use a
pending-only plan revision when it changes the broader sequence.

## Product documentation is separate

The repository's `README.md` and `AGENTS.md` are product artifacts, not
ShipLoop state. Survey may read and cite them; the dependency plan can add a
late, tested product-documentation step when needed. They must not become a
dump for session hashes, secret handles, raw machine inventory, or unique
receipts. `AGENTS.md` is an optional standing aid for future agents, never a
replacement for the printed action or the run records.
