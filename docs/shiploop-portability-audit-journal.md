# ShipLoop portability audit — journal

## Question (2026-10-31)

Can a machine that installs the `skill-craft@whichguy` marketplace plugin run ShipLoop immediately, given that
ShipLoop is script-backed (a Python CLI plus host hooks), and is shipping executable scripts through a marketplace
skill a problem? Audited at `240594c9922c42ac0a761717671f93f220e31743` (skill-craft 2.27.0, shiploop 1.26.0).

## What ships and how it runs

A host installs `plugins/skill-craft/` as a copy (Claude's installed 2.27.0 is byte-identical to the release output), so
scripts travel with the skill.
ShipLoop executes through three channels, each with its own prerequisites:

| Channel | Started by | Needs |
|---------|-----------|-------|
| CLI: `python3 <skill>/scripts/shiploop …` | the model, through the host's shell tool | `python3` on PATH, `git` on PATH, the absolute skill path from the host |
| Plugin hooks (`hooks/hooks.json`, `codex.json`, `cursor.json`) | the host, on every Bash call, Skill call, Stop and SessionEnd, in every project | the entry scripts' exec bit, `python3` (4 of 5 hooks) |
| Self-installed hooks | `shiploop` itself under Grok (`~/.grok/hooks/shiploop-keepalive.json`), or `shiploop-hook install` | write access to the host's config directory |

## Round 1 — clean-room probes (2026-10-31)

Conditions: the release payload `plugins/skill-craft` copied without `__pycache__`; `env -i`, a throwaway `HOME`,
`PATH=/usr/bin:/bin:/usr/sbin:/sbin`, `PYTHONDONTWRITEBYTECODE=1`; macOS arm64 Python 3.9.6 (Xcode's `/usr/bin/python3`)
unless stated. No model was involved.

| Probe | Result |
|-------|--------|
| `shiploop --help` under 3.9.6, 3.11.15, 3.13.17, 3.15.1 | exit 0 on all four |
| import all 47 `shiploop_*` modules under 3.9.6 | 47 imported, 0 failed |
| `workspace start` on a one-commit repo, no git identity configured | exit 0, intake packet printed |
| plugin copy and repo under paths with spaces | exit 0; printed commands are shell-quoted |
| repo whose parent directory is not writable | exit 3, `SHIPLOOP-GRANT-NEEDED`, rerun line with `--workspace-root` (text says "sandbox" although the cause is permissions) |
| Linux aarch64, Python 3.13.13, procps `ps`, no `node`, no git identity | `workspace start` exit 0; `init` in a non-git directory exit 0; hooks exit 0 |
| Linux, `git` removed from PATH | exit 2, "git is not available on PATH" |
| Debian 10 (`node:14` image), Python 3.7.3, git 2.20.1, Node 14 | `shiploop --help` and `workspace start` exit 1 with a bare traceback, `TypeError: 'ABCMeta' object is not subscriptable`, from `os.PathLike[str]` in `shiploop_store` (subscripting `os.PathLike` is Python 3.9+); `removeprefix` in `shiploop_navigator` is also 3.9+; all four Python hooks exit 1 with the same traceback on every call |
| each hook script with `python3` off PATH | `shiploop-status-hook` exit 0 (shell guard); `shiploop-keepalive-observe`, `-stop`, `-session-end` and `shiploop-skill-call` exit 127 with `env: python3: No such file or directory` |

Cost of the per-Bash-call hooks, 20 calls each, this M-series Mac, Python 3.9: `shiploop-keepalive-observe` 43 ms
with bytecode caching allowed, 61 ms without; `shiploop-status-hook` 11 ms (its shell `case` exits before Python).
A first pass measured 150–170 ms per call; it ran while a background job loaded the machine, and the second pass
replaced it (superseded, kept here so the discarded number is not rediscovered).

Install payload: `diff -rq plugins/skill-craft ~/.claude/plugins/cache/whichguy/skill-craft/2.27.0` differs only by
`.in_use`. All ten entry scripts are mode 100755 in `plugins/`; the 47 library modules are 100644.

Static facts: every import in `scripts/*.py` is the standard library or a `shiploop_*` sibling; the only network code
is the opt-in viewer bound to `127.0.0.1` (`shiploop_progress_serve.py`); `fcntl` makes the CLI POSIX-only, which the
frontmatter states (`platforms: linux, macos`). `references/` hold no `/Users/` or Homebrew paths.

## Round 2 — the ShipLoop suites under Python 3.9 (2026-10-31)

`bash test/run-all.sh --group shiploop` cannot start on 3.9: `run_process` in `test/run_suites.py` calls
`tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`, which is Python 3.10+ (a test-harness gap, not a product
gap). The 116 suites in the group were run one by one under 3.9.6 with the runner's own isolation (a private
`XDG_STATE_HOME`, no bytecode, `SHIPLOOP_PROGRESS=off`).

Result: 90 of 116 pass; 26 fail. None of the 26 tracebacks has a frame inside `skills/shiploop/`; every one is in test
code or the E2E apparatus.

- 4 suites (`shiploop-actual-improve-cli`, `-handoff`, `-skill-calls`, `-loophole-gates`): one module-level `Path | None`
  annotation in `test/shiploop-actual-improve-cli.test.py`, which lacked `from __future__ import annotations` (Python
  3.10+); the other three load that file. (First read as four test files; corrected on 2026-10-31 from their tracebacks.)
- 11 E2E suites: `os.waitid`, used by `test/shiploop_e2e/listeners.py` and two tests; absent from this macOS Python 3.9.
- 8 E2E suites: `ValueError: write to closed file` inside the apparatus; the cause was not isolated.
- `shiploop-e2e-stage-report`: `sys.stdlib_module_names` (3.10+). `shiploop-e2e-stage-build`: a "EVIL json imported from
  the working directory" check of the apparatus's interpreter isolation fails; not investigated.
- `shiploop-callback-contract`: the test expects Python 3.13's JSON error text ("Illegal trailing comma"). The product
  echoes the interpreter's own message, so a model's recovery text differs by Python version (3.9: "Expecting property
  name enclosed in double quotes"). Behaviour is correct; the assertion is version-bound.
- `shiploop-test-loop` timed out at the 900 s cap in the 6-way run, then passed alone: 518.6 s on 3.9.6 and 498.6 s on
  3.13.17, run side by side while other sessions' E2E runs loaded the machine (the catalog expects 94 s). The timeout was
  load, not the interpreter.

Evidence is the command lines and counts above; the per-suite logs were in the session scratchpad and are not retained.

## Findings

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F1 | The CLI needs only `python3` and `git`; no third-party packages, no outbound network | firm | import census; Round 1 static facts |
| F2 | The core path (`workspace start`, `init`, packet print, quoting, error exits) runs on stock macOS Python 3.9.6 and Linux Python 3.13 from a bare environment | firm for those two interpreters | Round 1 |
| F3 | Missing `git` and an unwritable parent fail with a named cause and a next step | firm | Round 1 |
| F4 | Four of five hooks fail with exit 127 and a stderr line when `python3` is missing; the fifth does not | firm; per-host effect of exit 127 not observed; fixed in Round 3 (exit 0, silent) | Round 1 |
| F5 | The real Python floor is 3.9 (3.7 verified failing; 3.8 inferred from the same missing 3.9 feature) and is declared nowhere: `SKILL.md` says `python3`; below 3.9 the CLI dies at import with a bare traceback and every hook exits 1 on each call; CI runs `3.x` latest on `ubuntu-latest` only; the test runner needs 3.10+ | firm for 3.7 and 3.9+; 3.8 interim; floor declared, checked and tested in Round 3 | `.github/workflows/ci.yml`; Round 1 Debian 10 row; Round 2 |
| F5b | On Python 3.9.6 no ShipLoop product code fails in the shiploop group: 90 suites pass, and the 26 that fail do so in test code or the E2E apparatus (those 26 do not show the product runs on 3.9) | firm for the 90 | Round 2 |
| F6 | The plugin's hooks are plugin-wide: anyone who installs `skill-craft` for any skill gets ShipLoop's hooks on every Bash call, about 45–60 ms each; `SHIPLOOP_KEEPALIVE=off` disables them | firm | Round 1; `references/keepalive.md` |
| F7 | Under Grok the first `shiploop` command writes `~/.grok/hooks/shiploop-keepalive.json` outside the project | firm (documented behaviour, not re-run) | `references/keepalive.md` |

## Unknowns

- Windows (excluded by `platforms:` and `fcntl`); WSL not tried.
- Python 3.8 itself (no image on this machine), and Linux images with busybox `ps` (`-o lstart` is read by the keepalive process table).
- macOS without the Command Line Tools (`/usr/bin/python3` and `git` are installer stubs).
- What Codex, Cursor and Grok do with a hook that exits 127 (Claude treats a non-2 exit as non-blocking).
- Whether hosts pass `PYTHONDONTWRITEBYTECODE` to hooks (this session's shell has it set, so hooks there pay the 61 ms figure).
- A live-model first run on a machine with nothing installed: earlier work covers installed-package calibration and the
  marketplace lifecycle (`docs/marketplace-e2e-testing.md`, eef1eda1) but not a machine without `python3`.

## Decisions (owner, 2026-10-31)

Asked whether to declare a floor, where the E2E apparatus stands, and whether to implement. Answers: the floor is
**Python 3.9** (not 3.8, which would need `os.PathLike[str]` and `str.removeprefix` replaced and could not be tested
here); the E2E apparatus is **declared 3.10+** and stays out of the 3.9 job; **implement and commit**.

## Round 3 — the fixes (2026-10-31)

Worktree `portability-floor-0430cb` from `bf68e959` (main had moved twice during the audit: 2.27.1 was released by another
session).

| Change | Where |
|--------|-------|
| One declaration of the floor and its check, written for Python 3.7 syntax so an old interpreter reaches it | `skills/shiploop/scripts/shiploop_pyfloor.py` (`FLOOR`, `require`) |
| `shiploop`, `shiploop-drive` and `shiploop-hook` call `require` before their first `shiploop_*` import; a host hook event exits 0 silently, everything else exits 2 with one line | the three entry scripts |
| The four Python hook entries become `sh` wrappers like `shiploop-status-hook`: no `python3`, exit 0, no output; otherwise `exec python3 …/shiploop-hook <verb> --host <host>` | `shiploop-keepalive-observe`, `-stop`, `-session-end`, `shiploop-skill-call` (same names, so `host-hooks.json` and the generated host files are unchanged) |
| The card states the prerequisite (30,011 of 30,500 bytes); the installer doc says it, with Linux/macOS only | `SKILL.md`, `docs/distribution.md` |
| A `python-floor` test group (every ShipLoop suite except `shiploop-e2e*`, 74 suites) and a CI leg that runs it on Python 3.9, added to the full tier | `test/suite_catalog.py`, `test/ci_policy.py`, `.github/workflows/ci.yml` |
| The test runner's scratch directory no longer needs Python 3.10 (`_scratch_directory`); the one test file that evaluated `Path \| None` at definition time imports `annotations`; the callback-contract test computes the JSON parser's wording instead of assuming 3.13's | `test/run_suites.py`, `test/shiploop-actual-improve-cli.test.py`, `test/shiploop-callback-contract.test.py` |
| `test/shiploop-python-floor.test.py` (9 tests): both exits under a simulated 3.8, silence for each hook verb, every entry that imports a ShipLoop module checks the floor first, the guard module parses as 3.7, each wrapper's exit and exact `shiploop-hook` arguments with a stub `python3`, and the card and CI naming the same floor | new suite; membership of the group is pinned in `test/test-groups.test.py` |

Real-interpreter check after the change, the same Debian 10 image (Python 3.7.3): all five hook entries exit 0 with empty
stdout and stderr; `shiploop --help`, `shiploop-next` and `shiploop-drive` exit 2 with `error: ShipLoop needs Python 3.9
or newer; this python3 is 3.7.3. Put a newer python3 first on PATH.`; `shiploop-hook status --host claude` exits 2 with the
same line; `shiploop-hook observe --host auto` exits 0 silently. Before: every one exited 1 with a `TypeError` traceback.

Lint: `ruff --select F,E9` on the eleven changed or new Python files shows the same four F811 findings in
`shiploop-actual-improve-cli.test.py` at HEAD and after (line numbers shifted by two); none are new.

The `python-floor` group through the real runner on Python 3.9.6 (the CI command, `CLAUDECODE=1`,
`CLAUDE_CODE_SESSION_ID=ci-stand-in`): 74 suites, 673.7 s wall at `--jobs 8` while other sessions loaded the machine.
73 passed at once. `shiploop-skill-calls` failed three tests with `SyntaxError` on `command -v python3 …`: it ran each hook
entry as `[sys.executable, entry]`, which interprets the shell wrapper as Python. A host runs the file, so the tests now run
each entry as a program with a `python3` shim for the interpreter under test; the suite then passed on Python 3.9.6 (34
tests, 49.4 s) and on the default Python 3.15.1 (48.1 s). What it teaches: a test that routes an entry through the
interpreter is coupled to the entry being Python, and nothing the host does depends on that.

Default Python 3.15.1: `shiploop-python-floor` (9 tests), `shiploop-package-integrity`, `test-groups` (52 tests, including
the new group assertion), `ci-policy` and `shiploop-callback-contract` pass. Adding the new suite to the quick baseline
broke four pinned selection expectations, because a suite that imports the catalog inherits every path the catalog names;
the suite is therefore not in the quick baseline, imports no catalog, and is still selected by a change to any file its
source names (`shiploop_pyfloor.py`, the hook entries, `SKILL.md`, `ci.yml`).

## Round 4 — learnings and what is left (2026-11-01)

Asked by the owner on 2026-11-01 ("Commit and merge everything to main and publish. Determine any learnings and things we
need to improve. I want to expose this through our marketplace"). Before publishing, the two Round 3 commits were rebased
onto `origin/main` (26 new commits, none touching `skills/`, `agents/`, `changes/`, `catalog/`, `.github/`,
`test/suite_catalog.py`, `test/ci_policy.py` or `test/test-groups.test.py`; they changed only docs, E2E-apparatus files
and six test files), so the hashes of both commits changed.

### Learnings

| # | Learning | Status | Evidence |
|---|----------|--------|----------|
| L1 | Shipping executable scripts through the marketplace is not what makes ShipLoop non-portable. The released tree arrives intact (installed copy identical to the source, execute bits kept); what varies is the machine's interpreter and whether the plugin's hooks tolerate its absence | firm | Round 1 |
| L2 | The two execution channels fail differently, and that decides the rule. The CLI the model runs fails once, visibly, with a named cause. A plugin hook fires on every Bash call in every project where the plugin is enabled, whether or not ShipLoop is in use, so a hook that errors is a cost to people who never asked for ShipLoop. The rule: **a plugin hook never fails the host's tool call** (no `python3` or too old: exit 0, silent), and the visible failure is kept for the explicit CLI path. `shiploop-status-hook` already followed it; four of five entries did not | firm | F4, Round 3 Debian 10 check |
| L3 | A prerequisite that is not declared is not tested. CI ran `python-version: '3.x'` with `check-latest` on one OS, so the floor existed only by accident (`os.PathLike[str]`, `str.removeprefix`). A floor needs three things together: a number in the card, a runtime check that names the number, and a CI leg that fails when the code crosses it. Any one alone drifts | firm | F5; `test/shiploop-python-floor.test.py` pins the card and `ci.yml` to the same number |
| L4 | The test harness had a higher floor than the product (`run_suites.py` needed 3.10's `ignore_cleanup_errors`), so the product's floor could not be tested at all until the harness was lowered. Check the harness's own floor before claiming a product floor is tested | firm | Round 2, `_scratch_directory` |
| L5 | Two tests were coupled to an implementation detail the host never depends on: `shiploop-skill-calls` ran hook entries as `[sys.executable, entry]`, which breaks the moment an entry is a shell wrapper, and `shiploop-callback-contract` asserted the JSON parser's wording from Python 3.13. Run an entry as a program, the way a host does, and compute any interpreter-worded text instead of copying it | firm | Round 3 |
| L6 | Quoting a commit's full hash in the next commit's message goes stale when the pair is rebased. It happened twice in this one change (a short hash in Round 3, the full hash of the first commit here). After any rebase, `git grep` the tree and `grep` the message for the old hashes before the push | firm | the pair was rebased twice before publication (onto 26, then 2 more upstream commits); the first commit's hash changed each time and the second commit's message cited it |
| L7 | A local pass does not prove a CI job. The first run of the new `python-floor` leg on GitHub (run 41311581045) failed at `actions/setup-python`, before any test ran: `ubuntu-latest` is Ubuntu 26.04, and the actions/python-versions manifest lists CPython 3.9 (newest 3.9.25) only for 22.04 and 24.04. The same 74 suites had passed on a local Python 3.9.6. A leg that exists to run an old interpreter has to name a runner image that still ships it; it is the one deliberate exception to "CI follows the latest image" | firm | run 41311581045, job 124862972188 (log: "The version '3.9' with architecture 'x64' was not found for Ubuntu 26.04."); run 41312286843, job 124865056886 |

### What is left, ranked by gain

1. **The CI leg had not run on GitHub: resolved 2026-11-01.** It failed on its first run (L7) and passed after the fix.
   Run 41312286843 (full tier, `workflow_dispatch` on `main` at the fix commit), job `full / python-floor`: image
   `ubuntu-24.04`, `Successfully set up CPython (3.9.25)`, 74 suites in 975.4 s wall at `--jobs 4`, `PASS (python-floor
   hermetic group selection)`, and the "Checkout unchanged" step passed. The step list shows `Run actions/setup-python@v7`
   succeeding where the first run failed. (Earlier text: "the first push to `main` is the first real proof"; it was, and it
   found the runner defect.)
2. **The floor is enforced only in the full tier.** A change that needs newer syntax fails in the post-merge full run, not
   in the quick tier a push gets. Cheap candidate: put `shiploop-python-floor` plus an import of every `shiploop_*` module
   under 3.9 in the quick tier. Not done: it is a CI-policy trade-off (cost on every push against catching a break
   earlier), and no break has yet reached `main` that it would have caught. **Round 8: dropped by decision, see its triage table.**
3. **Eight E2E-apparatus suites fail on 3.9 with "write to closed file", unexplained.** The apparatus is declared 3.10+, so
   they are out of the job, but a failure that is not a 3.10 API may be a real defect that only shows up there. Worth one
   short investigation before the declaration is relied on. **Round 8: explained, F23.**
4. **No live-model first run from a machine with nothing installed: resolved for both hosts 2026-11-01** (Round 5). One live
   `hello` session ran to `done` on the Codex host from a fresh-profile marketplace install of 2.27.2 (F9), and one on the
   Claude host on Sonnet 5.5 from the published 2.27.3 build (F12), every verdict passing. Boundary kept: the Claude session
   loaded the harness's export through `--plugin-dir`, and the native Claude install was probed separately without a model
   (F8); no run combined a native Claude install with a model. The first Claude attempt, on the Ollama model, was blocked by a
   usage limit (F10). Earlier wording, kept: "The marketplace lifecycle is covered (`docs/marketplace-e2e-testing.md`), and
   the clean-room probes here ran the CLI and hooks, not a model session."
5. **Hook cost and plugin-wide scope (F6) remain.** 45–60 ms per Bash call for every user of the plugin, ShipLoop or not.
   Splitting the hooks into a ShipLoop-only plugin would change the one-namespace decision, so it is the owner's call and
   is not proposed here.
6. **Unknowns unchanged:** Windows and WSL, Python 3.8 itself, busybox `ps`, macOS without the Command Line Tools, and
   Cursor and Grok's treatment of a failing hook (now moot for ShipLoop's own entries, which exit 0).

### Decision (routine, session)

Publish the two commits as one release (patch: shiploop 1.26.2, skill-craft 2.27.2). Why routine: the owner asked for it in
chat on 2026-11-01, `scripts/release.py`'s preflight passes (the second commit, the only one that touches `skills/shiploop/`, carries
its own `No-E2E-Round` trailer for the ShipLoop order check), and AGENTS.md lists publishing a release that fast-forwards `main` as routine. Contrary evidence
kept: no live-model round exercised the hook wrappers (item 4), and the CI leg was unproven on GitHub when this was written (item 1, since resolved: it failed once on the runner image and passed after the fix).

### Publication (2026-11-01)

| Step | Result |
|------|--------|
| Release | ``e13af240100c066489e83c028d97339845402b55`` skill-craft 2.27.2, shiploop 1.26.2, pushed over `ca2db2db741e2009b5737fe0b8a5363c8ae40780` with `scripts/release-push.py` and its four checks (sync-plugin-views, marketplace packages, release boundary, test-groups); the candidate was rebuilt three times because other sessions pushed docs-only commits while it was prepared |
| Verification before the push | `python-floor` group through the real runner on Python 3.9.6, rebased tree: 74 of 74 suites, 721.5 s wall at `--jobs 8` |
| Hosts | Claude `2.27.1` to `2.27.2` (installed copy: the four hook scripts exit 0 silently without `python3`; `shiploop --help` exits 0 on the default Python and on 3.9.6); Codex marketplace `whichguy` upgraded, `skill-craft@whichguy` 2.27.2; Grok updated 2.27.1 to 2.27.2; Cursor needs its app and is the owner's |
| Release run 41311581045 | `python-floor` failed (L7); `core`, `shiploop-1`, `shiploop-2`, `shiploop-3`, `e2e-apparatus`, `plan` and `release-boundary` passed; the `hermetic` aggregate failed only because of `python-floor` |
| CI fix | ``7047791fb298ac5490f8f43b9dd8a5d91bd17681`` runs the `python-floor` group on `ubuntu-24.04`; `test/ci-policy.test.py` now allows exactly that one pin (the earlier decision, `f14db1a41a143354a4435de820a9828252675e7d`, removed the pinned image so CI would follow `ubuntu-latest`; it still does for every other group) |
| CI fix verified | run 41312286843, job 124865056886: see open item 1 |

## Round 5 — clean install of the published release, live (2026-11-01)

Asked by the owner after the publication ("Yes run it"). Evidence and commands: `docs/experiments/clean-install-20261101/`
(`README.md`, `probes.sh`, `probes.out`, the two run results).

| Check | Result |
|-------|--------|
| Native Claude install into a fresh `CLAUDE_CONFIG_DIR` | one plugin, `skill-craft@whichguy` 2.27.2; installed tree identical to the published tree; eight entry scripts mode 755; floor and card text present |
| Installed tree on stock Python 3.9.6, `env -i` | `shiploop --help` exit 0; `workspace start` exit 0, 15,772-byte packet |
| Hooks with `python3` off PATH | all five exit 0, silent |
| Installed tree in a Python 3.7.3 container | hooks exit 0 silent; CLI exits 2 with the one-line floor message |
| Live `hello`, Claude host, Ollama model | blocked: the first model call returned 429, "monthly usage limit"; invoked and plugin verdicts passed, nothing downstream ran |
| Live `hello`, Codex host, gpt-6.1-terra xhigh, fresh-profile marketplace install | every verdict passed: `done`, committed, both request checks; 929.2 s, 202 turns, ShipLoop command failures 0 |
| Live `hello`, Claude host, claude-sonnet-5-5 (Anthropic), the build published at launch: 2.27.3 / 1.26.3 through `--plugin-dir` | every verdict passed: `done`, committed, both request checks; 969.2 s, 188 turns, $4.13; 3 designed gate refusals, no faults |

Findings:

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F8 | A person who installs the published plugin gets exactly the tree that was released, and its hooks, floor check and CLI behave as designed on stock macOS Python 3.9.6, with no Python, and below the floor | firm for those cases | `probes.out` |
| F9 | A live ShipLoop session runs to `done` from a fresh-profile Codex marketplace install of 2.27.2 on this Mac (n = 1, one tiny case) | interim | `codex-hello-result.json` |
| F10 | The E2E apparatus's default subject (Ollama) can be unavailable for a whole month, and a run that hits the limit still appends a baseline row; the row is labelled failed with the 429 as its stop reason and is excluded from comparisons, but it is a row about the quota, not about ShipLoop | firm | `claude-hello-429-result.json`; `test/shiploop_e2e/baselines.jsonl` |
| F11 | `workspace start` can print "progress observer unavailable" when the viewer misses its 1.0 s startup deadline; seen in 3 of 13 fresh starts at load average near 60; stderr only | interim, load-dependent | `shiploop_progress.start`; README side observation |
| F12 | A live ShipLoop session runs to `done` on the Claude host, on Sonnet 5.5, from the build the marketplace published at launch (2.27.3 / 1.26.3, which holds the 2.27.2 floor work): turns 193 to 188 and cost $3.88 to $4.13 against the 2026-10-26 run in the same cell on ShipLoop 1.15.0 (n = 1 each, load 28 to 167 on 18 CPUs) | interim | `claude-sonnet-hello-result.json` |

What this teaches: the install half of the portability claim is checked by native commands on the real release, and the
live half now has a passing session on each host. The Claude host's first attempt was blocked by a service quota the
owner controls, not by ShipLoop; the owner chose Sonnet for the rerun and it passed. Which interpreter the Codex session ran is inferred (the packets printed Xcode's Python
3.9.6; the session's PATH was not recorded), so the run is not yet proof of a live session on the floor.

## Round 6 — improvements from the audit (2026-11-01)

Asked by the owner after Round 5: "Do weekly run", then "skip ollama, just use Claude. Merge to main and publish, implement
improvements". Read as: add the weekly run; add the other no-secret improvement proposed (the consumer smoke) and write the
post-release live check down with Claude as its host; do not build Ollama-specific handling. The harness's default backend
(Ollama) was not changed, because that changes the subject model behind every earlier baseline; the owner had not said it
should be. **Superseded the same day (Round 7):** asked, the owner said yes.

| Change | Commit | Result |
|--------|--------|--------|
| Weekly full-tier CI run (Mondays 14:23 UTC): a schedule event maps to the full tier in `ci_policy.select` | `427c97b8801ba2216f6ebedca32653d3de4b7201` | two tests red then green; the first scheduled run is Monday 2026-11-02 and is not yet observed |
| `shiploop-clean-consumer`: the built package run in a scrubbed environment on the interpreter under test (CLI help, `workspace start` with no git identity, every hook entry with `python3` absent) | `be57e809ff9035d9a729ffda64e39e6bb7d61031` | 3 tests; fails with `(127, '', 'env: python3: No such file or directory')` when the pre-fix hook is restored; passes on 3.9.6 and the default Python; passed in the python-floor job of full-tier run 41323374730 |
| "Smoke checks after a release" in `docs/distribution.md`: the no-model probes, a live `hello` session on Claude (`--backend anthropic --model claude-sonnet-5-5`), and an optional Codex one | `116a65e8257f8258d1f48c0aae2b83adb7e77403` | the Claude path is documented as the default; Ollama is named only as the cause of two blocked runs |

Findings:

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F13 | The scrubbed-environment smoke of the built package passes on Linux, Python 3.9.25, `ubuntu-24.04`, as well as on macOS: the python-floor group is now 75 suites and ran in 1,202.9 s wall at `--jobs 4`, `shiploop-clean-consumer` OK | firm for that run | run 41323374730, job 124898192333 |
| F14 | The consumer smoke adds little over what existed (`shiploop-package-integrity` already checks entries compile and are executable; two suites already run built copies): its gain is the scrubbed environment only. A second mutation, removing an execute bit, never reached it because `scripts/build-packages.py` refuses the build first, so a redundant executability test was dropped | firm | mutation runs described in `be57e809ff9035d9a729ffda64e39e6bb7d61031` |

Not done, by the owner's choice: the harness preflight that makes a one-token Ollama call and the rule that a quota failure
appends no baseline row (finding F10 still stands: a run that hits a usage limit appends a failed row). Not done and still
open from "What is left": the floor is enforced only in the full tier (and now the weekly run), the eight unexplained
E2E-apparatus failures on 3.9, and the 1.0 s progress-observer deadline (F11), which is a limit the owner decides.

## Round 7 — Claude is the E2E harness's default backend (2026-11-01)

Asked at the end of Round 6: "Make Claude the E2E harness's default backend instead of Ollama?" Owner: "Yes use that as default".
Asked rather than done because AGENTS.md makes a default that breaks comparability with earlier evidence a one-way decision.

| Change | Where | Result |
|--------|-------|--------|
| An explicit Claude host with no `--backend` runs `claude-sonnet-5-5` on Anthropic; `--backend ollama` selects DeepSeek flash; `hosts.RUN_DEFAULT_BACKEND` and `hosts.run_default_model` are removed | `test/shiploop_e2e/hosts.py`, `run.py`, `slice.py`, `stage_suite/stages.py`, `iterate.py`, `experiment.py` | four tests fail on the old default and pass on the new; the roles, slice and Ollama-class suites pass |
| Docs say so | `test/shiploop_e2e/README.md`, `SPEC.md`, `LEARNINGS.md`, `docs/distribution.md` | the post-release Claude smoke no longer needs `--backend anthropic --model claude-sonnet-5-5` |

Finding F15: the default now matches what the audit's live checks needed. The one Ollama-default Claude run (2026-11-01) hit the
monthly cap at its first model call; the Sonnet run passed in 969.2 s for $4.13 (n = 1). Status: firm for the change, not
measured for any run on the new default. The decision, its effect on baseline cells (38 Sonnet rows, 9 DeepSeek rows, nothing
relabelled) and its cost are in `test/shiploop_e2e/LEARNINGS.md`, "the Claude host defaults to Anthropic's Sonnet 5.5".

## Round 8 — conclusion: closed, dropped, and the owner's (2026-11-01)

Asked after Round 7: "Determine how to conclude, plan out, and implement." Read as: close what the session can, check the
current release live on the new default, and leave the owner a short list of what is theirs. Order run: the state of the repo,
the hosts and CI; the install probes, the documented gate and one live session; a read of the weekly CI path; triage of the open
items of Rounds 4 and 6; this record. Evidence: `docs/experiments/release-smoke-20261101/`.

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F16 | The documented post-release smoke works as written on 2.31.0 (`--source marketplace` passes its gate, the probes pass) and, after the gate refused on 2.30.0, through `--plugin-dir` on an export of the served payload | firm | rows 1, 2, 5, 6 |
| F17 | A live `hello` session on the Claude host with no `--backend` and no `--model` passes every verdict on 2.30.0 / 1.29.0: backend `anthropic`, `claude-sonnet-5-5`, 1239.8 s, 280 turns, $5.6854 (n = 1). The cell's last six rows span 188 to 364 turns and $3.88 to $7.65, so no cost change is claimed | firm for the run | row 3 and the baseline row |
| F18 | A model session on the owner's native Claude install of 2.30.0 lists the three ShipLoop skills (1 turn, $0.13). A native Claude install and a model have now met; this shows discoverability, not a run | firm | row 4 |
| F19 | The harness gate refuses `--source marketplace` while any change note is pending on `origin/main`. On 2026-11-01 it refused 51 minutes after the 2.30.0 release commit and ten minutes before 2.31.0 was released, so a check that waits for the gate can wait a release cycle. The docs now give the `--plugin-dir` route and require the evidence to say the gate was bypassed | firm | `v2.30.0-gate-refused.txt`, `docs/distribution.md` |
| F20 | The weekly schedule path was read end to end and holds: `ci_policy.select` maps `schedule` to the full tier (unit-tested), the `release-boundary` step falls to `*) ... exit 0` for any event other than push and pull request, the concurrency group is keyed on `run_id`, and `plan` compares `github.sha` with the checkout, which on a schedule is the default branch's tip. The first real firing, Monday 2026-11-02 14:23 UTC, is unobserved | firm for the reading | `.github/workflows/ci.yml`, `test/ci-policy.test.py` |
| F21 | The `python-floor` leg (Python 3.9.25, `ubuntu-24.04`) passed in the full tier of the last three release commits: `570f308fda451c8b0b1a39ef16f33ffe32aa31d1` (run 41323924608, 20 min; that run was red in `shiploop-2` only), `4224161b095792825befe2a384075fab5660ae05` (41329381683, 20 min) and `41ee3d89d580fb715fc90994b2361348550698c7` (41332749569, 16 min) | firm | `gh run view` of those runs |
| F22 | Cursor is the one host that is not current: `~/.cursor/plugins/local/skill-craft` holds a local copy at 1.21.0 (directory dated 2026-10-05) and the only marketplace entry there is `claude-craft` (2026-09-11), none named `whichguy`. Claude, Codex and Grok list the current release. A stale local copy beside a later marketplace install would load old skills twice | firm (read-only look); resolved in Round 9 | `~/.cursor/plugins` |
| F23 | The "write to closed file" failures of Round 2 are explained. Under macOS Python 3.9.6 (Xcode's) the 47 E2E-apparatus suites give 23 passes and 24 stops at the first failure, with no timeouts; 17 of the 24 logs show `AttributeError: module 'os' has no attribute 'waitid'`, and the rest are 3.10 to 3.12 APIs (`unittest.enterContext`, `sys.stdlib_module_names`, `TemporaryDirectory(ignore_cleanup_errors=)`, `tarfile.extractall(filter=)`) or checks not examined (`environment`, `lifecycle`, `stage-build`, `stages`). The closed-file error is a knock-on: `run.launch`'s daemon `pump` thread writes to the events file after the main thread's `AttributeError` has left the `with` that opened it. Run without fail-fast, five of six `waitid` suites printed it (`delta`, `commit-counters`, `baseline`, `quality`, `reorientation`; `ticket-sla` did not). No frame in any of the 24 tracebacks is in `skills/shiploop/` | firm | `docs/experiments/release-smoke-20261101/py39-apparatus-probe.txt`; `run.py`, `launch`, `pump` and `record` |

### Triage of what was open

| Item | Where it stood | Now |
|------|----------------|-----|
| Live session on the new default | Round 7: not measured | closed, F17 |
| Native Claude install with a model | Round 5: never combined | partly closed, F18; a full run from a native install needs a login inside a disposable config, which is the owner's credential |
| Weekly run unobserved | Round 6 | reviewed, F20; the firing itself waits for Monday |
| Floor only in the full tier (Round 4, item 2) | open | dropped by decision: the floor held on three of three release commits (F21), no break has reached `main`, and a per-push leg costs a CI job on every push. Revisit if a break reaches a release. The owner may overrule; the cheap form is `shiploop-python-floor` plus an import of every `shiploop_*` module under 3.9 in the quick tier |
| Eight E2E-apparatus failures on 3.9 (Round 4, item 3) | unexplained | explained, F23: a knock-on of `os.waitid`, which macOS Python lacks; not a separate defect and not in the product |
| Windows | unknown | already declared unsupported in `docs/distribution.md` (the scripts use `fcntl`); WSL is Linux and untested |
| Python 3.8, macOS without the Command Line Tools | unknown | unchanged: 3.7 and 3.9 are covered, and below 3.9 the CLI says so in one line |
| The 1.0 s progress-observer deadline, hook cost and plugin-wide scope (F6) | the owner's | unchanged |
| Cursor | the owner's | F22 |

### The owner's, in order

1. ~~Install `skill-craft` in the Cursor app from the `whichguy` marketplace and remove the local 1.21.0 copy (F22).~~ Done the
   same day at the owner's word (Round 9).
2. The first scheduled CI run, Monday 2026-11-02 after 14:23 UTC. At the owner's word on 2026-11-01 ("Yes, schedule it") a
   one-time, read-only Desktop task, `read-first-weekly-ci-run-2026-11-02` (the app's Scheduled list), is set for 08:30 PST that
   day. It waits for the run and reports; it records nothing, so writing the observed half of F20 here still needs a session.
   It runs while the app is open, or on the next launch.
3. The 1.0 s progress-observer deadline (a limit) and the hook-cost split (F6), as before.

## Round 9 — skill-craft in the Cursor app, stale copies removed (2026-11-01)

Asked by the owner after Round 8, in dictated words: "I want Steelcraft to be in the Cursor app, and remove any Steel copies".
Read as skill-craft and stale copies, because Round 8 had just listed exactly that for Cursor. Cursor 3.27.22, one machine.

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F24 | Before: skill-craft was in Cursor only as a local copy at 1.21.0 (`~/.cursor/plugins/local/skill-craft`, directory dated 2026-10-05), and the Cursor account held three user-scope registrations of this repository, none current: `whichguy` pinned to `85d31923154d72a7e54dee9f294899aed48e66e5` (release 1.7.0, 2026-09-27), `skill-craft` pinned to `f6c95537e0ff20f7fd5faea56ea63322e3f6f6f9` (2026-09-24, the per-skill catalog) and `whichguy-skill-craft` with no pin, last indexed 2026-09-16. No plugin of any of them was installed in the app: there was no `plugins/cache` folder for them | firm | `cursor-agent plugin marketplace list --format json`; `~/.cursor/plugins` |
| F25 | `cursor-agent plugin marketplace update` does not move a registration. It re-indexed the old `whichguy` (indexed time moved) and left its `gitRef` at `85d31923...`. After a fresh `add`, the registration's `gitRef` was the commit `main` held at that moment, `f5fb7d6446bb461e1a771a7bc64effaabd6822d1`; a later `update` re-indexed it again and left it there while `main` had reached `36b6046e006f1338c0f4059273660fba20365397`. Following a release takes a remove and an add | firm (observed twice) | the `list` outputs before and after |
| F26 | Now: one registration, `whichguy`, user scope, indexed at `f5fb7d64...`. The plugin installed from it by one click (Browse Marketplace, Whichguy, skill-craft, Add) is skill-craft 2.32.1 with 23 skills, byte-identical to `git archive` of that commit, and the app's installed list shows one skill-craft with no Local badge. The local 1.21.0 copy is in the Trash (`~/.Trash/skill-craft-local-1.21.0-stale-20261101`). No skill-craft skill sits in `~/.cursor/skills`, `~/.claude/skills`, `~/.codex/skills` or `~/.agents/skills` | firm | `~/.cursor/plugins/cache/whichguy/skill-craft/`; the app's list |

Left, and why:
- Whether an installed marketplace plugin follows a newer commit by itself is not verified (no release has landed since); today a
  refresh is a remove, an add and a click. (2026-11-15: a re-registration did not move the installed plugin
  within minutes; see Round 10.)
- The app's installed count went from 32 to 31 across the change, where swapping one local copy for one marketplace plugin should
  have kept it at 32. Removing a registration may drop an installed entry; which one is not known.
- `~/.cursor/skills/.skill-craft/receipts.jsonl`, install.sh's ledger of links that no longer exist, was left: it is a record, not
  a copy, and Cursor does not read it.
- The app was driven in click-only mode (no typing), so the marketplace was registered from the CLI instead of the "Import from
  GitHub" form. After the app's screen lagged behind a screenshot, one click opened the detail page of an unrelated plugin (Amazon
  Location Service); its "Add to Cursor" button was not pressed.
- Cursor 3.27.22 on one machine; the Team-scope route is an administrator's and was not touched.

## Round 10 — Cursor on the latest release, with no pinned registration (2026-11-15)

Asked by the owner, in their words: "I really don't want to pin the registration anywhere. I want to use the latest." Read as
skill-craft's `whichguy` registration on every host. Cursor 3.30.14 with Cursor Agent 2026.09.23-86fc751, one machine.

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F27 | Only Cursor pins. Claude (`~/.claude/plugins/known_marketplaces.json`: `whichguy` is `{"source": "github", "repo": "whichguy/skill-craft"}`), Codex (`~/.codex/config.toml`: `[marketplaces.whichguy]`, a git source with no ref) and Grok (`grok plugin marketplace list`: the repository URL alone) name no ref, so each follows the default branch | firm | those files and listings |
| F28 | F25 holds on Cursor 3.30.14. `add --git-ref main` stored `gitRef` `0eb91fc0bc1860ee158c822d62b81e65c3099a18`, the commit `main` held then. Once `main` had reached `581791995824c9bce0d7ea32098f664caf67b5a7`, `update whichguy` printed "1 plugin indexed", moved `lastIndexedAt` from 1794760969681 to 1794761676548 and kept `gitRef`. The CLI's own help calls the ref the "Branch, tag, or commit to index" and `update` a re-index | firm (third observation) | `cursor-agent plugin marketplace list --format json` before and after |
| F29 | The app holds the registration it loaded. After the remove and add, the plugin page still read 2.39.0, and Add failed with "Plugin not found" until the window was reloaded with that error's Reload button (every chat in the sidebar read Completed first). Then the page read 2.40.0, and Add (Add for Myself) installed it: cache `0eb91fc0bc1860ee158c822d62b81e65c3099a18`, `plugin.json` version 2.40.0, in place of `c2ad82f57032930ef9ca66927d711a8f8f74b868` (2.39.0). The re-registration had not moved the installed 2.39.0 in the minutes before it was uninstalled | firm for what was seen; whether a reload alone moves an installed plugin is not tested | `~/.cursor/plugins/cache/whichguy/skill-craft/`; the app's page |

Decided (owner): no registration is pinned to a commit or a tag. Cursor registers the repository root on its default branch, and,
because it still snapshots the commit, each release's host refresh re-registers it and reinstalls the plugin, as
docs/distribution.md "Cursor" now lists. Left: Cursor's other registrations (`claude-plugins-official`, `openai-codex`,
`claude-craft`) sit at the commits they were added at, behind their default branches. They were not touched: the request named
skill-craft's registration, re-adding another publisher's marketplace changes what the account offers, and moving each plugin
installed from one takes an Uninstall and an Add.

## Round 11 — what Cursor loaded after the re-registration, and what one Add did (2026-11-15)

Asked by the owner, answering the offer to reinstall skill-craft in the app: "Open Cursor". Cursor 3.30.14 with Cursor Agent
2026.09.23-86fc751, one machine, 14:27 to 14:35 PST. The app had been closed. `main` had moved on to the 2.41.0 release
(`fe0e6ca39435d502bd0b8afd3ce300ff731e5683`), and another session's host refresh had re-registered `whichguy` at that commit
(`lastIndexedAt` 1794778636001, 13:37:16).

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F30 | After the re-registration, skill-craft was not installed natively. On launch the marketplace page read **Add** for it, not **Added** (`codex` and `async-suite` read Added); the account's enabled list at launch (`BackendMarketplaceClient: Adding enabled plugin`, 28 plugins) named no skill-craft; and the 2.40.0 copy from 08:52 (`~/.cursor/plugins/cache/whichguy/skill-craft/0eb91fc0bc1860ee158c822d62b81e65c3099a18`) was still on disk, unloaded. This fits a `marketplace remove` dropping the install, which Round 9 also saw (the installed count fell 32 to 31). Which of the day's re-registrations did it was not isolated | firm for the state; interim for the cause | the launch log (`Cursor Plugins`, window 1, `20261115T142754`); the cache listing |
| F31 | Cursor imports Claude Code's installed plugins. At launch it ran `loadClaudePlugin` for 12 of Claude Code's 17 installed plugins, `skill-craft@whichguy` among them, and the Installed list carried a skill-craft row with an **Imported** badge at 2.41.0. That is Claude Code's own install (`~/.claude/plugins/installed_plugins.json`: 2.41.0, `fe0e6ca39435`). So from launch Cursor ran 2.41.0 through the import, not the stale native copy | firm | the same log; that file |
| F32 | One click on **Add** (Browse Marketplace, Personal, Whichguy, skill-craft) installed 2.41.0 with no dialog and no Uninstall. The log: `Adding enabled plugin: skill-craft from fe0e6ca3… at plugins/skill-craft`; `Plugin missing from cache, installing`; the warning `Failed to install plugin skill-craft from marketplace cache, falling back to direct install`; a sparse shallow clone of 2,426.8 ms; `Found cached plugin`; `loadFromMarketplaceSource completed in 80.8ms (29 plugins loaded, 0 failures)`. The cache is `fe0e6ca39435d502bd0b8afd3ce300ff731e5683`, `plugin.json` 2.41.0, and Cursor removed the 2.40.0 folder itself | firm | the same log; the cache listing |
| F33 | The Installed list then shows two skill-craft rows (the native one and the Imported one) and counts 39 where it counted 38 before the click. The plugin loader's total did not move: `loadAllPlugins ... total=38 plugins` at 14:31:50 (28 marketplace plugins) and again at 14:32:19 (29). So the native copy took the Imported one's place in what loads. Not checked: whether a chat's skill list shows each skill once | firm for the counts; the reading is an inference | the same log; the app's header counts |

Decided (routine, session): add the plugin natively, as Round 9's owner decision has it, and do not press **Uninstall** on the
Imported row: that row is Claude Code's copy, and what the button does to an imported plugin was not tested. docs/distribution.md
"Cursor" now says to relaunch or reload the app after the re-registration and then click Add, and keeps Uninstall for a running
app that still shows the old install. Round 10 left open whether a reload alone moves an installed plugin; F30 answers it only in
part: after a relaunch there was no installed plugin left to move, so the Add made a fresh install. Left, the owner's: the import
already follows `claude plugin update`, so whether the native copy is still wanted is theirs to say.

## Round 12 — Cursor runs Claude Code's copy, with no registration (2026-11-15)

Asked by the owner, in their words: "Can you help me understand what we could do to better register with Cursor, because I don't
like it pinned or not having it be able to update automatically?" I read Cursor's documentation and forum replies and this
machine's Cursor logs, proposed the cheapest option (let Cursor use Claude Code's copy), and the owner answered "Yes, run the
test" and then "Yes, remove it". Cursor 3.30.14 with Cursor Agent 2026.09.23-86fc751, Claude Code 2.1.325, one machine, 16:00 to
16:58 PST (times below are PST). The grant for Cursor was click-only, so the app could be read and clicked but not quit or typed
into; the owner quit and reopened it.

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F34 | Cursor imports a plugin that Claude Code installs within about 2 s. Its agent host registers watchers on `~/.claude/plugins/installed_plugins.json`, `known_marketplaces.json` and `cache/` (log, 16:00:12). `sport80@fortified-strength` was installed in Claude Code at 16:00:01.9 and first loaded by Cursor (`loadClaudePlugin`) at 16:00:03.7; `fortified-strength-design@fortified-strength` was installed at 16:31:32.7, first loaded at 16:31:33.9, and the loader's total went from 40 to 41 at 16:31:34.4 | firm (two observations) | the "Cursor Plugins" log of launch 20261115T155928, `installed_plugins.json` |
| F35 | A version bump of a plugin Cursor already imports did not trigger a reload. `claude plugin update skill-craft@whichguy` (2.41.1 to 2.41.2) ran at 16:14:02; the last `loadAllPlugins` before it was at 16:09:41 and the next at 16:29:40, whose cause I did not identify | firm for that 15-minute window (one observation) | the same log |
| F36 | While Cursor's own copy was installed, the Installed list had one skill-craft row, the native one: v2.41.1 with 27 skills (sport80 included) and an Uninstall button, although Claude Code had 2.41.2 with 26 since 16:14:02 and Cursor had reloaded Claude Code's plugins at 16:29:40 and 16:31:34. A native copy shadows the Imported one and stays on its commit, as Round 11 inferred in F33. The removal of sport80 from skill-craft (`4ef10ecc7dd65341c77020905df6a48393cd2181`, released in `5b93207807a33e1610c89282031726e18285c021`) is what made the two copies tell apart: 27 skills against 26 | firm | the app's Installed list and the skill-craft page, read through the accessibility tree and screenshots; `~/.cursor/plugins/cache/whichguy/skill-craft/3c55b80288a0f7bd136c155342f27cdc43d1f557` (2.41.1) |
| F37 | After `cursor-agent plugin marketplace remove whichguy` (16:51:45) and the owner's quit and reopen (launch 16:55:12), the Installed list shows skill-craft **Imported**, publisher whichguy, v2.42.0, 26 skills: Claude Code's install (2.42.0 since 16:52:16, from another session's release `e0d4ec65b1f27c56a4ee9703abca69d4a52cb36d`). The launch log has `loadClaudePlugin skill-craft@whichguy` and no `Adding enabled plugin: skill-craft`. So with no native copy Cursor shows what Claude Code has installed, at the launch | firm (one launch) | the "Cursor Plugins" logs of launch 20261115T165512; the skill-craft page |
| F38 | The removal did not hold for a minute. Another session's 2.42.0 host refresh, following the procedure that this document then gave, re-registered `whichguy` at 16:52:51 (`gitRef` e0d4ec65b1f27c56a4ee9703abca69d4a52cb36d). No Add followed (no `Adding enabled plugin: skill-craft` in the relaunch log), the registration was removed again at about 16:58, and that session acknowledged by message that it will not re-register | firm | `cursor-agent plugin marketplace list --format json` (`lastIndexedAt`); the peer's reply |
| F39 | Cursor's own account of this, from its documentation and from forum replies that read as Cursor staff (2026-07-25 to 2026-11-03): a plugin added by `/add-plugin` from a GitHub URL stays at its install commit, which a reply calls a known bug with no date; plugins in the official Marketplace are pinned, and each update is reviewed before it reaches clients; the one documented way to track a branch is a team marketplace imported from GitHub with Auto Refresh (the Cursor GitHub app installed on the repository; at most one re-index every 10 minutes; Teams plan: one team marketplace, Enterprise: unlimited); forum users report that Auto Refresh sometimes misses changes. Cursor's documentation says nothing about imported plugins | interim (read from pages and replies, not exercised) | https://cursor.com/docs/plugins and the forum threads on plugin updates, team marketplaces and publishing an update |

Decided (owner, 2026-11-15, "Yes, remove it"): on a machine that has Claude Code, Cursor keeps no skill-craft registration and no
native install, and runs Claude Code's copy. docs/distribution.md "Cursor" and its refresh table now say so: the per-release
Cursor steps are gone, `claude plugin update skill-craft@whichguy` is Cursor's refresh and a Cursor launch shows it, and the native
route stays only for a machine without Claude Code. This supersedes the native install of Round 9
(`cd389ecdf3c61b5609c0e752f6b92bf941924f6b`) and Round 11 (`200903effa4c503c31a5f818dba94d245b2eaef3`) on this machine. The aim
of Round 9, skill-craft in the Cursor app, holds: it is there, as an Imported plugin.

Contrary evidence and unknowns:
- The Imported copy is Claude Code's. Cursor lags it until a launch (F35), a machine without Claude Code or with a Claude Code that
  nobody updated leaves Cursor behind, and Claude Code updates `whichguy` only when a session runs `claude plugin update`: its
  `known_marketplaces.json` carries no auto-update flag for any marketplace, and whether Claude Code can auto-update a third-party
  marketplace was not verified.
- One launch and one 15-minute window. Whether a window focus makes a running Cursor re-read Claude Code's install, as staff
  describe for marketplace plugins, is untested.
- The imported copy's hooks (the plugin ships ShipLoop's hooks) were not examined in Cursor; forum users report that hooks of
  imported Claude plugins misbehave there.
- Cursor's cloud agents read the account's enabled list, which no longer names skill-craft (inferred from the launch log, not read
  from the account).
- Cursor's other four registrations are still pinned at their add dates (claude-plugins-official 2026-09-03, grok-plugin-claude-code
  2026-07-13, openai-codex 2026-07-03, claude-craft 2026-06-15), and a `fortified-strength` registration made by another session is
  pinned at `5b2d2dcef56089ed74513461dfff8660e5742087`. None was touched. async-suite and codex are installed natively in Cursor (its launch log) at those registrations' commits and
  Claude Code has them too, so they probably sit behind a native copy in the same way; not checked.
- Cursor left the old cache folder of the native copy on disk.
- The Teams route (Auto Refresh) was not tried: it needs a paid plan, which I have not checked the owner has.

Evidence: the "Cursor Plugins" logs of launches 20261115T155928 and 20261115T165512 (under `~/Library/Application
Support/Cursor/logs/`; they list the account's whole plugin set, so they stay on this machine and the table carries the lines that
matter), `cursor-agent plugin marketplace list --format json` before and after, `~/.claude/plugins/installed_plugins.json`, and the
app's Installed list and skill-craft page.

## Round 13 — below the floor, ShipLoop runs again on a qualifying Python (2026-11-18)

Superseded in part by Round 14 (2026-11-18, the owner): the floor is now 3.9, what the code needs, and the card states no
version; the run again described here stays, for interpreters below 3.9.

Found by the closed-loop smoke of 2026-11-18 (`docs/closed-loop-journal.md` R15): in a login shell macOS path_helper puts
`/usr/bin` first, so `python3` was Apple's 3.9.6, below the 3.15 floor that 7a04fc044edb4418e92551c5619c48192862575b set
(that commit made no live run). One model session found `python3.15` and carried on; the other followed the card ("ShipLoop
needs `python3` 3.15 or newer ... report the missing prerequisite"), ran `python3 --version` itself and stopped before
starting the CLI. The owner, in their words: "We should not fail on the python version of we don't have to , that should be
just pick up the last minimal version." I read it, and said so, as: below the floor, use the newest installed Python that
meets it, and refuse only when there is none.

| Change | Where |
|---|---|
| Below the floor, `require` runs the same script again with `os.execv` (the process is replaced, so stdin, a hook's payload, is untouched and the exit status is the new run's) on the newest `python3` or `python3.N` on PATH that is 3.15 or newer, keeping `-I`, `-E`, `-s` and `-B`. Each candidate is asked its version once with `-c`; the running interpreter and a `python3.N` whose name is below the floor are not asked; one file under two names is asked once. `SHIPLOOP_PYTHON_REEXEC` marks the run again so a second one never follows, and an interpreter at the floor clears it for its children. With no qualifying Python, the CLI still exits 2 with one line (now naming the interpreter that ran) and a hook event still exits 0 silently | `skills/shiploop/scripts/shiploop_pyfloor.py` (`candidates`, `newest`, `require`), still Python 3.7 syntax |
| The card: start the CLI with `python3` even when `python3 --version` is older and do not check the version first; report a missing prerequisite only when the CLI refuses, or `git` or the CLI is unavailable | `skills/shiploop/SKILL.md` |
| The floor test (16 tests): the refusal with only old interpreters on PATH, or none; the run again picks the newest and keeps arguments, options and stdin; the mark stops a second run again; a chosen interpreter that cannot be run is named; at the floor the mark is cleared. Every other interpreter is a stub that answers the version query and records what it ran | `test/shiploop-python-floor.test.py` |
| The card's floor phrase, as the published-install smoke and the package-integrity fixture read it | `test/published-install-smoke.py`, `test/shiploop-package-integrity.test.py` |

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F40 | Apple's `python3` 3.9.6 first on PATH no longer stops ShipLoop on this Mac: in a throwaway HOME's login shell, as in the smoke, `python3 --version` says 3.9.6 and `python3 <cli> --help` exits 0 on Homebrew's 3.15.1; a hook event exits 0 with no output; with no qualifying Python on PATH the CLI exits 2, naming the interpreter that ran (Xcode's, behind the `/usr/bin` stub) | firm (one machine) | `docs/experiments/closed-loop-smoke-20261118/python-auto-select.txt` |
| F41 | The run again costs a hook event about 50 ms here: median 85 ms with Apple's `python3` first (search, then 3.15), 36 ms when `python3` already meets the floor, 16 ms for the old exit that did nothing (15 runs each, idle machine) | firm (one machine) | the same file |
| F42 | A card that states a prerequisite's version sends the model to check it and stop, where the CLI could have carried on; the card now says what the CLI does and when to report | interim (the old wording's effect rests on one session; the new wording has not met a live session) | `docs/experiments/closed-loop-smoke-20261118/python-in-login-shells.json` |
| F43 | Each rule of the search is held by a failing test when broken: 8 of 8 mutants caught (no name skip; no realpath dedupe; first qualifying instead of newest; no mark check; mark kept at the floor; options dropped; exec failure not named; a hook event printing the refusal), the file restored and its digest checked | firm | the mutation driver's output, quoted in the commit message |

Decided (routine): the newest qualifying interpreter, per the owner's words; `os.execv` rather than a child process, so no
second process carries ShipLoop's work and a hook's stdin needs no copying; the word "newest" stays out of the card, whose
recovery check forbids it (that rule is about guessing a run folder, so the card says "a `python3` or `python3.N`").

Published (2026-11-18): 11520fec0b3acf22e6228ef6a26d4efe8ad41189 (the harness's pin) and bd871a887de9a0481cd4d1483d54144bd14b20fd (this
change) through `release-push.py` with three checks, then release 95670c1b0f1c16e56dee8edfbae131bdf7a7aeab (skill-craft 3.1.0, shiploop
2.1.0) with four. Claude Code, Codex and Grok read back 3.1.0, and each installed copy holds the new `shiploop_pyfloor.py`; Cursor runs
Claude Code's copy. The published-install smoke passed on the release, including its Docker check on a real Python 3.7.3 with no newer
Python in the image: the CLI refuses (exit 2, one line) and a hook event stays silent (exit 0)
(`docs/experiments/closed-loop-smoke-20261118/published-install-3.1.0.txt`). CI on main: green for both pushes (run 44286570043 on the two commits, 44286733259 on the release).

Contrary evidence and unknowns:
- No live model session has met the new card wording or the run again. The next real E2E run will not exercise it either:
  the harness now pins `python3` in its throwaway homes (`docs/closed-loop-journal.md` R16).
- Linux was not run live; the hermetic tests run there in CI.
- A pyenv-style shim answers the version query through its own launcher; its cost and output were not measured.
- A free-threaded build (`python3.15t`) is not a candidate.
- The search runs on every hook event while `python3` is below the floor; nothing is cached.
- `shiploop_status_hook.py` (the status display hook) has no floor check; it still imports and exits 0 on 3.9.6, so it was
  left as it is.

## Round 14 — the floor is what the code needs, and the card states no version (2026-11-18)

Supersedes in part Round 13 (its "3.15 floor") and F42 (the card now states no version). The owner, in their words: "Do not put
artificial mandates which are not specifically necessary , such as the min python version. Don't fixate too much on this, lighten up the
restriction and republish. Merge to main and publish when done." The 3.15 floor came from the owner's 2026-11-16 direction to
standardize on the latest stable Python (7a04fc044edb4418e92551c5619c48192862575b), which raised ShipLoop's number and changed none of
its code. ShipLoop's own scripts now carry only what their code needs; the repository's tooling, the E2E apparatus and CI keep the
latest-stable policy.

| Change | Where |
|---|---|
| `FLOOR = (3, 9)`, what the code needs (Round 3's F5: `os.PathLike` subscripted, `str.removeprefix`); the run again of Round 13 stays for 3.7 and 3.8 | `skills/shiploop/scripts/shiploop_pyfloor.py` |
| The card asks for `python3` and `git` on PATH, states no version, and reports a missing prerequisite when the CLI says its Python is too old | `skills/shiploop/SKILL.md` |
| The floor test at 3.9; a card test that no Python version is named; the published-install smoke no longer ties the published FLOOR to the repository's 3.15 or to the card | `test/shiploop-python-floor.test.py`, `test/published-install-smoke.py`, `test/shiploop-package-integrity.test.py` |
| ShipLoop's minimum is its code's; the 3.15 statements are the repository tooling's | `docs/distribution.md`, `docs/ARCHITECTURE.md` |

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| F44 | ShipLoop's code still runs on Python 3.9: all 58 runtime files compile under Apple's 3.9.6, and the 76-suite `python-floor` selector with 3.9.6 as `python3` passes 74; the other two are tests about the floor itself (the floor test as it encoded 3.15, and the published-install probe's own 3.15 minimum as repository tooling), and both pass after the change. With FLOOR at 3.9, Apple's `python3` starts the CLI and a hook directly | firm | `docs/experiments/closed-loop-smoke-20261118/python-floor-3.9.6.txt` |

Unknowns: CI runs the latest stable Python only, so a later change can come to need a newer Python unnoticed; the floor is checked when
it changes (the `python-floor` selector under an old `python3`). The `shiploop-e2e*` suites are not in that selector and were not run on
3.9 (repository tooling, 3.15).

## Proposals as first written (2026-10-31; applied as Round 3)

1. **Declare the floor.** One line in `skills/shiploop/SKILL.md` and its README: Python 3.9 or newer and `git` on PATH.
   The card has 545 bytes of headroom under its 30,500-byte bound (`test/fixtures/shiploop-card-ledger.json`).
2. **Hooks fail open.** Replace the four Python hook entries with `sh` wrappers on the pattern `shiploop-status-hook`
   already uses (`command -v python3 … || exit 0`), and make the Python entry exit 0 under 3.8 or older; give the CLI a
   one-line "needs Python 3.9" message before its first import. Removes F4 and the bare traceback of F5.
3. **Test the floor.** One CI job on Python 3.9 over the product suites. It needs the runner's `ignore_cleanup_errors`
   removed, `from __future__ import annotations` in the four test files, and a decision whether the E2E apparatus
   (`os.waitid`, `sys.stdlib_module_names`) must also run on 3.9 or is declared 3.10+.
4. **Leave as is:** hook cost (45–60 ms; a text-only pre-filter would change `observe`'s claim refresh for bound
   sessions), the Grok hook self-install (documented), and no `doctor` verb (the failures already name their cause).
