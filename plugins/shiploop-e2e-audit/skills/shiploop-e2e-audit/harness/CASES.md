# ShipLoop live E2E game cases

`scenarios.json` is an executable-input manifest for a live-agent hosted-delivery
experiment. It describes nine literal GAS requests in three ordered product
families and one independent Salesforce checkers create. The manifest is not a
hidden implementation specification for Grok.
The product repository contains only the application produced by earlier steps;
the launcher, oracle, sanitized logs, and snapshots stay outside it.

## Run boundary

Create one disposable product repository for each family: `tic-tac-toe`,
`checkers`, `battleship`, and `salesforce-checkers`. It starts as an empty folder or unborn Git repository with no
product source, test, evaluator, or instruction files supplied by the
experiment. The harness records its initial identity before the first request.

For every manifest step, start one fresh Grok process and conversation with the
normal selected ShipLoop skill. Supply exactly the corresponding `prompt` bytes
from the manifest. The harness chooses the repository working directory and
external trial output; it observes the ShipLoop workspace chosen by Grok rather
than starting one itself. It must not append an oracle, a test plan,
selector advice, a retry instruction, or a follow-up message to the user prompt.
For a full GAS step, the literal prompt requires the builder to use the
configured Google Apps Script deployment MCP. The create request creates,
deploys, and publishes one dedicated test application; each later feature or
refinement is a fresh request against the same product repository and Apps
Script project. The observer captures the builder's real MCP and browser
evidence; it does not append deployment instructions, issue its own repair or
redeployment, or substitute a model/mock response.

The separate Salesforce create uses the existing authenticated default developer
org and configured Salesforce DX capabilities. It creates a dedicated Lightning
checkers app, deploys actual metadata, and verifies the authenticated Lightning
UI. It does not create an org or use GAS staging/promotion. Before launch, the
operator independently verifies the default target against the user's intended
org and retains its sanitized identity and developer-org evidence. Credentials
are never prompt inputs or retained artifacts. A missing or mismatched target
blocks launch.

Run exactly one selected case per invocation and review its output while it runs
and after it stops. A multi-case suite command without a single `--only` selection
is rejected. Authorized ShipLoop repairs, Improve, publication, installation
refresh and a fresh no-model check happen between retained attempts. Retest the
affected case before continuing; keep failures and unrun cases in campaign
accounting. See [the operator checkpoint](../SKILL.md#review-each-case-before-continuing).

The first step in a family is a new-project run. Its product must return to the
original repository before the next step may start. Each later step is a new
feature request against that same evolving original repository, with a fresh
ShipLoop workspace/run root and a fresh Grok process. It must never resume the
prior feature run with `next`. Earlier project documentation that the product
itself returned remains visible. The harness supplies no prior chat, temporary
run state, test code, oracle data, or evaluator mappings as model context.
These external files are not an OS-enforced isolation boundary.

Before each feature/refinement, the harness creates an immutable external
snapshot of the original repository and records Git/tree/content identity plus
the verified predecessor deployment identity and hosted-browser evidence. It
does not add a tag, commit, source file, or evaluator file to the product
repository. A scenario is rejected before model launch if the prior step does
not have an independent deployed-product receipt, unless explicitly marked diagnostic;
it must not create a substitute app in a
new directory to keep the sequence moving.

## Independent verifier receipt

An external verifier command receives the scenario, step, external pre-feature
snapshot, final original repository, and external evidence root. It emits one
structured receipt. At minimum the receipt identifies the manifest/version,
step, verifier version, input snapshot and final tree identities, semantic UI
mapping version, MCP deployment and release evidence, hosted browser evidence,
and each required check with a status of `pass`, `fail`, `blocked`, or
`unverified`. Use the actual
`shiploop-e2e-receipt/1` schema in `verification-template.json`; result summaries
use `passed` and `failed`. Additional verifier and UI-mapping provenance may be
retained in the evidence files.

Only a successful external verifier receipt can establish a full live product
check. Grok prose, a ShipLoop callback, an HTML achievement report, a Git
commit, and tests written by the development agent are useful evidence but cannot
themselves produce `passed`. If a human contributes screenshots, a browser
recording, or a selector map, record their provenance and leave the relevant
behavior check `unverified` until the independent verifier can reproduce the
claim. Receipt validation checks bindings, not whether the author told the
truth. Missing, malformed, contradictory, or stale evidence is fail-closed.

For GAS `authorized-deployment`, the verifier receipt must bind a real
`shiploop-e2e-authorized-deployment-observation/1` record to the trial and
candidate. It records `provider: "mcp-gas-deploy"`, `script_id`,
`version_number`, `deployment_id`, `web_app_url`, `published: true`, a staged
MCP receipt, a pinned `promotion_request`, a promotion MCP receipt, and a
source-to-deployment mapping. The staging receipt comes from
`deploy(action=deploy)` and includes its `stagingCandidate` identity. The
promotion request records `expectedStagingVersion` and
`expectedStagingDeploymentId`, which must match that staging candidate before
the promotion receipt can qualify. The promotion receipt comes from the guarded
`deploy(action=promote, expectedStagingVersion, expectedStagingDeploymentId)`
operation and records success, staging-to-production promotion, the promoted
version/deployment identity, and `webAppUrl`. The staging candidate deployment
ID and promoted production deployment ID are distinct pointers even when they
use the same version; only the latter binds `deployment_id` and the published
URL in the hosted observation. The published URL must be the candidate's HTTPS
`script.google.com` `/exec` URL, either the ordinary
`/macros/s/<deployment_id>/exec` form or the Workspace-domain
`/a/macros/<domain>/s/<deployment_id>/exec` form; a `/dev`, localhost, or
unbound URL cannot qualify. Preserve the configured authorized access mode;
publishing this dedicated test app does not imply anonymous public access. Every
`source_mapping.source_files` entry must name an existing regular
candidate-repository file whose SHA-256 matches the mapping; this binds source
files to the release without claiming whole-candidate byte equality.

```json
{
  "schema": "shiploop-e2e-authorized-deployment-observation/1",
  "trial_id": "TRIAL_ID",
  "candidate_digest": "CANDIDATE_SHA256",
  "provider": "mcp-gas-deploy",
  "script_id": "SCRIPT_ID",
  "version_number": 0,
  "deployment_id": "PROMOTED_PRODUCTION_DEPLOYMENT_ID",
  "web_app_url": "https://script.google.com/.../PROMOTED_PRODUCTION_DEPLOYMENT_ID/exec",
  "published": true,
  "staging_receipt": {"path": "…", "sha256": "…"},
  "promotion_request": {"path": "…", "sha256": "…"},
  "promotion_receipt": {"path": "…", "sha256": "…"},
  "source_mapping": {"path": "…", "sha256": "…"}
}
```

For GAS `hosted-game-behavior`, bind a real
`shiploop-e2e-hosted-game-observation/1` record to the same trial, candidate,
script, version, deployment, and web-app URL as `authorized-deployment`. Its
browser trace repeats that exact `{script_id, version_number, deployment_id,
web_app_url}` identity and lists each scenario semantic check, nonempty
structured actions and observed results, expected result, status, and retained
screenshots or equivalent trace evidence. When both checks are required, the
two observations and the browser trace must agree on that identity tuple. The
auditor must inspect the raw retained MCP receipts and browser trace too:
schema validation proves identity and completeness, not raw MCP or browser
authenticity.

```json
{
  "schema": "shiploop-e2e-hosted-game-observation/1",
  "trial_id": "TRIAL_ID",
  "candidate_digest": "CANDIDATE_SHA256",
  "script_id": "SCRIPT_ID",
  "version_number": 0,
  "deployment_id": "PROMOTED_PRODUCTION_DEPLOYMENT_ID",
  "web_app_url": "https://script.google.com/.../PROMOTED_PRODUCTION_DEPLOYMENT_ID/exec",
  "browser_trace": {"path": "…", "sha256": "…"},
  "cases": [{"id": "case", "check_id": "scenario-check", "actions": [{"type": "click"}], "expected": "…", "observed": "…", "status": "pass", "screenshots": [{"path": "…", "sha256": "…"}]}]
}
```

The current case set does **not** claim to contain a working universal Google
Apps Script emulator or automatic browser oracle. A first-run product can use a
wide range of Apps Script-compatible arrangements. The verifier may use a
candidate-specific hosted browser route only when it can exercise the produced
published web app without changing it. If no honest hosted route can be
established, record the affected UI check as `unverified`; do not patch the
product, invent a bridge, or call the result verified.

### Salesforce deployment and Lightning proof

The Salesforce case uses separate checks and schemas; GAS staging/promotion
records cannot qualify them. The operator's sanitized preflight uses
`shiploop-e2e-salesforce-target-preflight/1` with `status: "connected"`,
`org_type: "developer"`, `observed_org_id`/`observed_instance_url`/
`observed_lightning_host`, and independently supplied `expected_org_id`/
`expected_instance_url`/`expected_lightning_host`. Expected and observed
identities must match. For launch the receipt additionally requires a UTC
`checked_at` within 15 minutes and `product_cwd` naming the explicit empty
product directory. Pass it through `--salesforce-preflight`; the runner rejects
it before launch if these checks fail. See [the read-only preflight recipe](README.md#salesforce-default-dev-org-preflight).
Keep the target receipt outside the product and pin it alongside the actual
deployment evidence. Its hash must match `manifest.json`
`salesforce_preflight.sha256` from launch; substituting another valid target
receipt after the run cannot qualify the deployment. A schema-valid record is not proof of its authenticity;
inspect its origin and confirm it represents the user's intended default org.

The normal independent review's `review_owned_checks` includes these rows:

| Check | Required observation and evidence |
| --- | --- |
| `salesforce-authorized-deployment` | `shiploop-e2e-salesforce-deployment-observation/1`: trial/candidate, provider `salesforce-dx`, status `succeeded`, org ID, instance URL, deployment ID and Lightning host; references to pinned `target_preflight`, `raw_deployment_result`, `deployment_receipt` and `source_mapping`. |
| `salesforce-source-candidate` | `shiploop-e2e-salesforce-source-candidate-mapping/1`: the same trial/candidate/org/instance/deployment, rationale and nonempty `components` with relative `path`, `sha256`, `kind`, `component_type` and `full_name`. Each file must match the returned candidate and a successful deployed metadata member; at least one component is a `lightning-app` or `lightning-web-component`. |
| `salesforce-hosted-lightning-behavior` | `shiploop-e2e-salesforce-hosted-lightning-observation/1`: the same identities, `authenticated: true`, `lightning_route`, pinned `browser_trace`, and semantic cases with the required oracle actions, canonical per-action `observations`, expected/observed results, status and screenshots or equivalent trace evidence. |

The raw Salesforce DX deploy result is the retained actual tool/CLI JSON,
including `status: 0`, `result.id`, `result.status: "Succeeded"`,
`result.checkOnly: false`, and successful `details.componentSuccesses` members
matching every mapped component's type and full name. Failed components cannot
qualify. Retain
the invoked target and source selection with that result; the independent
reviewer must correlate it to the confirmed org and deployed components. A
normalized `shiploop-e2e-salesforce-dx-receipt/1` binds provider, success, `job_id`,
org/instance/candidate and SHA-256 values for that raw result and source mapping.
Do not manufacture the normalized record from a builder's completion claim.
A check-only operation does not deploy components; it cannot qualify this case.
The provider's deployment result contract is described in the
[Salesforce Metadata API guide](https://resources.docs.salesforce.com/latest/latest/en-us/sfdc/pdf/api_meta.pdf)
and the [Salesforce CLI result formatter](https://github.com/salesforcecli/plugin-deploy-retrieve/blob/main/src/formatters/deployResultFormatter.ts).

The browser trace uses `shiploop-e2e-salesforce-lightning-browser-trace/1` and
repeats the observation's trial/candidate/org/instance/deployment/route and
authenticated state. The route must use the preflight's Lightning host and an
actual `/lightning/n/...` or `/lightning/app/...` path. Host and job mismatches,
missing pins, changed source files, unsuccessful deployments and absent hosted
behavior leave the affected check unverified. The shared checkers oracle
supplies the base rule cases and evaluates the canonical observations in both
the hosted record and browser trace. Generic "interact" actions and assertion
prose cannot replace those observations. The independent browser evidence must
exercise the deployed app without installing product test hooks. A candidate
whose UI cannot honestly expose the required actions stays unverified.

Use a new external review/evidence directory and the existing receipt contract.
With actual driver and review inputs configured, assemble the receipt from a
finished trial without launching another model, then grade it:

```sh
SHIPLOOP_E2E_TRIAL=/absolute/salesforce-trial \
SHIPLOOP_E2E_REPO=/absolute/returned-product \
SHIPLOOP_E2E_EVIDENCE=/absolute/salesforce-trial/evidence \
python3 "$HARNESS/verify_suite.py" --drivers /absolute/drivers.json \
  --review /absolute/salesforce-review.json > /absolute/salesforce-verification.json
python3 "$HARNESS/run.py" grade --trial /absolute/salesforce-trial \
  --receipt /absolute/salesforce-verification.json
```

The driver and review paths described in the README are real operator-supplied inputs, not bundled
Salesforce automation. The JSON formats and evidence pinning use the same
independent review contract described in [README.md](README.md#independent-verification-and-incremental-feature-runs).
Until actual deployment and authenticated browser observations exist, the result
remains unverified. These offline validators do not connect to Salesforce,
authenticate receipts, operate the browser, or create an app.

### Target-runtime compatibility is separate from the hosted release

Deployment does not remove the requested Apps Script source contract. `Code.gs`
and `appsscript.json` existing is insufficient. Trace the actual `doGet` output,
client dependencies, and any build/include step. Every client dependency needs a
delivery path supported by the target runtime. A local static server that
conveniently serves a sibling `engine.js` can make a game playable while
concealing a missing HtmlService resource path; it cannot qualify the hosted
game check or replace the promoted `/exec` evidence.

Google documents client-side code in HTML files and template includes, as well
as HTTPS external resources. Check the actual arrangement; do not mandate one
filename or framework. A build that demonstrably embeds the engine may also be
valid. Source inspection can identify an absent dependency path; conversely, a
local assembly check is not proof of hosted execution.
[Google HtmlService guidance](https://developers.google.com/apps-script/guides/html/best-practices).

## Semantic UI mapping

The verifier may make a read-only, post-run mapping from the deployed web app's
product-specific UI elements to the roles needed by a case. It records the
mapping and its evidence outside the product repository. The mapping may identify,
for example:

- Tic-tac-toe board cells, active-player status, restart action, legal-move
  treatment, and single suggested move.
- Checkers pieces, selected state, legal destinations, active-player status,
  hint toggle, capture continuation, and restart action.
- Battleship setup boards, target boards, shot action, turn/status panel, shot
  history, filter controls, and restart action.

The mapping is a compatibility layer for independent black-box observation. It
must not prescribe DOM selectors, a framework, filenames, data attributes, or a
code architecture in the prompt. It must never patch the app, write a test hook
into it, or be shown to the development agent while that run is active. A mapping
that cannot make the requested behavior observable leaves the check unverified.

## Behavioral procedure

For a GAS create step, first establish a Google Apps Script-compatible artifact,
create and stage the dedicated test application through the configured MCP,
promote the exact staged candidate, and retain the published `/exec` URL and
receipt identities. Then use the semantic hosted mapping to exercise the public
behavior requested in that prompt.

For tic-tac-toe, test alternating marks, occupied-cell protection, a representative
win, a draw, and a new game. `ttt-guidance` then tests that the status matches the
turn and that every empty cell, but no occupied cell, receives the legal-move
treatment. `ttt-best-move` adds a distinct behavior: exactly one legal suggestion
is visible during an active turn; an immediate win is chosen when available, and
an immediate opponent win is blocked when necessary. When neither condition
applies, any legal tie choice is acceptable.

For checkers, test a normal diagonal move, required capture, continued capture
by the same piece, promotion, and a new game. `checkers-guidance` then checks the
active player and selected-piece destinations, allowing only captures when a
capture is required. `checkers-hint-toggle` adds a non-mutating visibility
preference: toggling hints must not change board or turn state, and a required
capture chain must continue to guide only the active piece's legal continuation
until that turn ends.

For Battleship, test separate hidden boards, fleet placement, alternating shots,
hit/miss feedback, sunk status, a winner, and a new game. `battleship-status-history`
then checks active-player/status updates and a history of actor, coordinate, and
hit/miss result without disclosing unshot opponent ships. `battleship-history-filter`
adds distinct filter behavior: all, hit, and miss filters show the matching
existing entries while preserving board, turn, fleet state, and ship privacy.

Run all predecessor behavior checks against the predecessor's retained hosted
deployment before each later feature, then against the candidate's new published
deployment afterward. A feature-specific check first uses the immutable
pre-feature snapshot together with its predecessor hosted evidence:

1. If the requested behavior is absent, the feature is eligible for a before/after
   observation. The same check must pass after the run.
2. If the predecessor already satisfies it, record
   `baseline-already-satisfies-feature`. This is not a product failure, but it is
   not evidence that the feature request caused a change.
3. If the behavior cannot be observed honestly before or after at the relevant
   hosted candidate, report `unverified`; do not infer it from source text,
   agent-generated tests, a local fixture, or a static server.

`previous-behavior-preserved` can pass only when the predecessor had a verified
hosted receipt, its hosted replay is green before the new run, and it is still
green afterward. Known prior failure, unavailable hosted route, or an incomplete
predecessor makes the dependent result blocked or unverified rather than
preserved.

## Incremental review

Every `feature` and `refine` step has `requires_incremental_review: true`. The
review compares the external snapshot and final product tree/Git evidence with
the behavior replay. It does not use arbitrary changed-line, changed-file, or
churn thresholds.

Mark `preserved-incrementally` only when the reachable predecessor application
and base-game flows remain present, predecessor behavior passes, the new
behavior is integrated into that application, and the feature reuses the same
Apps Script project while releasing the current candidate. Mark
`behavior-preserved-but-material-refactor` when behavior survives but the source
lineage is broad enough to require human review. Mark `replacement-or-regression`
when the old product or user flows disappear, a new parallel game is substituted,
history/tree evidence shows an unexplained replacement, or predecessor behavior
fails. Use `unverified` when the evidence cannot support a lineage conclusion.

This review judges product continuity, not whether a particular source file or
implementation technique was retained. A legitimate refactor is not automatically
wrong, and a small diff is not automatically incremental.

## Review ShipLoop itself after every run

Use [WORKFLOW-REVIEW.md](WORKFLOW-REVIEW.md) and the adjacent review template to
audit durable state and captured execution, including unsuccessful attempts.
A product pass or correlated callback sequence does not prove semantic adherence
to the SDLC. Keep this workflow review distinct from product grading and from
the observer's own capture defects.

## Future holdout, not scheduled

Keep Connect Four outside `scenarios.json` and do not run or score it in the
initial pilot. A future untouched holdout can begin with this literal request:

`/shiploop Create a Google Apps Script web app for Connect Four in this repository. It should let two players alternate dropping pieces into columns, identify a four-in-a-row winner or draw, and allow a new game. Use the configured Google Apps Script deployment MCP to create, deploy, and publish a dedicated test application, then open its deployed web-app URL and interact with it to verify these behaviors. Retain the real MCP deployment receipt and identifiers; do not use a mock deployment.`

Reserve it for a later, preregistered replication after the nine-step corpus and
verifier are stable. Do not use it to replace a failed or blocked scheduled case.
