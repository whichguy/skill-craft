# Iterative environmental and best-practice research

Research is a delivery activity with its own evidence and stopping condition,
not a one-shot report or a request to repeat the same answer. Start from the
incoming prompt, surveyed environment, available spec and recorded discoveries.
Follow the printed action; retain everything needed by the next iteration in
Markdown. Read only the section the current packet selects.

For a later feature, consult the [cross-run knowledge policy](project-knowledge.md):
read persistent environment/decision documents and relevant prior-run evidence,
revalidate what affects this request, and retain useful updates in repository
documentation. The new incoming prompt defines scope; an old prompt or work queue
is historical context, not a request to execute it again.

```mermaid
flowchart TD
  Q[Scoped questions] --> S[Review sources and investigate]
  S --> R[Revise evidence and resolve findings]
  R --> V[Lint, tests and learning commit]
  V --> G{Two trivial passes and no gaps?}
  G -->|No| S
  G -->|Yes| F[Fresh final checks]
  F --> N[Next phase with fresh context]
```

## Draft

Identify the environmental conditions and best-practice decisions that could
change the approach, feasibility, behavior, tests or deployment. Convert them
into a bounded question inventory. Scope the inventory to this task; do not
research every technology, invent an unnecessary environment, or impose a stack.

For each question, distinguish:

- what the user requires, with a prompt/spec reference;
- what the environment currently does, with direct evidence;
- what a source recommends, with applicability and contrary evidence;
- what remains unknown or requires a user decision.

Research begins with `body` and `research_state` in the normal Markdown result.
The script maintains `research.md` and `research-evidence.md` as candidate
components; host-authored result drafts belong in the printed inbox. The typed
legacy evidence structure is shown below. For a versioned run, use the packet's
extended template and the required
[result shape](research-result-schema.md#result-shape) and
[replacement rules](research-result-schema.md#replacement-rules), not this
legacy-only example. Those sections define every row shape, allowed enum and
stable-identity/link rule; no validator source inspection should be necessary.

```json
{
  "questions": [
    {
      "id": "Q-1",
      "question": "Which invocation boundary must the client use?",
      "origin": "Prompt R-1 and survey invocation uncertainty",
      "status": "resolved",
      "answer": "Use the documented service-visible operation and error envelope.",
      "sources": ["SRC-1"],
      "revalidate": "Recheck if the deployed interface version or client changes.",
      "rationale": "The documented boundary matches the requested client and current service."
    }
  ],
  "sources": [
    {
      "id": "SRC-1",
      "reference": "Safe primary-document or repository reference",
      "authority": "primary",
      "version_or_observed_at": "Exact inspected version or observation timestamp",
      "supports": "The exposed operation, input shape and error envelope",
      "limitations": "Does not prove live credential availability or a deployed result"
    }
  ]
}
```

Use stable IDs. Question status is `resolved`, `open`, `blocked`, or
`not-applicable`; source authority is `primary`, `local`, `secondary`, or `probe`.
`origin` explicitly references the prompt, spec or discovery that raised the
question. Preserve prior question and source IDs across application; changing a
source reference/authority needs a new ID rather than repurposing the old one.
A resolved question needs source support. An irrelevant question needs a concrete
inapplicability rationale. An open/blocked question records the gap in `answer`;
it cannot be hidden by removing its ID or declaring the pass trivial. Local-only
work can use actual repository/runtime evidence; no external-search quota or
third-party tool is mandatory. No relevant uncertainty still requires an explicit
bounded applicability review, not a fabricated source or silent empty result.

### Versioned system-context links

New runs that declare `system_context_protocol_version: 1` extend only their
`research_state`; older runs keep the exact two-key `questions`/`sources` shape.
The extension adds `parents`, `contract_refs`, `role_refs`, and `interface_refs`
to every question, plus one `system_context` record with a version, scope,
rationale, observations, roles, interfaces, and interactions. The detailed
model stays in `research.md` and `research-evidence.md`; packets carry only a
bounded selected projection and its evidence locator.

Use stable IDs and validate every source, parent, role, interface, and contract
reference. Question parents are acyclic. Contract/question links are reciprocal.
An interface that represents a surveyed platform names its frozen
`{platform_id, name}` identity rather than copying or changing the survey.
Roles record permitted actions and isolation without forcing a `dev`, `stage`,
or `prod` taxonomy. Include observed or explicitly blocked/not-applicable
code, state, system, and environment-role observations; unavailable evidence is
not permission to call a boundary irrelevant.

Each relevant interaction records caller/callee interfaces, operation,
input/output shape, state and failure semantics, supported SDK/client idiom,
risk, depth rationale, sources, questions, and affected consumer steps. Follow
causal boundaries as far as risk requires: a simple local call may stop with a
reason, while retries, duplicate effects, cancellation, partial commit, or role
differences need the relevant downstream state/service boundary. A numeric depth
claim is never evidence. Required unresolved interactions or their open/blocked
questions prevent research finalization; do not replace them with a future
consumer dependency or an invented probe.

Use the selected primary contract for an operation. The
[MCP tools specification](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
is an example of why operation/result/error envelopes need explicit evidence;
[MCP security guidance](https://modelcontextprotocol.io/docs/2025-11-25/tutorials/security/security_best_practices)
illustrates that an adapter boundary does not grant authority; and
[Google AIP-194](https://google.aip.dev/194) illustrates why retry ownership and
idempotency must come from the actual API contract. These are investigation
anchors, not a mandate to install an MCP server or adopt an RPC design.

## Recursive discovery and experiments

This is a generic discovery process for arbitrary referenced systems, whether
local or remote. Derive the concrete questions, access routes, libraries, patterns,
and experiments from the task and inspected contracts. Named technologies,
applications, transports, and example probes illustrate the method; they are not
required dependencies or a fixed discovery sequence. Do not assume an MCP server,
browser, client/server architecture, or remote deployment exists. Apply the same
method during environment investigation, inner-loop development, outer-loop
delivery, and test expansion when a consequential unknown arises; reuse existing
evidence instead of requiring a fresh investigation at every checkpoint.

Use [service discovery](service-discovery.md#select-scope) when affected flows
raise schema/state, query, caching, or asynchronous service choices behind an
MCP/API or local boundary. Assess existing owned observability for local systems
too; reuse event owners and sinks before adding coverage. Keep only relevant
decisions and current evidence in the existing durable notes and knowledge index.

### Scope, coverage, and frontier

Start with the task's affected flows, not a fixed number of hops. Read the repo
README and existing applicable AGENTS.md, architecture/design/environment notes,
and local skills before rediscovering their subject. Record absence or stale
claims explicitly. Recheck volatile facts; documentation is not live access proof.
Use the existing `body`, questions, sources, role/interface/interaction records,
and `depth_rationale`; do not add a recursive journal, schema, inventory, or
sidecar.

Before deep source or library research, make one cheap authorized read that
crosses the actual target boundary when it could settle access or target
uncertainty. A listed tool, credential-status response, local binding error, or
catalog does not establish account/project reachability. Do not create a target
solely to claim discovery access.

Apply [early access readiness](#early-access-readiness) at that first relevant
probe and whenever investigation exposes a new required access boundary.
Investigate the [environment lifecycle](environment-lifecycle.md) before planning
code: actual workspace/runtime/data isolation, setup prerequisites, automated
deployment triggers, and how the tested candidate reaches its intended consumer.
Retain preparation and promotion needs separately for their downstream owners.

Screen every affected flow and every consequential newly encountered boundary for
all eight areas below. Mark an area established, unresolved, or not applicable
with its reason and evidence. The screen is task-scoped: it does not authorize an
audit of every platform feature or private account.
These are analytical categories, not required components. Use the encountered
system's corresponding concepts; when an area has no counterpart, record why it
is not applicable rather than inventing a client, service, library, or cache.

| Area | Ask enough to choose or reuse safely |
| --- | --- |
| Message passing | Producers, consumers, operation/event contract, serialization, ordering, retries, duplicates, cancellation, errors, and the durable or user-visible effect. |
| Client connections | How a client reaches the actual callable boundary, including transport/session lifecycle, cleanup, and reconnect/offline behavior when relevant. |
| Service authentication | Discovery and runtime identities, delegation, credential-chain/refresh behavior, effective permissions, audience/scope, and proof limits without recording secrets. |
| Design | Existing architecture, ownership, state flow, code conventions, and relevant UI loading, error, accessibility, and interaction patterns. |
| Client-side libraries | Shipped dependencies and versions, initialization/wrappers, compatibility limits, and supported use before adding another dependency. |
| Storage | Source of truth, schema/access path, ownership, authorization, transaction/concurrency, failure, retention, and migration boundaries. |
| Caching | Relevant cache layers, scope/keys/TTL/invalidation, read-after-write and failure behavior, and separation from authoritative state. |
| Security considerations | Trust and tenant boundaries, input/output handling, authorization, transport/data protection, logging/secret exposure, and dependency provenance. |

For each relevant system, including the system behind an MCP gateway, identify the
actors, state owner, invocation convention, identities, permissions, and
downstream effects that could change implementation, tests, deployment, or reuse.
When a consequential unknown exposes another system or boundary, add its
unanswered contract to the same existing question frontier with parent/source and
interaction links. Reuse visited identities and sources when paths reconverge or
cycle. Reopen a branch only when changed or conflicting evidence could materially
change the plan; do not traverse unrelated integrations merely to be exhaustive.

Every explored branch needs a stopping reason in `depth_rationale` and the
existing report: the in-scope effect and relevant failure/security semantics are
supported, the branch is out of scope, it reconverges on inspected evidence, or an
explicit open/blocked question names the missing authorized route. A local call may
need one trace; a multi-service write can need several trust and persistence
boundaries. No route found is a recorded gap, not evidence that the system has no
behavior.

For interface decisions, apply the
[actors, channels, and state ownership guide](behavioral-requirements.md#actors-channels-and-state-ownership).
Trace the requested actor interactions before choosing transports or shared
state; retain the decision and its evidence in the existing notes for spec,
global planning, step planning, and affected Improve reviews to consume.

### Plan the investigation

After the initial repository baseline, choose investigation depth from the
decisions still at risk. First check the plan triggers below; revisit them when
new evidence creates a material conflict or dependency. If none applies and
direct inspection and the relevant checks can settle the decisions,
**omit an investigation-plan section and field table**; one sentence in the
existing note explaining the direct path is enough. A remote boundary alone does
not require a separate plan, and a simple deployed component can still need a
[runtime state decision](service-discovery.md#runtime-state-placement).

When evidence gathering has consequential dependencies, independent owners,
materially conflicting sources, expensive probes, or likely interruption, put a
compact investigation plan in the existing discovery/research note before further
dependent probes. Keep its outcome/stop record even when the investigation is
short; a retrospective list of gaps does not replace the plan. For this branch only,
name the question and affected decision, evidence already known, next evidence
route, prerequisites, owner, permitted effects, time/attempt bound, and sufficient
observation or stop condition. Reuse the current action's
[shared research allowance](#budget-stopping-and-convergence); delegation does not
multiply it. Split only investigations whose inputs and effects are independent.
When a read needs a target or identity from an earlier observation, obtain that
observation first. Revise the question frontier as evidence arrives, preserving
dated findings and why a decision changed rather than silently rewriting history.

End with the selected decision or unresolved question, its evidence and earliest
affected consumer. An unknown contract needs research; an owner or access
decision stays open; a known selected setup requirement can become prerequisite
work before its consumer. Leave independent investigation eligible within the
current action. Follow [decision boundaries](#decision-boundaries) and verify the
[discovery evidence handoff](project-knowledge.md#discovery-evidence-handoff).
This is organization within the existing action, not another stage, scheduler,
state file, callback or Improve campaign.

### Early access readiness

Notify early; block only work that needs the missing access. Start once a system,
target/environment role, and task-relevant need are concrete, normally during
`discovery` after the repository scan and before deeper dependent research. A
speculative technology or merely available connector is not a reason to sign in.
For a selected downstream test or delivery dependency, surface known access needs
now even if that later activity need not run yet.

Independent work stays within the current action and granted scope. Discovery
may continue local inspection, not future implementation; do not skip graph
stages or begin another action while this one is paused/blocked. When only a
downstream requirement remains and this action is genuinely complete, its
callback lets the script advance normally toward that later work.

First try one bounded, non-mutating read through the existing connection under
the current grant; ordinary supported credential refresh may suffice. Check the
intended target/role, not just tool availability. Reuse a sufficiently current
receipt for the same boundary instead of probing again on every Improve pass.
If no safe authorized probe exists, explain that limit and ask the necessary
scope/setup question; do not perform a write, create a resource, switch accounts,
or broaden access merely to test readiness.

For identity or access discovery, use supported non-mutating probes and
sanitized evidence. Normal supported tool-managed authentication and tool
configuration metadata without session material remain allowed. Builders and
reviewers must not read, decode, retain, or report local authentication,
session, or credential-store contents.

| Observation | Next action |
| --- | --- |
| Relevant read succeeds in the intended role | Record what that read establishes and continue without a login request. It does not prove write permission or consumer/browser access. |
| Missing/expired session remains after supported refresh | Prompt the user promptly for the required sign-in/reconnection, before more research that depends on it. |
| Wrong account/tenant, insufficient role, or consent required | Explain the specific selection/permission decision and ask the appropriate user or administrator; another login may not fix it. Never expand scopes automatically. |
| Missing tool/binding, network failure, or target not provisioned | Record a setup, connectivity, or provisioning gap. Do not diagnose authentication from a failed call alone; use bounded safe checks to distinguish causes. |
| Optional or unselected system | Defer access requests until the system becomes a concrete dependency. |

Give the user the system and non-secret environment/role alias, why access is
needed, the safe check attempted and its sanitized result, the smallest necessary
user action, the earliest activity it blocks, and what independent work can
continue. Use the supported host/provider authentication surface; never request
passwords, tokens, cookies, or credential-bearing links in chat or notes. A
request to authenticate is not permission to grant broader access or deploy.
Raise a known admin/approval lead time early, but do not front-load speculative
or unrelated privileges. Distinguish connector, downstream service, deployment,
and browser-consumer identities when they are separate boundaries.

Select the [lowest-overhead sufficient testing surface](testing-and-documentation.md#lightweight-and-browser-checks).
A curl/API probe may not share the browser's session or authentication flow.
Consider an existing authorized browser route for a real consumer-access need;
do not diagnose the destination as unavailable solely from a login redirect or
assume connector access establishes browser-user access.

Retain this request and its pending/declined/deferred/verified disposition in the
existing authored Markdown with the observed-at context, evidence locator,
affected work, owner, and safe recheck/resume condition. These are descriptive
notes, not new result fields or an authentication state machine. Reuse an existing
request for the same system/role/scope; do not repeatedly prompt on unchanged
blockers or after refusal. A changed need or new user direction can reopen it.
Before `plan-improve` completes, check that each concrete external dependency
has relevant access evidence or a disclosed access/setup requirement, owner,
and earliest gating stage.
An undisclosed known requirement is a planning defect; a disclosed downstream
requirement need not block independent work. A prerequisite for the current
action remains incomplete and uses that packet's pause/blocked route.

After the user responds, recover the current packet if context was cleared and
follow its resume route if paused/blocked. Recheck the relevant safe operation;
the user's confirmation alone is not access evidence. Keep failed verification
unresolved. Once access and the current action's remaining duties, including
any assigned Improve campaign, are complete, submit its exact current callback
and consume the next packet. Do not stop at a question answer, mark the whole
phase done just because login succeeded, or replay a pre-block callback.
Revalidate stale evidence or changed target/role/scope before use, especially at
step and release planning; do not rediscover settled access at every node.

This is host-executed policy. The navigator returns its reference and preserves
ordinary notes/result locators and pause/resume state; it neither authenticates
nor proves that a probe or user prompt occurred. Contextual minimum-scope requests
follow [OAuth incremental-authorization guidance](https://developers.google.com/identity/protocols/oauth2/resources/best-practices#use-incremental-authorization);
apply the actual provider's error and permission contract, not a universal
HTTP-status-to-login rule.

### Acquire a reader and establish access only when authorized

If a consequential observation is unavailable, compare available access routes,
such as MCP/API/CLI/SDK/browser interfaces, using
[platform discovery](platform-discovery.md#discover-before-choosing-a-mechanism).
Prefer an existing authorized tool or native facility. A missing skill, MCP
server, SDK, client, or test environment is a setup question before it becomes a
final access blocker, but acquire one only for a named gap that could change
discovery, reuse, implementation, or verification.

When the user's request or current task context authorizes discovery setup, that
authorization covers a reversible, task-local acquisition in the stated account,
resource, cost, and change scope; do not ask again for the same bounded setup.
Before acquisition,
verify the publisher/source and package metadata, select a resolved version or
commit where available, and inspect install scripts and requested permissions.
Never execute an unexamined floating installer; disable unnecessary install
scripts. After fetching but before execution, record and verify the resolved
bytes' hash or package integrity and relevant support/compatibility evidence. Use
a task-owned temporary workspace, dependency store, cache, and configuration;
avoid global installation and unrelated host or repository changes. A skill
supplies guidance, not credentials or implicit tool access.

For an MCP server, inspect its startup requirements and relevant schemas, then
initialize, catalog, and invoke one task-relevant operation through a supported
host connection or temporary protocol client. Record whether it is a native host
tool or a client-invoked process. An initial catalog is not a ceiling: another
supported existing or newly acquired reader may be used within the same authorized
account/data scope and grant. Preserve an actual permission, policy, or target
denial as evidence; do not route around it. Readers and validators may differ
from the selected writer, but acquisition never changes the frozen selected
interface, writer, or inventory and never licenses a second mutation mechanism.

Reuse ordinary credential chains and refresh under an existing grant. Starting a
login, selecting a new account, granting scopes, accepting terms, copying secrets,
or broadening privileges needs authorization covering that change; do not ask
again when it is already granted. Distinguish a package/tool being ready from an
identity being authenticated, an operation being authorized, the intended target
being selected, and target behavior being observed.

Prefer an existing authorized sandbox, then a temporary project, official sample
or test harness, emulator, or local service. Provision a disposable remote dev/
test resource only when the user's authorization covers that account and resource
type, its cost/quota and isolation, and cleanup. A temporary name does not make a
production operation safe. Record acquired artifacts, non-secret command/config
references, observed capabilities/effects, unresolved access, and task-owned
process/resource cleanup in the existing authored Markdown.

### Run bounded, discriminating experiments

Use an experiment when it settles a consequential uncertainty better than another
read. Before each experiment, record in the existing question/source/role/
interface/interaction and report material: its hypothesis; plausible outcomes and
the observation that distinguishes them; inspected existing mechanism; source,
configuration, target, and identity; allowed effects; time/attempt limit; cleanup;
and how each outcome changes the plan or reuse decision. Prefer non-mutating
inspection, then an authorized isolated fixture. Stop on unexpected effects or
missing authority; never use production merely because it is the only target.

Select only the experiments needed from this ladder, adapting each to the
encountered contract. The specific probes below are conditional examples, not
universal acceptance criteria:

- **Access setup:** acquire/configure a reader, initialize/catalog it, and make
  one authorized relevant read; distinguish package, startup, identity,
  permission, target, and data-access failures.
- **Interaction contract:** exercise supported valid and invalid interactions to
  learn the applicable input/output, error, ordering, and completion semantics.
  For example, when asynchronous results can affect newer consumer state,
  identify the existing result-acceptance policy. In an authorized isolated
  fixture or existing safe test, force reversed completion of two relevant
  operations and check the affected state, such as rendered or client-held state
  in a UI; mark absent surfaces not applicable. Do not assume a successful result
  is still current or duplicate a live mutation to test it.
  Record whether an existing sequence/version/cancellation mechanism can be
  reused, or a small extension needs implementation.
  A local RPC mock proves only its adapter.
- **Library and design compatibility:** run representative existing code or an
  official example under the actual framework or a clearly labeled local harness.
- **State and concurrency:** compare valid, stale, repeated, or concurrent
  disposable operations to learn ownership, isolation, transaction/version, and
  idempotency behavior.
- **Caching and failure recovery:** compare hit/miss, read-after-write, expiry,
  and a bounded safe failure without equating a cache with durable state.
- **Authorization and exposure:** use approved test identities or harmless local
  fixtures for a relevant allow/deny, input/output, or tenant-scope boundary.
- **Reuse comparison:** compare an existing facility and the smallest extension
  under equivalent inputs and a predeclared correctness, UX, reliability, cost,
  or security criterion.

Record actual positive, negative, or unresolved outcomes, source versions,
artifacts, and cleanup. Preserve non-secret request/outcome evidence such as a
role alias, operation, response status, and state effect independently of prose.
Redact sensitive fields; if the remaining receipt cannot substantiate a claim,
keep that claim unresolved. Label fidelity precisely: source-only inference, local
mock, actual framework test, actual service read, deployed endpoint, or
intended-user test. A successful local test cannot become a claim about a
deployed endpoint or user behavior. A material result re-enters the existing
review/plan/apply loop and resets convergence.

### Reuse before a new mechanism

For each implementation choice, inspect the current mechanism, configuration,
platform/native capability, shared code, library/version, and representative
supported use. Prefer **reuse**, then **configure**, then the smallest compatible
**extension**. Record the requirement met, applicable evidence, and material
limits. Do not duplicate an existing cache, authentication flow, transport
wrapper, storage abstraction, or design component merely because it is easier to
demonstrate a new one.

Use **replace/new proposal** only when evidence shows that the best applicable
existing option has a concrete task-relevant defect or unmet requirement and the
change brings a substantial improvement in correctness, security, user
experience, reliability, maintainability, performance, or cost. Compare
equivalent conditions when measured; otherwise give a concrete causal explanation.
Account for the smallest change, migration/compatibility, maintenance,
operational, dependency, and security costs. If the improvement is unproven or
access is missing, keep the suitable existing option as the default and defer the
alternative or frame it as a bounded experiment.
Do not copy an evidenced obsolete, insecure, or incompatible mechanism unchanged.

### Budget, stopping, and convergence

Use a user-supplied exploration allowance when present. Otherwise, one
investigation has at most 15 active minutes and 64 observable host actions, up to
two capability candidates and three experiments. Reserve two active minutes and
eight actions for reconciling findings, writing the result, and cleanup. The
allowance is shared across every reader, tool, environment, context reset, and
same-investigation review phase; opening a new tool or environment never refills
it. Known sufficient evidence may finish without using the allowance.

The host must check elapsed active work, observable-action counters, remaining
capacity, and a per-command timeout before starting work. At the default bound,
once 13 active minutes or 56 observable actions have been used, stop launching
exploration and use the reserve only for reconciliation, writing, and cleanup.
Set each exploration command's timeout within the remaining exploration allowance,
not merely the full deadline. Do not charge inactive time waiting for the user as
investigation activity. If the host cannot measure a counter honestly, state that
limitation in the existing Markdown and use the available conservative bound.
ShipLoop does not observe native host tools or kill them; this guidance is not a
claim of a script watchdog.

Record the investigation scope, start, elapsed active work, observed counters,
remaining allowance, conclusions, and best next gap in the existing authored
Markdown. Use the closing reserve to checkpoint before pausing:

- If the current action's duties can be completed honestly within the reserve,
  submit its valid result through the exact callback, retaining open/blocked
  questions and budget accounting, then pause at the returned packet. Do not
  submit an incomplete review or manufacture passing checks merely to checkpoint.
- Otherwise, write the partial result to the current packet's existing inbox
  path. Pause with a non-secret reason that includes that path, labels it an
  **unaccepted draft**, and records the remaining allowance and next gap. The
  accepted candidate remains unchanged. If the draft could not be written, say
  what was not retained; do not claim the discoveries were checkpointed.

Use the existing `pause` command for either a legacy or managed action. The
managed bridge owns its unfinished child status; do not invent a `stopped` result
or edit child state. `halt` is for deliberately ending the run unfinished, not the
default resumable budget checkpoint. On a later authorized resume, read the
recorded draft and accepted candidate, finish the current action's duties, and
use its current callback. Resuming does not replenish the exploration allowance.
At the allowance/deadline, do not autonomously renew, restart, or claim convergence.
An exhausted budget, failed probe, or repeated action never counts as a trivial
pass.

During each research review, challenge the most consequential conclusion with a
feasible independent source, counterexample, or safe probe; otherwise record that
limit. Unchanged blockers remain open. Two fully checked trivial passes can finish
only with no required unresolved questions. Carry durable reusable conclusions to
the existing plan, knowledge/outer-work records, and scoped product documentation
tasks; never hand-edit frozen environment state or create a second investigation
engine.

## Navigator execution mode adapter

Navigator packets select this adapter with the shared recursive-discovery
section above. Apply the same eight-area screen, consequential recursion,
authorized acquisition, experiments, reuse decisions, evidence fidelity, and
shared allowance. This adapter supplies the current protocol's record and owner
binding; the other detailed result-schema and child-phase sections in this guide
describe managed/legacy compatibility runs.

For navigator, keep findings in a durable run note, such as
`notes/<actionID>.md`, and include its locator in the current generic result's
`evidence_refs`. Use ordinary Markdown to retain questions and parent/source
links, visited boundaries, access and acquisition stages, observations and
limitations, reuse choices, cleanup, active time/action accounting, remaining
allowance, conclusions, and required open gaps. Use the current packet's result
envelope. Do not add `body`, `research_state`, `system_context`, or other legacy
fields to that envelope or create compatibility candidate files. Named
questions/sources/`depth_rationale` in the shared section describe information to
retain, not a mandatory navigator schema or note layout.

For [access requests](#early-access-readiness), keep the probe, user-facing ask,
disposition, owner, earliest gating stage and recheck condition in that same
note. Carry its locator in dependent results' `evidence_refs` and applicable
planned work-item `context` so a cold host can find it without conversation
memory. Update the existing note rather than creating a duplicate request.

Record the selected mutation route and its authorization boundaries. Extra
readers do not grant authority to change that route or evade a real denial.
References to a frozen inventory, selected-interface identity, or child state
describe compatibility enforcement; navigator does not freeze those artifacts
or require their certificates. The host must preserve the actual scope and
decisions and disclose changes without claiming script-enforced checks.

`discovery`, `research`, and `research-improve` use this policy for affected
environment flows. At `product-improve` and `outer-improve`, use it when a
consequential newly encountered boundary or conflicting evidence requires more
investigation. Do not restart settled research just because a later node reads
this guide. The same investigation's allowance follows its notes across nodes
and context resets; entering an Improve action never refills it.

An Improve node owns its entire review/plan/apply/check/record/assess campaign.
Perform those cycles internally under the navigator binding and preserve their
learnings. Do not submit a callback for each compatibility child phase. Required
unresolved questions prevent a host declaration of convergence; navigator
validates the result envelope, not the truth or completeness of those findings.

Use the closing reserve with the current packet's protocol:

- If the action's duties are complete, submit its valid generic result and pause
  the returned action when the investigation allowance is exhausted.
- For unfinished duties, retain the **unaccepted draft** at the current printed
  inbox path and call `pause` with the note/draft locator, remaining allowance,
  and next gap. Cold `next` and `resume` preserve that action ID and draft; neither
  accepts it or replenishes the allowance. Finish the actual duties before
  submitting that action's result.
- A substantiated access/owner blocker may instead be submitted as a valid
  `outcome: blocked` result with durable evidence references. That is an accepted
  blocker report and allocates a **new action ID at the same stage**; it is not a
  same-action draft checkpoint or a successful advance. Follow its returned
  blocked/resume packet. Never mark an unfinished campaign `done` just to save it.

## Decision boundaries

Classify the next useful action in the existing question's `answer`,
`rationale` and `revalidate` fields; these are not new status values or another
journal. Keep the distinction visible in the report and improvement plan:

- **Researchable unknown:** name the missing fact, the relevant repository or
  primary contract, a permitted probe and what observation would settle it.
  Investigate or independently recheck it, including consequential downstream
  behavior justified by the selected scope and risk.
- **Owner decision or authority:** name the precise policy, target, role or
  permission needed, and its consequence. Retain `open`/`blocked` status and
  request direction; use the existing pause route when progress depends on it.
  More public-document reading cannot establish account access or select the
  owner's policy. Do not invent a default or relabel the gap not-applicable.
- **Later-phase implementation:** when the underlying contract is established,
  record the known requirement and its downstream consumer (behavior/spec/test
  planning or an existing handoff route). Do not implement it during research.
  A genuinely unanswered prerequisite remains open; calling it future work
  does not resolve it or permit research finalization.

Derive safety expectations that hold independently of a missing policy. For
example, whatever identity or retention policy the owner selects, an unauthorized
state mutation must not be reported as accepted. Record that expectation and
its basis without claiming an identity scheme was selected or a security test
passed. Reserve the detailed test matrix for behavior/spec and the test phases.
Do not grow an unselected optional feature just to make its research exhaustive.

Each review distinguishes **new discoveries** from **unchanged blockers**.
Open/blocked questions still reset the current convergence streak even if this
pass found nothing new. Two quiet reviews with a missing owner decision are not
two successful trivial passes. Use the existing gates, result records and
carry-forward/outer-work routes; do not add a nested investigation engine.

## Review

Each pass reads its current question/source records, finding ledger, selected
candidate pages and required Git history. Use `next`, `context` and `history`;
do not load every old research report. Perform a new investigation or independent
recheck of the important conclusions, not merely a rewrite of prior prose.

Cover every research rubric key with a concise evidence-based explanation:

| Key | Question to answer in this pass |
|---|---|
| `prompt_coverage` | Which requirements/spec clauses/discoveries drive the inventory, and are any omitted or invented? |
| `environment_conditions` | What runtime, resource, data, concurrency, persistence, configuration and failure conditions actually matter? |
| `source_quality` | Do inspected sources directly support each conclusion at the relevant version/environment? |
| `contradictions` | Which sources, observations or requirements disagree, and what evidence or decision resolves the disagreement? |
| `best_practices` | Which alternatives fit local constraints, and what are their benefits, costs, failure modes and adoption reasons? |
| `access_readiness` | Are authorized roles, safe probes and prerequisite availability understood without recording secrets? |
| `invocation_contracts` | Are relevant client/service operations, envelopes, serialization and error/async behavior established on both sides? |
| `test_deploy_feasibility` | Which local, browser, service or API checks are required and possible in the intended environment? |
| `remaining_unknowns` | Which material questions remain, what should be investigated next, and what requires user direction? |

Start broad enough to identify plausible alternatives, then investigate the
highest-risk gaps deeply. Inspect relevant local contracts and current primary
documentation; use secondary/community reports to generate leads and failure
hypotheses, not as sole proof of a capability. Seek evidence that could disprove
the favored answer. Distinguish independent corroboration from copied sources.
Record what each safe probe or source actually establishes, including null or
negative results and why an alternative was rejected.

Use the existing planning result contract: `findings` with stable IDs and
material/trivial severity, the complete `coverage_review` object, `test_review`
and `learnings`. Plan every unresolved finding, then supply the updated complete
report and `research_state` at application. Research changes remain candidates
until checks and audit commits establish convergence.

The complete replacement result is an on-disk artifact, not a requirement to
paste the entire report or inventory into the model context. For large candidates,
read bounded relevant sections and assemble the replacement in the printed host
inbox from the current Markdown using scoped edits or local transformation
scripts. Do not edit script-owned candidates directly. Preserve untouched
records and stable IDs, then validate the assembled result. Never omit evidence
to fit the context window or rely on remembered records from a prior iteration.

## Evidence and freshness

Source identity and observation time serve different purposes. Prefer an exact
commit, release, document revision or other immutable identifier for stable
claims. Record when a volatile condition was observed and its safe point-of-use
revalidation trigger. The script's finalization time is when the checkpoint was
recorded, not proof that every remote source was freshly inspected then.

Treat a new/changed conclusion, newly discovered material question, environment
constraint, incompatibility, or test/deploy feasibility gap as material. A small
text edit can change the entire decision. Non-semantic report cleanup or a source
observation/version refresh that changes no conclusion may be trivial. The script
conservatively treats additions or edits to question records, source identities,
support or limitations as material, even if the host labels them trivial.
Unavailable evidence is not evidence that nothing material remains; record the
gap and pause as needed.

Each research iteration requires real candidate-bound lint and tests covering the
packet's exact `research evidence` acceptance. Useful checks include question/source
referential integrity, missing applicability/revalidation policy, contradictions
detectable from a structured model, and the expected results of safe local probes.
Test the asserted contract, not only file existence. Manual source interpretation
is host-reported evidence, not executable proof or a passed remote acceptance test.
Reconcile the report's required case map with the repeatable checks: every
required case needs an expected outcome and current execution evidence. Label
historical/manual observations separately; a passing subset does not validate
the whole case map or excuse an unavailable required check.

Use a distinct verbose audit-only commit per completed planning pass with the
recorded learnings. Two consecutive fully checked trivial-only passes, no open
questions/findings, and fresh final checks permit finalization. Apply trivial
fixes before the checks. A repeated action, failed probe, exhausted budget or
iteration cap never counts as another successful pass.

Keep secret values, credential-bearing URLs, account addresses and raw sensitive
responses out of reports, results and logs. Research does not authorize a new
credential grant, persistent configuration, destructive experiment, or
publication. When the user's request or task context authorizes bounded discovery
setup, a temporary task-local investigation reader, SDK, skill, or test dependency
may be acquired under the recursive-discovery rules; that does not alter the frozen
selected writer or interface inventory. Missing user policy is not resolvable by
additional web citations.

## Later discoveries

Research completion accepts a versioned evidence baseline, not a permanent claim
that discovery is over. Every implementation review explicitly assesses whether
its current scope needs new investigation:

```json
{
  "research_assessment": {
    "status": "required",
    "summary": "A newly observed boundary invalidates the current assumption.",
    "evidence": ["Safe reference to the retained observation"],
    "questions": ["Which supported behavior applies at this boundary?"]
  }
}
```

Statuses are `not-needed`, `resolved`, `required`, or `blocked`. Explain why no
research is needed when that is the decision. Required/blocked investigation is
material and cannot leave the improvement loop unresolved. Retain the answer,
evidence and revalidation policy when resolving it; repeat review and checks.
`resolved` means investigation was completed in this pass and still resets the
trivial streak. In a later pass, use `not-needed` when rechecking the existing
evidence reveals no new investigation need; explain why it remains applicable.
Every status requires a summary; all except `not-needed` require nonempty
`evidence` and `questions` lists. These are safe references and question text,
not an invitation to copy raw source output into the result.
Use the existing carry-forward checkpoint for facts other iterations need.

| Discovery location | Required route |
|---|---|
| Before any execution receipt | `revisit --to research` archives the old research and downstream planning, preserves the survey, and reconverges. A changed survey contract uses `--to survey`. |
| Within the active step's approved scope | Investigate during its ordinary Improve loop; unresolved research is material and resets convergence. |
| Required by future pending steps | Carry a `research`-domain `pending-replan` discovery. Post-inner maps it to an explicit `activity: research` producer, and every affected consumer must transitively depend on that producer. |
| Incompatible requirement, permission or completed-work assumption | Pause for direction. Research evidence is not authority to rewrite the approved baseline. |

A research DAG step names its checkable report/decision artifact in `produces`.
Its review supplies the full research rubric in `research_review` as well as the
ordinary execution fields. The step must pass the normal lint/tests,
carry-forward, verbose commit, two-trivial-pass, final-verify and merge gates.
Following steps consume the report and scoped knowledge with fresh context.
Mapping a research obligation means **scheduled**, not answered or verified.
In `pending_obligation_map`, a research obligation's `{id, steps}` entry lists
only the research producer IDs in `steps`. The script derives affected pending
consumers and checks their transitive dependencies separately; do not list those
consumers as research producers.

Generic improvements to ShipLoop belong in `shiploop-improvements.md`, separate
from product research and without permission to self-modify the harness.

## Basis and limits

Adaptive investigation and persistent artifacts are supported by
[Anthropic's research-system engineering experience](https://www.anthropic.com/engineering/multi-agent-research-system).
It also reports coordination and token costs, so parallel investigation is a
choice for independent questions, not a requirement for every pass.
[Self-Refine](https://arxiv.org/abs/2303.17651) reports task-specific improvements
from revision, while [intrinsic self-correction research](https://arxiv.org/abs/2310.01798)
shows important limits without external feedback. These motivate evidence-backed
iteration, not a guarantee of completeness or this exact two-pass threshold.
The threshold is ShipLoop's explicit operational stopping rule; semantic
adequacy, source interpretation and live-source truth still require judgment.
