# Ask Agent and Backchain task charters

Established 2026-09-18 at the user's request to coordinate the two active tasks.
This is development coordination guidance, not a new runtime, scheduler, skill,
or replacement for either package's execution contract. Later user instructions
take precedence. Existing authorized work continues within these boundaries.

## Task identities and ownership

| Task | Stable task ID | Owns |
| --- | --- | --- |
| Ask Agent — native delegation | `01a0b059-28a2-7761-bd73-5314618129fb` | Portable native delegation and the worker interaction contract. |
| Backchain — planning and orchestration | `01a09d6d-714a-73b2-b6ba-7f56f7cf342a` | Planning, Plan Dispatcher, and its active ShipLoop chain integration. |

These are development tasks. At runtime the initiating conversation can perform
both the dispatcher and Ask Agent roles; this split does not require extra agents.

### Ask Agent charter

Own the canonical `skills/ask-agent/` package in skill-craft, its generated
package views, and `test/experiments/portable_delegation/` qualification evidence.

- Native capability discovery, fresh contexts, asynchronous launch and collection.
- Instructions for requested model/effort propagation, observed-setting checks,
  mismatch disclosure, broad general-purpose selection and further delegation.
  The caller selects supported options; native host configuration determines the
  effective model, effort and capabilities. Prompt guidance cannot enforce parity.
- Launch/return notices, waiting-status guidance and honest unsupported behavior.
- Compact report handoffs: assignment reminder, task outcome, next action/owner,
  artifact locations, verification limits and temporary-report lifecycle.
- Generic Git contribution and integration contract, including the distinction
  between worker completion and parent acceptance.

Keep Ask Agent prompt-only. Do not add a graph scheduler, durable inbox, attempt
ledger, custom timer, model subprocess launcher, or fixed worker limits here.
The native host's actual capabilities and the assigned task scope still apply.

### Backchain charter

Own the Backchain repository's planning and `skills/plan-dispatcher/` packages,
their tests, and the active ShipLoop chain-integration slice. Coordinate that
slice with other ShipLoop work rather than claiming unrelated ShipLoop features.
These are ownership assignments, not claims that every planned helper is already
implemented or integrated. Report the exact checkout and verified capability.

- Forward planning, reverse dependency audit, ready/done conditions and constraints.
- Durable graph and attempt state, claims, retries, resource reservations,
  completion inbox, duplicate/stale receipt handling and recovery.
- Independent verification and settlement; accepted evidence unlocks successors.
- Concrete sibling-worktree allocation, exact bases/targets, serialized integration,
  combined verification and return to the initiating checkout.
- Append-only timestamped execution history and ShipLoop lifecycle binding.

Use the selected Ask Agent package for native delegation. Existing dispatcher and
ShipLoop state/Git helpers may implement their own responsibilities; they must
not replace native worker launch with a nested model CLI. Changes to the generic
Ask Agent contract belong to the Ask Agent task.

## Shared boundary

| Boundary | Authority and handoff |
| --- | --- |
| Work assignment | Dispatcher supplies run/step/attempt identity, objective, inputs, ready/done evidence, workspace, write ownership, resource constraints, model intent and output paths. |
| Launch | Ask Agent guides the native launch; dispatcher records the actual confirmed handle. A saved launch intent is not permission to launch twice. |
| Status | Dispatcher attempt state is authoritative for graph progress. The parent explicitly reconciles native observations and its Ask Agent pending list with those attempts; no automatic synchronization is implied. One initiating conversation emits combined notices. |
| Worker return | Worker returns a compact native receipt and publishes the dispatcher-assigned durable report/envelope when required. A standalone Ask Agent task can use a temporary report without dispatcher state. |
| Acceptance | Native completion, successful assigned work, accepted evidence, and integrated code are distinct facts. Only dispatcher verification/settlement releases dependencies. |
| Messaging | Durable inbox retains reports; native notification/collection signals the live parent; ledger records disposition. A file or Git merge alone does not establish worker termination or wake an ended session. |
| Integration | Ask Agent provides the general contract. Dispatcher/ShipLoop selects and controls actual worktrees, targets, integration order and acceptance. |
| Cleanup | Dispatcher-owned recovery receipts are durable. Delete temporary handoffs only when all consumers and unresolved actions are finished. Neither task may delete the other's evidence. |

The dispatcher may carry task-specific copies of required worker instructions,
but Ask Agent remains the source for generic delegation policy. Record the
selected skill/reference digests so copied guidance cannot silently drift.
When the selected Ask Agent package is absent or incompatible, disclose that
boundary; do not claim Ask Agent qualification for an alternate path.

## Cross-task change protocol

1. Each task edits its owned slice and preserves other tasks' working changes.
   Shared files or cross-boundary behavior need an explicit owner before editing.
2. Send the counterpart a concise notice for an interface change, material blocker,
   or completed candidate. Include artifact path, revision/digest, observed behavior,
   limitations, compatibility impact, and the exact requested next action.
3. A received message is coordination input, not evidence that work was implemented,
   tested, integrated or published. Reconcile it with current user instructions.
4. Ask Agent owns independent Claude/Grok/Codex/OpenCode native-interaction tests.
   Backchain owns DAG, inbox/ledger, resource, worktree and integrated consumer tests.
   The consumer task owns the cross-boundary smoke run against a selected frozen
   Ask Agent package; both tasks retain the receipt instead of rerunning equivalent
   campaigns without a new question.
5. Do not create periodic cross-task reminders or automatic message loops. Notify
   on meaningful changes, and preserve unresolved handoffs in existing task records.

## Current handoff and next increments

Ask Agent's current tested candidate is U17, version 0.3.0. Main card SHA-256:
`462583a2ac85f7fe4b4945a3859dc05a788b1f7e1ad41275ec21bfdc27966b40`.
Git reference SHA-256:
`127e0fad5af53067360e3429fd319870fec4f08f09a2f697bc6ccd4f533321fd`.
Read the [retained results](../test/experiments/portable_delegation/usability/INTEGRATION-RESULTS.md)
for the observed boundaries. Native lifecycle results do not establish uniform
periodic monitoring or full parent-child capability parity.

Ask Agent's proposed next increments are recursive model/freshness/role-policy
propagation, a clearer completion-versus-acceptance receipt example, and a tested
simplification of its operating checklist. They are proposals, not completed
changes. Keep resulting native tests scoped to those questions.

Backchain's next work remains its current authorized dispatcher/ShipLoop program:
durable completion messaging, settlement/recovery, dependency release and concrete
integration. Use the current selected Ask Agent contract and report the version
actually exercised. Broader progress/question messaging needs a separate contract
and must not silently redefine a terminal completion receipt.

Current user-selected live-test models are Claude Sonnet, Grok for OpenCode,
Grok for the native Grok lane, and Codex Luna with `xhigh` reasoning. Propagate
the applicable choice to descendants and verify observed settings when exposed.
This test profile does not hard-code a model into the portable skill or authorize
changing global defaults.

## Recognition receipts

The Ask Agent task adopts this charter in its initiating context. The Backchain
task is asked to read this exact file and record acknowledgment plus any concrete
ownership conflict in its active workspace. Acknowledgment must be observed before
reporting mutual adoption; sending the message alone is not acknowledgment.
