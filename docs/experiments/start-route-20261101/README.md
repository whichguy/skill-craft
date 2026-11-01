# Start route: does rewording the card's start section stop the wrong first command?

Status: **pre-registered 2026-11-01**, before the first scored trial. Results: see "Results" (empty until the batch has run).
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

## Results

(pending)

## Evidence

- `arms.json`, `stimuli/sf-ui.txt`, `plan.json`, `start_probe.py`, `analyze.py`: the design.
- `start_routes.py`, `recount.py`, `recount-output.txt`: the archive recount (run before any trial).
- Raw run folders (not committed): `~/e2e-runs-startroute/20261101/` (`results.jsonl`, `baselines-probe.jsonl`,
  `trials/<slot>-<arm>-<request>-<n>-a<attempt>/` with `events.jsonl`, `invocation.json`, `result.json`, `metrics.json`).
