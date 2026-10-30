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

## Findings

| # | Finding | Status | Evidence |
|---|---|---|---|
| F1 | The progress page's `<meta http-equiv="Content-Security-Policy">` tag lacked its closing quote since the page was first written, so it swallowed the next tag: a browser warned that `form-action` had an invalid source and dropped the colour-scheme tag. Fixed in this change. | firm | Introduced in `2148d213` (2026-09-28). Seen in the browser console once the page was served over HTTP; gone after the fix, with all four meta tags parsed. Test `test_head_meta_tags_are_closed_so_the_policy_and_color_scheme_both_apply`. |
| F2 | Over HTTP a browser will not open the page's `file:` links. The saved-report link now points at the viewer's own `/report.html`; the links to source documents stay `file:` (the previews are embedded). | firm | Browser check on a halted run; test `test_the_saved_report_link_can_be_pointed_at_the_viewer`. |
| F3 | The observer, started by `--serve`, rewrites `trace.html` and `progress.html` itself, so a test cannot plant those two files. | firm | Two first-draft tests failed on it; the tests now plant `report.html` and a symlinked `progress.html`. |
| F4 | `test/fixtures/shiploop-card-ledger.json` pins three anchor phrases in `run-start.md`, among them "Show it once per run". A first rewording ("Show both once per run") broke the ledger; the command rule now follows the pinned sentence. | firm | First quick-tier receipt, `shiploop-package-integrity`: `progress-view: run-start.md lacks 'Show it once per run'`; green on the rerun. |

## Not done

- No release: `scripts/release.py --dry-run` refuses this commit (2026-10-30), because it changes `skills/shiploop/` after the
  latest E2E round. It needs a ShipLoop E2E round and a later `test/shiploop_e2e/LEARNINGS.md` entry, or a `No-E2E-Round`
  trailer.
- The packet text changed for a run's first packet only; no model run has yet seen it. Whether a host relays the command
  to the user is not measured here.
