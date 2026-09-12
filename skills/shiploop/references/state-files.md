# Durable run files (`.shiploop/`)

Everything below belongs to a run directory, normally `<repo>/.shiploop`,
not to the installed ShipLoop package. Markdown is the authoritative state.
Each structured record has one `shiploop-state` JSON fence inside its Markdown
file. There is no writable JSON mirror.

| File or directory | Authority / purpose |
|---|---|
| `state.md` | Current phase, stage, action, revision, frozen hashes, active step and nested execution-plan cursor, completed-action replay digests, the bound current-knowledge revision/hash/action provenance, and accepted research digest/certificate/as-of bindings. |
| `run.md` | Persistent marker that identifies Markdown state authority and prevents accidental reinitialization/resurrection. |
| `prompt.md` | Original user request captured at initialization. |
| `preflight.md`, `approach.md` | Baseline facts and the initial delivery approach. |
| `environment.md` | Survey and research-facing environment brief. Its prose is human-readable; its single `## machine` JSON fence is the validated environment contract. |
| `knowledge.md` | Script-owned current knowledge ledger: `version: 1`, `revision`, `entries`, `obligations`, `blockers`, `learnings`, and `last_checkpoint`. It is authoritative for recorded current observations, not authority to alter approved baselines. |
| `knowledge-history/<carry-forward-action-id>.md` | Immutable snapshot for each accepted carry-forward checkpoint. |
| `knowledge-reads/<review-action-id>.md` | Fully paged bounded-knowledge selection bound to an execution or step-plan review result. |
| `research.md`, `research-evidence.md` | Script-owned paired mutable research report and typed question/source evidence candidates. They are imported only through research results and accepted together at research-finalize. |
| `behavior.md` | Product behavior model; mutable only through imported behavior-loop results, frozen at behavior-finalize. |
| `spec-draft.md`, `lifecycle-draft.md` | Mutable spec-loop candidates; not the frozen contract and not authority to start sequencing. |
| `planning/research.md`, `planning/behavior.md`, `planning/spec.md` | Loop receipts: candidate/ledger identity, stable findings, current iteration, streak and completed-pass references. |
| `planning/<kind>-iterations/<iteration-id>.md` | Completed or abandoned planning passes retained for audit, not all reloaded into the next prompt. |
| `objectives/<loop>.md` and `objectives/<loop>/` | Durable candidate, finding ledger, full-body history, completed/abandoned passes, and certificate for a universal substantive-objective loop. |
| `planning/research-certificate.md`, `planning/behavior-certificate.md`, `planning/spec-certificate.md` | Finalized convergence proof binding candidate/ledger identity, fresh final checks and audit history; downstream gates require intact certificates. The research certificate is an as-of evidence baseline, not a permanent freshness claim. |
| `step-planning/<loop>.md` | Durable cursor and finding ledger for one execution-plan loop: the initial plan before `implement`, or the post-review plan before `improve-apply`. It records the target action, current nested pass, repair epoch, completed-pass references, and any material `scope`/`behavior` disposition evidence. |
| `step-planning/<loop>/candidate.md` | The script-owned current executable plan candidate for that loop, imported only through the matching step-plan result. It is not product source and does not rewrite the frozen spec or DAG. |
| `step-planning/<loop>/passes/<pass>.md` | A completed nested plan pass with its review rubric, context evidence, revisions, checks, and audit-commit binding. A fresh packet does not load all passes. |
| `step-planning/<loop>/abandoned/<pass>.md` | An interrupted, repaired, or `no-contract-change`-disposed nested pass retained with its reason and material outcome; it does not count toward convergence. |
| `step-planning/<loop>/certificate.md` | Fresh-finalization proof for the exact step plan: candidate/ledger, accepted planning checks, audit history, and whether it released `implement` or `improve-apply`. |
| `spec.md` | Checkable `done_sentence:` and `checkable: true`; promoted product contract only after spec-loop finalization. |
| `lifecycle.md` | Whether preparation, quality, and publication belong in the DAG or outer loop, plus acceptance criteria and rationale. |
| `plan.md` | Human-readable sequence plan, including matching `done_sentence:` and the bound Review Coverage section. |
| `backchain/plan.md` | Canonical dependency DAG in a Markdown record. The JSON fence is authoritative for steps, dependencies, prompts, produces, and unresolved facts. |
| `steps/<id>.md` | Per-step receipt: allocation, branch/worktree, current/history execution-plan bindings, implementation evidence, Improve iterations and their carried nested-plan learnings, final check, broader-plan review, and merge result. |
| `results/<action>.md` | Immutable submitted result for a completed action. |
| `report.html` and `state.md.report` | Script-generated terminal-only offline view and compact integrity binding (`path`, HTML SHA-256, source digest, outcome, evidence completeness, schema version). The HTML is derived, not authoritative state. |
| `checks/<action>.md` | Manifest plus verified check evidence for that action. |
| `manifests/<step-or-outer>.md` | Last accepted manifest for change detection and required verification reason. |
| `check-attempts/<action>-<id>.md` | Every verification attempt, including failures, timeout evidence, and manifest-change reason. |
| `logs/<action>/` | Raw stdout/stderr logs named by check; evidence, not Markdown authority or prompt payload. |
| `history-pages/<action>-<skip>.md` | Persisted pages of full Git commit bodies read for an execution or step-plan review. |
| `history.md` | Append-only command/action history. |
| `shiploop-improvements.md` | Deduplicated generic ShipLoop improvement proposals with provenance; proposal-only. |
| `preparation.md`, `coverage.md`, `quality.md`, `delivery.md`, `handoff.md` | Outer-loop evidence and final handoff records. |
| `migration.md`, `legacy-backup/` | Explicit legacy-migration marker and copied pre-0.9 records. |
| `transaction.md` | Short-lived write-ahead transaction journal. The next locked command rolls it forward deterministically. |

`recap.html` from an older run may remain as a historical view, but it is not
the source of truth for the 0.9 protocol. Inspect `handoff.md`, checks,
receipts, history, and the journal for current evidence.

## Scope/behavior disposition

A material `scope` or `behavior` step-plan finding means the proposed work is a
new or contradictory requirement against the frozen contract. It is not the
category for an ordinary implementation gap in an already-approved flow; use
`implementation`, `flow`, or `edge-condition` for that review result.

Such a finding durably pauses the run at `step-plan-disposition`. `resume`
only makes that exact action available; it does not remove the blocker, change
the candidate, or move the run to `step-plan-revise`. To demonstrate that the
approved contract actually remains unchanged, the action result contains only
`summary`, `disposition: "no-contract-change"`, and `resolutions` with one
`{id,evidence}` entry for every and only material `scope`/`behavior` blocker.
The script records the disposition on each finding, archives the current pass,
rebinds a new execution-plan epoch, and starts a fresh review. The candidate,
product, DAG, and frozen contract remain unchanged.

If the contract really must change, halt and obtain direction. This disposition
does not implement a scope-changing rebaseline or authorize an in-place
contract edit.

## Authority and safety rules

- Do not create or edit `state.json`, `plan.json`, `steps/*.json`, or
  `history.jsonl`. They are legacy inputs only, never state authority once a
  Markdown run exists.
- The script rejects a legacy `state.json` until explicit `migrate`; it does
  not silently convert or resurrect JSON.
- `migrate` saves source JSON under `legacy-backup/`, creates
  `migration.md`, preserves code/branches/worktrees, and makes planning pass
  new evidence gates. It does not certify historical assertions.
- New Markdown runs retain state version 3 and add
  `planning_protocol_version: 2`, a monotonically advanced `planning_epoch`,
  and `step_planning_protocol_version: 1`. Pre-v2 Markdown runs, including
  version 1 or a missing upstream-planning marker, require the action-bound
  `planning-upgrade` route before mutation. With no step receipt or active
  work, it archives the research pair, all planning artifacts and downstream
  contracts, clears research/behavior/spec/lifecycle/plan bindings, and retains
  only an unfinished preflight/approach/survey/research cursor; otherwise it
  refuses the run.
  See [Earlier Markdown runs](planning-loops.md#earlier-markdown-runs).
- A v3 run that lacks `step_planning_protocol_version: 1` does not receive a
  retroactive plan certificate. At safe `schedule`, `implement`, or
  `improve-plan` boundaries ShipLoop records the marker and routes the next
  product edit through the appropriate step-plan loop; an active later
  execution stage must use its existing `repair` route to record the
  interruption before it can restart review. Read-only diagnosis remains safe.
- A state mutation writes one transaction intent before targets. If an
  interruption leaves `transaction.md`, the next locked command recovers it.
  Do not hand-delete it to make a run appear healthy.
- A result is action-bound. The same action plus byte-equivalent structured
  result is replay-safe; a different result for an already consumed action is
  rejected.
- The state record binds the current ledger through
  `carry_forward_protocol_version: 1`, `knowledge_revision`,
  `knowledge_sha256`, and `knowledge_action_id`. A stale carry-forward revision
  cannot overwrite newer knowledge, and unknown carry-forward result fields are
  rejected before an immutable result snapshot is written.
- Execution-plan records remain Markdown authority under `step-planning/`. The
  internal continuation policy has no state files of its own: do not create
  `.until-loop/`, `state.json`, a separate lock, or a parallel loop journal.
- Worktrees live below `<repo>/.worktrees/shiploop/<run-id>/<step-id>` and
  branches are retained after merge. The session checkout is the local merge
  destination; unrelated dirty files are preserved and block an implicit
  merge rather than being swept in.
- Results, check-attempt records, and raw logs can retain exact host-provided
  content. Do not include credentials or secrets; storage permissions reduce
  accidental exposure but do not promise perfect redaction.
- A knowledge observation may name an expected role and a documented
  non-mutating probe, plus when the observation was made and what to
  revalidate. Never record a credential value, secret ID, account address,
  signed URL, or raw credential-bearing output. The observation is current
  evidence, not a timeless claim that access remains valid.

## Frozen planning contracts

`environment.md` and `backchain/plan.md` are hashed when their owning stage
completes. `research.md` plus `research-evidence.md` finalize as one paired
baseline at research-finalize; `state.md` records `research_sha256`,
`research_certificate_sha256`, and script-generated `research_as_of` for that
accepted pair. The as-of time records when the certificate was accepted, not a
timeless or remotely verified fact. `behavior.md` freezes at behavior-finalize;
`spec.md` and lifecycle freeze only at spec-finalize. Mutable planning drafts
are still identity-bound: only imported results may replace them, and their
checks cannot survive drift. The [planning-loop contract](planning-loops.md)
defines candidate promotion, findings, audit commits and bounded
`planning`/`iteration` retrieval; the exact research state is in
[Research draft](research-loop.md#draft).

Behavior and specification receipts/certificates carry the matching research
candidate digest, certificate digest, and as-of binding. They cannot treat a
different or manually edited research pair as the evidence they reviewed.

An execution-plan candidate is deliberately narrower and shorter-lived than a
frozen planning contract. Before the initial source edit and before every
Improve application, its loop binds the current step prompt/outputs, actual
worktree implementation and diff, selected environment/knowledge observations,
direct dependencies, findings, checks, and audit history. `step-plan-finalize`
then releases only the exact checked candidate to its recorded target. The
certificate cannot stand in for later product lint/tests, a primary Improve
commit, final verification, or a broader pending-plan revision. See
[Execution-plan convergence](execution-planning.md).

For an Improve-routed loop, that binding additionally includes the compact
`enclosing_review` projection within the `step-context` section and its digest.
Its stable `PARENT-…` IDs must appear in the Improve candidate so no parent finding is
silently dropped. They record that the plan covers the parent review; they are
not a premature claim that product code has fixed it.

For an Improve-routed loop, finalization copies its deduplicated nested
review/revise learnings into the enclosing current iteration in
`steps/<id>.md`. The later primary commit must preserve them verbatim alongside
ordinary review, application, and carry-forward learnings; the nested audit
commits never replace that primary commit.

`knowledge.md` is a separate current overlay. `context --section environment`
shows the approved frozen baseline alongside a clearly labeled overlay; the
overlay is authoritative state for its recorded host-reported observations and
obligations but has no authority to rebase the baseline. `context --section knowledge` returns
active-step and `all`-scoped entries plus every open/scheduled obligation and
open blocker. Every execution review must fully page that selection and bind its
revision, digest, and scope in `knowledge_read`; historical checkpoints remain
out of the default cold-start payload.

Drift fails closed rather than being silently reinterpreted. Before any step
receipt or active work, `revisit --to survey|research|behavior|spec` archives
affected drafts, loop receipts and certificates; it cannot reuse superseded clean
passes. `--to research` requires/preserves `environment.md` while archiving the
research pair, behavior/spec/sequence downstream artifacts, every planning
receipt/certificate, and their bindings. `--to survey` archives all planning,
including `environment.md`; behavior/spec targets retain accepted research proof.
After execution begins, the completed step's `post-inner` action or outer
`coverage`/`quality` replan can replace `plan.md` and `backchain/plan.md` together
after candidate validation, and only change pending steps while retaining goal,
initial state, completed receipts, and the running receipt.

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

The carry-forward checkpoint can retain a non-secret operational observation,
pending obligation, or pause blocker without rewriting this survey contract.
Its `pending-replan` obligations require an explicit post-inner mapping to
compatible pending work; a `research`-domain obligation maps only added/changed
pending `activity: research` producer IDs, while affected consumers are derived
from its scope and must transitively depend on a mapped producer. A pause blocker
requires a later `no-contract-change` resolution and cannot be bypassed by
`resume`. See [Carry-forward checkpoint](carry-forward.md) and
[later research discoveries](research-loop.md#later-discoveries).

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
