# ShipLoop architecture rubric

A living rubric for judging the architecture plans ShipLoop produces for web
products on hosted runtimes (Google Apps Script, Salesforce, Cloudflare Workers
and similar). It is the scoring standard for prompt experiments: every new
experiment grades against these criteria, and a prompt change ships only when
it raises the relevant scores without lowering proportion (P1).

The machine-readable form is [rubric.json](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/rubric.json)
(criteria and grades) and [scenarios.json](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/scenarios.json)
(scenario catalog). The judge ([judge.py](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/judge.py))
reads both, so this page and the scorer cannot drift. Results:
[2026-09-26](shiploop-architecture-rubric-results-2026-09-26.md).

## The principle: as simple as the request allows, as native as the runtime allows

A product's architecture sits somewhere on a lifecycle ladder. The request
decides the rung; the plan's job is to land on that rung, not above or below it.

| Tier | When | Typical shape |
| --- | --- | --- |
| client-only | One person, or people sharing one screen; nothing shared or trusted outlives the page | All logic in the browser; browser storage only if resuming is asked for |
| client-plus-light-server | A client product with one shared or trusted piece (a leaderboard, a saved preference that must follow the user) | The client does the work; a small endpoint validates and stores the shared piece |
| host-scoped | The product extends a host record or document (a Docs sidebar, a Salesforce record page) | State lives with the host (document properties, the record's related data) and follows the host's sharing; no separate store or access model |
| server-shared-async | Several people share state; changes matter on the next visit or within hours | Server-held state, runtime identity, notification by email or platform notification |
| server-shared-live | Several people share state and must see changes within seconds or a minute | Server-held state, runtime identity, polling or a push channel justified by the stated freshness |
| server-batch | Scheduled or triggered work with no interactive client | Idempotent, retried, rate-limited, observable jobs |
| server-public | Anonymous or untrusted callers reach server state | Validation, abuse controls, staff-only administration |

Moving up a rung adds identity, storage, authorization, concurrency, recovery,
retention and cost obligations. That is why overbuilding is graded as a
failure, not a bonus: a single-player game that "hides the computer's fleet on
the server" pays all of those costs to protect nothing. Hidden information
matters when one user must not see what another user has; a lone user who
cheats only cheats themselves.

## Grades

| Grade | Meaning | Score |
| --- | --- | --- |
| met | The plan adopts what the criterion asks, sized to the request | 1 |
| partial | Named, but a material part is undecided or wrong | 0.5 |
| missed | Applies, and the plan does not address it | 0 |
| overbuilt | Builds more than the request needs | 0 |
| na | Does not apply | — |

Only the criteria a scenario lists in `applies` are graded for it.

## Criteria

### Proportion and scope

| ID | Criterion | Asks |
| --- | --- | --- |
| P1 | Proportion | The simplest placement that meets the request: the scenario's tier, no less and no more. |
| P2 | Open choices | Where the request leaves players, devices, persistence, sign-in or freshness open, ask or state the default and what it rules out. |
| P3 | Scope | No unrequested features. |

### Identity and access

| ID | Criterion | Asks |
| --- | --- | --- |
| I1 | Identity | The runtime's own sign-in where users must be told apart; none where they need not be. |
| I2 | Authorization | Server-side, per-action checks; never trust client-supplied identity, role or ownership. |
| I3 | Sharing model | Who may read and change each record, in the runtime's native access model. |
| I4 | Untrusted callers | Validation, rate limits or abuse controls, and plausibility checks on submitted values, or an explicit accepted risk. |

### State and storage

| ID | Criterion | Asks |
| --- | --- | --- |
| S1 | State home | Each state's owner and native store, and why that store fits (capacity, query, consistency). |
| S2 | Concurrency | How simultaneous changes resolve: lock, transaction, version check or single-writer object. |
| S3 | Recovery | What survives a reload, disconnect or crash mid-action, and how the client resynchronizes. |
| S4 | End of life | What ends each state and what removes or archives it. |

### Connectivity

| ID | Criterion | Asks |
| --- | --- | --- |
| C1 | Channel choice | A channel per interaction, justified by the freshness the request states. |
| C2 | Missed updates | After a push, poll gap or reconnect, read authoritative state back. |
| C3 | Idempotency | Retries and duplicate deliveries cannot apply an action twice. |
| C4 | Offline | For intermittent connectivity: a durable local queue, replay order and a conflict rule. |
| C5 | Channel cost | The channel's cost against runtime quotas or limits. |

The channel ladder, lightest first. Pick the lowest rung that meets the stated
freshness, and move up only when the request's latency needs it:

1. Request/response on the user's own action.
2. Refresh on focus or navigation (the next visit sees the change).
3. Email or platform notification, for changes hours apart.
4. Polling at a stated interval, for changes within a minute; its cost is interval × users × request cost.
5. Server-sent events, long polling, WebSockets or platform push (for example Salesforce platform events, or Durable Objects with WebSockets), when seconds matter.

A push is a wake-up signal, not the state: after it arrives, or after a gap,
read the authoritative state back (C2). Which rungs a runtime supports is a
platform fact to verify, not recall (R3): Apps Script, for example, has no
server push to a web app page, so its live tier is polling.

### Caching

| ID | Criterion | Asks |
| --- | --- | --- |
| K1 | Cache use | The runtime's native cache or precomputation for derived or expensive data, where it pays off. |
| K2 | Freshness | The expiry or invalidation rule, matched to the staleness the request allows. |
| K3 | Cache restraint | A cache is never the authority; no cache where it does not pay off. |

### Information lifecycle

| ID | Criterion | Asks |
| --- | --- | --- |
| D1 | Personal data | Personal or sensitive data held, or sent to a third party. |
| D2 | Retention and deletion | How long it is kept and how it is removed. |
| D3 | Logs | No personal data or secrets in logs or error messages. |
| D4 | Secrets | Credentials in the runtime's secret facility, never sent to the client. |

### Runtime leverage and accuracy

| ID | Criterion | Asks |
| --- | --- | --- |
| R1 | Leverage | Native storage, identity, workflow, scheduling, cache and notification before custom equivalents. |
| R2 | Limits | The runtime quotas and limits the design meets. |
| R3 | Accuracy | No false claim about the runtime's or a library's capabilities. |

### Verification and failure

| ID | Criterion | Asks |
| --- | --- | --- |
| V1 | Verification | Checks on the deployed runtime surface, with negative cases for authorization and concurrency where they apply. |
| O1 | Failure visibility | Background or asynchronous failures are recorded and shown to whoever must act. |

### Client UI frameworks

Graded only when the request names a framework (for example Bootstrap or
Material Design).

| ID | Criterion | Asks |
| --- | --- | --- |
| U1 | UI framework fit | The requested or existing framework at its current version, through its supported components, theming and loading path; no second UI stack; nothing the framework provides rebuilt by hand. |
| U2 | Interaction states | Loading, empty, error and success states; accessible names, focus and keyboard paths for the main interactions; feedback for async work. |
| U3 | Host fit | Build versus CDN, content security policy, sandboxed iframes, server versus client rendering, and the host's native design system where one exists. |

### Measured by dedicated experiments

These criteria need a code fixture or a second stage, so the scenario judge does
not grade them; the experiments named here do.

| ID | Criterion | Experiment |
| --- | --- | --- |
| M1 | Composition: reuse, compose or augment before new; no near-copies or fused rules | E0 |
| M2 | Project layers: follow the project's conventions and check what each layer exposes | E7 |
| M3 | Intake questions about actors, devices, persistence, sign-in and hidden information | E3 |
| M4 | The planning review catches platform claims the plan stage introduced | E6b |

## Environments

Scenarios run on the hosted runtimes ShipLoop targets and on common general
deployments. Each environment has a platform card in
[references/platforms](../skills/shiploop/references/platforms/) that planning
reads for background; the cards' dated facts and claims to check come from
sourced fact sheets in [factsheets/](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/factsheets/).

| Key | Environment | Card |
| --- | --- | --- |
| GAS | Google Apps Script web app | apps-script.md |
| SF | Salesforce DX with Lightning Web Components | salesforce.md |
| CF | Cloudflare Workers | cloudflare-workers.md |
| VERCEL | Next.js on Vercel | vercel.md |
| AWS | AWS serverless (CDK) | aws.md |
| GCP | Google Cloud Run | gcp.md |
| NODE | Self-hosted Node.js with Express | node-express.md |

Client frameworks (Bootstrap, Material Design 3 implementations, React,
Next.js, Vue, Svelte, Tailwind) share [ui-frameworks.md](../skills/shiploop/references/platforms/ui-frameworks.md).

## Scenario catalog

Each scenario names its expected tier, the runtimes it is tried on, the criteria
that apply and what counts as overbuilt. Full definitions: [scenarios.json](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/scenarios.json).

| ID | Scenario | Tier | Hosted runtimes | Main pressure |
| --- | --- | --- | --- | --- |
| S01 | Battleship against the computer | client-only | GAS, SF | Does not overbuild |
| S02 | Hotseat checkers | client-only | GAS, CF | Does not overbuild |
| S03 | Solo minesweeper with shared leaderboard | client-plus-light-server | GAS, CF | Only the shared part goes server-side; score plausibility |
| S04 | Correspondence chess, moves a day apart | server-shared-async | SF, GAS | Notification, not a live channel |
| S05 | Live multiplayer Battleship | server-shared-live | CF, SF | Live channel justified by seconds; recovery |
| S06 | Team task board, one-minute freshness | server-shared-live | SF, GAS | Polling cost vs push; native records |
| S07 | Expense approval with audit trail | server-shared-async | SF, GAS | Native workflow; roles; retention |
| S08 | Read-heavy KPI dashboard, 15-minute staleness | server-shared-async | GAS, SF | Native cache or precomputation; no write path |
| S09 | Nightly partner API sync | server-batch | GAS, CF | Idempotency, rate limits, secrets, failure visibility |
| S10 | Public anonymous feedback form | server-public | CF, GAS | Abuse controls; staff-only access |
| S11 | Receipt photo upload and extraction | server-shared-async | GAS, SF | Native file storage; async status |
| S12 | Team chat room | server-shared-live | CF, SF | Channel, history retention, no unrequested presence |
| S13 | Offline field checklist | server-shared-async | SF, CF | Durable local queue, idempotent upload, conflicts |
| S14 | AI summarizer button | server-shared-async | GAS, CF | Secret custody, cost, third-party data |
| S15 | Docs sidebar that tags sections | host-scoped | GAS | Document properties and sharing, not a database |
| S16 | Account record-page panel of open cases | host-scoped | SF | Standard objects and the org's sharing are the authority |
| S17 | Multi-tenant appointment booking | server-shared-async | VERCEL, AWS | Tenant isolation on every query, with a negative test |
| S18 | 200-seat registration, never oversold | server-public | GCP, NODE | Atomic conditional write under a rush |
| S19 | Payment webhook, duplicates and reordering | server-public | NODE, CF | Signature check, idempotency by event ID |

## Running the harness

- Every headless trial passes `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`,
  with the prompt on stdin. Without it, each `claude -p` starts the user's MCP
  servers, including a Chrome DevTools server that opens a browser per trial.
- A trial with no tools sometimes stops after announcing it will inspect the
  project. Treat any plan under 150 words as a stub: rerun it with the same
  prompt ([redo.sh](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/redo.sh)), and exclude it if it
  stays a stub, rather than grading it as missed.
- A control must not be able to reach the treatment. When the card variant can
  read a directory, run the control from a directory without that access; a
  control that could see the cards read them in 22 of 32 trials.
- Pin Sonnet for trials and judges; grade blind, one plan at a time.
- The judge skips any output without a finished plan of at least 150 words, so
  a file still being written is never graded.
- Compare variants under one condition. Rerun the baseline alongside the
  candidates rather than reusing results from another condition, and report
  paired wins and losses per scenario-runtime cell as well as means.
- Use [judge2.py](https://github.com/whichguy/shiploop-prompt-lab/blob/main/experiments/judge2.py): an evidence quote
  before every grade, per-grade anchors, criteria before and after the plan, and a
  five-minute timeout with logged failures. Re-grading 30 plans changed a plan's
  score by 0.017 on average (judge v1: 0.041).
- Judge v1 reliability (40 plans graded twice): 91% of criterion grades and 39 of
  40 tier calls agree; a plan's score moves 0.04 on average. Differences of a
  few hundredths across one variant's 100 plans are therefore not judge noise,
  but trial-to-trial variation is larger: confirm a leader with a second trial.

## Adding to the rubric

- A new criterion needs an ID, a one-line "asks", the scenarios it applies to,
  and an entry in `rubric.json`. Grade it on existing outputs before trusting a
  prompt change aimed at it.
- A new scenario needs a request written the way a user would say it, an
  expected tier, the applicable criteria and an overbuild note. Include at
  least one scenario at the tier below and one above any new pressure, so
  overbuilding and underbuilding are both visible.
- Candidate scenarios not yet in the catalog: a mobile web app with push
  notifications; a data-export feature with large files; a scheduled report
  emailed to managers; an admin console with audit logging; a feature flag
  rollout.
