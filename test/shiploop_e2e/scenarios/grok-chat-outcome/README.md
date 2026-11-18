# Grok chat outcome scenario — operator preparation

`grok-chat-outcome` is registered as an opt-in discovery case. The catalog pins the exact UTF-8 builder prompt, including its Codex skill invocation. Preparation is **PREPARED**, live launch is **BLOCKED**, the evaluator is **UNQUALIFIED**, and product acceptance is **NOT_RUN**.

From the repository root, `python3 -B test/shiploop_e2e/run.py --case grok-chat-outcome --preflight-only` reports the launch blockers and exits before setting up a host or touching the target.

## Keep the delivery boundary narrow

| Material | Destination and purpose |
| --- | --- |
| `BUILDER_PROMPT.md` | The customer request; freeze its exact literal bytes for a future independent create attempt. |
| Resolved environment/authority binding | Minimal nonsecret launch input identifying the authorized environment and permitted scope. |
| This README, `OUTCOME_REVIEW.md`, `READINESS.json` | Operator evidence and gates only; do not send to the builder. |
| Historical fixed contracts and checks | Retained history; do not seed them into builder inputs or helper tools. |

A future hosted attempt must use the frozen brief and minimal resolved binding through the installed ShipLoop. Record the install identity. Before each fresh launch, resolve the latest available SOL and Astra releases from the current official catalog. Record the exact model IDs and the actual parent and default-child launch controls. Use SOL at medium effort for builder and test sessions and Astra at high effort for independent review. `gpt-6.2-sol` and `gpt-6.2-astra` are observed examples. Preserve the recorded identities of prior and frozen runs.

The catalog entry contains zero fixed checks and provides no platform wrappers or helper tools. It is outside the live suites and closed-loop allowlist. Its `discovery_only` marker excludes it from strict `promotion/5` registration. The runner refuses seed shortcuts and planning-review injection for pre-invoked prompts. Hosted lifecycle, authority binding and independent observation still need integration. [Case catalog](../../cases.json) · [Runner](../../run.py)

## Resolve authority before any builder launch

Keep this gate outside the product brief. Resolve the canonical org, user and target; explicit setup, deployment and synthetic-data scope; and conflicts with existing work. Never rely on ambient defaults. Establish a test-owned inventory across older prefixes, exact job and late-deployment containment and quiescence, and owned teardown. Existing gym cleanup does not cover jobs or late deployments.

Require a verified startup reset once per independent create attempt, including an observed empty no-op when nothing is present. Do not reset on every test, Proof or repair: preserve the candidate within that attempt. After success, failure or interruption, clean up only verified owned artifacts. Preserve unrelated applications and data, User accounts, other active work, existing keys and historical evidence.

Resolve the current provider's nonsecret reference, endpoint and model; operator-only secret handling and principal grants; a safe browser/authentication route; independent read-only observation capability; and observation deadlines. Missing values block dependent external actions. Product setup can be assessed after construction; pre-builder authority does not require an application that does not yet exist. These gates describe prerequisites, not executed setup, reset, cleanup or readiness.

## Preserve evidence boundaries

The runner treats `READY` with an empty blocker list as a trusted operator assertion. The operator owns verification of those prerequisites. Before launch inspect the entire builder-visible input for inherited fixed checks, labels or schemas, including seeded files, helper tools and the effective host environment. Codex can inherit `PATH` and `E2E_*` from its parent. Use `OUTCOME_REVIEW.md` independently after construction. Do not inherit preparation verdicts, rendered-document claims or acceptance from older packets.

The full messages of `fc4ac19952cfc73c5361378a8dd5bee97b36137b`, `cf211dab4409e0452235138a6b72dce6ac07655d` and `f87061c07caa5901e0c35244dce62d52a83dfcf0` informed the preparation/live distinction, independent observation and owned lifecycle gates. Their implementation contracts are not builder requirements here. At initial packet commit `71fa298e44db73f6afa46217377ba0ea850de916`, the prompt was rendered and inspected at desktop width, and the outcome review at a 390px document width. The subsequent owner-directed Grok Bot reference clarification was checked as source against official material; those earlier renders and independent review do not cover the revised bytes. This README was checked as source; none of these checks renders or accepts an application.
