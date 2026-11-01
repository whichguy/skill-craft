# Evidence the Backchain 2026-11 change rests on

Source of every figure: skill-craft `docs/backchain-efficiency-journal-2026-11.md` (branch `backchain-eff-9aea18`)
and `docs/experiments/backchain-efficiency-20261101/audit.json`, which re-read the 36 retained runs of the
2026-10-16 study (`/Users/dadleet/src/backchain/docs/experiments/2026-10-16-backchain-full-workflow.md`).

## The 2026-10-16 study (prior evidence, not new runs)

- 6 synthetic cases x 3 repetitions x 2 arms; subject and blind grader gpt-6-astra medium through Codex CLI 0.163.0.
  Control Backchain 0.6.3; candidate "lean" (direct synthesis prompt 8.8 KB; generator 19 -> 6 KB; elaborator
  51 -> 17 KB; same Until Loop binding, lenses, confirmations, source and bounds rules).
- Both arms qualified 11/18 (qualification = mechanical workflow checks AND adjudicated blind semantic pass). Final
  adjudicated semantic pass: control 13/18, lean 14/18. Across the 5 jointly qualifying pairs the lean arm used
  21.2% fewer reported tokens (ratio of sums; median paired change -12.6%, uncached -8.8%) and 11.5% less summed
  wall time. Lean qualified lower in three case families (bounded repair 1/3 vs 2/3; external approval 1/3 vs 3/3;
  missing normative source 0/3 vs 2/3); its losses were all binding or transport failures. Adoption was deferred.
- An adversarial review then confirmed one hazard: direct synthesis can create edges that the add-only elaborator
  cannot later remove without separate repair authority.

## New readings of that study (this work, Round 0)

- Cost is instructions: a control run's commands name ~194 KB of Backchain files plus the Until Loop card and runtime
  document (38 KB then, 53 KB now); medians per control run 16.5 commands, 967,778 input tokens (84,170 uncached,
  91% cached), 7,507 output, 168 s.
- Every run wrote 5-16 (median 7) blocks of its own Python/Node bookkeeping code.
- 12 of the 14 disqualified runs include a bookkeeping error; 8 (4 per arm) have nothing else: `convergence.md` (8)
  or the Until Loop script (3) missing from the contract's bound resources, or the latest packet not retained (5).
  Their graders passed the plans' dependency logic and usability and failed the completion claims for that reason.
- One disqualification is a plan defect caused by the contract: the control's review found its elaborator's own
  null-origin inputs unjustified but kept them because "never remove an existing edge" also covered edges the run
  generated (`independent-inspection-scopes-current-r1`, review-01).
- Confirming reviews: 12 runs used the two-review gate; 11 ran a review after a trivial one; none changed anything
  (same candidate digest). Improve dropped its own confirming pass on 2026-10-20 for the same reason (owner: "the
  current criteria may iterate far too often without results").
- ShipLoop: on Luna xhigh the plan-stage Backchain work was 64 min (17% of planning); on Grok medium the Backchain
  loop was 2.7 min of a 22-min planning window. Backchain and Improve reviews both missed a plan gap (tests had no
  real module to load) that later cost a 166-min redo; the deterministic validator caught an orphan discovered step
  that later model passes and Improve had accepted.

## Owner decisions (2026-11-01)

- D1: by default the first trivial review completes (gate 1); `Backchain passes: one` unchanged (gate 0);
  `Backchain passes: converge` keeps two consecutive trivial reviews; ShipLoop's `converge` runs keep two through
  that marker.
- D2: adopt prompt changes only after a cohort (the six 2026-10-16 cases plus four blind held-out cases, 3 reps per
  arm, same subject and grader) decides by quality first, then tokens, then time (rubric-eval SPEC section 8).

## Mechanical results of the change (tests, no model runs)

- The validator moved from ShipLoop to Backchain's package: ShipLoop receipts byte-identical on all 95 inputs tried.
- `backchain.py export` agrees with the checkout's JS exporter on all 88 corpus plans (same verdict; identical graphs
  for the 33 exported); Plan Dispatcher's `validate-graph` accepts all 33.
- 22 toolkit tests, 10 of them full runs through the real Until Loop runtime with scripted assessments (each gate;
  a changed plan is never trivial; refused records; inherited vs generated edges; tamper detection; honest stop).
- A fresh request's full reads fall from 231,784 to 140,574 bytes before the lean prompts (−39.4%).
- Of 207 rendered ShipLoop Backchain texts (every stage, delegation and mode), only the 7 `converge` ones changed.
- Not yet measured: any live model run with the toolkit (the pilot and cohort follow this review).
