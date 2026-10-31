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
