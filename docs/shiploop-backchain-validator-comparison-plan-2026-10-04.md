# ShipLoop plan: a Backchain graph check, and a comparison of what Backchain's loop adds

Execute: inline

Status: **plan v2.1: I1 and I2 are built (local commits, unreleased); I2b is next.** Revised after an independent adversarial review whose blockers I re-ran
against the run. Execute I1, I2 and I2b now (local commits; no release until the Luna run ends and the batch is
verified). Later iterations stop at the points named in section 5. Numbers marked *measured* come from the Luna max
battleship run on 1.16.1 (`/Users/dadleet/e2e-runs/20261003/v1161-battleship-luna`, one run, one model), so they
are exploratory. Governed by `test/shiploop_e2e/SPEC.md`. The iterations, with what we expect at each and the
reasons expectations were revised, are on the run review page (https://claude.ai/artifact/BFc6JGjLhENVJ9shRAA2iA,
private); this file is the durable copy. Expectation ids (B1 every pass earns its time, B2 a script verifies the
graph, B3 the script uses the graph, B4 planning is not repeated for the same facts, B5 a closed plan is not
revised for visible gaps, P2 the script writes every loop contract, P5 evidence is trustworthy and in the repo) are
in `skills/shiploop-e2e-audit/run-review/defaults/expectations.json`. Action a02 is a script-written Backchain loop
contract; a05 is deciding what the plan graph is for.

## 1. Questions

1. **Check.** Should a ShipLoop script, not the model, check a Backchain candidate graph and write the receipt
   Backchain's own rules ask for? Anchors: S-5, S-9, S-12.
2. **Comparison.** Does Backchain's review loop earn its time against a one-shot elaborated plan that a script has
   checked? Anchors: S-9 and expectations B1, B4, B5.

The second answer decides D1, whether the script should require, offer or drop the loop at `plan`; D2, which finding
kinds a script should catch before a model is asked. A third question came from the owner: have the planning prompts
grown, or contain a mistake (Part C)? The exit rule (two clean passes, no pass cap) is S-10 and stays
unless the spec is amended first.

## 2. Evidence (measured, exploratory)

Per pass, from candidate digests and snapshots the loops left behind. The pre-loop plan candidate is recovered
byte-exact: the block embedded in `pass-reports/pass-01-audit-input.md`, plus a newline, hashes to the freeze-log
digest `9e321e3d`. The script kept no file copy.

| Loop | Pass | Min | What changed in the candidate | Findings | Clean streak after |
| --- | --- | --- | --- | --- | --- |
| plan | 1 | 11 | 14 of 20 steps edited, +5.8 KB, inputs 56 to 58 | F-1 wrong supplier direction, F-2 API concurrency obligation, F-3 browser recovery requirement | 0 |
| plan | 2 | 15 | confirm clause of S2 (inspect to execute), +0 B | F-4 | 0 |
| plan | 3 | 26 | confirm clause of S4, +198 B | F-5 | 0 |
| plan | 4 | 18 | confirm clause of S11, +224 B | F-6 | 0 |
| plan | 5 | 17 | nothing (digest `3853b978` before and after) | F-7, a stale label in Backchain's own metadata | 0 |
| plan | 6 | 12 | nothing | none | 1 |
| plan | 7 | 4 | nothing | none | 2 |
| step-plan | 1 | 42 | structure: discovered steps added (snapshot `6f971770`, 19 steps) | F-01 rejection tests and docstrings, F-02 style note | 0 |
| step-plan | 2 | 55 | structure: D3 added, 16 steps changed (`024b3dc3`) | F-03 README and local-skill fit, F-04 effort comparison | 0 |
| step-plan | 3 | 6 | nothing | none | 1 |
| step-plan | 4 | 4 | nothing | none | 2 |

- **Time.** At the 15:03Z snapshot (969 min in) the two Backchain stages took 384 min (40%), the loops' passes 210
  (22%); the rest is gathering, writing the result and Improve's mandatory review (44 and 24 min, three passes each).
- **F-7** did not reset the streak (it was 0 until pass 6). Its cost is the extra pass 7 (4 to 12 min) plus its repair.
- **The reference validator (`lib.js`) finds a defect the loop missed.** Packaged, the three plan candidates pass.
  Both step-plan candidates fail invariant 4: pass 1's repair added discovered step D1, which nothing consumes, and
  passes 2 to 4 and Improve accepted it. Raw, every candidate fails invariant 6 because Backchain keeps
  `parallel_groups: []`. So the check saves no plan-loop pass, but it catches a real structural defect.
- **Requirement-id coverage was tested and rejected:** 13 of 46 ids are mentioned, unchanged by the loop.
- **The step-plan loop is off-protocol.** Its caller packet requests plan/draft, but only the plan stage may
  (`BACKCHAIN_NATIVE_CALLS`); step-plan allows audit and revise. Treat its numbers as off-protocol data.
- **Backchain is optional and unchecked** (the packet says the host "may request" it). Luna ran two loops; the four
  Sonnet runs ran none (no Backchain scratch directory, no receipt; plan stage 0.5 to 1.1 min; Improve reviews 98 to
  439 bytes against 2.3 KB on Luna).
- **Effort confounds model:** Sonnet's battleship run took about 19 min; Luna's passed 16 hours. Every arm below holds
  model and effort fixed.

## 3. Part A: the graph check

### 3.1 Decision: a ShipLoop-owned Python port

The seven invariants live in the Backchain checkout (`/Users/dadleet/src/backchain/harness/lib.js`:
`validateStructure` :1155, `computeParallelGroups` :259, `completionStatus` :1356, `packagePlan` :1083; the stored-group
check is at :1321 to :1329). The marketplace install ships only the skill directory, so every run is `native-unvalidated`.

| Option | Verdict |
| --- | --- |
| Python port in `skills/shiploop/scripts/shiploop_backchain_graph.py` | **Recommended.** ShipLoop is Python; no new dependency on every plan stage; directly testable |
| Call `lib.js` through `node` | Rejected: plan stages would need Node (only the parallel chain does today) |
| Vendor a trimmed `lib.js` | Rejected: carries harness code and still needs `node` |
| Ship it in `skills/backchain/scripts` | Deferred: changes Backchain from prompt-only and its documented layout |

Port rules, from what the review found in `lib.js`:
- **The arbiter is `lib.js` plus a recorded corpus, not SKILL.md alone.** SKILL.md's invariant 4 is strict; `lib.js`
  exempts a discovered step whose produces satisfy a declared goal need or are a substring of the goal sentence (the
  code does this although its own comment says goal-sentence matching does not work), and has circular-bookkeeping rules.
- **Validate a packaged clone** (recompute `parallel_groups` first); port `computeParallelGroups` and the packaged clone of `packagePlan`, not the rest of it.
- **Be deterministic:** reproduce JavaScript insertion order (group members, the reported cycle), never sorted sets, because the verdict text depends on it; use an explicit ECMAScript whitespace class, because Python's `\s` and `strip`
  differ from JS on `\x1c`-`\x1f`, `\x85` and U+FEFF.
- **Keep the copies honest inside skill-craft CI:** commit a recorded corpus (the checkout's structural good and bad
  fixtures and the Luna candidates, with the JS verdict for each packaged plan and its provenance); the port must
  reproduce it. Refresh it from the checkout whenever `lib.js` changes. A live parity run also stays in the checkout.

### 3.2 First increment (I1, I2): record only

- `shiploop backchain-check --candidate PATH`: packaged clone, seven invariants, completion status, advisory
  unconfirmed produces. It writes an immutable snapshot of the bytes checked and a receipt (schema
  `shiploop-backchain-check/v1`: candidate sha256, `ok`, failures with invariant numbers, completion, groups, counts)
  under `run/backchain/<action>/`. Exit 0 valid, 1 invalid structure, 3 could not run (lint's convention).
- Two packet additions, in producer Backchain routes only (not while Improve is pending): a 131-byte guidance line
  (size pinned by a test) and the navigator's printed command, which carries `--run-dir RUN` because walking up from
  the working directory never finds workspace runs. The guidance: run the check after each revision; a failing check is a finding for the
  loop; cite the receipt in `evidence_refs`. The run review exporter's loop ledger reads the receipts. Nothing is refused.

### 3.3 Deferred: a refusal gate

A refusal at `complete` arrives after the loop has converged: the step-plan fix for D1 would cost a re-loop (about
107 + 24 min on Luna), and the cheapest fix a model can make is to relabel D1 as a seed, which games the check. The
right place is inside the loop: once a script writes the loop contract (a02), the check is an exit condition. If a
gate returns earlier, it must: look only at cited files under `run/`; prefer the digest the cited loop receipt names
(newest-by-mtime would pick the last review snapshot, and the run holds eight Backchain-shaped files); detect the
one-level `{plan, convergence}` wrapper; ignore fixture directories (the checkout's `structural/bad` holds
intentionally invalid files); re-run at `improve-complete`; and never trust a receipt file.

### 3.4 Tests (hermetic unless noted)

1. One minimal violating graph per invariant, each valid after the fix; both invariant-4 exemptions (a declared goal
   need, and a produce that is a substring of the goal sentence).
2. The deciding fixtures: pre-loop, after-pass-1 and final plan candidates (ok packaged) and both step-plan candidates
   (fail invariant 4, D1), plus the raw-versus-packaged invariant-6 case and the four stored-group fixtures that pass
   only once packaged (their verdicts record the raw result too).
3. The recorded corpus reproduced exactly; whitespace edge cases; identical output across runs and hash seeds.
4. CLI exit codes 0, 1, 3; receipts and snapshots idempotent; no run state touched; guidance line size pinned; the
   printed command appears in producer packets only.
5. Parity in the Backchain checkout on every fixture and single-edit mutations; register the new suite in
   `test/suite_catalog.py`.

### 3.5 Not in scope

A script-written loop contract (a02) and per-pass snapshots; using `parallel_groups` to open work items (a05);
semantic need-to-produce matching.

## 4. Part B: the comparison

**Track 0, the trace (free).** Receipts and snapshots give every future loop a per-pass record. Stage minutes come from
accept timestamps; another session's analysis (`docs/shiploop-graph-engineering-comparison-2026-10-04.md`, item A2)
builds that reader, so build it once, there.

**Track 1, from the planted draft.** The casebook's 19 `expect.A.json` files (7 graded by an LLM judge, the rest
deterministic) score a fixed planted draft (`sources.draft`) and name its step ids, so arms start from that draft, not
from the generator.

| Arm | What runs |
| --- | --- |
| A | the packaged planted draft |
| B | dependency review and elaborator on the draft, then the check |
| C | B plus the Until Loop to two consecutive trivial reviews (needs a runner; built only after the pilot) |

- **Cases:** the six held-out fixtures' cases, opened at a declared decision point; each burn is recorded
  (`docs/holdout.md`). Git cannot show which cases informed a prompt change, so the earlier "choose by git evidence"
  does not work.
- **Rule:** register a new decision rule in the checkout before any run. The existing preregistration was written for
  raw-prompt eval cases scored by a pairwise judge, so reuse its form (structural gate, per-case regression gate, sign
  test over cases, ties excluded) and its thresholds as written, and state the reps. With fewer than five decisive cases
  nothing is significant: the result is UNDERPOWERED and no policy changes.
- **Model and mode:** the pilot runs on Sonnet 5.5 (exploration). A decision needs the owner's pairing (Grok 4.7
  medium executing, Opus 5.5 medium judging, one judge per round) and limits the policy to the model tested. The
  casebook is compatibility-native with no sources, while ShipLoop's loops are source-aware, so transfer is weak.
- **Scoring:** structural gate, then the case's checks; cost columns (minutes, tokens, passes); a failed arm counts as
  that arm's failure; a missing output is a failure, not a skip.

**Track 2, only if Track 1 shows lift.** ShipLoop A/B on `seat-reservations` at the plan stage only (arm L requests the
loop there; step-plan is off-protocol). A `variants` request sentence reaches the spec stage as part of the request, so
its effect on acceptance criteria is a known unknown. Three runs per arm is screening.

**Hypotheses.** H1: C beats B in a majority of decisive cases. H3: if H1 holds, Track 2 shows fewer failed
verifications or replans. H4: B beats A (shown on the casebook before). Whether later passes only refine confirmations
is an observation, not a hypothesis: the plan loop did, the step-plan loop did not.

| Result | Policy | Expectations revised |
| --- | --- | --- |
| UNDERPOWERED (fewer than five decisive) | No policy change; size a confirmatory run | none |
| C ties or loses to B | Offer the loop; the script decides when; no pass cap | B1, B4 |
| C beats B and Track 2 shows downstream benefit | Script-owned loop (a02); require it at plan above a measured size | B1, B3, B5 |
| C beats B in Track 1 only | Keep it optional; the lift did not reach real runs | B1, B5 |
| B ties A | Question Backchain at ShipLoop level; owner decision | B1 to B5 |

Priority is the repo's: a material quality difference first, then fewer tokens, then less time. Confounds: model and
effort (fixed); Improve's overlapping review (every arm gets it; review size is recorded because Sonnet's is thin);
compute (C spends more; an optional matched-compute arm D only if C beats B); saturation (if every arm passes, report
cost at equal outcome, never equivalence).

## 4b. Part C: trim the planning prompts (I2b, before the comparison)

Owner, 2026-10-04: planning stages look excessively large; is a planning prompt wrong, and keep the language concise
and aimed at meaningful change. *Measured* by an independent investigation, spot-checked against the repo:

- **Packets barely regressed.** Full producer packets grew 20 to 24% from 1.0.0 to 1.16.1 and the printed head shrank
  tenfold at 1.5.0. Sonnet got the same packets and planned in 4 minutes, so packet size is not what drives time.
- **One change inflated reading:** 1.16.0 (`db61a4a7`, a justified fix for stalled planning) prints the six-file Backchain and
  Until Loop list at all five Backchain stages (+86 KB, +40% required reading) though only `plan` may start a whole loop.
- **One packet invites a loop it forbids:** step-plan allows audit and, after a finding, repair or revise; Luna ran a
  whole plan/draft loop there: 136 of 592 planning minutes.
- **By cause (inferred from timestamps):** step-plan loop 23%, plan loop 22%, Improve review loops 31%, Improve opening
  files 6%, producer work 18%.
- **Contradicting per-pass rules:** `convergence.md` asks every pass for actual card reads and an all-42-lens screen,
  while `technical-lenses.md` says to screen once; review records are 36 to 39 KB, about 60% a copied lens screen.

Changes: cut ineffective text, keep every justified obligation.
1. **Print the loop text and resource list only at `plan`.** At the other four Backchain stages print the audit route,
   its one resource, and that a material finding may request repair or revise. About 553 words become 75; the Improve-owner
   variant 509 become 40 (`_backchain_guidance`, and the resource list in `shiploop_navigator.py`).
2. **Cut the repeated identity and digest instructions** (about 339 words to 80; `backchain-planning.md` 154 to 40).
   Keep: a `MISSING` resource blocks the route; no substitute install; record binding, candidate and receipt paths; a
   planned check is not execution evidence. Nothing machine-checks the rest.
3. **Review records point to the existing lens screen instead of copying it** (`convergence.md`,
   `convergence-review.prompt.md`; needs a Backchain change note). Whether to screen the lenses only once per loop is a
   rigor change (pass 3's T42 came from a re-screen), so it waits for the comparison.

Keep: the per-outcome confirmations (`backchain-planning.md` 80-98), `PLANNING_REVIEW_FOCUS`, the S-14 text, the state-budget
rule, and Improve after Backchain (it found a UI fix that seven Backchain passes missed). **Tests:** `graph-dry-run` word
and byte counts per stage pinned before and after; the step-plan packet no longer contains the resource list; guidance tests;
then one seeded Luna run at step-plan once the current run ends. Dropping a lens-screen rule, a bookkeeping line the model
actually acts on, or the audit route would weaken S-3 or S-6; each cut is checked against that.

## 5. Iterations and expectations

Each iteration states what we expect before it runs (I0's was written after looking, so it is exploratory). The
expectations below are the revised ones; the page keeps the original wording and the reason for each revision.
I1, I2 and I2b run now. I3 onward costs money and starts only after I2 and I2b pass.

| Iteration | What runs | We expect | If refuted | Touches |
| --- | --- | --- | --- | --- |
| **I0** Replay the Luna 1.16.1 loops from what the run kept | Luna max battleship, 1.16.1 (still running) (no model cost) | The first productive pass changes most of the graph and later passes mostly refine confirmation clauses. A structural check and a requirement-id check would not have found the loop's findings. *(written after looking; exploratory)* | n/a (done: partly) | B1, B2, B4 |
| **I1** Build the check and prove it against the reference verdicts | unit tests, recorded verdicts of the reference validator (no model cost) | A Python port of Backchain's seven invariants gives the same verdict as the reference validator on every recorded fixture (the structural good and bad corpus, and the Luna candidates, each packaged first): the same ok, failing invariant numbers and parallel groups. It passes the plan candidates and rejects both step-plan candidates on invariant 4 (discovered step D1 unconsumed), as the reference does. *(revised)* | A disagreement is settled against lib.js and the recorded corpus, not SKILL.md alone. The wrong side is fixed and the case joins the corpus. | B2 |
| **I2** Wire it in, record only: verb, packet lines, receipts, snapshots | hermetic tests, then the Sonnet hello gate (about $3 for the hello gate) | A run that never invokes the check behaves exactly as before: Sonnet hello passes; its plan packet gains the two Backchain-check lines and nothing else. A run that invokes it gets a receipt and a snapshot written by the script, and a failing check is reported to the model as a finding for the loop. Nothing is refused. *(revised)* | A false report on a valid candidate blocks the release; the verb stays, the packet line goes. | B2, P2, P5 |
| **I2b** Trim the planning prompts: step-plan route, repeated bookkeeping, copied lens screen | hermetic tests and graph-dry-run counts, then one seeded Luna run at step-plan (no model cost for the text; hours for the seeded run) | The step-plan packet no longer prints the six-file Backchain list or the loop text, and still offers the audit route and repair or revise after a material finding. At spec and step-plan the Backchain text falls from about 553 to about 75 words and the repeated identity and digest instructions at plan from about 339 to about 80. Review records point to the existing lens screen instead of copying it. Every justified obligation stays. A seeded Luna run at step-plan starts no whole plan/draft loop. | If the model still starts a whole loop at step-plan, the text is not the cause: revisit which route the packet makes reachable. | B1, B4, P3 |
| **I3** Pilot Track 1 from the planted draft: arms A and B | one held-out case, packaged draft versus dependency review and elaborator plus the check (measured by the pilot) | Arms A (the packaged planted draft) and B (dependency review and elaborator on that draft, then the check) run headless on one held-out case and are scored by its expect.A.json checks. The loop arm C waits until the runner can start the Until Loop. The pilot measures minutes, variance and whether B beats A, as the casebook showed. *(revised)* | If an arm cannot be run or scored headless, stop and report. Do not build the screen on a runner that cannot hold its own arms. | B1 |
| **I4** Screen A, B and C on the held-out cases, with a rule registered first | held-out casebook cases, three arms each (measured by the pilot) | C beats B in a majority of decisive held-out cases on the planted-defect checks. Otherwise, or when fewer than five cases are decisive, no policy changes and a confirmatory run is sized. *(revised)* | Skip I5. The loop stays optional and the script decides when to offer it. | B1, B4 |
| **I5** ShipLoop A/B at the plan stage on seat-reservations, only if I4 shows lift | Sonnet 5.5, three runs per arm, then one Luna pair for depth (about $21 a run on average) | With a loop requested at the plan stage only (the step-plan loop is off-protocol), there are fewer failed system-test verifications and no second work item. Cases that already pass without a loop do not change. *(revised)* | The lift stays at plan level. Keep the loop optional. | B1, B5 |
| **I6** Decide the loop policy, revise the expectations, release | the evidence from I0 to I5 (one release and one verification run) | The data supports one of three policies: require the loop at plan above a measured size, offer it, or drop it and rely on Improve. The exit rule (two clean passes, no pass cap) stays unless SPEC S-10 is amended first. B1 to B5 are revised to match, each with its reason. *(revised)* | - | B1, B2, B3, B4, B5 |

## 6. Change admission (SPEC)

**Anchor.** S-5, S-9, S-12; run evidence in section 2. **Non-regression.** The first increment adds a verb, a packet
line and files; no state field, refusal, loop contract or exit rule changes (S-10 untouched). **Evidence.** The tests in
3.4, the Sonnet hello gate, and the next looped Luna run.

| Scenario | Disposition |
| --- | --- |
| The port disagrees with the reference | Recorded corpus in CI plus live parity; settled against `lib.js`. Mitigated |
| The model ignores the packet line | Accepted: Backchain is optional; the harness flags loops with no receipt |
| A failing check invites relabelling (D1 as a seed) | No refusal now; the check becomes an exit condition with a script-owned contract (a02). Accepted |
| Packet text grows | One line, Backchain routes only, size pinned. Mitigated |
| Another host or platform breaks | Python stdlib, JSON only. Mitigated |
| A trim removes text the model acts on | Each cut is classified (changes behaviour, ineffective, justified); justified obligations are listed and kept; word counts and the audit route are pinned. Mitigated |
| The seeded step-plan run proves little (synthetic spec) | It tests only whether the model starts a whole loop; accepted |
| Saved runs, tests or catalogs pin the verb list | Additive verb; update the tables and tests that enumerate verbs. Mitigated |
| The ledger is gamed by hand-set verdicts | Derive from digests and receipts where kept; hand verdicts stay interim. Mitigated |
| The comparison costs more than it informs | Pilot first with a stop rule; Track 2 only if Track 1 shows lift. Mitigated |
| "More inference" mistaken for "better planning" | Cost columns; optional matched-compute arm. Mitigated |
| Held-out cases are burned | Declared decision point; each burn recorded. Mitigated |
| Everything passes (saturation) | Report cost at equal outcome. Accepted |
| Overlap with the other session's document | Share its A2 reader; do not touch `baseline_row()`. Mitigated |

## 7. Unknowns

- **U1.** Does a headless host run the Until Loop on request for arm C? Sonnet never started one inside ShipLoop.
  *Probe in I3, before building the runner.*
- **U2.** How the seven LLM-graded casebook cases score without an LLM judge. *Decide in I3.*
- **U3.** Which cases the six held-out fixtures belong to. *Read the manifest before I3.*
- **U4.** Whether a `variants` sentence changes the spec stage's acceptance criteria. *Probe before Track 2.*

## 8. Rollback

Revert the commits: the verb, packet line and metrics block are additive. Receipts and snapshots under `run/backchain/`
are ignorable files.
