# Start route: does rewording the card's start section stop the wrong first command?

Status: **done 2026-11-01.** Pre-registered before the first scored trial; T2 met the registered bar and shipped as skill-craft 2.27.3 / shiploop 1.26.3 (release f24746fa6193007235818f2d8b109408d70ca413); a published-build confirmation held and a clean replication (R2) held too (see "Results" and "Replication R2: result"). Follow-ups the same day, in the order
they ran: the explicit in-place requests still start with `init` (48 of 48); T2 does nothing either way on Claude or Grok (no regression); a script guard
that refuses `init` in an empty non-Git folder failed its first design (0 of 16 mistaken starts refused, the override was in `--help`) and met every
registered condition in its second (20 of 20), released as skill-craft 2.31.0 / shiploop 1.30.0 (5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a).
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
  **Superseded 2026-11-01:** in R2 the figures were 25, 19 and 23 of 40, so there is no consistent drop; do not rely on it.
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

## Replication R2: result

Run 2026-11-01 07:06 to 07:31 in one launch, 180 slots, the order of `plan-r2.json`, the final driver, no change while it ran:
180 valid sessions in 180 attempts (no invalid attempt, no superseded row, no fault), `analysis-r2-output.txt`,
`results-r2-compact.jsonl`. Wrong = the first ShipLoop start command was `init`.

| request | card | sessions | `workspace start` | `init` | wrong rate (95% interval) |
|---|---|---|---|---|---|
| sf-ui | C, the old wording | 40 | 32 | **8** | 20% (10% to 35%) |
| sf-ui | T1, lead-in names an empty directory | 40 | 39 | **1** | 2.5% (0% to 13%) |
| sf-ui | T2, the published card | 40 | 39 | **1** | 2.5% (0% to 13%) |
| hello | C, T1, T2 | 10 each | 10 each | 0 | 0% (0% to 28%) each |
| repo | C, T1, T2 | 10 each | 10 each | 0 | 0% (0% to 28%) each |

- **The bar.** T2 meets all six items against C again (one-sided Fisher p 0.0144, rate 2.5% against 20%, no session without a
  start, guards 0 of 60, card 30,115 bytes), so **R2 replicates**. T1 meets it too. The analysis script's "ship" line names T1 here,
  because the two tie at one wrong start each and its tie-break takes the smaller card; that line selects between candidates and
  was settled by the first batch. R2 asks whether T2 holds, and it does.
- **Two readings of the route.** The route read from the command and the route read from what the start left on disk agree in all
  176 sessions where both are readable (workspace.md present and the empty folder turned into a Git repository for every
  `workspace start`; only state.md for every `init`); 4 starts were stopped before they wrote anything.
- **The two batches together** (descriptive): C 25 of 80 wrong (31%, 22% to 42%), T1 5 of 80 (6.2%), T2 1 of 80 (1.3%, 0.2% to 6.7%);
  T2 against C one-sided p 5e-08. T2 against T1 alone: 1 of 80 against 5 of 80, p 0.105. The data still do not separate T2 from T1.
- **Prediction check.** C 25% to 45%: observed 20%, **below the range**. T1 15% or less: 2.5%, held. T2 5% or less: 2.5%, held. No
  guard session started with `init`: held. The two readings agree: held.
- **The control's rate is not a constant.** 17 of 40 in the first batch, 8 of 40 in R2 (two-sided exact p 0.053), on packages that
  differ only in version strings; T2 was 0 of 40 and 1 of 40. The comparison inside each batch held both times, but the size of
  the failure on the old wording moves from hour to hour, so a single batch's rate should not be quoted as the rate. R2's 20% is
  closer to the archive's Salesforce-prompt rate (3 of 12).
- **The one wrong start with T2** (slot 68) was `init --repo "$PWD" --run-dir "$PWD/../shiploop-run"` for the Salesforce request: the
  new sentence lowers the rate, it does not remove it. T1's one (slot 132) used a Python one-liner.
- **Cost.** 558 model calls (mean input peak 39,344 tokens), about 12M to 22M tokens processed with cache reads counted (an
  estimate); 30 s median to the start.

## The opposite direction: explicit in-place requests (registered 2026-11-01, before its first trial)

**Why.** Every guard above is a request where `workspace start` is the right first command. T2's sentence says the direct entry
(`init`) is for a run the user explicitly asks to be in place or non-Git; nobody has checked that a session still honors that
request. If the new sentence over-corrects, the published card now costs the user the in-place run they asked for.

**Design.** Same harness, model and effort (Codex gpt-6.1-terra, xhigh, through `run.py`), stop rule and fault policy as R2. Three
requests in an empty folder that is not a Git repository, each asking explicitly (`stimuli/`): `inplace-hello` (the smoke request
plus "I explicitly want an in-place run, with no isolated workspace and no separate worktree"), `nogit-hello` (the smoke request
plus "this folder must not become a Git repository ... a non-Git run, so do not initialize Git") and `inplace-sf` (the Salesforce
request plus the in-place sentence). Two cards: C, the old wording, and T2, the published card (`arms-r2.json`, the same hashes
as R2). 16 sessions per request per card, 96 in all, one launch in the random order of `plan-inplace.json` (seed 20261103). Three
unscored smoke sessions on T2 (one per request) each began with `init`.

**Outcome.** The first start command: `init` is the right one here, `workspace start` ignores the request. The on-disk reading of
the route is recorded beside it, as in R2.

**Decision rule.** T2 *harms* the explicit path if, over the three requests together, its `init` share is at least 20 points below
the control's with one-sided Fisher p below 0.05; a single request is flagged at a 30-point drop with the same p. Otherwise the
verdict is "no harm found", which with 16 sessions per cell cannot see a drop smaller than about 30 points. If the control honors
the explicit request in under 30% of sessions, T2 is judged only on not being worse. A harm verdict means the sentence is reworded
and retested before anything else is built on it, and is reported to the owner.

**Prediction.** C begins with `init` in 70% to 100% of sessions on each request, and T2 is within 15 points of C on each.

### Result of the opposite-direction probe

Run 2026-11-01 07:54 to 08:07, one launch, 96 slots in 96 attempts (no invalid attempt, no fault), on the published 2.27.4
package; `analysis-i1-output.txt`, `results-i1-compact.jsonl`. The first start was `init` (the right one here) in **every**
session: 16 of 16 on each request on each card, 48 of 48 per card. The route read from the command and the route read from the
disk agree in all 96. No session in `nogit-hello` ran its own `git init`, `git config` or `git commit`.

| request | old wording | published card (T2) |
|---|---|---|
| inplace-hello | 16 of 16 `init` | 16 of 16 |
| nogit-hello | 16 of 16 | 16 of 16 |
| inplace-sf | 16 of 16 | 16 of 16 |

**Verdict: no harm found.** The pooled `init` share on T2 is 48 of 48 (95% interval 93% to 100%), so a drop of 20 points, the registered
harm, is excluded; so is any drop larger than about 7 points on these requests. Prediction held (C at 100%, T2 within 15 points of
it). Because the old wording already honored the explicit request every time, this shows T2 broke nothing, not that it improved
anything. Cost: 260 model calls (mean input peak 35,398 tokens), about 5M to 9M tokens (an estimate).

## Other hosts: does T2 hold on Claude and Grok? (registered 2026-11-01, before its first trial)

**Why.** The wording was tuned on Codex Terra, the only host that ever chose `init` in the archive (Claude 0 of 56 starts, Grok 0 of
111, all before T2). Neither host has been run on the new sentence, in either direction: it could make them start with `init`
where `workspace start` is right, or with `workspace start` where the user asked for an in-place run.

**Design.** The same driver, stop rule and fault policy, one launch per host through `run.py`, each host at the harness's own
defaults: Claude `claude-sonnet-5-5` on its own models (`--backend anthropic`, no effort), Grok `grok-4.7` at medium. Two cards (`arms-r2.json`): C, the old
wording, and T2, the published card. Four requests per card (`plan --set hosts`, seed 20261104, `plan-hosts.json`): `sf-ui` 16,
`repo` 8 (an existing Git repository), `inplace-hello` 12 and `nogit-hello` 12 (the explicit requests): 48 per card, 96 per host.
One unscored smoke session per host (T2, `sf-ui`) began with `workspace start` and the card hashes matched.

**Outcome and rule** (`analyze.py --mode hosts`, per host). A host *regresses* if T2 starts with `init` at least 3 times more often
than C on `sf-ui` or `repo` with one-sided Fisher p below 0.05 (T2 more), or if over the two explicit requests together its `init`
share is at least 20 points below C's with one-sided p below 0.05. Otherwise "no regression found", which with these sizes cannot see
a smaller change. A regression is reported to the owner and the sentence is reworded and retested; a host that does not
reach the start in most sessions is reported as unreadable, not as fine.

**Prediction.** Claude and Grok start with `init` in 2 or fewer sessions per card on `sf-ui` and `repo` together, and with `init` in
at least 80% of the explicit sessions on both cards.

**Limits.** Each host is one model at one setting; Claude loads the owner's global instructions, as the harness's Claude host
always does. Small base rates mean this checks for harm, not benefit.

### Result of the other-hosts probe

Both hosts ran the registered plan to the end on 2026-11-01 (`plan-hosts.json`, seed 20261104, one launch per host, `run.py`, the
final driver, no change while they ran): 96 valid sessions each, every slot valid, the installed card equal to the arm's card in
every session (C `dd1a2ebf1d5d`, T2 `fe70f7b8e3b8`; the package the host probe was cut from was 2.28.1, three releases after the R2
build's 2.27.3). Claude `claude-sonnet-5-5` on its own models, Grok `grok-4.7` at medium. `analyze.py --mode hosts`
(`analysis-h-claude-output.txt`, `analysis-h-grok-output.txt`; sessions in `results-h-claude-compact.jsonl`,
`results-h-grok-compact.jsonl`):

| request | card | Claude: first start `init` | Grok: first start `init` |
|---|---|---|---|
| `sf-ui` (the failing prompt) | C, old wording | 0 of 16 | 0 of 16 |
| `sf-ui` | T2, published | 0 of 16 | 0 of 16 |
| `repo` (an existing Git repository) | C | 0 of 8 | 0 of 8 |
| `repo` | T2 | 0 of 8 | 0 of 8 |
| `inplace-hello` (explicit in-place) | C | 12 of 12 | 12 of 12 |
| `inplace-hello` | T2 | 12 of 12 | 12 of 12 |
| `nogit-hello` (explicit non-Git) | C | 12 of 12 | 12 of 12 |
| `nogit-hello` | T2 | 12 of 12 | 12 of 12 |

**Verdict, both hosts: no regression found.** The rule's two triggers were not near: on `sf-ui` and `repo` T2 started with `init`
0 times against 0 for C, and over the two explicit requests the `init` share was 24 of 24 for both cards (drop 0). The prediction held
on both hosts (2 or fewer `init` per card on `sf-ui` and `repo`; at least 80% `init` on the explicit requests, here 100%).

**What it shows and what it cannot.** T2 does not move either host in either direction on these requests, and neither host ever
started the Salesforce request with `init` on the old wording either (0 of 16 each), as the archive said (Claude 0 of 56 starts, Grok 0
of 111). So there is a floor: T2 cannot be shown to help on these hosts, only not to hurt, and with 16 sessions a rate under
about 17% (Wilson upper bound 0.19) could still be hidden in each cell. The sentence's benefit is Codex Terra's.

**Faults.** Claude: 4 invalid attempts (three had no run record, one ended without a skill call), each retried to a valid session
by the driver; they are in `results.jsonl` and are not outcomes. Grok: none. Route readings: Claude's command route and the route
on disk agreed in all 83 sessions where both were readable (13 command only); Grok's stop precedes any write, so all 96 rest on the
command alone, as registered. Median time to the start: Claude 24 s, Grok 65 s.

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

## The `init` guard: what does a session do after `init` is refused? (registered 2026-11-01, before its first trial)

**Why.** T2 fixed the wording (0 of 80 Salesforce-request sessions began with `init` against 25 of 80 on the old wording, pooled over
the first batch and R2), and the other-hosts probe showed no effect either way on Claude or Grok. One of 80 sessions on T2 still
began with `init` in an empty non-Git folder, which leaves a run whose product is never committed (the live run that started this
experiment). The owner asked for a script guard as well (2026-11-01, "All of them"): `init` in an empty folder that is not a Git
repository is refused with the `workspace start` command to run instead, unless the user's own request for an in-place or non-Git
run is stated with `--in-place` (commit d8a8dce097368ae349ba051ec76c83d036e7f2ef, on a branch not yet pushed). A refusal only helps if the session then takes the isolated entry; it harms if
sessions add `--in-place` reflexively, or if it blocks an explicit in-place request.

**Design.** Codex `gpt-6.1-terra` at `xhigh` through `run.py` with `--stop-after-start` (the harness ends the host once a run
exists on disk, so the recovery after a refusal is observed to its end; 288f35c59dd56f65aee82e27ae80630bfcc6ef22). Two builds cut
with `scripts/build-packages.py` from the guard commit (`--package-root`): **G**, the build as it stands (T2 wording plus the guard),
and **GOLD**, G with T2's sentence reversed (the old wording, so that wrong first attempts are frequent enough to observe: 8 to 17
of 40 `sf-ui` sessions on the old wording). Requests (`plan --set guard`, seed 20261105, `plan-guard.json`): `sf-ui` 60 sessions on
GOLD and 20 on G; `inplace-hello` 12 and `nogit-hello` 12 on G: 104 sessions (60 old-wording sessions give at
least 8 refusals with probability 93% at a first-start `init` rate of 20%, the lowest the old wording showed, and above 99.9% at
the pooled 31%). G: card `9571cfb4b317 (30,115 bytes)`, `shiploop_protocol.py`
`7caafc6adf1a`; GOLD: card `4e455a833e85 (30,011 bytes)`.

**Measured per session.** The first ShipLoop start command and its route; whether the guard's refusal appeared (as rendered, with a
path); every start command and whether it carried `--in-place`; the route of the run that exists on disk at the end (`start_route`).

**Rule** (`analyze.py --mode guard`, one launch, no change while it runs, a fault restarts the batch):
- *H1, recovery.* Among `sf-ui` sessions where the guard refused an `init`, at least 80% end on the isolated entry
  (`workspace start`) with a Wilson lower bound of at least 0.50, from at least 8 such sessions. Fewer than 8: "insufficient";
  more old-wording sessions are added to the same batch, not a restart.
- *H2, explicit requests honored.* Over `inplace-hello` and `nogit-hello` (G), at least 80% end on the direct entry, lower bound at
  least 0.50.
- *H3, right starts stay right.* Of the G `sf-ui` sessions that were never refused, at most 1 ends off `workspace start`.
- Reported, not gated: sessions that never made a run; refused sessions that then used `--in-place` without the user's request.
If H1, H2 and H3 are met the guard is released; if H2 fails the message or the flag is reworked; if H1 fails (sessions answer the
refusal with `--in-place`) the guard is not released as it stands. Whatever the result, it is reported in full.

**Prediction.** GOLD begins with `init` in 15% to 45% of `sf-ui` sessions and G in 5% or fewer; of the refused sessions at least 90%
end on `workspace start`; at least 90% of the explicit sessions end `direct` (those that begin with `init` are refused once and
then rerun it with `--in-place`).

**Limits.** One model at one setting, one Salesforce prompt, one pair of explicit requests; the sessions that begin with
`workspace start` never see the guard, so G only measures the guard's cost on right starts through H3. The benefit on the current
card is small by construction (T2 leaves about 1 wrong start in 80); the probe asks whether the guard is safe and effective, not how
often it will fire.

**Cost.** About 104 sessions at roughly a minute and 0.2M tokens each (an estimate from the earlier probes plus one recovery step).

**Command** (one launch, no change while it runs):
`python3 start_probe.py run --host codex --arms arms-guard.json --package-root <build-packages.py output of the guard commit>
--effect-stop --plan plan-guard.json --out ~/e2e-runs-startroute/20261101-guard --jobs 4`; analysis
`python3 analyze.py <out>/results.jsonl --mode guard --export results-guard-compact.jsonl`.


### Result of the first guard probe (104 sessions, 2026-11-01)

One launch, no change while it ran, 104 valid sessions and no invalid attempt; the installed card equalled the build's card in every
session (`analysis-guard-output.txt`, `results-guard-compact.jsonl`). Codex `gpt-6.1-terra` at `xhigh`, builds cut from d8a8dce097368ae349ba051ec76c83d036e7f2ef.

| request | build | sessions | `init` first | refused | ended on `workspace start` | ended on the direct entry | no run |
|---|---|---|---|---|---|---|---|
| `sf-ui` | GOLD (old wording) | 60 | 16 | 0 | 44 | 15 | 1 |
| `sf-ui` | G (T2) | 20 | 0 | 0 | 20 | 0 | 0 |
| `inplace-hello` | G | 12 | 12 | 4 | 0 | 12 | 0 |
| `nogit-hello` | G | 12 | 12 | 8 | 0 | 12 | 0 |

**Registered verdict: INSUFFICIENT.** H1 could not be judged: 0 of the 60 old-wording sessions were refused (8 were needed). H2 held
(24 of 24 explicit sessions ended on the direct entry, Wilson 0.86-1.00) and H3 held (20 of 20 G sessions that were never refused ended on
`workspace start`).

**What the zero means.** 16 old-wording sessions began with `init`, and not one was refused, because every one of the 16 carried
`--in-place` on its first command. Every one of them had run a `--help` on the ShipLoop CLI before its first start (16 of 16; of the 44
that began with `workspace start`, 7 had), and `--in-place` was in `init --help`. Sessions read `references/run-start.md` first (101 of
104), then `run-options.md` (54); none read `references/navigator.md`, the other place the flag was mentioned. So the sessions that had
chosen the direct entry by mistake learned the override before they used `init`, and passed it as the user's request. Effectiveness
(an added line, see below): 0 of 16 first-`init` sessions ended on `workspace start` (Wilson upper bound 0.19). The guard stopped no
wrong start. It refused only the sessions that did not know the flag, 12 of the 24 explicit sessions, all of which then passed it: a
one-command cost on half of the explicit requests, for nothing. On the T2 card nothing began with `init` (0 of 20), so the guard had
nothing to do there either.

**Deviations from the registration, recorded.** (1) The analysis gained the effectiveness line E (of the `sf-ui` sessions whose first
start was `init`, refused or not, how many ended on `workspace start`) and a `--gate` option; I added them at 16 of 104 sessions
when the progress monitor showed three `init` first starts carrying `--in-place`, before the end of the batch, and the registered
H1 gate was not changed (this verdict is H1's). (2) The registered remedy for "insufficient", adding old-wording sessions to the same
batch, was not carried out: 0 of 16 first-`init` sessions were refused, so the refusal rate per `init` start is below 19% (95% upper
bound), and 8 refusals would take at least 42 first-`init` sessions, about 160 more old-wording sessions, and more at any lower rate;
the extra sessions could not change what the 16 show, which is why they were not run. (3) Everything else ran as registered.

**What follows.** A guard whose override a session can read first is not a guard. The cause is specific and cheap to change: the flag
was visible in `--help`, which the sessions that chose `init` read first. A second design hides the override from `--help` and puts
the card's cue in the refusal itself (f9f91667228c1ef719cfb916757cba015e9189c7), and is registered below before its first trial.

## The `init` guard, second design: does hiding the override from `--help` and sharpening the refusal make it work? (registered 2026-11-01, before its first trial)

**Why.** The first probe (above) found the override self-certified in advance: 16 of 16 first-`init` old-wording sessions had run
`--help`, saw `--in-place`, and passed it, so the refusal was never shown to the sessions it was for. The second design
(f9f91667228c1ef719cfb916757cba015e9189c7, on the same unpushed branch as the first) changes two things: `--in-place` is hidden
from `--help` (the refusal and the README name it), and the refusal repeats the card's cue at the moment of the decision ("a request
that names the current directory is not that: `workspace start` returns the finished work there"). `references/navigator.md` no longer
names the flag. Card unchanged.

**Design.** The same as the first probe except the build and the order: builds cut with `scripts/build-packages.py` from the second
commit, G (card `9571cfb4b317`, `shiploop_protocol.py` `87e9798247b1`) and GOLD (card `4e455a833e85`); `plan --set guard`, seed
20261106 (`plan-guard2.json`); `--effect-stop`; sf-ui 60 GOLD and 20 G, inplace-hello 12 and nogit-hello 12 on G (104 sessions).

**Rule** (`analyze.py --mode guard --gate e`). Gate **E**: among the `sf-ui` sessions whose first start was `init` (refused or not),
at least 80% end on `workspace start`, Wilson lower bound at least 0.50, from at least 8 such sessions (60 old-wording sessions gave
16 in the first probe). **H2** and **H3** unchanged (explicit sessions at least 80% on the direct entry, lower bound 0.50; at most 1 of
the never-refused G sessions off `workspace start`). H1 is printed, not gated. Release the guard only if E, H2 and H3 are met. If E
fails, the guard is not released in either design: a script guard whose override the session can self-certify does not stop the wrong
start, and the T2 wording alone stands (the owner decides whether to try anything else, for example reading the request for the
words "in place"; I do not build that, because a language heuristic in the script refuses legitimate requests worded differently).

**Prediction.** E between 50% and 90%: a session refused with the sharper message mostly takes the isolated entry, but some will
still answer with `--in-place` because they believe the request said so. H2 at least 90%: almost every explicit session is now refused
once (it cannot know the flag) and then passes it, so the cost is one command each. H3 holds.

**Limits.** As the first probe: one model and setting, one Salesforce prompt, one pair of explicit requests; the explicit requests now
always pay the extra command, which is a cost of the design, not a fault.

**Command**: as above with `--package-root <build of the second commit>`, `--plan plan-guard2.json`, `--out
~/e2e-runs-startroute/20261101-guard2`.

### Result of the second guard probe (104 sessions, 2026-11-01)

One launch, no change while it ran, 104 valid sessions, no invalid attempt; installed cards equal to the builds' (G `9571cfb4b317`, GOLD
`4e455a833e85`). Builds cut from f9f91667228c1ef719cfb916757cba015e9189c7 (`analysis-guard2-output.txt`, `results-guard2-compact.jsonl`).

| request | build | sessions | `init` first | refused | ended on `workspace start` | ended on the direct entry | no run |
|---|---|---|---|---|---|---|---|
| `sf-ui` | GOLD (old wording) | 60 | 20 | 20 | 60 | 0 | 0 |
| `sf-ui` | G (T2) | 20 | 0 | 0 | 20 | 0 | 0 |
| `inplace-hello` | G | 12 | 12 | 12 | 0 | 12 | 0 |
| `nogit-hello` | G | 12 | 12 | 12 | 0 | 12 | 0 |

**Registered verdict: RELEASE.** E (the gate): 20 of 20 `sf-ui` sessions whose first start was `init` ended on `workspace start` (Wilson
0.84-1.00), none of them carried `--in-place` on that first command (20 of 20 were refused), and none answered the refusal with it. H1 is
the same 20 of 20. H2: 24 of 24 explicit sessions ended on the direct entry (Wilson 0.86-1.00). H3: 20 of 20 never-refused G sessions
ended on `workspace start`. Every refused `sf-ui` session ran `init` once and then `workspace start` (20 of 20); every explicit session
ran `init`, was refused, and ran `init --in-place` (24 of 24).

**Against the first design.** The same old wording, the same request, the same model: first design 0 of 16 first-`init` sessions ended on
`workspace start`, second design 20 of 20. The second design changed two things together: it hid the flag from `--help`, and it added the
card's cue to the refusal. The data support the first (the first design's 16 pre-emptive passes of the flag all followed a `--help` that
showed it; none of the second design's 20 passed it before the refusal; of the 20, 7 had run a `--help` and 13 had not). They cannot
separate the cue's part in what the sessions did after the refusal (all 20 took `workspace start`), because the first design had no
refused wrong start to compare with (Astra's review, below). The prediction (E between 50% and 90%) was too cautious.

**Costs, measured.** Every explicit in-place or non-Git session now pays one refused command (24 of 24; with the flag in `--help`
it was 12 of 24). On the old wording the refused sessions took a median 50 s to reach their run against 44 s for the old-wording
sessions that were not refused; that is an observation of two groups that took different routes, not a measured cost of the refusal.
On the T2 card nothing changed (0 of 20 began with `init`).

**Limits.** Codex `gpt-6.1-terra` at `xhigh` only; Claude and Grok never began the Salesforce request with `init`, so their answer to
the refusal text is untested (the text is plain and names the command to run); one Salesforce prompt and one pair of explicit requests.
A user or script outside this repository that runs `init` in an empty non-Git folder now needs `--in-place` (the message says so).
The guard's benefit on the current card is small by construction (T2 leaves about 1 wrong start in 80 on Codex); what the probe
establishes is that it is safe and effective when a start is wrong, and that the old wording's failure would be caught.

**Decision.** Released with the second design, as registered (E, H2 and H3 met). The first design is not released. Published as
skill-craft 2.31.0 / shiploop 1.30.0 in 5c9bf5e8786a1d44a1389a3b98fa8c5da3c05a8a (the guard d8a8dce097368ae349ba051ec76c83d036e7f2ef and its second
design f9f91667228c1ef719cfb916757cba015e9189c7; the journal entries behind the release gate are in `test/shiploop_e2e/LEARNINGS.md`).

**A side effect of the probes, found by another session.** The Salesforce prompt makes a session run the real `sf` in the trial's
throwaway HOME before its run exists. On macOS the CLI's first org command there raised a "Keychain Not Found" dialog on the owner's
screen and left a `security add-generic-password` child (parent 1, working directory in the trial's work folder, for example
`20261101-guard/trials/098-GOLD-sf-ui-13-a1/work`) that the driver's per-trial cleanup, which matched command lines, did not reach. The
fix for the harness is f9717c93631ae068bec75c6dc9238a2f878cc8ec (`SF_USE_GENERIC_UNIX_KEYCHAIN` in every throwaway HOME); the driver's
`reap` now also matches the working directory. Whether a measure changed is not established by the medians (44 to 50 s): a session that
waited on a dialog would show as a tail, and there was no invalid attempt in either guard launch, which is weaker than "none waited". What the
stored sessions do show (Astra's review, below): in every stored event stream, 17 sessions ran the real Salesforce CLI as a program, and
their commands were `sf --version` (17), `sf data query --target-org de` (3) and `sf org list` (1), all read-only, none on the Claude
host; no session ran a deploy, an Apex run or a data write (the many matches of those commands are the request text written to a file).
The exposure is structural all the same: the request tells a session to deploy, the Claude host keeps the real HOME, and a probe stops at
the first run, not before.

### Post-release checks of the published build (2.31.0 / 1.30.0, 2026-11-01)

- *The published bytes, no model.* `init --repo <empty folder> --run-dir <beside it>` from the marketplace copy of the plugin exits 2 with the
  refusal and creates nothing; `init --help` does not mention `--in-place`; with `--in-place` the run starts. `docs/distribution.md`'s
  clean-install probes (`docs/experiments/clean-install-20261101/probes.sh`, a disposable Claude config, Python 3.9 and 3.7) printed output
  identical to the committed 2.27.x output once paths, version and packet size are normalized, and the install reported
  `skill-craft@whichguy 2.31.0 enabled`.
- *A live case from the published build.* `run.py --case hello --host codex --source marketplace` (a fresh Codex profile, Terra 6.1 at
  `xhigh`): `PASS every verdict passed`, marketplace versions skill-craft 2.31.0 / ShipLoop 1.30.0, `shiploop PASS done`, exited rc=0 in
  569.8 s, both product checks passed, no refusal in the stream (it began with `workspace start`, recorded as `"start_route": "workspace"`
  in `result.json`: the harness field of this series, read from the disk in a real full run). n = 1: it shows the guard does not get in the
  way of an ordinary run, not a rate. Output: `~/e2e-runs-startroute/20261101-release-smoke-codex`.
- *Hosts.* `claude plugin update skill-craft@whichguy` took Claude's install from 2.30.0 to 2.31.0 (a restart applies it); the Codex and Grok
  marketplace refreshes show skill-craft 2.31.0 / ShipLoop 1.30.0 with the guard in their copies. Cursor is the owner's, in its app.

## Astra's review (2026-11-01, after the work had shipped)

Not asked before the plan went to the owner or before the guard shipped, against the owner's standing rule that design feedback goes to
Astra at max effort; asked on the owner's question afterwards. The brief, the runner's report and Astra's answer verbatim are in
`astra-review-2026-11-01.md` (gpt-6-astra, effort max, read-only, no fallback). Each finding below was checked against the code or the
stored runs before it was relied on; "done" names what changed, and the commits that did it are in the history of this folder.

| Astra's finding | What I checked | Disposition |
|---|---|---|
| P0 probe containment: a probe stops at the first run, not before it; the Salesforce request tells the model to deploy; the Claude host keeps the real HOME; Codex runs with full access in a throwaway HOME | Source confirmed. Scan of every stored stream: 17 sessions ran `sf` as a program, all read-only (see the side-effect paragraph above), none on the Claude host | Not fixed in the driver. Open for the owner: future probes should use a request that keeps the "current directory itself" wording and drops the live-org actions |
| P0 `reap` matched path prefixes and any owner | Confirmed in the code; `/t/trial-a1` would have matched `/t/trial-a10` | Done: matches by path component and by owner; checked against a neighbouring trial |
| P1 `start_route.route` credited `workspace` on `workspace.md` alone | Confirmed: `prepare` writes it before the internal init, and a blocked one is possible. All 80 workspace endings of the second guard probe (the 20 recoveries among them) and all 64 of the first had a `state.md` on disk, so no result moved | Done: a run state is required; a probe records the first route its watcher saw |
| P1 the command detector counts a help request that names `--repo` and printed text, takes an unrelated `['init']` list for a start, and misses `$CLI` without the word shiploop | Reproduced all four | Done for the help request; the other three are recorded as expected failures in `check_analyzer.py`. In the effect-stop probes the route that decides is read from the disk |
| P1 the analyzer prints RELEASE for a partial design, NO REGRESSION FOUND for a host with no starts, and takes card sizes from today's card | Reproduced all three (RELEASE for 8 old-wording and 4 explicit sessions; `arms.json` gave 30,115 and 30,137 bytes) | Done: missing cells and planned slots make a verdict INSUFFICIENT, an unreadable host is reported as such (as registered), H3 cannot pass on nothing, recorded sizes are used. `check_analyzer.py` replays all 7 committed batches and each keeps its conclusion |
| P1 validity checks the card hash, not the script that holds the guard; a session that never touches the skill is retried as invalid | Confirmed (one Claude row) | Done: the driver also records and checks the guard script's hash. The retry of a no-skill session is kept and noted in the checklist |
| P1 the guard refused a folder holding only an empty `.shiploop` and sent the session to a `workspace start` that then failed | Reproduced on the released 2.31.0 CLI: the empty folder recovers, the `.shiploop` and `.shiploop/.lock` folders do not | Done in the next patch release: such a folder is not refused (the card's non-empty route); a test runs the printed recovery |
| P1 the printed command drops `--delivery-contract`, `--delegation`, `--lint`, `--backchain-passes`, `--planning-review` and `--improve-skill` | Confirmed | Done in the same patch: the command repeats them; a test runs the recovery and reads the options from the new run |
| P1 the Git diagnostic is read in English only | Confirmed | Done: the probe runs under `LC_ALL=C` |
| P1 no outcome-level check for direct runs (`workspace_completion_guard` covers isolated runs only; `_commit_stage` skips a step with no base) | Confirmed in `shiploop_protocol.py` and `shiploop_navigator.py` | Open for the owner: this is the protection the original incident needed; the entry guard only makes the wrong entry rarer |
| P1 hidden-from-help is a bundle with the sharper refusal; the other hosts were probed before the refusal existed | Confirmed (see "Against the first design") | Wording corrected. Open for the owner: a cross-host recovery screen (Astra sketches 36 short sessions) |
| P1 the release gate no longer reads a conflict resolution's own text; default history simplification hides non-merge commits (797 against 806 here) | Confirmed; the 9 hidden commits are from 2026-09-15 to 2026-09-27, none in a current release interval | Open for the owner: exempt mechanical merges only, and use full history; not changed |
| P2 17/40 against 8/40 is not drift; one prompt; H2 tolerated 4 of 24 explicit requests dishonoured; "50 s against 44 s" is observational; "no measure changed" | Agreed on each | Wording corrected above; the checklist asks for a high bar on paths that must not be harmed and for blocked replication when the question is variation over time |
| P2 fixtures changed from plain folders to `git init -q` change the behaviour they exercise | Agreed: 15 suites now exercise the Git case where they exercised the non-Git direct case | Open for the owner: restore `--in-place` in them |

Astra's "do not change" list matches what stands: T2, the direct entry on the card, no silent Git bootstrap in `init`, the refusal before
the run lock, the failed first design kept in this journal, the stop-race test fix, the bounded teardown retry as a disclosed mitigation,
and first-start probes as a cheap tool that does not certify delivery. Its remark that "E2E cases start with workspace start" is a weak
reason for the guard commit's `No-E2E-Round` trailer is right: the probes are the evidence, as the entry in `test/shiploop_e2e/LEARNINGS.md` says.

## Release CI

The full CI run of the release commit f24746fa6193007235818f2d8b109408d70ca413 (run 41318115086) failed one job, `full /
shiploop-3`, on `test_a_document_rerun_is_held_to_the_count_the_test_stage_accepted` in `shiploop-test-loop`: `OSError: [Errno 39]
Directory not empty: '.../repo/.git/objects'` raised by `tempfile` while it removed the test's temporary Git repository, a cleanup
race, not an assertion about the card. The test passes alone (3 of 3 locally), every other job of the run passed, and rerunning the
failed job passed, so the run ended green. The same class of race was fixed for another fixture in
f48df6587d78cf3e958120382128e072cfa948f4 (isolate ephemeral fixtures from progress writers); this test's temporary repository is not isolated that way.

**Follow-up (2026-11-01).** No writer was found: the suite starts no thread or process, `run_suites.py` already sets
`SHIPLOOP_PROGRESS=off`, the named test passed 150 of 150 runs alone and the whole class 8 of 8 times (4 at a time) under a load above 80.
fbcbf0d53345b3e65f24b316a3df1125bfc2ec20 repeats the fixtures' directory removal (up to 5 passes, the last error raised) in the four
real-Git fixtures of that file instead; whether the failure returns is the test of it. The CI run that failed:
https://github.com/whichguy/skill-craft/actions/runs/41318115086.

## Evidence

- `arms.json`, `stimuli/sf-ui.txt`, `plan.json`, `start_probe.py`, `analyze.py`: the design. `arms-r2.json`, `plan-r2.json`: the replication's.
  `stimuli/inplace-*.txt`, `stimuli/nogit-hello.txt`, `plan-inplace.json`: the explicit in-place set (`plan --set inplace`, `analyze.py --mode inplace`).
  `plan-hosts.json`: the other-hosts set (`plan --set hosts`, `start_probe.py run --host claude|grok`, `analyze.py --mode hosts`). `start_probe.py reclassify` and
  `rescan` are the two detector corrections of "Deviations" 4 and 6.
- `confirm-output.txt`, `confirm-compact.jsonl`: the published-build confirmation (`start_probe.py confirm`).
- `analysis-r2-output.txt`, `results-r2-compact.jsonl`: the replication's result. Raw rows: `~/e2e-runs-startroute/20261101-r2/`.
- `analysis-i1-output.txt`, `results-i1-compact.jsonl`: the opposite-direction result. Raw rows: `~/e2e-runs-startroute/20261101-i1/`.
- `analysis-output.txt`, `results-compact.jsonl`: the result (the compact rows trim each command; the raw rows are below).
- `start_routes.py`, `recount.py`, `recount-output.txt`: the archive recount (run before any trial).
- Other hosts: `analysis-h-claude-output.txt`, `analysis-h-grok-output.txt`, `results-h-claude-compact.jsonl`, `results-h-grok-compact.jsonl`.
  The guard probes: `arms-guard.json`, `plan-guard.json` and `plan-guard2.json` (`plan --set guard`), `analysis-guard-output.txt` and
  `results-guard-compact.jsonl` (first design), `analysis-guard2-output.txt` and `results-guard2-compact.jsonl` (second design);
  `start_probe.py run --effect-stop --package-root <build>` and `analyze.py --mode guard --gate e` are the instruments, and
  `analyze.py --replicates` prints whether a second batch repeats a selection.
- Raw run folders for the follow-ups (not committed): `~/e2e-runs-startroute/20261101-h-claude`, `-h-grok`, `-guard`, `-guard2`.
- Raw run folders (not committed): `~/e2e-runs-startroute/20261101/` (`results.jsonl`, `baselines-probe.jsonl`,
  `trials/<slot>-<arm>-<request>-<n>-a<attempt>/` with `events.jsonl`, `invocation.json`, `result.json`, `metrics.json`).
