# ShipLoop remaining recommendations

Baseline: `e01a7dd`. Scope: finish the concrete recommendations left by the
prior audits, without installing connectors, changing credentials, creating
automations, publishing an application, or touching unrelated Review Coverage
work. Markdown remains authoritative; the calling skill remains one action/done
interface. This plan is the implementation tracker, not a second run scheduler.

## Disposition

| ID | Recommendation | Decision and intended evidence |
| --- | --- | --- |
| R1 | Explicit generic platform capabilities and target topology | Adopt. Versioned `machine.platform_discovery` in existing environment Markdown; new runs require an applicability decision. Interfaces, versions, safe identity probes, writer and limitations remain distinct from observed execution. |
| R2 | Ordered bootstrap, development validation and promotion | Adopt. Bind declarations to existing preparation/publication lifecycle and DAG prerequisites; reject unresolved or inconsistent required routes. Keep local merge distinct from remote publication. |
| R3 | Security and fuzz applicability | Adopt. Explicit decisions in existing lifecycle Markdown, with required case IDs mapped to step test contracts. Inapplicability needs rationale; unavailable required testing is blocked, not waived. |
| R4 | Ongoing dependency maintenance | Adopt as product planning, not a generic automatic updater. Record owner, advisory source, cadence, mechanism, validation and rollback; implementation-now needs a DAG producer, while operate-later is explicitly a future plan without scheduling. Six hours is an example to evaluate, not a hard-coded schedule or permission. |
| R5 | Bounded full Git learning messages | Adopt. Page large full-message history with action/HEAD/digest-bound coverage; partial pages cannot establish that the full required history was delivered. Preserve existing whole-message compatibility. |
| R6 | Broader offline trials and lifecycle routing regression | Adopt. Exercise missing access, configured checks, local-only versus remote routes, unsafe drift/replay, and cold recovery with isolated fixtures. No live platform certification claim. |
| R7 | Local microplans and embedded until policy | Already implemented (`3f79978`, `0591ce0`); preserve their existing convergence, Git and lint/test gates. Do not add a second scheduler. |
| R8 | Single invocation, acknowledgments and HTML report | Already implemented/hardened (`0591ce0`, `e01a7dd`); retain terminal integrity and evidence labels. |
| R9 | Semantic completeness oracle, automatic authority changes, live host certification | Not justified or outside authority. Two stable passes and schemas do not prove semantic perfection. Live credentials/targets are not supplied; incompatible frozen scope/authority still requires direction. |
| R10 | Aborted/rejected merge intent can strand a step | Adopt. Explicit action-bound recovery after Git reconciliation; refuse in-progress or already-landed merges, retain audit evidence and restart review. Never abort Git automatically. |
| R11 | Legacy migration omits recoverable prompt content | Adopt. Restore exact retained intent to prompt Markdown atomically; if absent, label it unrecoverable and block false advancement rather than invent it. |

## Evidence and tradeoffs

Baseline source inspection found shallow tools/MCP and initiation records,
missing security/fuzz/maintenance decisions, and unbounded full Git bodies.
The implementation uses the existing convergence, snapshot and candidate
validation points rather than adding independent persistence.

The [MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
distinguishes discovery from invocation and says tool annotations are untrusted
unless from trusted servers. Therefore a capability declaration is not proof of
access or permission. The [MCP maintainers' risk discussion](https://blog.modelcontextprotocol.io/posts/2026-03-16-tool-annotations/)
also cautions that hints are not enforcement. These support explicit probes and
permission boundaries, not adding a connector automatically.
[NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final) supplies a technology-neutral
secure-development reference; this increment selects relevant risk decisions,
not a claim of SSDF compliance. Cost: stricter records and fixture migration;
mitigation: compact local-only cases, bounded packets and legacy compatibility.

## Dependency plan

Mode: native-unvalidated Backchain. Forward draft: record contracts, protocol
integration, bounded history, operator guidance, then independent verification.
Dependency review resolved existing Markdown and convergence support by source
inspection; it did not assume remote tools, accounts or deployment permission.
Backward review makes protocol integration consume validated record contracts;
history paging is independent of platform semantics. Each verification sink
inspects its specific implementation rather than a generic green badge.

```json
{
  "goal": "The remaining ShipLoop platform, risk and bounded-history recommendations have executable evidence and cold-host guidance.",
  "initial_state": [
    "ShipLoop has Markdown-authoritative environment and lifecycle records.",
    "ShipLoop has action-bound history coverage and convergence gates.",
    "The user authorized implementation of the remaining recommendations."
  ],
  "goal_needs": [
    "Platform and risk decisions reject missing or inconsistent required evidence in regression fixtures.",
    "Bounded history paging rejects partial coverage and stale identities in regression fixtures.",
    "A cold host can locate the applicable decisions and next callback without remembered workflow state.",
    "Merge-intent and legacy-prompt recovery preserve audit evidence and reject ambiguous advancement."
  ],
  "steps": [
    {"id":"S1","statement":"Generic platform and risk record contracts are defined and unit tested.","produces":["Versioned platform and risk record contracts exist."],"inputs":[{"need":"ShipLoop has Markdown-authoritative environment and lifecycle records.","from":null}],"origin":"seed"},
    {"id":"S2","statement":"Current protocol gates consume the versioned platform and risk records.","produces":["Protocol discovery and lifecycle gates use the record contracts."],"inputs":[{"need":"Versioned platform and risk record contracts exist.","from":"S1"}],"origin":"seed"},
    {"id":"S3","statement":"Full Git learning messages have bounded action-bound pages.","produces":["Bounded history pages preserve complete-message coverage accounting."],"inputs":[{"need":"ShipLoop has action-bound history coverage and convergence gates.","from":null}],"origin":"seed"},
    {"id":"S4","statement":"Stage-selected guidance documents the new records, evidence boundaries and recovery.","produces":["Cold packets and operator references document the new contracts."],"inputs":[{"need":"Protocol discovery and lifecycle gates use the record contracts.","from":"S2"},{"need":"Bounded history pages preserve complete-message coverage accounting.","from":"S3"}],"origin":"seed"},
    {"id":"S5","statement":"Platform and risk gate behavior is confirmed by isolated regression fixtures.","produces":["Platform and risk decisions reject missing or inconsistent required evidence in regression fixtures."],"inputs":[{"need":"Protocol discovery and lifecycle gates use the record contracts.","from":"S2"}],"origin":"seed"},
    {"id":"S6","statement":"Paged history coverage and drift behavior is confirmed by isolated regression fixtures.","produces":["Bounded history paging rejects partial coverage and stale identities in regression fixtures."],"inputs":[{"need":"Bounded history pages preserve complete-message coverage accounting.","from":"S3"}],"origin":"seed"},
    {"id":"S7","statement":"Cold packet guidance is confirmed by an independent bounded host trial.","produces":["A cold host can locate the applicable decisions and next callback without remembered workflow state."],"inputs":[{"need":"Cold packets and operator references document the new contracts.","from":"S4"}],"origin":"seed"},
    {"id":"S8","statement":"Explicit reconciled merge-intent recovery retains evidence and restarts review.","produces":["A scoped merge-recover command exists."],"inputs":[{"need":"The user authorized implementation of the remaining recommendations.","from":null}],"origin":"seed"},
    {"id":"S9","statement":"Legacy migration recovers retained intent and blocks unrecoverable intent.","produces":["Legacy prompt recovery is explicit and durable."],"inputs":[{"need":"ShipLoop has Markdown-authoritative environment and lifecycle records.","from":null}],"origin":"seed"},
    {"id":"S10","statement":"Isolated recovery fixtures and independent review confirm fail-closed recovery.","produces":["Merge-intent and legacy-prompt recovery preserve audit evidence and reject ambiguous advancement."],"inputs":[{"need":"A scoped merge-recover command exists.","from":"S8"},{"need":"Legacy prompt recovery is explicit and durable.","from":"S9"}],"origin":"seed"}
  ],
  "parallel_groups": [],
  "unresolved": []
}
```

Forward check: S1 precedes S2; S2 and S3 precede their own regression sinks;
S4 consumes both interfaces before S7. No live-world prerequisite is silently
closed. Full host/deployment certification is explicitly not this plan's goal.

## Implementation gates

Before edits: preserve the exact prior dirty paths; agree schema/ownership.
During edits: write negative and positive tests, run lint every implementation
pass, inspect actual failures, preserve all required checks. New runs must be
strict without silently upgrading old runs. Unknown record versions must not
downgrade to legacy handling. Page coverage must be identity-bound and must not
count an index or partial body as full history.

Before completion: selected unit/CLI/cold integration suites, real terminal
walk, independent review, canonical-to-ShipLoop-plugin sync, frontmatter and
audited local-change gate. Record exact test counts and limitations below.

## Progress

- Planning, implementation and verification: complete. R1–R6 and R10–R11
  implemented; R7–R8 preserved; R9's authority/information boundaries retained.
- Final residual audit added R10 and R11 as independent recovery work. Their
  tests are additional verification sinks; neither changes discovery/history
  scheduling or grants new external authority.

## Verification ledger

These are isolated local tests, not certification of a live hosted platform.
The first broader run correctly rejected old fixture records missing the new
explicit decisions. Fixture migration added local-only/risk rationales; no
checks or acceptance assertions were waived. Independent review also drove
malformed-input hardening, exact history fragment verification, preservation of
merge-ready evidence, and removal of an invalid resume recommendation.

| Evidence | Result |
| --- | --- |
| Real two-step CLI action walk | Passed, 204.237 seconds; exercised planning, checks, history, commits, revisions and terminal journal/report. |
| Full step-planning suite | 17 passed, 283.138 seconds. |
| Full planning / knowledge suites | 28 passed (490.586 seconds) / 4 passed (536.678 seconds). |
| Store / report / contracts / until | 7 / 11 / 10 / 7 passed. |
| Evidence / boundaries / validators | 8 / 10 / 39 passed. |
| Contract protocol / delivery | 10 / 6 passed. |
| Current packet suite | 18 passed after the bounded-navigation and prompt-recovery guidance changes. |
| Frontmatter | All 17 skill packages passed. |
| Final audited eight-suite gate | 108 tests passed from raw unittest totals; `PASS_CLEAN_SCOPED`, no package file changes or control failures. |
| Final lint / shell syntax / mirror / whitespace checks | Passed; only ShipLoop's plugin view synchronized. |
| Independent review | Discovery/risk, history paging, merge recovery and prompt recovery: no remaining actionable findings after fixes. |

Final audited run:
`/Users/dadleet/.grok/runs/test-harness/shiploop/20260912T162220Z-63ee68`.
It ran discovery (14), risk (11), history pages (8), merge recovery (7), migration
prompt (2), protocol (33), packets (18), and objectives (15). Its `suite_scope=full`
describes the supplied eight-suite command, **not the entire repository or full
ShipLoop shell runner**. The harness did not parse unittest case counts; its
zero parsed cases are not zero executed tests. Raw `round-1/stderr.log` records
all eight successful totals. The supervisor flagged stderr volume (2,473 bytes);
manual inspection found only normal unittest progress, successful case names,
timings and `OK`, with no warnings/errors or package deltas. No output was
suppressed to obtain the pass.

The full two-step walk and long planning suites preceded only narrow final
projection/recovery guidance and fixture corrections; the final gate tested the
current source after those corrections. A duplicate worker planning/action-walk
process was stopped after root's selected runs finished; its unfinished walk
is not counted as passing. The normal CI entrypoint now includes all five new
regression files. No live certification, publishing or full-runner pass is claimed.

### Cold-host trial

A fresh host received only the package/run locators, read the thin skill and
current packet, and completed exactly one real survey callback. The isolated
request named hypothetical CLI/MCP interfaces without credentials, connection
or authority. The result kept the hosted platform applicable and explicitly
blocked its interfaces, identity, authority, bootstrap, development validation
and promotion. It made no live probe, installation or external mutation.

Action `20260912T160433Z-ae1499e0-423037b2fa32` was accepted and returned a new
`objective-review` action; the host stopped there. Root revalidated that exact
record against the current discovery schema. This proves current packet
discoverability and one callback, not semantic exhaustiveness or live service
operation. Local trial state:
`/private/var/folders/_n/cth41tgs171367b_gghs0kgm0000gn/T/shiploop-action-walk-kwtc57_l/repo/.shiploop`.

The illustrative end-to-end walk report was retained at
`/private/tmp/shiploop-single-action-validation.GLLQGa/example-report.html`.
It describes the test fixture's achievement, not this repository's deployment.

## Generic ShipLoop improvement journal

- Adopted here: keep selected required interfaces distinct from optional
  alternatives, and inventory separate from proven usability/authorization.
- Adopted here: bounded navigation must link to full durable facts; truncated
  identifiers never become operation arguments or full-history proof.
- Adopted here: recovery is a state-machine route, not an invitation to delete
  evidence or rerun an uncertain external operation. Recovery packet commands
  must themselves be executable for the recorded blocker.
- Keep testing cold roles and negative transitions as schemas evolve; an
  accepted declaration is not a semantic-completeness certificate.
- Future live platform/deployment trials require a separately supplied safe
  environment and authorization. Do not install MCPs, schedule dependency
  updates or create production effects merely to broaden this test ledger.
