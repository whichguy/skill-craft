# test-harness skill journal

Living record for the `test-harness` skill: what was asked, what was measured, what was decided and why. Newest round last.
Finding status: **firm** (reproduced, or read from the code), **interim** (one observation), **exploratory** (a lead),
**superseded** (kept, marked, with the date and the reason). Evidence lives in `docs/evidence/test-harness-20261108/summary.json`.
No person, account, machine path or private project name is recorded here or in the skill. The source repository is
identified only by a commit hash.

## Request and consumers

Owner, 2026-11-08, through a triage of personal skills for public release: only generic skills go public, and this one ranked
first of 24 (bash and Python standard library, no network; its own suite reported 266 of 266 assertions passing from a clean
export, in 61 s, on one macOS machine; a public sibling's reference already names an installed `test-harness` as an optional
gate). Preparation stops at the repository checks and `scripts/release.py --dry-run`. Publishing needs a separate, explicit
"publish"; the approval given for an earlier skill's release does not carry over.

Reading: one skill leaf, `test-harness`, script-backed. Consumers: an agent in any host that can run bash and Python (reads
the card, runs `scripts/run-harness.sh`), an operator reading `report.html` or `results.md`, CI (the hermetic suite
`test/test-harness.test.py`), and `skills/backchain/references/harness.md`, which names an installed `test-harness` and its
`references/gate-snippet.md`, `references/local-change-gate.md` and `scripts/run-harness.sh`; all three still exist.

## Round 0 - sources and repository state (2026-11-08)

- Export: `git archive` of `skills/test-harness` at commit `41ee32f1ba2abe1e9bb432fb4fb9cf4f82ae14ee` of a private repository.
  22 files, 390,528 bytes, as the triage counted. Tracked files only; the live folder was never copied. The SHA-256 of every
  exported and shipped file is in the evidence file, so a reader holding the source can check what changed.
- Base: `origin/main` at `d4ff1a47ce89aec5ee546d1601c401850561c58f` (24 skills; release 2.35.7 and the `sport80` 0.1.1 record).
  Work happened in a new worktree and branch cut from it; the main checkout was not touched.
- Main moved twice while this was being built, and the other candidate landed first. First `a4c773afb6c6320af4b54bedf801985e097aacd9`
  (releases 2.35.8 and 2.35.9, two new apparatus suites), merged into the branch, as the repository does, in
  `74653f0365f49464ef05f91678e7e5b44a20301b`; then `03f68d93a44500aca958db74440c1483e9038e11` ("release: skill-craft 2.35.10,
  pushpress 0.1.0": the other candidate), merged in `09297ba07cbad85b125e32baaf7cf8a2ce00987b`. The feature commit is
  `162d8b6e16433329f54a6cd953d5cb42a0891c15`. Each merge had one conflict, in the suite counts in `test/test-groups.test.py`,
  resolved to core 60 and total 202, then core 61 and total 203. This journal and the evidence file describe the tree of the
  second merge.
- Rules that bind (AGENTS.md, `changes/README.md`): a new skill's first note is `version: 0.1.0`; the suite is registered in
  `test/suite_catalog.py` and `test/suite_durations.json` and counted in `test/test-groups.test.py` as `sport80` did in
  `c1c1cf5b638e5c1bafe06820163a40951baf794b`; the registration must not assert that the pending note exists, because
  `scripts/release.py` consumes it (`f7b66f577ea5f656dd21971ddf42cfa364463e18`); release output is written only by
  `scripts/release.py`. The sport80 journal records an owner note of 2026-10-29: no `Co-Authored-By` trailer. This work follows it.

## Round 1 - does the source's own suite pass? (2026-11-08)

Question: the triage reported 266 of 266 assertions. Does that hold here, and is it a property of the skill or of the machine
it ran on?

Conditions: the unmodified export copied to scratch, `HOME` and `TMPDIR` redirected to fresh scratch folders, no network, one
run at a time, exit code captured directly. Other work was loading the machine (load average sampled once while the first
four runs were going: 88 over 1 minute, 71 over 5, 44 over 15, on 18 CPUs); a Python start measured 28 ms at the median, so
interpreter speed was not the cause.

Result: four of four runs gave **264 passed, 2 failed, exit 1**, in 87 to 90 s, and failed the same two assertions each time
("hard lifecycle duration stays below advertised cap" and "blocked path setup finishes below advertised cap"). A fifth run,
after the other work on the machine had stopped (1-minute load average 9 to 11), gave **266 passed, 0 failed, exit 0, in 50 s**: the
triage's figure holds on a quiet machine and fails on a busy one.

| Run | Machine load | Passed | Failed | Exit | Wall |
|---|---|---|---|---|---|
| unmodified, run 1 | busy | 264 | 2 | 1 | 90 s |
| unmodified, run 2 | busy | 264 | 2 | 1 | 87 s |
| unmodified, run 3 | busy | 264 | 2 | 1 | 87 s |
| unmodified, run 4 | busy | 264 | 2 | 1 | 87 s |
| unmodified, run 5 | quiet (1-minute average 9 to 11) | 266 | 0 | 0 | 50 s |

Reading: both assertions time a supervisor whose cap is 1 s from the outside and require the total to stay under 1000 ms. The
supervisor keeps about 100 ms of design margin at that cap (`accounting_margin = min(0.25, max(0.05, timeout / 10))`), and the
measurement adds interpreter starts and scheduling delay on top. They pass on an idle machine (run 5) and fail on a busy one.

## Round 2 - reading every shipped file (2026-11-08)

A pattern scan finds shapes, not sentences, so every file was read: the card, all seven references, all twelve scripts, and the
2,800-line self-test. (The two longest files were read in full for code and, for the report generator's rendering half, by
extracting every comment and string literal.) What reading found that a scan of names could not:

- **F3 (firm) The triage listed one default run root; there are two.** `run-harness.sh` names one, and the hard supervisor
  names another. The supervisor is the one that decides in practice: `run-harness.sh` always re-executes under it, and the
  supervisor names the run directory and passes it down. Both defaulted to a host's home directory.
- **F4 (firm) The unmodified self-test wrote under the caller's home.** Every case that ran the driver before the fix-loop
  smoke case left the run root unset, so records went to the default run root. After a run with `HOME` redirected, the
  scratch home held a host-named directory with 4 run folders under 2 slugs. After the change it holds nothing.
- **F5 (firm) The report generator labelled ordinary tests with another project's claims.** `emit-report.py` shipped five
  case-grouping rules keyed to one private project's test-name vocabulary, each with a "what this verifies" sentence. Fed five
  ordinary names (`test_compile_succeeds_on_empty_input`, `test_when_user_is_anonymous`, `test_import_rejects_bad_csv`,
  `test_nested_dict_roundtrip`, `test_harness_setup`), the unmodified code put all five into groups whose title and
  verification sentence were written for a different project (three distinct groups), and none of them describes the test.
  That is a false verification claim in the report of any other project. All five rules are removed; names fall back to the
  path-shaped group or the generic group, whose claim is "suite-reported case (see name)", and the same five names now all
  land there.
- **F6 (firm) Discovery carried adapters for one private project's layout.** A tier keyed to a particular pair of files and a
  hard-coded fast subset command, a preference for one specifically named `run_<name>.test.sh`, and a runner path inside
  another private skills folder. A generic user's repository never matches them; they named private files. Removed. A
  project whose layout is not recognised pins its suite with `.test-harness.yml` (tier 1.5, already there). The plain
  layouts are unchanged and pinned. The remaining hermetic-suite tier was renamed 3b, since 3b no longer exists beside it.
- **F7 (firm) A default forbidden phrase from one project's state machine.** `DEFAULT_FORBID` held a sentence from a private
  project's runtime beside `Traceback`, so any suite that printed it would have failed the control-channel check. Removed.
  The self-test's required-marker example used the same project's exit code and marker; it is now a neutral marker and code.
- **F8 (firm) Fixtures named other tools' real tests and skills.** Skill folder names, a backlog path, and the real suite names
  and an error line (with a measured duration) of a published runner. Replaced by invented labels in the same shapes (one label
  stays longer than the 55-column pad, because the case exists to cover it).
- **F9 (firm) Environment-variable and directory names of other tools in recognisers.** The live-gate pattern listed three
  other tools' names (one already covered by the generic `*_LIVE_TEST`), and the ambient-directory list named one tool's
  working folder (redundant: an ignored write outside product paths is a note anyway, and a project can list its own with
  `ignored_write_note_globs`). Removed, together with the two layout-specific `skills/<name>/...` entries in the product
  prefixes. Names of other tools in code comments are reworded.
- **F10 (firm) The triage called `references/dogfood-matrix.md` a run log. It is a pin table.** It holds generic cases only.
  It is kept as `references/self-test-matrix.md`, with two cases added that the self-test already pins; only
  `references/dogfood-log.md`, which recorded runs of private repositories, is deleted.
- **F12 (firm) Two dummy credentials were shaped like secrets in source.** A `Bearer` fixture appeared as a literal in two
  files; it is now assembled at run time, as the provider-shaped fixtures already were.

## Round 3 - an independent read (2026-11-08)

After my own read, a fresh read-only agent was given a frozen copy of the shipped files, the owner's rule, and none of my
conclusions. It read every file in full and reported 25 items (4 high, 10 medium, 11 low). I checked each against the code.
My first pass had been too lenient in one place and had written one false sentence in this journal; both are corrected.

- **F11 (firm) Report features keyed to private output vocabulary, which I had left in as "inert".** An excerpt block for one
  tool's `CONCLUSION` / `RESULT outcome=` output format; two rollup rules for one project's banner (a case named `chain` or
  `suite`, or a line starting `PASS chain`, was silently dropped from the inventory of any other project); four observation
  tokens with their own report section; `CONTROL` and `DATA` word counts shown as columns; a live-gate name. All removed.
  The journal had said each was "described in `references/report-template.md`"; that was false.
- **F14 (firm) Documents that said something the code does not do.** The report template called the driver once-only
  ("fix-loop is the agent's slash command") and listed the report sections in a different order from the generator's; the
  taxonomy named `git checkout` for a restore the code does with `git restore --worktree` (which never touches the index),
  and a `fail if tracked pollution` rule that no code path has; the card said discovery searches the repository root for its
  config (it reads only the package root) and that `--full` gives a 3,600 s suite budget (only when the profile resolves to
  `full`); the generator's next-step text told the reader to "re-run without --once" for a fix loop, which is `--mode
  fix-loop`; the card listed 16 of its 20 package files. All corrected, and `<slug>` is now defined as the sanitized basename of `--repo`.
- **F15 (firm) Behaviour the card did not state.** The suite command runs under `bash -lc`, so the caller's login profile is
  sourced; fix-loop adds a branch and a worktree registration to the repository under test; the raw logs in a run record are
  private but not redacted. All three are now in the card's honest limits.
- **F16 (firm) Two non-portable dependencies.** The printed "Open:" line and the report's dive-in commands used `open`, which
  exists on macOS only, while the frontmatter declares Linux; the self-test needed ripgrep for one check and passed vacuously
  without it. The commands now print the path and say to open it in a browser, and the check uses `grep`.
- **F17 (interim) The self-test's count is a count of recorded checks.** 34 of them are unconditional `assert "<name>" true`
  markers after Python heredoc checks that already abort the script (`set -e`) on failure, so a failure is never silent, but the
  number is not that many independent checks. The wrapper's floor of 270 guards against a truncated run, not against a weak
  one, and a comment at the `assert` helper says so.

Left as they were, on purpose: the dead `ignored_write_fail_under` branch in the classifier (the key is not accepted by the
policy loader; removing it is redesign); the optional `test/harness-allowlist.yml` policy path; the `suite:` header cue in the
supervisor's attempt-line pattern; discovery marking its path guesses `fast` (a design choice the card states); the `runs/`
and `reports/harness` ambient globs; this journal's process details and source commit hash (the owner decides those).
The same reader then re-read the files that had changed. It confirmed 21 of the 25 as fixed, found three still partly open (a
harness directory missing from the taxonomy, a pair of fixture files whose purpose was unexplained, and discovery's `fast`
guesses not reflected in the card's profile gate), agreed to leave the rest, and reported 10 new items (4 medium, 6 low). All
10 are fixed except one that was already moot: it read an older copy of this journal. The medium ones, which were real:
- **F18 (firm) Two defects in the source that a generic user meets.** `ignored_write_note_globs` is documented as a policy key,
  but the YAML reader did not treat it as a list: its items were appended to whichever list key came before it (so they could
  become forbidden output strings) or dropped; it worked only in the JSON form. And the fix-loop branch name was built from
  the raw repository folder name, so a folder such as `my repo.v2` made `git worktree add -b` fail (exit 255, "not a valid
  branch name") and fix-loop was unusable there. Both are fixed and each has a self-test case; the whole driver was also run in
  fix-loop mode in such a folder and passed.
- The card's profile gate said `fast` needs documentation, a flag, a fast-named target or config, while the discovery table
  returns `fast` for built-in path guesses; the gate now says so, and says what `fast` unlocks.
- The taxonomy and this journal both promised the `ignored_write_note_globs` key worked in YAML (see F18).

## Round 4 - what changed, file by file (2026-11-08)

| File | Change |
|---|---|
| `SKILL.md` | Frontmatter (`version: 0.1.0`, `license: MIT`, `platforms`, `metadata.skill_craft.kind: script-backed`); a Binding section that names the package root, the repository under test and the write root apart; `SKILL_ROOT` for the card's `SKILL_DIR`; a neutral run root; generic examples; the sentence naming other tools replaced; a generic example card; the package list completed; Honest limits (platforms, recognised output shapes, branch and worktree, login shell, unredacted raw logs). |
| `references/local-change-gate.md`, `gate-snippet.md` | `SKILL_ROOT` bound from the loaded card; the `$HOME`-based default and the owner's consumer table replaced; the discovery table loses the named wrapper; no macOS-only command. |
| `references/discovery-matrix.md` | The project-specific adapter tier, the named wrapper and the test-kit entry removed; the hermetic-suite tier renumbered 3b; a note on `.test-harness.yml`; the profile gate says built-in path guesses give `fast`; the Makefile tier as the code behaves. |
| `references/report-template.md` | Neutral run root; the shapes of suite output the report understands; section orders as emitted; the driver described as both modes. |
| `references/side-effect-taxonomy.md`, `operator-guide.md` | The restore command and two classes as the code behaves; no model-provider wording; a portable way to open the report. |
| `references/self-test-matrix.md` | Renamed from `dogfood-matrix.md`; two pinned cases added. `dogfood-log.md` deleted. |
| `scripts/run-harness.sh`, `scripts/run-harness-hard-supervisor.py` | Default run root `${XDG_STATE_HOME:-$HOME/.local/state}/test-harness/runs` in both; `TEST_HARNESS_RUN_ROOT` still overrides; no `open` line. |
| `scripts/discover-test-cmd.sh` | Private-layout adapter, named wrapper preference and test-kit entry removed; tier renamed 3b. |
| `scripts/emit-report.py` | No default group rules; tagged control lines (`[tag] text`) instead of two named prefixes; no CONCLUSION excerpt, no observation tokens or section, no CONTROL / DATA columns, no rollup rules for one banner; suite-rollup naming; next steps and dive-in text as the driver behaves; comments reworded. |
| `scripts/classify-side-effects.py`, `scripts/control_policy.py` | Live-gate pattern, ambient list and product prefixes lose tool and layout names; the private default forbid, marker and exit code removed; the bearer fixture assembled; `ignored_write_note_globs` read as a list in YAML policy files (F18). |
| `scripts/worktree-fixloop.sh` | The fix-loop branch name is the repository folder name reduced to letters, digits, `_` and `-` (F18). |
| `scripts/test-harness-tests.sh` | Run root exported to a scratch folder at the top; invented fixture labels; slack on external wall-clock caps and a 10 s budget for the two hang cases (below); default-run-root cases added; a case for the YAML glob key and one for a folder name with a space and a dot (F18); `grep` for `rg`; a comment at the `assert` helper about markers. |
| `test/test-harness.test.py` | New: runs the self-test in a scratch home, checks the packaging contract, and lints the shipped files on the shapes of an email, a home path, a host home directory and a secret, proven on seeded leaks. |
| `test/suite_catalog.py`, `test/suite_durations.json`, `test/test-groups.test.py` | One core suite registered; counts core 59 to 60 and total 199 to 200 (202 on the merged tree, where main had added two). |
| `changes/test-harness/initial.md` | First-release note, `version: 0.1.0`. |

Timing decision. The two failing cases compare wall time measured from outside with a 1 s cap; they now require the cap plus
1,500 ms of slack (overridable by `TEST_HARNESS_TEST_TIMING_SLACK_MS`), because the property under test is that a
60-second TERM-ignoring child or a blocked path resolver is cut off at the cap. One strict check was added where the product
records its own monotonic clock (`hard-timeout.json` `elapsed_ms` is under 1000). Two further cases hung in the classifier or
the report writer under a 4 s budget; under load that budget was spent on setup and the run ended as
`STOPPED_TIMEOUT_BUDGET` before the hang was reached (three more failures in the first modified run). They now use 10 s.
Rejected: widening every cap, and passing if any of several attempts passes (it would hide a supervisor that is sometimes slow).
The suite is registered at 90.0 s: 91 s was the slowest wrapper run (under load, inside the quick tier) and 68 to 71 s the
quiet ones; the quick-tier audit limit is 120 s.

## Round 5 - verification (2026-11-08)

Every command was run with its exit code captured directly, not through a pipe. The evidence file holds the counts and the
machine load for each self-test run (`self_test_runs`) and every other check (`checks`).

| Check | Result |
|---|---|
| The bundled self-test, run from the worktree with `HOME` and `TMPDIR` in scratch folders, final content | 279 recorded checks, 0 failed, exit 0, 69 s at a 1-minute load of 9 |
| The same script again from the worktree, on the second merged tree | 279, 0 failed, exit 0, 80 s at a 1-minute load of 14 |
| The same script in a Debian 13 aarch64 container (bash 5.2, Python 3.13, git 2.47; no network; skill mounted read-only) | 279, 0 failed, exit 0, 58 s |
| The same script, intermediate content (276 checks), under load (1-minute average 55 to 85) | 276, 0 failed, exit 0, 111 s |
| `python3 -B test/test-harness.test.py` | 8 tests OK, exit 0, 78 s before the merges; 77 s inside the quick tier on the first merged tree |
| `node test/skill-frontmatter.test.js` | PASS 25 skills, exit 0 |
| `python3 -B test/test-groups.test.py` | 61 tests OK before the merges; 64 OK on the first merged tree (core 60, total 202) and on the second (core 61, total 203), exit 0 |
| `scripts/build-packages.py`, then `scripts/check-marketplace-packages.py --root` on its output | exit 0 and 0, on the first and again on the second merged tree; the packaged copy of the skill is identical to the source, no symlinks; the second package holds 26 skills |
| `python3 -B scripts/release.py --dry-run` | exit 0: `test-harness 0.1.0 -> 0.1.0 (1 note)`; `skill-craft 2.35.7 -> 2.35.8` before the merges, `2.35.9 -> 2.35.10` on the first merged tree, `2.35.10 -> 2.35.11` on the second |
| `python3 -B scripts/check-release-boundary.py --base origin/main` | exit 0, OK, on the first and on the second merged tree |
| `bash test/run-all.sh --group quick --changed-from origin/main --jobs 4` on the first merged tree | exit 0: 17 suites in 249 s; this suite 77 s |
| The same quick tier on the second merged tree | exit 0: 17 suites in 259 s; this suite 73 s |
| `node test/skill-frontmatter.test.js` on the second merged tree | PASS 26 skills (this skill and the other one side by side), exit 0 |
| The same quick tier before the merge | exit 1, 46 suites in 408 s, one failure: this suite's tree-unchanged assertion tripped because I deleted a stray bytecode directory while the run was going. The wrapper alone then passed; the assertion now ignores bytecode caches. |
| Privacy gate: an external scan with a 44-entry denylist kept outside the repository, every path its own argument | 25 files, about 451,000 bytes on the last run (the skill, the note, the wrapper, this journal and the evidence file; 24 files and 427,327 bytes before the evidence file existed); no email, home path, host home directory, secret shape or URL; no private name from the denylist (its `pushpress` entry, written while that skill was unreleased, matches two quotations of the public release commit subject on `main`); loopback addresses only; vendor mentions reviewed (provider hostnames and standard environment-variable names used as redaction and live-call data, one CSS property, one document name) |
| Controls for that scan | seeded leaks in all five categories found (exit 1); an unquoted variable holding two paths in zsh is refused as one non-file argument (exit 2); no paths refused (exit 2); a clean file alone reads and passes (exit 0) |
| Independent reads | pass 1: 25 items; pass 2: 21 of them fixed, 3 partly open, 10 new; everything real is fixed (Round 3) |

The first modified run failed three checks before the hang-case budget was raised (273 of 276 at a load of 155; see the timing
decision in Round 4). The wrapper's own lint reads this journal and the evidence file, so both are held to the same four shapes
as the skill.

## Round 6 - the other candidate and the shared files (2026-11-08)

Another candidate skill was prepared in parallel, on its own branch from the same `origin/main` (`d4ff1a47ce89aec5ee546d1601c401850561c58f`).
It was released first (`03f68d93a44500aca958db74440c1483e9038e11`, skill-craft 2.35.10), and the conflict described below happened
exactly as simulated when its release was merged into this branch. Both edit `test/suite_catalog.py`, `test/suite_durations.json` and `test/test-groups.test.py`. A simulated merge
of the two (a dangling commit of this tree against the other branch's tip, `git merge-tree`, no ref touched; checked against its
first tip `d33177a13c863a89525e12be85571d7498b6d49d` and again against its later tip `c5b48560df50c2c97911a3b7c428b5fec5f24cec`)
merged the first two files cleanly, because the lines were placed apart, and conflicted only in `test/test-groups.test.py`,
where both change the same two count assertions. The counts on the second merged tree are core 61 and total 203. Releases are
serial and each bumps the one plugin version: with the other candidate on `main`, `release.py --dry-run` here reports
`skill-craft 2.35.10 -> 2.35.11` (superseded 2026-11-08: a third release landed on `main` before this one; see Round 7).

## Round 7 - publication (2026-11-08)

The owner answered "Publish" in chat to the report that closed Round 6. That is the explicit instruction the request called for,
and it covers this skill only. The release followed the repository's checklist: merge the current `origin/main`, preview, cut,
qualify the release tree, then one guarded, non-forced push of the frozen release commit.

**Main moved a third time while the branch waited.** It gained the next skill's feature commit, that skill's release
(`67f8bd77989ae0dc1017dea19b613109822e1b98`, skill-craft 2.36.0) and two docs-only publication records; the tip was
`57dd76f396314f74ac03cab9f540a9f282ce4c29`. It was merged in as `011949df0675afede3ae04bf541ea7149a24c343`. Since the merge base
this branch had changed 28 files and `main` 34, and no file is on both lists (`git diff --name-only` and `comm`, each list with a
control); the three shared test files were not touched upstream, so the counts stay core 61 and total 203. The simulated merge
made beforehand predicted tree `aabf014a812e5b02c07871be63885b652f3c9f0a`, and the merge produced exactly that tree.

**The cut.** `python3 -B scripts/release.py --dry-run` on the merged tree (exit 0) printed
`test-harness 0.1.0 -> 0.1.0 (1 note(s))` and `skill-craft 2.36.0 -> 2.36.1` and nothing else, so no other skill and no output
drift rode along. `python3 -B scripts/release.py` (exit 0) made one commit, `ff0ba75549f747ba79e4fa50053db041c47902e3` (tree
`cace7f7042463f417e3f8c1786728fdc85e400ad`, parent the merge above), subject `release: skill-craft 2.36.1, test-harness 0.1.0`,
trailer `Skill-Craft-Release: skill-craft@2.36.1, test-harness@0.1.0`. It consumed `changes/test-harness/initial.md` and wrote 25
files under `plugins/skill-craft`, the three host catalogs, the plugin version, the README inventory (26 skills) and the
changelog. The published copy of the skill is byte-identical to the folder that was read and scanned (`diff -rq`, 21 files).

**Checks on the release tree, before the push.** Each exit code was read from the runner's own record, not through a pipe; the
1-minute load was 5.8 before and 6.5 after.

| Check | Result |
|---|---|
| `bash scripts/sync-plugin-views.sh --check` | exit 0, 2 s |
| `python3 -B scripts/check-marketplace-packages.py` | exit 0, under 1 s (offline payload validation only) |
| `python3 -B scripts/check-release-boundary.py --base origin/main` | exit 0, 5 s |
| `python3 -B test/test-groups.test.py` | exit 0, 64 tests OK, 14 s |
| `node test/skill-frontmatter.test.js` | exit 0, PASS 26 skills |
| `python3 -B test/test-harness.test.py` | exit 0, 8 tests OK, 67 s |

The wrapper passes on the release tree, where the change note is already consumed. It never asserts the note
(`f7b66f577ea5f656dd21971ddf42cfa364463e18`), and only a run on the release tree could have caught such an assertion, so this
run is the proof.

**The push.** One run of `scripts/release-push.py` without force, with the same six commands as `--check`s and three literal
values read after the cut: head `ff0ba75549f747ba79e4fa50053db041c47902e3`, tree `cace7f7042463f417e3f8c1786728fdc85e400ad`,
base `57dd76f396314f74ac03cab9f540a9f282ce4c29` (which `git ls-remote` had just confirmed was the live remote `main`). All six
checks passed again on the frozen candidate and the helper reported `pushed`, range `57dd76f3..ff0ba755` on `main`. Afterwards
`git ls-remote` of the remote `main` printed the release commit, the local ref and `HEAD` agreed after a fetch, and the worktree
was clean, ignored files included. Eight commits arrived together: the feature commit, three merges, three docs commits and the
release commit.

**Not done.** No host was refreshed: step 5 of the release checklist has installers refresh, so the owner's installed copies stay
at the previous plugin version until they do. The owner's separate private copy of this skill was not touched. The push run of the
repository's CI for the release commit had passed its `release-boundary`, `plan` and `browser-fixtures` jobs and had six jobs
still running (core, python-floor, three shiploop shards, e2e-apparatus) when this was recorded; it was not waited on.

**Superseded by this round.** Rounds 5 and 6 quote `skill-craft 2.35.10 -> 2.35.11` for the dry run on the second merged tree.
The plugin version a dry run prints depends on what `main` has released before the cut, not on the candidate: it was
`2.35.7 -> 2.35.8`, then `2.35.9 -> 2.35.10`, then `2.35.10 -> 2.35.11`, and finally `2.36.0 -> 2.36.1`. The skill's own `0.1.0`
is the only version that did not move.

## Findings register

| ID | Finding | Status | Evidence |
|---|---|---|---|
| F1 | The unmodified export passes 264 of 266 on a busy machine (four runs of four, load 55 to 90) and 266 of 266 on a quiet one (load 9 to 11, 50 s): two assertions are load-sensitive. | firm | Round 1; evidence `self_test_runs` |
| F2 | The modified suite passes every recorded check under load and when quiet, and in a Linux container. | firm | Round 5 |
| F3 | Two default run roots, the decisive one not listed by the triage. | firm | `run-harness.sh`, hard supervisor |
| F4 | The unmodified self-test wrote run records under the caller's home. | firm | Round 2; evidence `home_after_self_test` |
| F5 | Five group rules put another project's claims in every report. | firm | Round 2; evidence `group_claims` |
| F6 | Discovery adapters for one private layout. | firm | Round 2 |
| F7 | A private default forbid phrase, marker and exit code. | firm | Round 2 |
| F8 | Fixtures named other skills and a published runner's tests. | firm | Round 2 |
| F9 | Other tools' names and one layout in the live-gate pattern, ambient list and product prefixes. | firm | Round 2 |
| F10 | The matrix file was generic; only the log was private. | firm | Round 2 |
| F11 | Report features keyed to private output vocabulary, first judged inert, found by the independent read. | firm | Round 3 |
| F12 | Dummy bearer fixtures assembled at run time. | firm | Round 2 |
| F13 | Both prepared candidates edit the same three shared test files; one textual conflict, in the group counts. | firm | Round 6; evidence `shared_files` |
| F14 | Documents that described the code wrongly. | firm | Round 3 |
| F15 | Behaviour the card did not state. | firm | Round 3 |
| F16 | macOS-only `open` and a hidden ripgrep dependency. | firm | Round 3 |
| F17 | 34 of the self-test's recorded checks are unconditional markers after heredoc checks that already abort on failure. | interim | Round 3 |
| F18 | Two source defects a generic user meets: the YAML glob key, and a fix-loop branch name that is invalid for a folder name with a space. | firm | Round 3 |
| F19 | The plugin version a dry run prints depends on what `main` has released before the cut, not on the candidate: it changed four times while the branch waited, and the skill's own version is the only stable figure. | firm | Rounds 5 to 7; evidence `published.plugin_version_by_dry_run_while_waiting` |

## Not verified, and decisions left to the owner

- Never run against a real project other than the harness's own self-test and the fixtures it builds; the discovery tiers were
  exercised on constructed layouts only.
- Python 3.9 to 3.12 were not run (3.9 grammar was checked by parsing); x86_64 and other Linux distributions were not run; the
  Linux run was one aarch64 Debian 13 container with Python 3.13 and bash 5.2.
- The dispositions left on purpose in Round 3.
- Whether to keep the source commit hash and the process details in this journal and in the evidence file. The hash identifies
  no repository by itself.
- The removals in F5 to F9 and F11 change behaviour relative to the private copy this was taken from. A project that relied
  on one of those adapters pins its suite with `.test-harness.yml`.
- Publication: nothing was released, pushed or merged by this work. **Superseded 2026-11-08**: the owner said "Publish" and the
  release was pushed (Round 7); the line was true while the branch waited.
- Decisions, as published: the owner said "Publish" without asking for changes, so the removals in F5 to F9 and F11, and the
  source commit hash and the process details in this journal and the evidence file, are in the published tree as they stood.
- After the push: no installed host ran the published version, so what a user receives from a marketplace refresh is unverified
  here beyond the offline package checks, and the CI result for the release commit was not awaited.
