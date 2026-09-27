# ShipLoop plan after E2E runs 1-8b (2026-09-27, revision 2)

Execute: ask

Supersedes the open items of `shiploop-e2e-verification-plan-2026-09-26.md`.
Judged against `test/shiploop_e2e/SPEC.md`: ShipLoop is a general SDLC
execution engine (Purpose), product- and technology-agnostic (S-8), fixed
generically (S-13), with one implementation per mechanism (S-12).

## Audit that shaped this revision

Core ShipLoop text (scripts, prompts, SKILL.md, general cards; platform cards
excluded):

- **Rule stated in game/technology terms**: the 1.7.0 lifecycle prompt ("a
  single-user game or tool ... runs entirely in the client"; "an opponent's
  hidden game state"; a channel ladder naming server-sent events and
  WebSockets as rungs).
- **Tool knowledge inside script logic**: per-runner test-count parsers
  (Jest, pytest, Mocha, cargo, go, dotnet) in `shiploop_test_counts.py`; the
  `npm run lint` / `make lint` fallback in `shiploop_lint.py`.
- **Illustrations only** (acceptable, but one domain): `game.js` in the
  workspace card, a Tic-Tac-Toe row in behavioral requirements, Salesforce
  tab examples in two messages, a Django link.
- **Harness core**: metrics recognise test runs by tool name (`node --test`,
  `pytest`, `npm test`) instead of ShipLoop's own records; `run.py` keeps its
  own copy of the requirement-ID pattern.
- **Probe diversity**: every live run so far used one domain (a browser game
  over HTTP). Improvements may be tuned to it without anyone noticing.

## Each candidate, critically

| # | Candidate | Verdict | Critical view |
|---|---|---|---|
| A | Add a second and third case from other domains | **Do first** | Eight runs of one game cannot show generality (Purpose, harness rules). Candidates: a command-line data tool (files in, report out, no server), and a small service with persistent state and a concurrency rule. Each with product checks only in `cases.json`. |
| B | Harness core agnostic: count ShipLoop's verify records, reuse ShipLoop's requirement-ID pattern | **Do** | The harness broke its own rule; cheap. |
| C | Model-glue metric (S-4/S-5) | **Do, generic** | Define glue by ShipLoop's own directories and verbs, not by tools: writes into run/workspace/receipt paths by shell, hand-built loop JSON, commits/renames there. |
| D | One commit path + secret screen | **Do** | Generic, S-12, and a real safety gap (a secret could reach the user's branch). |
| E | One loop-contract builder for test, quality and Improve, exit criteria from the stage's own `done_when` | **Do the builder; defer the new `loop-start` verb** | The builder removes duplication and gives Improve stage-specific exits (S-10). The verb would change two start paths that failed zero times in runs 7/8b; uniformity alone does not justify that churn now. Revisit if a run shows a start problem. |
| F | Trim Improve packet text the scripts now own | **Do, carefully** | S-7 without breaking S-6. Only remove steps the script performs; keep each obligation once. |
| G | Neutralize the 1.7.0 lifecycle wording | **Propose (owner's change)** | State the rule in SDLC terms: placement follows who must see and change the state and how fresh it must be; information a user must not see stays where that user cannot read it; lightest channel that meets the stated freshness. Keep at most one labelled, varied example. Needs the owner's rubric results rechecked, because the wording was tuned by experiment. |
| H | Move tool knowledge out of script logic into catalogs | **Do later (low risk, low urgency)** | Test-count parsers are necessary for S-9; keep the behaviour, move per-tool patterns into one catalog module/table with a documented extension point; same for the lint fallback. No functional change. |
| I | Neutral illustrations in general cards | **Do with G** | Replace `game.js`, Tic-Tac-Toe and repeated Salesforce examples with varied or neutral ones. |
| J | Battleship hidden-state check | **Replace by a generic evaluation** | As a Battleship check it tests one product. Instead: a harness review question "did information one user must not see stay out of that user's reach?" plus, in any case whose request has hidden information, a case-level check. Kept out of the harness core. |
| K | Probe Grok's auto-mode refusals | **Do, host-neutral outcome** | Useful to understand lost sessions, but any resulting change must be host-agnostic guidance (for example "write scripts to files inside the workspace and run the file"), never Grok-specific logic. |
| L | Until Loop short output (upstream) | **Propose separately** | Generic and the largest context driver; another repository, owner decision. |
| M | Skip skill stages / trim planning / `--always-approve` / print whole packets | **Drop** | Cheap stages; owner accepts planning size in files; unrealistic host; contradicts S-7. |

## Plan (order)

1. **A + B + C** (harness only): two new cases in other domains; case-agnostic
   metrics; generic glue metric. Run each new case once on 1.7.0 to get a
   baseline across domains before changing ShipLoop.
2. **D + E(builder) + F** (ShipLoop, one release): shared commit helper with
   secret screen; shared contract builder with stage done_when exits;
   Improve packets state each obligation once.
3. **G + I** (ShipLoop prompts/cards, owner review of G first): neutral rule
   wording and varied illustrations.
4. **Release**, full hermetic tier first, host updates, then one run of each
   case (three domains) through the version gate. Acceptance: every verdict
   passes in every domain, 0 ShipLoop command failures, glue 0 for mechanical
   steps, cost no worse than each case's baseline, Improve packets smaller.
5. **K** probe, **H** catalog move, **L** proposal, as separate small steps.

## Negative implications and how each is handled

| Change | Risk | Mitigation |
|---|---|---|
| A new cases | More runs, more cost (~$25-35 each) | Keep cases small; one run per case per release; follow-ons only for the domain under study |
| A new cases | A case that fails for product reasons, not ShipLoop | Review against the spec: product defects are evidence only; checks limited to observable behaviour the prompt states |
| B/C metrics | Glue metric misclassifies legitimate product work | Count only shell writes into ShipLoop-owned paths and ShipLoop mechanics; report the commands so a reviewer can confirm |
| D secret screen | False positives on fixture tokens | Skip only that file, name it, never fail the stage; the model sanitizes and recommits |
| D secret screen | Slow on large/binary files | Text files only, size-capped |
| D identity | Fallback author reaches user history | Only without a configured identity; stated in the handoff |
| E exits from done_when | More review passes, higher cost | Intended (S-10); compare against baselines; tune wording, not the rule |
| E builder | A contract field changes meaning for in-flight runs | Contracts are frozen on disk when written; new code builds only new ones; one supported version |
| F trimming | Losing an obligation after context loss (S-6) | Remove only script-performed steps; packet-contract tests assert the remaining obligations |
| G rewording | Losing the safeguards the experiment measured | Owner reviews; rerun the architecture-rubric scenarios before release |
| G/I/H | Test churn from changed wording | Change tests that pin wording in the same commit; full tier before release |
| H catalog | Regressions in count parsing | Behaviour-preserving move; existing parser tests unchanged and green |
| K probe | Temptation to encode host quirks | Only host-neutral guidance may result |
| All | One run is weak evidence; runs are nondeterministic | Compare with the same case's prior runs; repeat when a result contradicts the trend |
| All | Concurrent releases from other sessions | Fetch before each step; the version gate stops mismatched runs |
