# B-planning review: test-strategy, plan, prepare (2026-10-31, main 441b1b3b)

**Read the stage-health counts with care.** Many of the refusals they count come from code that no longer exists.
- test-strategy: 23 of its 28 refusals are per-field size caps, removed in 16a3279f (2026-10-28).
- plan: 10 of its 19 refusals are the 1,200-character cap on concern rows, removed in 232689c5 (2026-10-29).

What still happens is rare and the model repairs it on its own. The median minutes are low because Codex Terra finishes
each of these stages in 10–40 s. For example, in `~/e2e-runs-brownfield/20261029/bf-codex-r1-user-listing` test-strategy
took 22 s, plan 22 s and prepare 18 s. Per-run figures come from a read-only scan of the 96 traces.

### test-strategy — verdict: improve
Signals: 61 runs, 64 packets. 11 real refusals and 17 check-only ones. Of these, 23 are retired, and 5 are live: 4 for a
missing unit row, 1 for the result-wrapper shape. Minutes: Terra 0.1–0.7, DeepSeek 3.5–13.1. Total 127 minutes, 53 of
them in one outlier run.

Findings:
- **The `## ID convention` record is wrong on the current runner.**
  - Evidence: 5 of 8 Codex Terra hello runs dated 10-29 to 10-31 declare the ID inside the test method name:
    - `~/e2e-runs/20261030/hello-terra-2243-0c81bf`: "`TC_1` is included in the unittest method name";
    - `~/e2e-runs/2026-10-30/shiploop-serve-hello-fc0832`: "`test_TC_1_output`";
    - also `control-hello-hook-continuation-1`, `published-verification-01` and `shiploop-learning-focus-192828`.
  - The matcher `shiploop_test_counts._id_pattern`, `(?<![\w-])ID(?![\w])`, matches neither `test_TC_1_output` nor
    `test_TC_1 (…)`. I checked this offline.
  - The runs passed only because the implement stage put the ID in a docstring. The hello-terra-2243 check record prints
    "TC_1 verifies the exact greeting. ... ok". None of the 8 records says this, so the knowledge home hands the next run
    a convention that fails.
  - Earlier runs show the same fault. Improve reviews of test-strategy acted on 6 findings about the ID convention, and
    3 of them were exactly this identifier case. They are in `findings.json` for hello ×2, live-sonnet-hello-b01d1c,
    pa-ds-battleship, pc-ds-hello-note and pilot-ollama.
  - The cause is in item 10. It steers models to `TC_1` "where a hyphen is not" legal, which means runners that name
    tests by identifiers. Its only counter-example is a suffix (`TC-4a`).
  - Live in current code: yes. The item 10 wording dates from 2be02de1 and `ID_WORD_RULE` from 178b514c.
- **The unit-row refusal ("no unit or component row") is live and costs little.**
  - It occurred in 4 runs: ds-flash-978478, v2170-ds, pa-ds and v2170-sonnet-battleship.
  - In each, a page with an inline script was listed only at the e2e layer, and one resubmit repaired it within a
    minute.
  - The rule has been in item 4 and in the Checked-by line since 52789f8f and ed41369f. No change.
- **The 53.4-minute outlier says nothing about the prompt.**
  - Run: `~/e2e-runs-owner-note/20261028/pc-ds-hello-note-b45e87`.
  - 48 minutes passed between a check-only that passed (20:00:23) and the real complete (20:48:39).
  - `transcript.md` shows no tool call in between (lines 207–208).
- **Item 13 ("Before you submit") restates the planning review focus (7d372c5a), and the review still finds plenty.**
  - The test-strategy Improve review edited in its first pass in 14 of 17 one-item runs, with 57 findings (Improve
    value journal, F6).
  - abdb0fdd left this open: "whether the wording makes a model validate rather than restate" was never measured.
    Top pick 2 covers it.

Proposal: change item 10 only (`shiploop_prompts.py`, the test-strategy duty). Leave the shared `ID_WORD_RULE` alone:
step-plan prints it too, and the inline step-plan head is at 19,888 of the 20,000-character cut. New item 10:

> Under KNOWLEDGE/environment.md ## ID convention declare each ID as tests will be titled, with one line as the runner
> will print it; choose IDs legal in the runner's test names (`TC_1` where a hyphen is not). {ID_WORD_RULE} Nor does a
> name such as `test_TC_1_output` show `TC_1`.

This adds about 100 characters to a head printed at about 17,200 (`terra-high-user-listing`).

Gain / risk:
- Gain: on any project whose runner names tests by identifiers, which most xUnit-style runners do, the knowledge home
  records a correct convention the first time, and one review finding goes away. The printed line it asks for is a
  string `named()` can read, so a script can check it later.
- Risk: the model may write a stand-in test to get the line, which item 11 already allows. No gate changes.

Side test: not needed to decide. A cheap confirmation:
- run AS1-style slices (`--seed-at test-strategy --stop-after test-strategy`, as in 5ca57d9e) of hello on Terra high,
  4 per arm;
- score by script: 1 if `named()` shows every declared ID on the line the section states, 0 if the section states no
  line;
- adopt if arm B scores at least 3 of 4 and raises no new refusal;
- cost: about 30 minutes.

History respected:
- 178b514c: whole-word matching stays strict.
- 2be02de1: the item 10 wording this edits.
- 16a3279f and 232689c5: the size caps stay gone.
- 52789f8f: the test_layers gates.

### plan — verdict: no-change
Signals: 61 runs, 63 packets. 9 real refusals and 10 check-only ones, in 13 runs. Of these, 10 are retired (the
concern-row cap) and 9 are live: 8 for concern-row shape, 1 for assumption shape. Minutes: Terra 0.2–0.6, DeepSeek
1.9–8.8, Sonnet up to 16.2.

Findings:
- **Concern-row shape refusals are live and cheap.**
  - Evidence: 8 refusals in 6 runs. Four gave an `owner_stage` outside the six allowed stages; four used the wrong shape
    for an applicable or not-applicable row. The latest was 2026-10-30, `qualification-full-ui/runs/config-control`.
    `bf-ds-r1-ticket-assignment` made 4 check-only resubmits within 28 s.
  - The template shows one applicable row. The not-applicable form is stated only in duty item 3, and the list of
    owner stages only in the refusal; fff7fa13 trimmed the template to fit the head.
  - The plan head's required text ends at the 19,500-character bound (fdec0f6e; plan §10, the Wave A review).
  - Spending head bytes to save a repair of a few seconds in about 10% of runs does not pay.
- **The concern map is used, not filler.** Across 63 plan results the median is 5 applicable rows and 12
  not-applicable, about 1,900 characters per run (counted from each run's `results/`).
- **Plan's Improve review yields the least of the planning reviews.**
  - It finds 0.51 findings per minute, and 19.8 of its 37.3 minutes go to passes that edited nothing (journal F6).
  - Its 47 acted-on findings are spread across classes. No single class is common enough that a duty sentence would
    prevent it; the largest is about 6 test IDs owned by the wrong work item.
  - The lever for this time is F1, not the plan prompt. F1 holds one bundle review at prepare (owner Q2; held for the
    three-arm batch, 45a4d2ff).
- Item sizing was closed by E6 (2026-10-28), so it is not reopened here.

Proposal: none.

History respected:
- fff7fa13: the concern map.
- 232689c5: no caps on model text.
- fdec0f6e: coverage is checked at plan. Hidden checks stayed at 43/43, and no run left a primary requirement out of
  `follows`.
- E6: closed.
- 45a4d2ff: F1.

### prepare — verdict: no-change
Signals: 61 runs, 62 packets. 2 real refusals, both live; no check-only refusals. Median 0.2 minutes, maximum 3.7.

Findings:
- **Both refusals come from the gate on readable harness evidence (dc83bc19).**
  - `live-sonnet-battleship-01b9b3` (10-26) cited a CDP probe page.
  - `gym-published-baseline-03` (10-31) cited its own notes file, `run/notes/runner-readiness.md`, for an Apex component
    row. It repaired this in 12 s.
  - Duty item 3 already asks for "its saved output, the runner's summary included", and the refusal names the runners
    ShipLoop can read. Live: yes. No change.
- **Item 8 (tool state in `.gitignore`) holds.** No refusal in the 96 traces mentions a tool file left out of
  `.gitignore`; I searched for one.

Proposal: none.

History respected:
- dc83bc19: the harness-evidence gate.
- 52789f8f: `harness_runs`.

## Group top picks
1. **Change the wording of test-strategy item 10 (ID convention).** It is live and repeats on the owner's runner:
   5 of 8 recent Terra hello runs record a convention the matcher rejects.
   - Cost: one sentence, about 100 characters in one packet.
   - Optional confirmation: 8 slices, about 30 minutes on Terra.
2. **Add a count of record findings to F1's planned three-arm batch.** This needs no new runs.
   - What to count: for the test-strategy and plan records, the fixes the per-stage arm makes and the fixes the
     bundle-at-prepare arm makes, by class, using the journal's `extract.py` method.
   - What it measures: F1's stated risk ("a defect found late costs a rewrite of more than one document"), and whether
     item 13 must carry the self-check once the per-stage reviews are gone.
   - Cost: one analysis pass over the batch.
