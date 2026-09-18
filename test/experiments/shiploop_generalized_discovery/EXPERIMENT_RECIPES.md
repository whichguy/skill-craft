# Bounded discovery validation recipes

Use these optional experiments to resolve a specific unknown in generic
discovery. They are examples for the experiment apparatus, not mandatory steps
in the installed skill. Start with existing access and procedures; acquire a new
capability only when a named observation cannot otherwise be made.

## Freeze the question and its stopping rule

Record the affected flow, the claim being tested, the smallest discriminating
observation, target identity, permitted effects, and an overall deadline with
cleanup/reporting reserve. Keep source inspection, local execution, authenticated
reads, hosted execution, and deployment as separate evidence levels. Stop when
the question is resolved, a prerequisite is missing, or the allowance expires.

For a prompt comparison, freeze the exact baseline, candidate, fixtures, input
hashes, review criteria, and adoption rule before launching contexts. Compare
consequential correct findings, including failures and missing connections. A
passing transport/oracle check does not mean the prompt is better. Replicate only
when the preregistered primary outcome and regression guardrails pass.

## Acquire a task-local reader and procedure

The opt-in `acquisition_probe.py` exercises one pinned public filesystem MCP
server and one pinned published skill against synthetic/local files. It requires
Node/npm, Git, and network access. It never runs as part of CI.

```sh
python3 test/experiments/shiploop_generalized_discovery/acquisition_probe.py \
  --out /absolute/new-access-evidence-directory
```

Use a new evidence directory; refusal to overwrite must happen before acquisition.
Keep exact version/commit provenance, inspected installation behavior, effective
tool catalog, allowed read, outside-scope refusal, applied skill procedure, and
cleanup results. A catalog entry is not a working connection; reading a skill
card is not evidence of autonomous selection or improved model performance.
This particular recipe applies static HTML reconnaissance, not browser automation.

Treat the pinned registry digest as provenance unless the acquired artifact is
independently checked against it. Retain any missing lockfile-integrity field as
missing; hashes of installed files do not fill that verification gap. The
September measurement established a tested filesystem scope, not arbitrary
service authorization or a reason to install this server permanently.

## Trace an existing application through an authorized route

Resolve the known project/tenant, active binding, read-only operation, and current
source/configuration before following a client/service path. Inspect selection
points: entrypoint, component import or routing, transport, identity, state owner,
and consumer result. Follow only dependencies needed to answer the frozen question.

For an existing hosted target, preserve the exact boundary of any refusal. A
local reader rejecting a mismatched target pin is different from the remote
service rejecting authorization. Use a correctly bound existing authorized
reader when available; otherwise record the missing prerequisite. Do not turn
stale deployment records or an already-open page into a fresh hosted action trace.

A minimal real transport experiment can load an existing application whose
initialization performs a read, then correlate that client action with the service
receipt and rendered result. For example, the September loopback fixture produced
`GET /api/state` → HTTP 200/version 1 → rendered version 1. Its source was frozen,
no write route ran, and its server/tab were cleaned up. This is local transport
evidence; it does not prove the Apps Script or Salesforce route behaves the same.

## Bound an independent subprocess review

Give each reviewer only the blinded reports and relevant evidence. Run it through
the existing host CLI using `review_runner.py`; choose the command explicitly.

```sh
python3 test/experiments/shiploop_generalized_discovery/review_runner.py \
  --cwd /absolute/review-workspace \
  --output-dir /absolute/new-review-evidence-directory \
  --timeout-seconds 300 \
  --hard-deadline-epoch "$study_closeout_epoch" \
  --stdin-file /absolute/frozen-review-input.md \
  -- /absolute/host-cli its-explicit-review-arguments
```

The deadline comes from the original study, not a reset clock. Account for all
simultaneous worker/reviewer processes and leave time for group cleanup. The
helper captures raw streams and failure receipts; independently validate the
verdict's structure, evidence, and adoption criteria. Its POSIX process-group
cleanup does not cover deliberately detached processes or native host agents.

## Carry evidence through the delivery work

| Stage | Reuse the observation | Reopen only when |
| --- | --- | --- |
| Environment investigation | Target, identity, effective access, selected libraries and routes | A needed target/permission/binding is unresolved |
| Inner loop | Existing components and smallest executable contract checks | Implementation changes a boundary or invalidates a premise |
| Outer loop | Consumer, deployment identity, and service receipts | Local evidence cannot establish the required hosted result |
| Test expansion | Actual errors, denial cases, stale state, ordering, cleanup | A material untested behavior remains |

Keep all eight discovery areas visible: message passing, client connections,
service authentication, design, client libraries, storage, caching, and security.
Use justified N/A or unresolved entries rather than inventing a component to fill
a category. A new MCP server or skill is conditional in every stage.
