# Backchain's recorded value evidence, July to November 2026

A read-only research agent (Claude Sonnet, 2026-11-15) compiled this from the private harness `backchain/` (its git
history, `docs/`, `results/` summaries) and skill-craft `origin/main` (`skills/backchain` history, the efficiency
journal, `docs/experiments/backchain-*`, `test/shiploop_e2e/LEARNINGS.md`). The main session checked the claims the
Round 15 verdict rests on; its notes are in the last section, and they correct three readings of the report.
Local account paths are shortened to `backchain/` (the private harness checkout) and `skill-craft/`.

## A. Original premise and intent

- `3d2f486e` (backchain, 2026-07-12, "feat: initial Backchain build"): a forward-drafted plan's steps have real needs
  that no dependency edge expresses. A backward pass infers each step's needs, wires each to an earlier satisfying step,
  inserts new steps to close genuine gaps, and never closes a cycle silently. It is checked by a deterministic
  structural validator (6 invariants then, 7 now) and an LLM rubric judge.
- Scope changes since then, with the reason each gives:
  - `10efadae` / `40a63163` (2026-09-25): the skill source moves to skill-craft; `backchain/` becomes the research and
    evaluation harness.
  - `2c301dca` (2026-09-27): exported graphs must pass Plan Dispatcher's `validate-graph`, a downstream contract that
    did not exist at the start.
  - `b655b804`, `26d47855`, `a0178072` (2026-11-01): a scripted caller contract (`prepare`, `freeze`, `record`,
    `verify`, `finish`) replaces a model-built binding, after an adversarial review showed the model-built one could be
    spoofed (findings F1-F5, F8).
  - Owner decision D1 (journal Rounds 0 and 2, 2026-11-01): the review gate stops at the first trivial review instead
    of always requiring two.
  - `27fa9c92` (2026-11-15): ShipLoop's default calls no Backchain child; Backchain becomes opt-in.

## B. Backchain against no Backchain

| Date | Models | N | Metric | Result | Evidence |
|---|---|---|---|---|---|
| 2026-07-21, repeated 07-23 | Sonnet; 2 curated planted-gap cases (oauth-seeded-user, two-hop-ladder) | 2 | regex intent oracle | 2 of 2 "LIFT" | `backchain/results/casebook-ab-backchain-20260721T191829Z/SUMMARY.md`; `phase2-ab-backchain-20260723T221857Z` |
| 2026-07-25 | Sonnet unaided, 5 cases, n = 1 each, single rater | 5 | expectations met | 2 cases "LOW" (near-perfect unaided), 2 "RETAINED" (real gaps, including a security downgrade gap), 1 mixed | `backchain/docs/experiments/phase0b-discriminating-power-2026-07-25.md` ("SCREENING ONLY") |
| 2026-07-26 | Sonnet implementer, 2 backlog tasks, with plan vs without | 2 | acceptance criteria and traceability | both arms passed; the with-plan arm did strictly more, traced to plan steps; no cost column | `backchain/docs/experiments/plan-value-n2-2026-07-26.md` ("screening evidence, not a result") |
| 2026-11-15 | Grok 4.6 xhigh, Sol 6.1 medium, Sonnet 5.5 high; 10 cases × 2 arms | 30 pairs | blind Opus, 2 passes, δ = 5 | +0.7 [−0.6, +2.0]; +0.5 [−3.4, +4.8]; −0.2 [−1.3, +1.1]: no meaningful edge on all three | skill-craft `docs/experiments/backchain-value-20261115/RESULTS.md` (registration `b9393e61`, result `20ec94e2`) |

## C. Backchain version against version (cannot speak to B)

| Date | Comparison | N | Result |
|---|---|---|---|
| 2026-10-16 | 0.6.3 against a compressed "lean" variant, gpt-6-astra medium | 18 qualified pairs of 36 | equal qualification (11 of 18 each); lean −21.2% tokens, −11.5% time; adoption deferred |
| 2026-11-01 | 0.6.6 against the scripted-toolkit candidate (0.7.0) | 60 attempts | quality inconclusive (−1.19 [−8.85, +6.26]; +2.18 [−1.93, +7.49] after removing a grading artifact); candidate −48% tokens, −51% time; shipped on cost (D4) |

## D. Recorded catches

- The deterministic graph check, live, on a Luna 1.16.1 ShipLoop run (2026-10-04): both step-plan candidates fail
  invariant 4 for discovered step D1, which "Passes 2 to 4 and Improve accepted" (`LEARNINGS.md`, "Backchain graph
  check, I1 and I2" and the "Second correction" of the "Backchain ledger"). The clearest catch in the record, and it is
  the script, not the review loop.
- Improve, run after Backchain, "found a UI fix seven Backchain passes missed" (same ledger, "Justified, keep").
- The fresh route's question phase caught gaps in 4 of 15 pilot runs; in 3 of those the review loop caught them too
  (journal R10-8).
- The July screening: unaided Sonnet missed the downgrade risk and the rollback clock reset on a token-to-session
  migration (phase0b case 4), n = 1, single rater.
- A judge-falsification run (2026-07-25) caught 9 of 10 scoreable broken plans: evidence that the grading instrument
  works, not that Backchain does.

## E. Recorded harms

- Confirming reviews changed nothing in 0 of 11 (2026-10-16) and 0 of 7 more (2026-11-01): 0 of 18 (journal R9-9).
- A caller-bounds fix (Round 4, F3) itself refused a correct authorized repair (R6-3), corrected the same day
  (`b655b804`).
- The 2026-11-01 cohort's two largest "losses" came from graders penalizing a recomputed `parallel_groups` (R9-5), and
  orders-cancel-rpc's oracle rewarded a split the contract forbids (R10-3).
- Live cost: Backchain stages took 384 of 969 minutes (40%) of one Luna run at the snapshot, the loops' own passes 210
  minutes (22%) (`LEARNINGS.md`, "Backchain ledger", 2026-10-04, interim).
- NBQ (Next Best Questions, a separate feature) raised a false "seed drop" flag (`backchain/docs/nbq-value-campaign.md`).

## F. Cost

The 2026-11-15 study: Backchain used 10-15 times the processed tokens of the no-skill arm (medians Grok 2.56M against
171k, Sol 1.03M against 96k, Sonnet 1.03M against 100k) and 2.3-3.3 times the median wall time. In the 2026-11-01
cohort, 95.2% of the saving between Backchain versions was cached input (R10-10).

## G. Claims superseded, refuted or never tested

- A 45-trial pre-registered outcome campaign (does a Backchain plan change what gets built; `002d39b`, `ec7875d`, July
  2026) was designed with its harness scripts and never run; no results file exists. The only downstream evidence is
  the n = 2 screening above.
- "A fresh request's reads fall 39-66%" (journal Rounds 2-3) was superseded the same day (R10-9).
- "NBQ reliably improves hop-correct plans": not supported (`nbq-value-campaign.md`).
- "A validator would have found nothing" (2026-10-04) was superseded in the same entry once the real validator ran.
- ShipLoop's `converge` never reached its marker after 0.7.0 (R10-12); owner decision D-D ratified the behaviour.
- "Single-host operator-ready" (Phase 1, `backchain/docs/casebook-residuals.md`) rested on curated cases with no
  no-skill comparison and was never revisited after 2026-11-15.

## H. The agent's summary

The program grew rigorous (pre-registration, adversarial review, blind grading). Its most controlled test found no
planning-quality edge at 10-15 times the tokens. Every other comparison used curated planted-gap fixtures, compared
Backchain versions, or was self-labelled screening. The downstream question was registered in July and never run. The
clearest catch came from the deterministic script, and the confirming review found nothing in 18 of 18 tries. Largest
gaps: harder or longer planning, a cheaper single-pass path, the naming prime, and the never-reconciled "operator-ready"
claim. (The agent notes it did not open every experiment document, for example `track-b-tranche2-results`,
`skill-creator-pilot` and `source-aware-pilot`, which looked like mechanism or infrastructure checks.)

## Verification by the main session (2026-11-15)

Checked against the files:

- **B, July lift: corrected reading.** The control arm ran no model at all: `SUMMARY.md` says "Control packages the
  raw planted draft only (elaborator not run)". So "2 of 2 LIFT" shows that Backchain's elaborator fixes a gap planted
  in a fixed draft. It is not a comparison with a model planning without Backchain.
- **B, July screening: confirmed.** "SCREENING ONLY, n=1, single-rater"; cases 2, 3 and 5 rated LOW. Case 5 (a widget
  storage migration) got right the very clock-restart requirement that case 4 missed.
- **D, the live catch: confirmed, with one addition.** D1 was added by pass 1's own repair ("added by pass 1's repair,
  the production Node entrypoint contract"), so the one defect the script caught had been introduced by the review
  loop, and the loop's later passes accepted it. The entry also says "The check saves no plan-loop pass, but it finds a
  real defect."
- **E, the 40%: confirmed** as an interim snapshot ("status: interim (run still active ...)").
- **G, operator-ready: confirmed** (`casebook-residuals.md`: "Claim after integration: single-host operator-ready").
- **G, the outcome campaign: consistent.** No `results/` entry is named for a campaign or outcome run; the
  `docs/campaign-latest.md` page covers kernel variance and S-tier cases, not the 45-trial campaign.
- **Provenance of two prompt rules: added.** The cutover-clock and signed-format downgrade rules in the fresh route
  (`skills/backchain/prompts/direct.v1.md`, "Focus verification and transition gates") are phase0b case 4's two
  misses, written as general rules. They entered the fresh route in 090e37f5 (2026-11-01).
- **R12-4 wording: corrected.** Grok's no-skill subject *reasoned in backchaining terms* in 4 of 10 attempts (the
  RESULTS wording); it did not read or name the skill.
- **Repositories of the cited commits: corrected.** `b655b804`, `26d47855` and `a0178072` (the scripted caller
  contract, 2026-11-01) are skill-craft commits, not the harness's; `3d2f486e`, `10efadae`, `40a63163` and
  `2c301dca` are the harness's. Full hashes resolved with `git rev-parse` in each checkout.
