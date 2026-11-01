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
   earlier), and no break has yet reached `main` that it would have caught.
3. **Eight E2E-apparatus suites fail on 3.9 with "write to closed file", unexplained.** The apparatus is declared 3.10+, so
   they are out of the job, but a failure that is not a 3.10 API may be a real defect that only shows up there. Worth one
   short investigation before the declaration is relied on.
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
