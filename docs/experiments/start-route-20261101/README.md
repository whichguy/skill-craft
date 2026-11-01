# Start route: does rewording the card's start section stop the wrong first command?

Status: **done 2026-11-01.** Pre-registered before the first scored trial; T2 met the registered bar and shipped as skill-craft 2.27.3 / shiploop 1.26.3 (release f24746fa6193007235818f2d8b109408d70ca413); a published-build confirmation held (see "Results").
Owner: Jim Wiese. Model and harness (owner, 2026-11-01: "Use terra at xhigh", "We should be using the codex harness"):
the E2E harness `test/shiploop_e2e/run.py` on its Codex host, `gpt-6.1-terra` at `xhigh`.

Words used here. The **start route** is the first ShipLoop command a session runs to begin a run: `workspace start` (the
**isolated entry**: the work happens in a separate worktree and the finished work is returned to the starting directory) or
`init` (the **direct entry**: the work happens in place, with no automatic return protection). An **arm** is one version of
the skill card under test. A **request** is one prompt together with the directory the session starts in.

## Question

A session that starts in an empty directory that is not a Git repository should run `workspace start`: the card says so
("An empty starting directory needs no setup: `workspace start` makes it a Git repository on `main` with one empty baseline
commit"). Some sessions run `init` instead. Does a small rewording of the card's start section make the wrong route rarer,
without harming the right one elsewhere?

## What we knew before this experiment

- **The failure.** The second live Salesforce run (`~/e2e-runs-hostonly/20261031/ui-live-2`) ran
  `init --repo <work> --run-dir <output>/battleship-run`; the runs beside it ran `workspace start`. With `init` the work folder
  never became a Git repository, so the harness's `committed` verdict failed
  (`docs/experiments/host-only-refusal-20261031/README.md`, finding L3, commit
  3a2c9986f1f2987750c208fe1eb849726e927136). That run read `references/run-start.md`, ran `pwd && ls -la && git status`
  (`fatal: not a git repository`), read `references/run-options.md`, ran `--help`, and then `init`. Codex does not record its
  reasoning, so why it chose `init` is not known.
- **How often (recount, 2026-11-01).** `start_routes.py` and `recount.py` (output in `recount-output.txt`) read the first
  ShipLoop start command in every archived event stream since 2026-10-24. Model-chosen first starts: Codex 131 `workspace
  start` and 4 `init` (3.0%); Claude 56 and 0; Grok 111 and 0. The 4 Codex `init` starts are all `gpt-6.1-terra`; 3 were
  Salesforce prompts (3 of 12 Codex Salesforce starts, 25%) and 1 was `hello` (1 of 123 other starts, 0.8%; that `hello`
  session had first missed the skill and started late, so it is a weak sample). 51 further `init` rows belong to the case
  `hello-startup-contract`: another session's evaluator controls and probes (paths `construction-controls-01/inputs`,
  `neutral-diagnostics-01`, `scoped-boundary-controls-01/inputs`, `startup-scorer-adversarial-probes-01`; no model recorded),
  not a model's choice; they are left out. Its two real runs (`startup-behavior-qualification-01/epoch/runs`) both ran
  `workspace start`. This
  recount **supersedes the earlier "8 of 168 readable starts" figure** in the L3 finding (a different corpus); the
  conclusion that the wrong route is rare overall and concentrated in the Salesforce prompts is the recount's.
  Status: firm for the archive, exploratory for the cause (n = 12 Salesforce starts).
- **What the Salesforce prompts say.** "in a Salesforce DX project in the current directory" and "The Salesforce DX project
  root (`sfdx-project.json` and `force-app/`) is the current directory itself, not a subfolder." A reader can take "the
  current directory itself" to mean "work in place", and the card lets an "explicitly selected in-place/non-Git run" use `init`.
- **The card's start section today** (`skills/shiploop/SKILL.md`, identical in published 2.27.2 / ShipLoop 1.26.2, release
  e13af240100c066489e83c028d97339845402b55; the start section is unchanged since 2.27.1, that release changed the version line and one sentence about Python 3.9):
  - lead-in: "For new work in an existing Git repository, use the isolated entry below." (introduced by
    d880a47a29b77eccf53d62693df63b3220e18e95, 2026-09-17)
  - empty directory: "An empty starting directory needs no setup: `workspace start` makes it a Git repository on `main` ..."
    (introduced by b04297eea6054eab2621f785d71e5649e71067f1, 2026-09-26, after a Grok run lost three sessions to its own
    `git init` script)
  - direct entry: "An explicitly selected in-place/non-Git run may instead use the direct entry, documenting why isolation is not
    used; it has no automatic workspace-return protection:" (introduced by b960891b8fdb2b47e85eca1beeb113c827bb6664, 2026-09-24)
  Two places may mislead: the lead-in names only "an existing Git repository", and "in-place/non-Git" lumps two different
  things, so a folder that is not a Git repository, in a request that says "current directory", can read as an in-place run.
- **Limits from other sessions' work, read before this change.** The card has a size cap of 30,500 bytes
  (`test/fixtures/shiploop-card-ledger.json`, `card_max_bytes`); the card is 30,011 bytes, so 489 bytes of room. Another
  session's startup-guidance candidate grew the card by 700 bytes and failed the cap
  (df44fd30d19455515cc2434dd21b18520e2a5f48), was trimmed to 30,440 (07faf147dcba79d412e2d673685ea24acf1a139c) and stood
  at 30,448 in its final form (b1891ab4656613467a75427a6d57e902e94c3067), and was **dropped** because the cost of a protected case rose 45.9%
  (f842a624e95bdcdbf434ce785d08e9ae65ca9c6f). That candidate changed how the CLI is quoted, not the start route, and both of
  its logical starts used `workspace start`; its result is no evidence about this wording. Its admission
  (a0e46b2c90c47d012fcca19e03ee6fa1b3279cbc) and ed2f0a3481c8abda9d7d22a98fa7275685fd6a2f also say: do not widen the
  observer, do not rescue a missed threshold, and keep each claim to what was measured. This experiment follows those rules.

## Arms

Exact text edits to `skills/shiploop/SKILL.md` are in `arms.json`; each arm is the published plugin package
(`plugins/skill-craft`, 2.27.2) with only that edit. The harness installs the arm through `--plugin-dir` and its plugin check
(`plugin_verdict`) and the installed card's hash are recorded for every trial.

| arm | edit | card bytes | cap |
|---|---|---|---|
| C (control) | none: the published card | 30,011 | 30,500 |
| T1 | lead-in: "... in an existing Git repository **or an empty directory**, use the isolated entry below." | 30,033 (+22) | ok |
| T2 | direct-entry sentence: "Use the direct entry only when the user explicitly asks for an in-place or non-Git run (naming the current directory is not that: `workspace start` returns the finished work there), documenting why isolation is not used; ..." | 30,115 (+104) | ok |

T2 keeps the card's meaning (the direct entry stays for an explicitly requested in-place or non-Git run) and adds what the
request wording does and does not select. The statement "`workspace start` returns the finished work there" is true: the
finished work is returned to the starting checkout at the end (`references/run-start.md`, "Workspace return").

**Prediction (registered now).** In the probe's Salesforce request the control's wrong-route rate is about 25% (the archive's
3 of 12; the one unscored control smoke trial also chose `init`). T2, which addresses the "current directory" reading, brings
it to 10% or less; T1, which only names the empty directory the card's next paragraph already covers, changes little.
If T1 alone works, it is the smaller change and wins.

## Requests

| request | how it is given | start directory | why |
|---|---|---|---|
| `sf-ui` | `--prompt`, the host prompt of run 2 minus the skill prefix, byte for byte (`stimuli/sf-ui.txt`, 6,960 bytes) | empty, not a Git repository | the failing situation |
| `hello` | `--case hello` | empty, not a Git repository | regression guard: a plain request, no "current directory" wording |
| `repo` | `--case ticket-assignment-tests` (first choice `user-listing`: see "Deviations") | an existing Git repository (a Node project) | regression guard: the case the lead-in's first clause covers |

No platform is declared, so no org is touched: the harness profile holds no login, and no run is built (see "Method").

## Method

- One trial = one `run.py` run: `--host codex --model gpt-6.1-terra --effort xhigh --plugin-dir <arm> --output <new folder>
  --timeout 240 --quiet --baseline <probe file>` plus `--prompt <text>` or `--case <name>`. The harness builds the throwaway
  profile, installs the plugin, runs `codex exec`, and records `events.jsonl`, `invocation.json`, `result.json`,
  `metrics.json` and the rest as for any E2E run. `--baseline` points at a probe file, so the committed `baselines.jsonl`
  is untouched.
- `start_probe.py` is only a driver: it watches each run's `events.jsonl` and, when the model issues its first ShipLoop
  start command (`workspace start` or `init`, as a shell command, a `$CLI` variable or a Python argument list; a reader
  command that mentions the words is not a start), creates `<run>/stop`, the harness's own way to end a host on purpose. That
  command is the outcome. The harness is then given 120 s to write its records; the driver ends a run still alive after 420 s.
- **Trials.** 180 slots in one fixed random order (seed 20261101, `plan.json`): `sf-ui` 40 per arm, `hello` 10 per arm,
  `repo` 10 per arm; 4 at a time. Arms are interleaved so drift in the service falls on all arms alike.
- **Valid trial.** The harness recorded host `codex`, model `gpt-6.1-terra`, effort `xhigh`; the installed card is the arm's
  card (sha256 prefix compared); and either a start command was issued, or the session ended or timed out after touching the
  skill. An invalid trial (an infrastructure fault, a wrong build) is rerun up to 3 times; a trial is **never** rerun for what
  the model did.
- **Cost.** A stopped session reports no token totals. The smoke trial made 3 model calls with an input peak of 36,673
  tokens, about 20 s end to end, so the batch is estimated at about 0.1M tokens per trial and about 18M in all (estimate,
  not measured). Wall time about 15 minutes.
- **Unscored smoke trials** (driver test, before registration, on the 2.27.1 package; the base moved to 2.27.2 before any scored trial): C/`sf-ui` ran `init`; T2/`sf-ui` ran `workspace start`;
  T1/`hello` and T2/`repo` ran `workspace start`. They are not in the data, whichever way they fell.

## Outcomes

For each trial, from the model's first start command: `workspace` (right in all three requests), `direct` (wrong in all three:
none asks for an in-place run), or `none` (the session ended without a start). Secondary: the model ran its own `git init`,
`git config` or `git commit` before the start (`self_bootstrap`, which the card forbids), whether it read `run-start.md`
first, and the seconds to the start.

## Decision rule (registered now)

Rate = `direct` / (`workspace` + `direct`) among valid `sf-ui` trials. A candidate **meets the bar** only if all hold:

1. The control's `sf-ui` wrong count is at least 5 (otherwise the probe cannot tell the arms apart; report it and ship nothing).
2. One-sided Fisher exact p < 0.025 for "candidate wrong count is lower than control" (0.05 split over the two candidates).
3. The candidate's rate is at most half the control's.
4. The candidate's share of sessions with no start is at most the control's plus 10 points.
5. Over `hello` and `repo` together (20 trials per arm), the candidate's `direct` plus `self_bootstrap` count is at most the
   control's plus 1.
6. The candidate's card stays at or under 30,500 bytes (the size test must pass; the cap is not raised).

If both candidates meet the bar, ship the one with the fewer `sf-ui` wrong starts, then the smaller card. If neither does, ship
nothing: the card is unchanged, the result and the reason go in this journal, and no release is cut. A result with p between
0.025 and 0.10 is reported as suggestive and is not shipped; extending the sample needs a new registration. Shipping also needs
the changed-file tests to pass, a change note (`changes/shiploop/`), and a verbose commit message with the evidence.

## What this cannot show

- It measures the **first command** of **Codex Terra at xhigh** on **one** Salesforce-style request and two plain ones. Claude
  and Grok never chose the wrong route in the archive (0 of 56, 0 of 111), so no effect on them can be shown or is claimed.
- It does not run the workflow, so it cannot show a saving in minutes, tokens or loops; the cost of one wrong start (an
  uncommitted product, a failed `committed` verdict) is argued from run 2 only.
- A null result does not prove the wording is harmless or useless; it shows this sample could not tell the arms apart under the
  rule above.
- The reasoning behind a choice is not recorded, so a working arm shows that the wording matters, not which words.

## Deviations from the registration

Recorded as they happened; none changes an arm, the sample sizes, the order, or the decision rule.

1. **The `repo` request was replaced (2026-11-01, 05:46, after 32 rows).** Launch 1 ran `repo` as `--case user-listing`. All 15
   attempts (5 slots, 3 attempts each) were refused by the harness in 1 to 2 seconds, with no model call: that case declares port
   3000, which the harness leases machine-wide, and another session's run (`e2e-runs-tl/20261101/A-user-listing-s1`) held it.
   The replacement `ticket-assignment-tests` was refused the same way (port 4180, held by that session's `ticket-assignment`
   run), so `repo` trials now run with a private lease folder per trial (`SHIPLOOP_E2E_LEASES`, the harness's own setting). That
   is safe here because every trial ends within seconds of the model's first start command, before anything could be built or
   served on that port. The 15 refusals stay in `results.jsonl` as invalid rows; no valid `repo` trial existed before the change.
   The 14 valid `sf-ui` and 3 valid `hello` trials of launch 1 stay in the data (the driver code for those requests did not change).
2. **Attempt accounting.** The driver numbered attempts across launches, so slots refused in launch 1 would never have been
   retried; a launch now makes at most 3 attempts per slot and numbers them after the earlier ones.
3. **Timing.** The `repo` slots run after their planned position, so the guard's trials are not interleaved in time with the
   other requests. The `sf-ui` comparison, the one the decision rests on, is unaffected.

4. **The start detector was fixed (2026-11-01, 05:49, after 40 rows).** The detector counted `... init --help` and
   `... workspace start --help` as starts, so a session was ended at a help request, before its real decision. 14 of the 40 stored
   rows (all `sf-ui`: 11 recorded as `workspace`, 3 as `direct`; control 6, T1 5, T2 3) were of this kind. A start must now carry
   `--repo` or `--prompt`, which a help request does not. `start_probe.py reclassify` re-read every stored trial's `events.jsonl`
   with the fixed detector, superseded those 14 rows with invalid rows, and the 14 slots ran again; the other 26 rows read
   identically. The last row of a slot decides whether the slot has a valid trial (`analyze.py` and the driver both read it that
   way). The definition of the outcome is unchanged: the first command that starts a run.
5. **Stray observers blocked the harness (2026-11-01, 06:03, at 102 counted rows).** When a start command gets as far as
   running before the stop file ends the host, the ShipLoop CLI has already spawned its read-only progress observer, which can
   outlive the harness. The harness refuses every later launch while such an orphan lives ("no host is started" in the trial
   log), so 47 attempts in two minutes (about 120 invalid rows in all, every request) ended in 3 to 4 seconds with no model
   call. I killed my own observers (12, each naming one of my trial folders; no other session's process), ran the harness's
   `lifecycle.py cleanup` for the one trial it named, added a per-trial cleanup to the driver (`reap`), and relaunched; the
   refused slots ran again. These refusals made no model call and are not outcomes.
6. **The detector missed one start form (2026-11-01, 06:23, after all 180 slots had a valid row).** A start written as a
   `python3 -c` one-liner inside a double-quoted shell command carries its quotes backslash-escaped
   (`\"workspace\",\"start\"`), which the pattern did not match. Such a session was not stopped at its start and ran on to the
   240 s host timeout, so it was recorded as "no start" (9 sessions, all `sf-ui`: control 2, T1 4, T2 3) although ShipLoop had
   started in each. `start_probe.py rescan` re-read all 180 stored event streams with a pattern that allows the escapes: 171
   rows read identically, and those 9 now read as starts (control 1 `init` and 1 `workspace start`; T1 4 and T2 3 `workspace
   start`). The analysis before the rescan (control 16 wrong of 38 started, T1 4 of 36, T2 0 of 37, 9 without a start) and after
   it (below) give the same decision. The rule is unchanged, and the fix is by command form, not by outcome.

## Results

180 valid sessions (the last row of each slot decides), `analysis-output.txt`, compact rows in `results-compact.jsonl`.
Wrong = the first ShipLoop start command was `init`.

| request | card | sessions | `workspace start` | `init` | wrong rate (95% interval) |
|---|---|---|---|---|---|
| sf-ui | C, the published card | 40 | 23 | **17** | 42.5% (29% to 58%) |
| sf-ui | T1, lead-in names an empty directory | 40 | 36 | **4** | 10% (4% to 23%) |
| sf-ui | T2, direct entry is for an explicitly requested in-place or non-Git run | 40 | 40 | **0** | 0% (0% to 9%) |
| hello | C, T1, T2 | 10 each | 10 each | 0 | 0% (0% to 28%) each |
| repo | C, T1, T2 | 10 each | 10 each | 0 | 0% (0% to 28%) each |

- **The bar.** Both candidates meet all six items. T1: one-sided Fisher p 0.0009, rate 10% against 42.5%. T2: p below 0.0001.
  Neither added a session without a start (0 of 40 in every arm after the rescan), no guard session started with `init` or ran its
  own `git init`/`git config`/`git commit` (0 of 60), and the cards are 30,033 and 30,115 bytes against the 30,500 cap.
- **The choice.** The registered tie-break (fewer wrong starts, then the smaller card) picks **T2**. T2 against T1 on their own is
  0 of 40 against 4 of 40, one-sided p 0.058: the data do not show T2 better than T1, and T1 is the smaller change (+22 bytes
  against +104). T2 ships because the rule said so before the data existed, not because the two differ measurably.
- **Prediction check.** Control about 25%: observed 42.5% (the archive's 3 of 12 has an interval of 6% to 57%, so they agree).
  T2 at most 10%: held (0%). T1 "changes little": **refuted** (10% against 42.5%); naming the empty directory in the lead-in
  mattered much more than expected.
- **Exploratory: how often a session read a start verb's `--help` first.** Control 24 of 40, T1 16 of 40, T2 12 of 40. The
  published wording leaves many sessions unsure which verb to use; both edits cut that. Not a registered outcome.
- **Cost.** 180 valid sessions made 820 model calls (mean input peak 42,212 tokens), about 17M to 35M tokens processed with
  cache reads counted: an estimate, since a stopped session reports no totals. Median 30 s to the start in every arm. 137
  attempts made no model call (123 refused by the harness, 14 superseded by the detector fix).

Findings.
- F1, **firm** for this probe: on the Salesforce-style request, Codex Terra at xhigh began with `init` in 17 of 40 sessions on the
  published 2.27.2 card, 4 of 40 with T1, 0 of 40 with T2 (pre-registered, interleaved, one fixed order).
- F2, **firm**: the guards held: 60 of 60 plain and existing-repository sessions began with `workspace start` on all three cards.
- F3, **interim**: T1 and T2 each reduce the wrong route; the data cannot say whether the empty-directory lead-in, the
  current-directory sentence, or both do the work in each, and the two edits were not tested together.
- F4, **exploratory**: the archive's concentration of `init` starts in Salesforce prompts (3 of 12, against 1 of 123 for every
  other prompt) matches the probe: the probe's request is the one that provokes it. The probe's control rate (42.5%) is above
  the archive's overall Codex rate (3.0%), so the saving in real runs will be smaller than the probe's drop.
- Limits as registered: first command only, Codex Terra xhigh only, one Salesforce request; Claude and Grok never chose `init`
  in the archive, so nothing is claimed for them; no minutes, tokens or loops saved are measured.

## Published-build confirmation (registered 2026-11-01, before it runs)

After the release, `start_probe.py confirm` runs 12 sessions of the `sf-ui` request on the build a user installs (the published
marketplace build, `--source marketplace`, same model, effort, stop rule and detector). Prediction: at most 2 of 12 begin with
`init` (T2 was 0 of 40; the published card before the change would give about 5 of 12). It gates nothing already published; 5 or
more of 12 would mean the package differs from the tested arm in a way that matters, and the cause would be investigated before
any further claim. The installed card's hash must equal the release package's card.

**Confirmation result.** 12 of 12 sessions on the published 2.27.3 build began with `workspace start` (0 `init`); the installed
card's hash equals the release package's card on every session and the harness recorded plugin 2.27.3 from the marketplace
(`confirm-output.txt`, `confirm-compact.jsonl`). The prediction held. With 0 of 12 the interval reaches 24%, so this confirms the
package, not the rate: the rate is the 0 of 40 above.

## Replication R2 (registered 2026-11-01, before its first trial)

**Why.** The owner asked for a rerun wherever accuracy needs it. The first batch reached its decision only after four
corrections made while it ran (a help request read as a start, a start form the detector missed, stray observers that blocked
the harness, a port lease held by another session) and a re-read of the stored event streams; its numbers are right as
corrected, but they did not come from one clean run. R2 repeats the whole design in one launch with the final instrument.

**What is the same.** The question, the three requests, the model and effort (Codex gpt-6.1-terra, xhigh, through `run.py`),
the sample sizes (40, 10 and 10 per card), the stop rule, and the decision rule above.

**What is different.**
1. *Base.* The published 2.27.3 package, whose card already carries T2's wording. The cards are rebuilt from it
   (`arms-r2.json`): C is the old wording (T2's edit reversed; hash 772ef68948a6, 30,011 bytes), T1 is the old wording plus T1's
   edit (6fb44b49c5ca, 30,033), T2 is the published card (9588268edbe9, 30,115; the hash the confirmation measured).
2. *Order.* A new random order, seed 20261102 (`plan-r2.json`); one launch; the final driver (the `--help` rule, escaped-quote
   starts, per-trial cleanup, private lease folders for the `repo` request from the start).
3. *Faults.* No fix is made while the batch runs. Six invalid attempts in a row stop it (the driver aborts); a valid session with no
   start, or a command route that differs from the route on disk, is investigated before the result is used. A fault means the cause
   is fixed and the whole batch restarts from scratch; the aborted data stay as evidence and are not pooled.
4. *A second reading of the route.* After each session, before its folders are removed, the driver records what the start left on
   disk: `workspace.md` (the isolated entry) or only `state.md` (the direct entry), and whether the folder became a Git repository.
   `analyze.py` prints it beside the route read from the command.

**Decision.** R2 replicates the first batch if T2 meets all six items against C again. Whatever it shows is reported in full and both
batches stand; a pooled table is descriptive. If T2 fails the bar, or C shows fewer than 5 wrong starts, the first result is not
relied on and the release goes back to the owner (reverting a published release is theirs to decide).

**Prediction.** C 25% to 45% wrong on `sf-ui`, T1 15% or less, T2 5% or less; no guard session starts with `init`; the two readings of
the route agree wherever both are readable.

**Cost.** About 18M tokens and 15 to 35 minutes, as the first batch (estimate; a stopped session reports no totals).

## Evidence

- `arms.json`, `stimuli/sf-ui.txt`, `plan.json`, `start_probe.py`, `analyze.py`: the design. `arms-r2.json`, `plan-r2.json`: the replication's. `start_probe.py reclassify` and
  `rescan` are the two detector corrections of "Deviations" 4 and 6.
- `confirm-output.txt`, `confirm-compact.jsonl`: the published-build confirmation (`start_probe.py confirm`).
- `analysis-output.txt`, `results-compact.jsonl`: the result (the compact rows trim each command; the raw rows are below).
- `start_routes.py`, `recount.py`, `recount-output.txt`: the archive recount (run before any trial).
- Raw run folders (not committed): `~/e2e-runs-startroute/20261101/` (`results.jsonl`, `baselines-probe.jsonl`,
  `trials/<slot>-<arm>-<request>-<n>-a<attempt>/` with `events.jsonl`, `invocation.json`, `result.json`, `metrics.json`).
