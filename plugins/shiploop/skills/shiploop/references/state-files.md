# Durable run files (`.shiploop/`)

This catalog describes retained managed/legacy protocols. For navigator v3,
use the [navigator guide](navigator.md) and the packet's actual run/child locations.
Neither catalog replaces the repository's
[maintained product requirements](project-knowledge.md#maintained-product-requirements).

For Navigator v3 test planning, `state.md` retains accepted strategy results in
`accepted`/`history`, and initial item test decisions in existing `work_items[*].context`.
Packets derive a bounded **Run-wide test strategy source** from the latest
completed root `test-strategy` result, with its `results/<action>.md` and
`accepted.<action>` locators. The actual Improve handoff receives that same
source plus the **Current item test-decision source**: the latest completed
`step-plan`, `test-spec`, `test-author`, `test-refine` or `regression` result owned
by the current item. These producers retain decision revisions in ordinary
`evidence_refs`, not by rewriting the item's initial context. Improve receives
the completed sources alongside its separate pending producer result.
These are untrusted host reports
to revalidate, not a new test-state schema or a passing-check receipt. Follow
[test decision handoffs](repeatable-test-suites.md#carry-test-decisions-through-stages)
to retain fixture, suite and local/remote choices through later work.

Everything below belongs to a run directory, normally `<repo>/.shiploop`,
not to the installed ShipLoop package. Markdown is the authoritative state.
Each structured record has one `shiploop-state` JSON fence inside its Markdown
file. There is no writable JSON mirror.

| File or directory | Authority / purpose |
|---|---|
| `state.md` | Current phase, stage, action, revision, frozen hashes, active step and nested execution-plan cursor, completed-action replay digests, the bound current-knowledge revision/hash/action provenance, and accepted research digest/certificate/as-of bindings. New-run protocol markers also select the immutable seven-message history policy, versioned system-context evidence, the converged handoff objective, the early-observation callback, the content-pinned `improve_policy` binding, and (when created) the bound outer-work journal. |
| `run.md` | Persistent marker that identifies Markdown state authority and prevents accidental reinitialization/resurrection. |
| `prompt.md` | Original user request captured at initialization. |
| `improve-policy.md` | New-run snapshot of the byte-pinned declarative Improve review policy. Its `state.md.improve_policy` binding contains only `{version: 1, policy_id: "improve/review-policy/v1", sha256}`. Active product Improve packets/callbacks validate these saved bytes; unrelated stages and diagnostic recovery do not use the snapshot. |
| `preflight.md`, `approach.md` | Baseline facts and the initial delivery approach. |
| `environment.md` | Survey and research-facing environment brief. Its prose is human-readable; its single `## machine` JSON fence is the validated environment contract. |
| `knowledge.md` | Script-owned current knowledge ledger: `version: 1`, `revision`, `entries`, `obligations`, `blockers`, `learnings`, and `last_checkpoint`. It is authoritative for recorded current observations, not authority to alter approved baselines. |
| `knowledge-history/<action-id>.md` | Immutable snapshot for each accepted carry-forward or script-issued early-observation checkpoint. |
| `knowledge-reads/<review-action-id>.md` | Fully paged bounded-knowledge selection bound to an execution or step-plan review result. |
| `observations/<OBS-id>.md` | Immutable receipt for a script-issued, unverified early-observation callback. It binds the parent action, prior/current knowledge revisions, source fingerprint, no-test boundary, and selected unchanged-parent or recovery route without completing the parent. |
| `outer-work.md` | Lazily created, script-maintained outer-work obligation ledger. Any active inner action may request an append-side callback; it records a non-secret dependency for `quality`, `publish`, or `handoff`, never deployment authority or completion of the parent action. |
| `journal-requests/<request-id>.md` | Immutable input digest, provenance, request/result, operation, and receipt for a script-issued outer-work side callback. It makes an exact callback replay safe while refusing changed payloads. |
| `outer-work-reads/<outer-action-id>.md` | Action-bound proof that an outer activity paged the current rendered journal before it resolved due work or advanced. Its bound revision/digest and the target stage derived from that action prevent a stale read from satisfying the gate. |
| `research.md`, `research-evidence.md` | Script-owned paired mutable research report and typed question/source evidence candidates. New runs also retain a compact system context: observed code/state/system/environment-role facets, roles, surveyed interfaces, selected interaction contracts, question/source links, and bounded task projections. They are imported only through research results and accepted together at research-finalize. |
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
| `spec.md` | Checkable `done_sentence:` and `checkable: true`; frozen current-run contract only after spec-loop finalization, not the sole cross-run product requirements home. |
| `lifecycle.md` | Whether preparation, quality, and publication belong in the DAG or outer loop, plus acceptance criteria, rationale and versioned `risk_policy` decisions. |
| `plan.md` | Human-readable sequence plan, including matching `done_sentence:` and the bound Review Coverage section. |
| `backchain/plan.md` | Canonical dependency DAG in a Markdown record. The JSON fence is authoritative for steps, dependencies, prompts, produces, and unresolved facts. |
| `steps/<id>.md` | Per-step receipt: allocation, branch/worktree, current/history execution-plan bindings, implementation evidence, Improve iterations and their carried nested-plan learnings, final check, broader-plan review, and merge result. |
| `results/<action>.md` | Immutable submitted result for a completed action. Outer-work side callbacks use their own script-issued request IDs and receipts; they do not consume or complete the active parent action. |
| `inbox/<action>.md`, `inbox/checks-*.md` | Packet-directed host result and manifest drafts. `complete --result` or a verification command consumes only its explicitly supplied path; an unsubmitted draft is not durable state or proof that the host performed work. |
| `report.html` and `state.md.report` | Script-generated terminal-only offline view and compact integrity binding (`path`, HTML SHA-256, source digest, outcome, evidence completeness, schema version). The HTML is derived, not authoritative state. |
| `checks/<action>.md` | Manifest plus verified check evidence for that action. |
| `manifests/<step-or-outer>.md` | Last accepted manifest for change detection and required verification reason. |
| `check-attempts/<action>-<id>.md` | Every verification attempt, including failures, timeout evidence, and manifest-change reason. |
| `logs/<action>/` | Raw stdout/stderr logs named by check; evidence, not Markdown authority or prompt payload. |
| `history-pages/<action>-<skip>.md` | Persisted pages of full Git commit bodies read for an execution or step-plan review. |
| `merge-recoveries/<action>.md` | Immutable evidence of explicit recovery from a reconciled, unlanded merge intent. It does not itself abort or undo Git work. |
| `history.md` | Append-only command/action history. |

Bounded history uses `history_paging` inside the active objective/planning pass,
step-plan pass, or execution iteration receipt. It binds action, HEAD, commit,
full-body identity and contiguous fragment offsets/digests. Only complete
coverage creates the existing full-body `history.pages` proof and archived
Markdown body. Fragment metadata is not a second state file or proof of
semantic understanding; a changed source or damaged fragment ledger is rejected.
| `shiploop-improvements.md` | Deduplicated generic ShipLoop improvement proposals with provenance; proposal-only. |
| `preparation.md`, `coverage.md`, `quality.md`, `delivery.md`, `handoff.md` | Outer-loop evidence and final handoff records. In new runs, `handoff` is itself a converged substantive objective whose context binds the relevant outer evidence and outer-work ledger rather than a bare terminal note. |
| `migration.md`, `legacy-backup/` | Explicit legacy-migration marker and copied pre-0.9 records. |
| `transaction.md` | Short-lived write-ahead transaction journal. The next locked command rolls it forward deterministically. |

`recap.html` from an older run may remain as a historical view, but it is not
the source of truth for the 0.9 protocol. Inspect `handoff.md`, checks,
receipts, history, and the journal for current evidence.

## Reader and writer map

The catalog is deliberately conditional: a stored record needs the reader that
matches its purpose, not an invented consumer or a claim that a host understood
every byte. `context --section artifacts` returns the bounded catalog used to
route a fresh host. It is a navigation aid, not a second state store.

| Family | Script-owned writer | Reader and trigger | What the reader may establish |
|---|---|---|---|
| Current planning, research, ordinary knowledge, and step records | The matching accepted action transaction | Selected cold-context projection, identity/certificate checks, and the next matching action | Current bounded facts and whether the current artifact binding is still valid. |
| `improve-policy.md` and `state.md.improve_policy` | New-run initialization validates the package pin/body pair and writes both in its Markdown transaction. | Active product Improve packet/callback digest validation; trigger: new run, resume into product Improve, and each product Improve stage. | The run still has the exact policy it started with. It does not select a stage, count a pass, or make an active run follow a package upgrade. |
| `observations/<OBS-id>.md` and matching `knowledge-history/<OBS-id>.md` | The script-issued `context --section observation` / `done` callback | Current knowledge projection, callback replay guard, and bounded history diagnostic | A non-secret, host-reported fact was recorded as unverified before parent completion. It cannot establish a passed check, resolve a blocker, or grant authority. |
| `outer-work.md` | The outer journal append/resolve callback | Any inner action pages it to deduplicate; `quality`, `publish`, and `handoff` page current entries and resolve rows due at their stage | A current obligation was recorded/read/resolved at the allowed stage. It never establishes remote permission or effect. |
| `journal-requests/*` | The same outer journal callback | Exact callback replay and `audit` diagnostic | The request/result and its immutable replay outcome, never a completed parent action or external effect. |
| `outer-work-reads/*` | Outer-work context paging transaction | The matching outer transition gate | That action covered the current journal pages; changed journal bytes invalidate the read. |
| `check-attempts/*` and `logs/*` | `verify` / `planning-verify` | Report attempt summary; `context --section check-log` resolves a selected action/attempt/check record to a bounded screened excerpt | Local diagnostic evidence only. A clipped/redacted excerpt is neither a complete log review nor a passing check. |
| `knowledge-history/*`, `merge-recoveries/*`, `planning-history/*`, `legacy-backup/*`, `journal-requests/*`, and `history-pages/*` | Checkpoint, recovery, revisit/migration, callback replay, or history commands | `context --section audit --kind … [--record …]` returns a bounded, allowlisted historical diagnostic | Provenance/audit comparison only; it never restores or promotes historical content as current authority. |
| `preparation.md`, `coverage.md`, `quality.md`, `delivery.md`, `handoff.md` | The corresponding outer activity | Bounded outer context and terminal report; the handoff objective binds the applicable outer evidence | Host-reported outer evidence and report consistency, not proof of a live remote system. |
| `report.html`, `state.md.report` | Terminal renderer / explicit `report` command | Report-integrity validation and a human reader | A derived view agrees with selected source records; it is not workflow state or proof of semantic acceptance. |

Raw logs are not a normal cold-start payload and archive readers never execute
their contents. Every reader enforces an allowlist and safe path/type/size
boundary; a missing or withheld diagnostic is reported honestly instead of
repairing state.

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
- Migration records `prompt_recovery` in `state.md` and `migration.md`. A
  nonempty legacy `state.prompt` is copied exactly to `prompt.md` with a source
  digest. Missing/blank/non-string intent is `unrecoverable`, not fabricated;
  the run remains paused and permits diagnostics instead of advancement.
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
- New runs also bind `improve_policy` exactly as version 1,
  `improve/review-policy/v1`, and the SHA-256 of `improve-policy.md`. The
  snapshot is written from ShipLoop's checked bundled policy, not a host Improve
  installation. Its bytes are reread only for active product Improve work;
  status, bounded context, pause/halt, and terminal reporting remain available
  when a validly bound snapshot is missing or damaged. A malformed binding is
  a fail-closed state error. Existing runs with no binding keep the established
  ShipLoop loop policy, and a package upgrade never rewrites their run state or
  snapshot.
- The Improve binding detects a changed snapshot against an unchanged state
  record. It is not tamperproof against an actor able to rewrite both
  `state.md` and `improve-policy.md`; that is the existing protected-workspace
  boundary, not a new reliability claim.
- A v3 run that lacks `step_planning_protocol_version: 1` does not receive a
  retroactive plan certificate. At safe `schedule`, `implement`, or
  `improve-plan` boundaries ShipLoop records the marker and routes the next
  product edit through the appropriate step-plan loop; an active later
  execution stage must use its existing `repair` route to record the
  interruption before it can restart review. Read-only diagnosis remains safe.
- New runs carry `platform_discovery_protocol_version: 1` and
  `risk_policy_version: 1` in `state.md`. They require the versioned
  `machine.platform_discovery` in `environment.md` and `risk_policy` in the
  lifecycle draft/frozen record. Missing markers preserve legacy compatibility;
  present malformed or unknown versions never silently downgrade. These
  declarations do not retrospectively certify old runs or live access.
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
- New runs declare `platform_revalidation_protocol_version: 1`. Selected
  external action results retain host-reported safe-probe attestations in the
  existing `results/<action>.md` record, bound to action, platform, trigger and
  environment digest. Preparation objective refinement preserves its original
  accepted probe evidence rather than rewriting observation history. Absent
  marker means legacy compatibility; explicit invalid versions fail closed.
  Neither this record nor the frozen declaration proves live access by itself.
- New runs carry `history_policy: {version: 2, required_limit: 7}`. Every new
  planning/objective/step pass binds that policy to its full-message history
  proof. A run without the marker remains permanently on the legacy
  ten-message policy; an explicit malformed or unknown policy fails closed
  rather than silently changing what a completed pass was required to read.
- New runs carry `system_context_protocol_version: 1`. Their paired research
  evidence validates a compact, source-linked map of observations, roles,
  interfaces and interaction contracts. The script projects only task-relevant
  rows into cold planning context and binds the evidence bytes into the plan;
  it does not assert that a host's research or a remote probe is true.
- New runs carry `outer_work_protocol_version: 1`. `outer-work.md` is absent
  until a script-issued journal request is accepted. Once present, its revision
  and SHA-256 bind state and objective context. A changed or stale journal
  invalidates the affected objective rather than inheriting a trivial streak.
  Legacy runs without this marker retain their existing outer-flow contract.
- New runs carry `observation_protocol_version: 1`. `context --section
  observation` issues a replay-safe `OBS-…` ticket only while a parent action is
  active. Its accepted callback atomically updates the current knowledge ledger,
  its immutable checkpoint/history, and an observation receipt while preserving
  the parent action. A repair-requiring observation is accepted only where a
  compatible existing repair route exists; unsupported context/proof changes
  and pause/permission/contract blockers are rejected before mutation. An
  accepted route cannot reuse prior checks through `resume` alone.

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

For a versioned system-context run, the research pair additionally carries the
compact map needed after a cold boundary: observed code/state/system/
environment-role facets, role and interface identities, interaction contracts,
their question/source links, and explicit blocked/not-applicable reasoning.
The plan step context projects only the selected step and direct-consumer rows
within a fixed bound, with the evidence and context digests. A changed research
pair or projection cannot release an old checked microplan; repair and fresh
convergence are required. Detailed narrative remains in the research pair, not
in a second database or an ever-growing packet.

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

`outer-work.md` is separate from both knowledge and the generic ShipLoop
proposal journal. An inner action may ask the script to append a durable outer
obligation before its own successful check or completion. The callback stores
the journal request and returns the unchanged parent action, so it cannot turn
a failed or unfinished inner action into a success. The next inner action may
read the ledger and reuse the stable dedupe key. At an outer stage, the current
full ledger read is bound to the action and target stage; only that target stage
can resolve its planned entries. See [Outer-work journal](outer-work.md).

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
