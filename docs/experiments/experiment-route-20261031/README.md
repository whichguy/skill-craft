# Plan-time experiments in ShipLoop planning (2026-10-31)

The owner, 2026-10-31: "I was noticing that sometimes planning out and implementing experiments, or adding extended
tests on existing code base can clarify conditions, state & system behavior. Not sure if we would introduce that into a
prompt or a specific step enforced by scripts", then "Do all" to this plan: a no-tool routing test, a required experiment
route built as a candidate, existing-code cases where reading misleads, and a live A/B on the Codex harness (Terra 6.1
high, all tools, 6 runs per side).

Prior evidence: plan-time experiments are offered and unused (docs/shiploop-planning-pipeline-2026-10-30.md F7: no live
run records a `probed` assumption; the 2026-09-21 pilot found no consequential gain); in the four live runs of
2026-10-31 that stored an intake ledger, 1 of 10 questions took the `experiment` route
(../question-record-20261031/scores-e2e-ab.json and the runs under ~/e2e-runs-qr/20261031).

## E12. Corpus: do runs miss runtime facts or break existing behaviour? (run first; objective, not pre-registered)

Every saved product of the node-tickets cases, copied and started outside the run (corpus/):

| Probe | What it asks | Result |
|---|---|---|
| `probe.mjs` on the base | 36 claims of docs/api.md and docs/operations.md against the running base | 35 hold; 1 drift: filters OR (`matchesFilters` uses `some`) where the docs say they combine |
| `combine.mjs` | do the product's filters combine (status+priority, assignee+status)? | AND in 17 of 18 completed products; OR in 1 (bf-ds-r1, DeepSeek flash, which never implemented assignment) |
| `restart.mjs` | does a ticket keep its assignee across a SIGTERM restart (DATA_FILE)? | 17 of 17 products that implement assignment |
| `escalate.mjs` | escalated at most once across a SIGTERM and a SIGKILL restart? | 5 of 5 completed escalation products; 2 interrupted runs never built it |
| `probe.mjs` on each product, diffed with the base | any documented claim broken, or any of 7 undocumented behaviours changed? | 0 of 17 products |

And the harness's own held-out acceptance (result.json `quality.acceptance`) over every saved brownfield run: 26 of 26
completed runs pass every check (ticket-assignment 10 runs x 18 checks, ticket-escalation 5 x 14, user-listing 11 x 11),
DeepSeek flash and Codex Terra, both arms of the 2026-10-31 A/B. Those checks include the latent facts the cases were
built to hide (filters that combine, a dropped partial last page, old data files, state across restarts, escalation at
most once).

Reading: on the cases we have, runs already find the system's runtime facts and keep its behaviour. A required
experiment step or characterization tests would bind nothing there; the live A/B needs a case whose deciding fact only
running settles.

## XR. Does one sentence move runtime questions to the `experiment` route? (pre-registered)

- Subject: Codex `gpt-6.1-terra` at high (run.py: throwaway CODEX_HOME, read-only, ephemeral, no tools in the frame).
- Prompts (build_routing.py): X1's intake exercise frame, unchanged, with ShipLoop's shipped intake duty (main 02a215e9).
  Arm A: as shipped. Arm B: the `experiment` route reads "experiment: only running something answers it, as for how fast
  or how much the existing system handles, what it keeps across a restart or a concurrent change, and what it really
  does where its code, documents and tests disagree;". Nothing else differs.
- Requests: the live prompts of user-listing, ticket-assignment, ticket-escalation, and ticket-import (XI). 4 samples per
  case and arm: 32 calls.
- Judge (Opus, one call per case and sample pair; arms shuffled and relabelled; the judge sees each question's id,
  category, text and `changes`, never its route): each question is RUNTIME when settling it reliably needs the existing
  system observed while it runs (how fast or how much it handles, what it keeps across a restart, a crash or a
  concurrent change, the exact output, order or shape it produces, or which of conflicting sources holds), else
  NOT_RUNTIME (intent or policy the request leaves open, structure or conventions read from the code, delivery, a
  person's decision).
- M1 per output: RUNTIME questions routed `experiment`. M2: NOT_RUNTIME questions routed `experiment`. Ledger validity:
  ShipLoop's own shape check (`shiploop_navigator._check_intake_questions`).
- Rule: the sentence moves routing iff mean M1 rises by at least 1.0 from A to B with an exact one-sided permutation
  p < 0.05 over the 16 + 16 outputs, mean M2 in B is at most A's + 0.5, and B has at most one more invalid ledger than A.
  Otherwise the candidate keeps the shipped route text.

### XR result (scores-routing.json; 32 of 32 outputs parsed, 8 judge calls, every question id classed)

| Arm | RUNTIME questions per output | of them routed `experiment` (M1) | share routed | NOT_RUNTIME routed `experiment` (M2) | questions per output | invalid ledgers |
|---|---|---|---|---|---|---|
| A (shipped) | 2.56 | 0.25 | 10% | 0.25 | 11.75 | 0 |
| B (route sentence) | 3.19 | 1.06 | 33% | 0.00 | 12.0 | 0 |

- The rise in M1 is 0.81 per output, exact one-sided p = 0.0035; M2 falls by 0.25; no invalid ledger. The rule asks for a rise
  of at least 1.0: **not met**, so the candidate keeps the shipped route text. The sentence works in the direction meant and
  over-routes nothing, but two-thirds of the questions the judge calls RUNTIME still take `inspect`.
- Per case, M1 A -> B: ticket-assignment 0 -> 0.75, ticket-escalation 0 -> 1.5, ticket-import 0.75 -> 2.0, user-listing
  0.25 -> 0.
- Seen on the way: on ticket-import the shipped intake already raises the deciding facts (request-size limits, per-ticket
  storage I/O against the 10-second bound, atomicity) in every sample, and routes the timing question to `experiment` in all
  four arm-A samples; concurrency and restart questions mostly take `inspect`.

## XI. A case whose deciding facts only running settles, and a futility-gated live A/B (pre-registered)

- Case `ticket-import` on fixtures/node-tickets, unchanged (pin 5652a97375d0). Request: ticket-import-prompt.txt
  (POST /tickets/import of up to 5000 tickets, all or none, answered within 10 seconds). Facts it depends on and does not
  name, each in the base: requests over MAX_BODY_BYTES (64 KiB by default; src/config.js, README) are refused, so a
  5000-item body is refused unless the route accepts it; the data file is rewritten whole after every change
  (docs/operations.md, decision 8), so creating 5000 tickets one by one takes minutes; a create audits and enqueues a
  notification, which an all-or-nothing import must not leave behind; numbers are given out in order.
- Held-out acceptance (checks/ticket_import_accept.py) calibrated per SPEC ("A brownfield case") before any live run:
  base fails every fail-to-pass check and passes the pass-to-pass ones; a reference passes all; an alternative passes
  all; each targeted defect fails exactly its checks.
- Runner: `run.py --case ticket-import --host codex --model gpt-6.1-terra --effort high --source checkout --timeout
  7200`, hooks on, output ~/e2e-runs-xr/20261031/<arm>-ticket-import-s<n>, one lane (port 4180).
- A run passes when every acceptance check passes.
- Stage 1, futility: three arm-A runs (ShipLoop at main, its own run.py, the case added). If all three pass, stop: with
  A passing at least 3 of 6, even 6 of 6 for B gives p >= 0.09, so the adoption rule below cannot be met. Verdict: no
  measured headroom for a required experiment route on this case.
- Stage 2, only when an A run fails an acceptance check: build the candidate (XR's route text if XR adopts it; a
  research duty and a research gate: each intake question routed `experiment` is probed, with its command and saved
  output, or left open with the item that settles it), run 3 more A and 6 B, interleaved. Adopt iff B's pass rate beats
  A's with an exact one-sided permutation p < 0.05 (6 vs 6), no B run fails a pass-to-pass check A passes, and the probe
  commands appear in the host event stream of at least 4 of the 6 B runs. Secondary: minutes, send-backs.
- Amendment, 2026-10-31 13:45, after A s1 and before any arm-B work: A s1 delivered nothing. ShipLoop paused at
  step-plan: its plan had recorded "Persisted 5000-ticket response can meet 10 seconds" as an open assumption due at W1
  (reason "Candidate does not exist"), the step-plan gate asked for an expectation checked on the unchanged base, and the
  model judged that impossible and stopped. Intake had routed Q2 ("What limits and costs affect a 5000-ticket
  request?") to `experiment`; nothing probed it. No acceptance was observed, so A s1 is a non-pass; the pre-registration
  named neither this nor a run that delivers nothing. Read as written in spirit: the futility stop needs three passes,
  which can no longer happen, so Stage 2 opens, with the candidate as registered (the shipped route text, since XR did
  not adopt the sentence; a research duty and a research gate for each intake question routed `experiment`). The
  adoption rule is unchanged. A run that delivers nothing counts as a non-pass in either arm.
- The live hold: other sessions record an owner hold on new live E2E cycles (d9fefb11, 488ffbd9, 8975a5bc). The owner's
  go for this live work came in this session ("Do all", to a plan naming a live A/B of 6 runs per side); the runs are
  confined to this gated design.

## FX. Settling an open item through an executed criterion (pre-registered 2026-10-31 14:40, before any FX run)

- Why: replaying the 205 traced runs, the step-plan rule that turns each open plan assumption due at an item into an
  expectation (checked on the unchanged base) refused in 15. In 4 the assumption was about what exists and the
  expectation was a real experiment; in 11 it was about what the item builds or deploys, and 10 were met with a check
  that settled nothing while 1 (XI A s1) stopped. The fix (branch fix/assumption-settled-by-criterion-ee94d1, fd8f9239)
  lets an executed criterion cite the item in `from`, offers that row in the template, and keeps the expectation route.
- Arms on ticket-import, Codex `gpt-6.1-terra` at high, all tools, `--source checkout`, one lane: P = ShipLoop as on main
  7f565994 plus the case (exp/xi-case-on-main, 7167c284); F = P plus the fix (exp/xi-fix-on-main, aa99fdff). Four runs
  each, in the order P F F P P F F P, after XI's own runs end; outputs ~/e2e-runs-xr/20261031/<P|F>-ticket-import-s<n>.
- Measures per run: every held-out check passes; ShipLoop's end state; each open plan assumption due at an item and the
  route its step plan cites it by (criterion, expectation, none); this rule's refusals in the trace; minutes.
- Rule: adopt the fix iff (1) F passes at least as many runs as P, (2) in the F runs whose plan leaves an item open, the
  step plan cites it through a criterion in at least 3 (with fewer than 2 such runs the route is not exercised live,
  and adoption rests on the replay and (1)), and (3) the quick tier passes on the fix. This is a no-harm and
  mechanism test, not a superiority test: a stall like A s1 is rare, so 4 runs a side cannot show its rate falling.
- Note, 14:30, before any FX run: the fix's quick tier failed one suite (shiploop-package-integrity: the new paragraph took
  references/inner-loop.md over its 8,192-byte bound). The paragraph became a reworded sentence (dcf98cb6, no script
  change), so F is rebuilt at 52feffd0 = aa99fdff + dcf98cb6, and FX waits for the rerun tier to pass.

## XI interim and FX status (2026-10-31 15:15)

| Arm | Runs scored | Pass every held-out check | Stopped in planning | Research probes recorded |
|---|---|---|---|---|
| A, ShipLoop as on main 02a215e9 | 5 | 3 (s2, s3, s5) | 2 (s1, s4: the open timing assumption had to become an expectation checked on the unchanged base) | n/a |
| B, A plus research probes | 5 | 5 | 0 | 0 of 5 (s1, s2, s5 recorded the question open, "the endpoint does not exist yet"; s3, s4 routed nothing to experiment) |

- Decided before its last runs: XI does not adopt the candidate. With A at 3 passes, even 6 of 6 for B gives p >= 0.09,
  and the probe clause (probe commands in the event stream of at least 4 of 6 B runs) has 0 so far. B's clean record
  does not come from probing; the likelier reading is that B's runs met the same rule with a check of their own (an
  expectation citing the open item, 5 of 5) where two A runs stopped.
- B s6 was cut off at 15:11 when the operating Claude Code session restarted and its background jobs ended (the harness
  died mid-run; its orphaned progress viewer was stopped). It is an infrastructure stop, not a subject result: excluded,
  and replaced by B s7 from the same candidate checkout. A s6 follows, then FX.
- Fix 1 (an open item settled by an executed criterion) is published in skill-craft 2.27.0 / ShipLoop 1.26.0 at the
  owner's word ("Merge to main and publish") before FX ran, with a No-E2E-Round trailer on its two commits; FX is its live
  check. Release eeb433d5, published 15:13 over main 2bfe9334 after CI passed there.

