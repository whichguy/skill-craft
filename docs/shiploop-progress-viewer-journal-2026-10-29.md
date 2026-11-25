# ShipLoop progress viewer journal

Owner request, 2026-10-29: "when we begin a shiploop, we should emit a suggestion on how to launch the server to follow
the progress." The owner meant a localhost server for following a run. Design context:
[shiploop-owner-notes-design-2026-10.md](shiploop-owner-notes-design-2026-10.md) (option b of D5, "Not now" until this).
Reference: [status-display.md](../skills/shiploop/references/status-display.md#browser-viewer).

## Q1. Does a ShipLoop localhost status server exist? (2026-10-29)

**Finding (firm): no.** Before building, the whole machine was searched:

- A history pickaxe over all branches (`serve_forever`, `ThreadingHTTPServer`, `http.server`, `EventSource`,
  `text/event-stream`, `--serve`) found one ShipLoop hit, `03ebe9b8`, the owner-notes design that rejected `trace --serve`.
  Every other hit is an E2E check or a delivery fixture (`test/shiploop_e2e/checks/serve.py`,
  `test/experiments/shiploop_delivery/browser_consumer/serve_fixture.py`).
- `git grep --untracked` in the seven worktrees, the canonical checkout among them (so an uncommitted `serve` script would show) found no server code under
  `skills/`.
- `find` for `*serve*`, `*dashboard*`, `*status*server*` modified in the last four days found fixtures only; `lsof` showed no
  ShipLoop listener (ports 8765 and 8766 belong to `~/Documents/ChatGPT/local-net-updates`).
- The `shiploop_progress.py` docstring, `status-display.md`, `state-files.md` and `README.md` all said there was no HTTP
  listener or web server, and no test pinned that.
- A search of the owner's Claude Code and Codex session logs for a request or a build of it found none; sessions run from
  other surfaces may keep their logs elsewhere.

The start-of-run packet shared only the `progress.html` link, so there was nothing to launch.

## Decisions (routine, made in this change; AGENTS.md "Decisions")

| # | Decision | Why |
|---|---|---|
| D1 | Read-only: GET and HEAD for `progress.html` (also `/`), `trace.html`, `report.html`; 405 for any write method, 404 for any other path | The owner asked to follow progress. The reasons option b was refused for notes (a write path, a token, cross-site protection for it) do not apply to a viewer. |
| D2 | Loopback only (`127.0.0.1`), a Host check, `no-store`, a content security policy | The pages quote repository documents. A page on another site that resolves its own name to 127.0.0.1 must not read them. |
| D3 | The user starts it from a printed command; ShipLoop never does | Owner rule of 2026-10-11 (kept in the owner's memory, not in this repository): host hooks must see every command a skill runs. A model that ran it would also block on a server that never exits. |
| D4 | The command rides on the existing `Progress view:` line of a run's first packet (`state["history"]` empty) | `test/shiploop_e2e/packet_anatomy.py` classifies the line by its `Progress view: ` prefix, and `shiploop-head-order`, `shiploop-packet-completeness` and `shiploop-e2e-packet-anatomy` name the line or its block, so a second line would need new classifications. Later packets would only repeat it, and heads are tight (the coordination note of 2026-10-29 has a step-plan head at 19,997 of 20,000 characters). |
| D5 | The default port comes from a hash of the run directory; a taken port moves on to the next free one | A run keeps its address across restarts and two runs rarely collide. `--port N` and `--port 0` are explicit. |
| D6 | `--serve` clears a `--stop`, as `--start` and `--watch` do, and starts the observer unless the run is done or halted | The user who launches a viewer wants the page to move. A finished run keeps its frozen pages. |
| D7 | No server-sent events | The page already reloads on its timer; push is a separate step if wanted. |

## Verification (2026-10-29, worktree branch `feat/shiploop-serve-3f0ce7`, uncommitted)

- `test/shiploop-progress.test.py`: 26 tests pass (15 existing, 11 new in `ViewerTests`); `test/shiploop-progress-render.test.py`:
  13 pass (2 new). The new tests run the real CLI: the exact command the first packet prints is extracted, run with
  `--port 0`, and its page fetched. They cover the read-only methods, 404 for the run's other files and traversal spellings,
  the Host refusals, 403 for a symlinked or hard-linked page, loopback binding, port fallback and an explicit busy port,
  `--stop` followed by `--serve`, a finished run, and the interrupt path.
- Browser (the desktop app's built-in browser pane), `progress.html`, `trace.html`, `report.html` served by
  `view --serve`: the page's scripts run, the policy header blocked nothing, and the report link points at the viewer.
- Lint: `ruff --select F,E9,B,W6,E7` reports the same five findings before and after (old, none in the new code).
- A `ResourceWarning: subprocess is still running` in `ProgressTests` is in the unmodified baseline; `ViewerTests` run clean.
- Quick tier, `bash test/run-all.sh --group quick --changed-from HEAD` (41 suites, `--jobs 8`): the first run **failed** in
  `shiploop-package-integrity` (4 tests), and the second, after the fix below, **passed 41 of 41** in 154.6 s. The first run's
  shell exit code (0) was that of a trailing `tail`; the receipt (`status: failed`) was the verdict.
- `test/shiploop-e2e-packet-anatomy.test.py` (outside the quick tier): 30 pass.
- Rebase, 2026-10-30: the branch was rebased onto `origin/main` (`7fce12e4`, 11 commits ahead of its first base; none touched
  these files) as one commit. The quick tier, `--changed-from 7fce12e4`, **passed** again (41 suites in 179.6 s; receipt
  `status: passed`, run-all exit 0), and `test/shiploop-progress.test.py` (26) and `test/shiploop-progress-render.test.py`
  (13) pass when run directly. A docs commit from another session that the first rebase carried over (`c51f2266`, the
  stack-reference note in `test/shiploop_e2e/LEARNINGS.md`; its twin `4a8b6af1` is unpushed on local `main`) was dropped
  from this branch, so the change is only the viewer.
- Full tier, 2026-10-30 (`bash test/run-all.sh --group all --jobs 4`, 163 suites in 2,402 s, on the viewer commit rebased
  onto `5ca57d9e`, built `e4bb796b`): 161 pass, 2 fail, `shiploop-e2e-stage-oracle` (1 test, an environment probe) and
  `shiploop-e2e-stage-build` (2 tests, `/private/var` against `/var`). Both fail the same way on a clean `origin/main`
  (`ee831200`, run in a scratch worktree) and `8ff81566e1ef45054964bbcc65a1edac59f296a6` recorded the same two on
  `5ca57d9e`, so they are this Mac's. The run beside a live E2E round loaded the machine to a load average above 40.
- Second rebase, 2026-10-30, onto `origin/main` `ee831200` (three more commits; `shiploop_navigator.py` is touched on both
  sides and merged without a conflict; `baselines.jsonl` conflicted on appended rows and was resolved by keeping both
  sides). The quick tier, `--changed-from ee831200` (45 suites, `--jobs 8`), passed 44; `shiploop-e2e` failed one timing
  test, `SeedTest.test_launch_returns_when_the_host_exits_instead_of_sleeping_out_the_poll_tick` (1.7 s against a 1.5 s
  bound, at a load average above 40). Alone it passes 3 of 3 at 0.5 s, and the suite's other 492 tests pass.
- E2E round, 2026-10-30: `hello` on Codex `gpt-6.1-terra` at xhigh, built from this checkout, passes every verdict (702 s,
  167 turns). The first packet carried the command, the model gave it to the user in a code block and did not run it, the
  other 19 outputs that showed a `Progress view:` line carried none, and the printed command served the finished run
  (200 for the four pages, 404 for other paths, 405 for POST, no file in the run changed). Entry "Progress viewer: does a
  host relay the first packet's launch command without running it?" in `test/shiploop_e2e/LEARNINGS.md`; evidence in
  `docs/experiments/progress-viewer-20261030/`.

## Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | The progress page's `<meta http-equiv="Content-Security-Policy">` tag lacked its closing quote since the page was first written, so it swallowed the next tag: a browser warned that `form-action` had an invalid source and dropped the colour-scheme tag. Fixed in this change. | firm | Introduced in `2148d213` (2026-09-28). Seen in the browser console once the page was served over HTTP; gone after the fix, with all four meta tags parsed. Test `test_head_meta_tags_are_closed_so_the_policy_and_color_scheme_both_apply`. |
| F2 | Over HTTP a browser will not open the page's `file:` links. The saved-report link now points at the viewer's own `/report.html`; the links to source documents stay `file:` (the previews are embedded). | firm | Browser check on a halted run; test `test_the_saved_report_link_can_be_pointed_at_the_viewer`. |
| F3 | The observer, started by `--serve`, rewrites `trace.html` and `progress.html` itself, so a test cannot plant those two files. | firm | Two first-draft tests failed on it; the tests now plant `report.html` and a symlinked `progress.html`. |
| F4 | `test/fixtures/shiploop-card-ledger.json` pins three anchor phrases in `run-start.md`, among them "Show it once per run". A first rewording ("Show both once per run") broke the ledger; the command rule now follows the pinned sentence. | firm | First quick-tier receipt, `shiploop-package-integrity`: `progress-view: run-start.md lacks 'Show it once per run'`; green on the rerun. |
| F5 | A Codex Terra host relays the first packet's command to the user once and does not run it, so a run does not stall on a server that never exits. | firm for one run (n = 1: one host, one case) | `docs/experiments/progress-viewer-20261030/` (`score.txt`, `model-relay-message.md`, `serve-probe.txt`); the LEARNINGS entry above. |

## Not done

- No release and no push. After this change is on `main`, `scripts/release.py` ships it with whatever other notes are
  pending (at least the Apps Script card's, and the document stage's not-applicable record), and the hosts are refreshed.
- One host, one case: the Claude and Grok hosts, a hooks-off row and a second case are not measured, so the rate at which a
  model runs the command instead of relaying it is unknown.
- A run made by an older ShipLoop version was not served; only runs created by this branch were.

## 2026-11-19: the pages stop reloading; statuses say what was recorded

Owner request, 2026-11-19: the live view "does an incessant flickering refresh, like every second or so", and wants
"more of a background check and maybe a single-page app that would actually update if need be"; also "some of the items
that were done don't seem to have a status, and I don't know if that's an error or not". The owner then chose to build
all three parts of the plan (stop the flicker, fix the statuses, fix the layout), which included three reversals of
earlier choices, named below. Evidence: [measurements](experiments/progress-view-inplace-20261119/measurements.md).

### Q2. Why does the page flicker?

**Finding (firm).** The page called `location.reload()` every 5 seconds whether or not anything had changed (the trace
page every 10), on a page of 2.96 MB and 24,841 elements, and put the scroll position back one frame after the first
paint. The observer also rewrote both pages about every 13 seconds on an idle run (its heartbeat), so a check of the
file's date would not have helped.

### Q3. Are the missing statuses errors in the run?

**Finding (firm): no, none of them.** All were the display's own: a packet's status read from a field only commands
have; a raw exit code shown as a status; three files asked of every visit although most stages never write them (all 110
"missing" rows were never due); records past the 160-file preview budget shown as "unavailable" instead of read; Improve
passes shown outside every visit; and four lifecycle rows that only an optional producer file can fill. Two test records
that really had failed were hidden behind "unavailable" until every record was read.

### Decisions

| # | Decision | Why |
|---|---|---|
| D8 | The open page checks a sibling script (`progress-version.js`) with a `<script>` tag and takes new content from another (`progress-content.js`, `trace-content.js`). No `fetch`. | A `file:` page cannot fetch, and the file is the default way to open the view. One mechanism serves the file and `view --serve`, so there is one behaviour to test. Measured: Chrome admits the sibling script under `script-src 'unsafe-inline' 'self'`. |
| D9 | The page is built from keyed blocks with a digest each; an update replaces only blocks whose digest moved. | A whole-section swap would close what the reader opened and lose the selection. With blocks, one new trace line replaces 5 of 487. |
| D10 | The observer rewrites a page only when its version moves; the version script is the heartbeat. **Reverses** the heartbeat republication of `2fdb95003103efb1b8e9653aabdee3cff4240087` (owner, 2026-11-19). | The heartbeat existed to move the page's embedded clock. The page now takes the clock from the version script, so an idle run writes 277 bytes per sample and not 10 MB per 13 seconds. The two pages can now carry different observation times, since each is rewritten on its own change. |
| D11 | A visit lists an Until receipt, check, expectations or test record only when the file exists. **Reverses** the always-listed candidates of `2fdb95003103efb1b8e9653aabdee3cff4240087`, which counted "20 missing candidates" as coverage (owner, 2026-11-19). | The owner read "missing" on finished stages as possible errors, and every one was a file never due. A file that disappears between the listing and the read still shows "missing". |
| D12 | With no producer reporting, the four external lifecycle rows become one "not reported" line. **Narrows** "unknown stays unknown" (owner, 2026-11-19): once any producer reports, every unreported row still shows `unknown`. | Four rows of "unknown" at the top of every ordinary run read as four failures. |
| D13 | Every structured record is read; the 160-file budget bounds only embedded previews (`not embedded`), and an unread packet preview says `not loaded`. Unchanged files are reused after one `stat`. | A status must come from the record, not from whether its preview fitted. The reuse keeps the observer's cost flat (0.212 s against 0.225 s). |
| D14 | An event no longer prints its journal's whole-file hash; the hash stays on the coverage row and the preview. | The hash moves at every appended line, which changed every visit's block: 78 blocks per line instead of 5. |
| D15 | Where the run stands (phase strip, current focus) comes before the journal; evidence previews and source coverage are folded under a count line. | They sat 104,556 px down the page. The page is now 43,245 px tall with the strip at 597 px. |

### Not done, and unknown

- No release and no push in this change. A ShipLoop release needs an E2E round journaled after it, or a `No-E2E-Round`
  trailer; the owner decides which.
- Safari and Firefox were not measured. If one refuses a sibling script on a `file:` page, the page there stays as
  opened and its "data age" line grows stale; `view --serve` is the way round it.
- A page already open when a new ShipLoop version starts observing keeps its old script until the reader reloads it.
- A snapshot page (an observer that stopped at its idle timeout) still does not come back to life when a later packet
  restarts the observer; it did not before either. The version script makes that cheap to add.
- The observer's own cost (about 43% of one core on the measured run, most of it rebuilding and screening both models
  every 2 seconds) is unchanged and was out of scope.
- The owner's live run keeps its 3.3.0 pages until that host's plugin is updated and its observer and viewer restart.

## 2026-11-24: canonical 8-state display, idle stat-gating, auto-revive, and multi-run Hub

Owner request, 2026-11-24: organize ShipLoop's status reporting and browser server coherently around all run states, surface clear startup browser-server instructions without auto-launching background servers implicitly, reduce observer watching overhead, and support multiple concurrent ShipLoop runs across repositories.

### Changes and measurements

- **8 canonical display states (`Active`, `Reviewing`, `Waiting on you`, `Waiting on service`, `Paused`, `Blocked`, `Done`, `Halted`) & aligned surface rules:** Added `display_status()` in `shiploop_navigator.py`, aligned `status_line()` onto Improve packets as a single compact line, added step-level `(Step <id> <n>/<total>)` progress to `implement`/`test`/`document` `Where:` and `narrative_facts()`, and unified `PROGRESS_REPORTING` in `shiploop_prompts.py` with `references/status-display.md`.
- **Stat-gated observer & `revivable` auto-revive (closing two 2026-11-19 open items):** `_watch_signature()` stats run inputs, `workspace.md`/`return-receipt.md`, inner-loop/check/note dirs, and watched repo docs (`docs/shiploop/spec.md`, `ARCHITECTURE.md`, `improve/receipt.json`). Idle watch samples skip `build_snapshot()` and `_refresh_trace()` and only rewrite `progress-version.js` + `progress-observer.json` (`test_stat_gate_skips_projection_when_idle_and_invalidates_on_doc_or_loop_change`: `build_snapshot` call count stayed `1` across 3+ idle ticks). Idle-timeout exit writes `revivable: true`, switching the browser page to 15 s polling until the next packet restarts the observer.
- **No-auto-launch startup recommendation + multi-run Hub (`shiploop_registry.py`, `shiploop_progress_serve.py`, `shiploop_protocol.py`):** First packet checks `active_viewer()`; if a Hub runs, it shares both `<url>/runs/<key>/` and `<url>/`; otherwise it recommends `shiploop view --serve` / `--serve --background` (and `view --run-dir=... --serve`). Added sandbox-safe registry (`SHIPLOOP_STATE_HOME` / `XDG_STATE_HOME` / `.shiploop-runs` / keepalive discovery), `shiploop view --serve` default multi-run Hub (`127.0.0.1:41730`, `--background`, `--stop-server`), `shiploop runs [--json|--active|--watch]`, and `shiploop status --watch`.
- **Small-scenario live concurrent check (disposable `/tmp/shiploop-hub-scenario-6vecfgd0`, isolated state homes):** 3 concurrent runs across 2 repos (`Reviewing`, `Waiting on you`, `Halted`, with shared-source-repo conflict between the two `repo-alpha` runs) + `view --serve --background`: `shiploop runs --json` returned `{"active": 1, "attention": 2, "done": 1, "paused": 0, "total": 3}` and reported the `repo-alpha` conflict; a 4th `shiploop init` printed both live Hub URLs; HTTP `GET /` (13,023 B), `GET /api/runs`, and all 3 `/runs/<key>/progress.html` returned 200; headless Chrome `--dump-dom` rendered `/` (18,973 B DOM, `Reviewing` + shared-repo banner present) and `/runs/<key>/progress.html` (70,856 B DOM); `view --stop-server` terminated the Hub and closed its port.
- **Suite isolation (`run_suites.py`, `state_home.py`, 5 CLI suites):** Added `SHIPLOOP_STATE_HOME` to `_STATE_OVERRIDES`/`STATE_OVERRIDES` and added `state_home.isolate()` to 5 suites that previously leaked subprocess registry writes to suite-level `XDG_STATE_HOME`. `--group quick --changed-from origin/main` passed 99/99 suites in 605.7 s wall, plus all 7 previously failing `--group shiploop` suites and `check-release-boundary.py --base origin/main` passed.

## 2026-11-25 follow-up: `experiments/` stat-gate closure, registry `--prune`, Hub UX polish, and idle CPU benchmark

- **`RUN/experiments/` & `Plan Improve` stat-gate closure (`15c641228` integration):** Added `experiments` (up to 24 sandboxes + `decision.md`/`meta.json` + 64 direct entries each, plus `.shiploop-improve/.experiments/<run_id>/`) to `_watch_signature()` in `shiploop_progress.py` and `_experiments_mtime()` in `shiploop_progress_serve.py`'s `_run_cache_key()`, and surfaced `Plan loop` / `Plan` summary chips in `/api/runs`, `_HUB_HTML`, and `shiploop runs`.
- **Registry hygiene & Hub operator UX:** Added `shiploop_registry.prune_registry()` (called on `shiploop runs --prune` and `serve_hub()` startup), dynamic `(<n>) ShipLoop Hub` attention title badge, and clipboard copy buttons (`status` / `resume` CLI commands) on blocked/waiting/paused Hub cards. Added standalone `startup_viewer_compliance()` audit helper in `test/shiploop_e2e/run_trace.py`.
- **Measured observer & 10-run Hub benchmark (disposable `/tmp/shiploop-bench-*`, synthetic 5-visit/50-trace-event run + `experiments/`):**
  - Uncached full `sample()` + `_refresh_trace()` + `publish()`: `46.39 ms` wall, `40.63 ms` CPU (`2.03%` of 1 core at a 2 s interval).
  - Stat-gated idle `sample(previous=last, previous_sig=sig)` + `announce()`: `1.10 ms` wall, `0.90 ms` CPU (`0.04%` of 1 core at a 2 s interval — ~45x lower CPU per idle tick).
  - 10 concurrent runs via `hub_runs_payload(cache=...)`: `7.60 ms` uncached -> `1.81 ms` cached.
