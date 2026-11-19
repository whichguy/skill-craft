# ShipLoop E2E skill inspection, 2026-11-19

**Question (owner, 2026-11-19):** "Deeply inspect our e2e test skill and recommend if there is anything we should do."

**Subject:** the `shiploop-e2e-audit` skill (1.1.0, released in skill-craft 3.3.0): its card, `IMPROVE.md`, `AUDIT.md`
and bundled `harness/`, together with the source harness `test/shiploop_e2e/` that its improvement route drives. All
of it at origin/main d1bc14e4ba94edcab016917c452b53dd60b73634.

**Method.**
- I read the card, the two guides, the bundled harness's README and catalogs, the full messages of the commits that
  shaped the current route (3c81b3ae0cbd2a9a39500ded991fc3c9d0443f4b, 49fbb7aa39dcf755cc9eac4f5ff876c26e386dcf,
  d1bc14e4ba94edcab016917c452b53dd60b73634, 7fb5ba64f019230c24b5f3099d4154357dc6891f,
  44e9a60d8b6cd646c73412877097c4e872cbb6b1 and the 2026-11-18 Salesforce commits), and the 2026-11-18 campaign's
  findings report. That report sits outside the repository and is summarized below.
- I measured size, growth, suite time and CI results ([measurements.txt](measurements.txt)).
- I ran the skill's own suites and the source-harness suites a campaign uses on Python 3.15 and 3.13. I called the
  two version-sensitive code paths directly on 3.9, 3.11, 3.13 and 3.15 ([python-floor.txt](python-floor.txt)).
- An independent review ran on Sol 6.2 at max, read-only, on a neutral export
  ([method](sol-review-method.md), [brief](sol-review-brief.md), [verbatim answer](sol-review.md)).

Status of every finding: **interim**. Each awaits the owner's decisions below; nothing has been changed yet.

## What the skill is today

- **Improve route** (`IMPROVE.md`, added 2026-11-18 by a Codex session at the owner's request: "stop asking for routine
  preflight approval ... start the first pass from a clean repository"). It runs `test/shiploop_e2e/run.py` on the
  published build, then `iterate.py` to review the run, and `iterate.py --qualify` for a registered comparison.
- **Audit route** (`AUDIT.md`, the earlier card body). Its mock, check and live audits run the **bundled harness**
  (`skills/shiploop-e2e-audit/harness/`). That harness is the first-generation "one-shot Grok E2E campaign"
  (its README's title): ten game requests, nine on Google Apps Script (tic-tac-toe, checkers, battleship) and one
  Salesforce checkers. Its last audit evidence folder is `docs/experiments/shiploop-e2e-audit-20261016/`. Since
  2026-10-20 its only changes have been repairs after ShipLoop changes broke it (Grok adapter verb pins, fixture re-pins).
- The **latest campaign** (2026-11-18, csv-report, Sol 6.2 medium, about 17 minutes) passed all five catalog checks and
  all six delivered tests. A supplemental probe then reproduced a wrong result on valid CSV: one quoted field over
  131,072 characters produced a phantom West sale of 891.00 instead of one East sale of 2.50. The independent review
  and judge admitted no ShipLoop change. A paired probe of a criterion-timing reminder scored 4 of 4 in both arms.
  Its report and evidence live only in `~/.codex/visualizations/2026/11/18/.../shiploop-sdlc-first-pass/`;
  `test/shiploop_e2e/LEARNINGS.md` ends at 2026-11-16.

## Findings from my own reading (checked against the code)

**F1. The improve route runs the improver at medium; the owner chose max.** On 2026-11-15 the owner said the improver
"should be sol 6.1 max or sonnet 5.5 max (or latest of either of these models)". 7fb5ba64 made that the harness default:
`hosts.ROLE_DEFAULTS["improver"]` is Sol at `max`, `hosts.ROLE_EFFORT = {"improver": "max"}`, and
`test/shiploop_e2e/README.md` documents it. `IMPROVE.md` (3c81b3ae, 2026-11-18) says "Use Sol medium for the subject
and improver" and passes `--improver-effort medium`. An explicit effort wins over the default, so every campaign that
follows the card runs the improver at medium. The commit cites the 2026-11-08 choice (44e9a60d) and not the
2026-11-15 one. No improver has run under it yet: the 2026-11-18 pass admitted no candidate.

**F2. The default first case cannot show an improvement in testing.** `IMPROVE.md` starts with `csv-report`. Its five
checks each test one sentence of the prompt (`checks_source` in `cases.json`), and it has no held-out
`quality.acceptance` block; the cases that have one include checkers, the user-* cases and most ticket cases. The
2026-11-18 run passed everything while returning a wrong total for valid CSV. So on this case a campaign sees a pass
whether or not ShipLoop's test step improved; the 4 of 4 against 4 of 4 timing probe is the same ceiling.

**F3. Campaign learnings and evidence stay outside the repository.** `IMPROVE.md` step 3 records the
findings-and-changes report "in the campaign output". `iterate.py` logs each iteration to the output directory and
commits its LEARNINGS entry on the iteration's own branch (`record_learnings`). A qualified cycle does the same on its
loop branch (`cycle.py` step 7). Either reaches main only when that branch is merged, which happens after a PROMOTE.
The 2026-11-18 pass is in neither main nor any branch of the canonical checkout: no LEARNINGS.md commit exists after
2026-11-16, and `git log --all -S'131,072'` finds no entry. That breaks the standing rule to keep a journal next to
the work, with compact evidence in the repository.

**F4. Two front doors lead to the same comparison, under different builder permissions.** The closed-loop skill's
ShipLoop adapter (`test/shiploop_e2e/adapter/facade.py`, built 2026-11-15/16) and `IMPROVE.md` both run
`iterate.py --qualify --iterations 1`. The 2026-11-18 session chose not to use the adapter ("need not use generic
closed-loop adapter or its hosted ratification"). The adapter passes no permission flag, so its Codex builder gets
`iterate.py`'s default `auto`, which `CodexHost.argv` maps to `-s danger-full-access` with approval `never`. The
improve route uses `--codex-auto-review`: the workspace sandbox with each blocked command reviewed. Inside one
comparison, both arms must match (`promotion.py` compares host, effort, permission mode and timeout), so no qualified
decision mixes them. A campaign from one door is still not comparable with one from the other. The adapter's three
suites take 581 s of recorded CI time; `shiploop-e2e-adapter-steps` alone takes 428 s, the slowest E2E suite.

**F5. The bundled audit harness looks like legacy weight in every installed package.** It is 30,639 lines in 118
files, installed with skill-craft on every host. Its live route is Grok-only and depends on GAS deployment or a
Salesforce org. Most of its modules last changed in September or October; capture, evidence and planning evidence changed on
2026-11-08. The improve route does not use it.
Two of its parts are live dependencies of the source harness: `planning_boundary.py` loads its `planning_trace.py`,
and `planning_comparison.py` puts the whole harness directory on `sys.path`. Its mock replay runs in CI (the
`e2e-apparatus` group).

**F6. The skill's documents state Python 3.15+, and its commands call `python3.15`.** This is the kind of mandate the
owner removed from ShipLoop on 2026-11-18: `IMPROVE.md` (both commands), `AUDIT.md` ("Use Python 3.15+"), the
bundled README, and the 1.0.0 changelog line. Every one of the 187 Python files in both harnesses parses on 3.9. Running the code
shows two real needs ([python-floor.txt](python-floor.txt)). On macOS, the builder wait loop
(`listeners.unreaped`) needs `os.waitid`, which macOS Python gained in 3.13; it fails on 3.9 and 3.11. The bundled
game oracles need 3.10 for `zip(strict=True)`. Nothing found needs 3.15. Where `python3.15` is not installed under that
name, such as most Linux machines, the documented command fails outright. The pin comment in `hosts.py`
(`PYTHON_PIN_DIR`) still says ShipLoop's minimum is 3.15; it has been 3.9 since 12c8f967.

**F7. The apparatus is about 3.6 times the size of the skill it tests, and it is growing fast.** ShipLoop is 56,352
lines. The E2E apparatus is about 204,000: the bundled harness 30,639, the source harness 83,217 of code and 21,274 of
documents, and the suites 68,555. Since 2026-10-20 the source harness and suites gained 93,185 lines of Python, while
ShipLoop's net change was about 1,200 lines. The E2E suites take 47% of the recorded suite time. On 2026-11-18 four
pushes to main from harness work failed CI, each fixed by a later commit; the fixes chose a login shell, isolated Git
config and child-process signals in the fake hosts, and restored an unset legacy permission mode. Code named for Salesforce or hosted cases is at least 14,173 lines in the harness and 14,996 in the
suites. On 2026-11-15 the owner said the Salesforce run would be deleted later; on 2026-11-18 the owner commissioned
the Grok Bot hosted case.

**F8. Each fresh campaign takes the newest model family.** `IMPROVE.md` says to "resolve the latest available Sol and
Astra families" for each fresh campaign, so the 2026-11-18 pass used Sol 6.2 and Astra 6.2. The harness defaults are
still `gpt-6.1-sol` and `gpt-6-astra`. Each new family starts a new baseline cell. AGENTS.md lists a change that breaks
comparability with earlier evidence among the owner's decisions.

**F9. Retained runs pile up.** About 88 GB of run folders sit under `~/e2e-runs`: 61 dated folders, 2026-10-03 to
2026-11-15. The canonical checkout has 239 registered worktrees, 80 of them inside `~/e2e-runs/2026-10-30` to
`2026-11-02`, and 209 local branches. `~/.codex/visualizations` holds another 59 GB, not all of it E2E. The skill says
to preserve each attempt, and nothing says when one may be removed. These runs belong to other sessions; removing them
is the owner's decision.

**F10. On Codex, the efficiency figure that decides a tie counts only the parent thread.** A qualified cycle decides on
tokens when quality is equal (`cycle.py` docstring, step 4: "efficiency on tokens"). `promotion.py` refuses a total that
is a lower bound, but `metrics.lower_bound` only knows about launched sessions that never reported. The Codex stream
reader takes usage from the parent's `turn.completed` events (`CodexHost`, `usage`). Native workers, which the harness
puts on the subject's model through `agents.default_subagent_model`, and automatic approval reviews are not counted, and
nothing marks the total as partial. The 2026-11-18 report says the same: "The token counter covered the parent thread."
So a candidate that moves work into workers would look cheaper and could be promoted on efficiency alone.

## The independent review, and what I verified of it

Sol 6.2 at max (899 s, read-only) returned 13 recommendations ([verbatim](sol-review.md)). Its verdict: keep the source
harness as the main way to improve ShipLoop, fix the comparison code before using `PROMOTE` to ship a change, and spend
the next campaign on a case whose check can actually fail. I checked each claim I relay against the code. I did not
re-run its in-memory reproductions.

| Sol | Claim | My check |
|---|---|---|
| 1 (P0) | Promotion can compare arms that ran different host CLI builds | **Verified in code.** The strict check in `promotion.py` compares host, model, effort, permission mode and timeout only; `scorecard.py` flags a build change within one run, never across arms |
| 2 (P0) | A calibration report is accepted for a driver it never measured | **Verified in code.** `cycle._load_calibration` checks the contract, the cases, the scoring digest and that a tolerance was recommended, but not the driver, the usable attempts or the floors |
| 3 (P1) | The first run is not runnable from the card alone | **Partly verified.** `listeners.py` calls `os.waitid`, which macOS Python lacks before 3.13 (`hasattr` false on 3.9 and 3.11, true on 3.13 and 3.15); the bundled game oracles use `zip(strict=True)` (3.10). The qualification line alone stops without `--calibration` or `--attempts` with `--tolerance`. Reproduced: a copied package's `check_suite.py --suite mock --list` exits 2 without `--skill-root` and 0 with it; `AUDIT.md`'s mock row omits it, and `test/installed-skill-invocation.test.py` always passes it |
| 4 (P1) | Cancelling a qualification can orphan the builder | **Verified in code.** `epoch.py launch` calls `runner.main()` directly; only `run.py`'s `__main__` installs the SIGTERM and SIGHUP handlers. Not checked: the post-dispatch invocation comparison |
| 5 (P1) | Incremental (`follows`) cases fail only after the improver has run | **Partly verified.** `cycle.registration_template` carries no predecessor binding and is built after the improve and purpose steps; I did not reproduce the "missing user-teams" error |
| 6 (P1) | The CSV unit check passes a suite whose only test was skipped | **Verified in code.** `checks/csv_report.py` `unit` needs exit 0 and `Ran N tests` with N of 1 or more, so a skipped test counts. `checks/seat_service.py` has the same pattern |
| 7 (P1) | Arm order and counters bias the efficiency comparison | **Verified in code.** `registration_template` queues every control attempt of a case before its candidates; the token scope is my F10 |
| 8 (P1) | An incomplete review overwrites a script `PROMOTE` | **Verified in code.** `epoch.decide` replaces the decision and its reasons (a deliberate rule, per its comment), so the record loses the numeric verdict. Not checked: the prediction reader |
| 9 (P1) | Assessment is not retryable; qualification never runs the quick tier itself | **Second half verified:** `iterate.quick_suite` runs in exploration only; `cycle.py` has no call to it. First half not checked |
| 10 (P1) | The bundled workflow inventory misreads multi-item runs | Not checked |
| 11 (P1) | Journal entries are not reproducible from the repository | The same as F3 |
| 12 (P2) | Duplicate operator instructions; the mock modules run twice in CI | **Verified:** `run_suites.py --list` runs `check_suite.py --suite mock` and `--suite all`, and `all` includes the mock modules |
| 13 (P2) | Park Salesforce-specific expansion (an owner decision) | Consistent with F7 |

Sol did not raise F1; the brief did not quote the owner's improver decision. It differs from me on the bundled harness
and on the two front doors. It would keep the bundled Grok audit for explicit hosted and workflow investigations, and
keep Closed Loop opt-in because merging the paths "would add coupling across different inputs and users".

## Recommendations

**Now (small, routine, no change to grading):**
1. `IMPROVE.md`: let the improver run at the owner's max, by dropping the `--improver-*` overrides or passing `max` (F1).
2. Python: state the real need, or none, and write `python3` in the commands. The real need is 3.13 on macOS
   (`os.waitid`) and 3.10 for the bundled game oracles. Correct the `hosts.py` pin comment (F6, Sol 3).
3. The CSV and seat unit checks: require at least one test that actually ran, not skipped (Sol 6).
4. `IMPROVE.md`: every attempt ends with a `LEARNINGS.md` entry and compact evidence in the repository. Backfill the
   2026-11-18 pass from its owner's evidence (F3, Sol 11).

**Before trusting any `PROMOTE` from the improve route:**
5. Compare the observed host CLI build across arms (Sol 1).
6. Bind a calibration to its driver, usable attempts and floors (Sol 2).
7. Mark Codex token totals as partial when workers or automatic review ran, and interleave control and candidate
   attempts (F10, Sol 7).
8. Install the runner's termination handlers in `epoch.py launch`. Run the quick tier from the script in qualification.
   Check an incremental case's inputs before calling the improver (Sol 4, 9, 5).

**Next campaign:** use a case whose oracle can fail, such as `ticket-assignment-tests` (calibrated test adequacy) or
`ticket-import` (brownfield), and keep `csv-report` as the cheap launch smoke. Add a calibrated record-boundary check
to `csv-report` only after it is checked on a correct and a faulty copy (F2, Sol 6).

**Owner decisions:**
- The bundled harness's live Grok, GAS and Salesforce route: retire it, keeping the mock replay and the two imported
  modules (my lean, F5), or keep it for hosted and workflow investigations (Sol).
- The closed-loop ShipLoop adapter: keep it opt-in (Sol) but launch its builder with the improve route's permission
  mode so their results compare, or park it (F4).
- The hosted Salesforce cases: whether they stay, given F7's size and growth (Sol 13).
- Comparison policy: the newest model family each campaign or a pinned series, the effect size worth detecting, attempts
  and compute (F8, Sol).
- Whether a completed independent review must gate the loop tip, with the script's verdict kept beside it (Sol 8).
- A retention rule for the 88 GB of run folders, 239 worktrees and 209 branches (F9).

**Checked and fine (leave alone):** every flag in `IMPROVE.md` exists (`iterate.py` builds the per-role flags in
`add_argument(f"--{role}-host")`). The promotion contract refuses unknown quality, mixed evaluators and mismatched
requested settings. The clean-source, fresh-product and installed-bytes checks run before dispatch (d1bc14e4 compares
archives, so ignored caches no longer refuse a clean checkout). Qualified cycles journal into the repository
themselves. Sol adds: keep the identity and delivery safeguards, cost per success including failed attempts, and the
refusal of incomplete totals.
