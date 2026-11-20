# Progress view: in-place updates and plain statuses (2026-11-19)

Compact evidence for the journal section "2026-11-19: the pages stop reloading" in
[shiploop-progress-viewer-journal-2026-10-29.md](../../shiploop-progress-viewer-journal-2026-10-29.md).
Subject: one live run on this Mac (Codex host, ShipLoop 3.3.0 from the plugin cache, 80 visits, revision 97, one
Improve pass active). "Before" was read from that run's own viewer and observer without touching either. "After" is
this change run on a private copy of that run directory. The display scripts of 3.3.0 are byte-identical to the base
commit `90c381507ce1e690084b8476ae0d7dcc68422036`, so "before" is also the base.

## Before (the live run's own page and observer)

| What | Value |
|---|---|
| `progress.html` | 2,962,181 bytes, 24,841 elements, 132,420 px tall |
| `trace.html` | 7,285,690 bytes |
| Page refresh | `location.reload()` every 5 s (progress) and every 10 s (trace), changed or not |
| Scroll after a reload | restored one animation frame after the first paint (the visible jump) |
| Page rewrites while idle | both pages rewritten about every 13 s (10 s heartbeat plus sample time), 15 samples over 30 s |
| Observer cost | 75 min 24 s of CPU in 2 h 56 min elapsed (about 43% of one core) |
| Phase strip and "Current focus" | 104,556 px below the top, under 512 source-coverage rows |

Event rows inside the 80 visits, by `kind · status`:

| Row | Before | After | Why it was wrong |
|---|---|---|---|
| `command · 0` / `command · 2` | 243 / 14 | 0 | the raw exit code was the status |
| `command · ok` / `not passed (exit 2)` / `refused (exit 2)` | 0 | 243 / 8 / 6 | |
| `packet · unknown` | 117 | 0 | status was read from `exit`, which a packet has not |
| `packet · sent` | 0 | 117 | |
| `expectation · missing`, `check · missing`, `until · missing` | 72, 22, 16 | 0 | every visit was asked for all three files; all 110 were never due (checked against the run directory, stage by stage) |
| `test · unavailable` | 121 | 0 | past the 160-file budget the record was never read |
| `test · passed` / `skipped` / `failed` | 15 / 15 / 0 | 79 / 70 / 2 | two failed test records had been hidden as "unavailable" |
| `expectation · unknown` | 8 | 0 | the record has no status key |
| `expectation · N of M matched` | 0 | 8 | |
| events outside every visit | 87 | 0 | 84 belong to Improve passes; 3 to the stage under active review |
| lifecycle rows showing `unknown` | 4 | 0 (one "not reported" line) | no producer file exists in an ordinary run |

Stage by stage, which of the three per-visit files the run really wrote (visits / Until receipt / check / expectations):
intake to prepare 8/0/0/0; step-plan 8/8/8/0; test-spec 8/8/8/0; validate-existing 8/1/0/8; implement 19/19/14/0;
test 14/14/14/0; document 13/13/13/0; carry-forward 1/1/1/0.

## After (this change, private copy of the same run)

| What | Value |
|---|---|
| `progress.html` / `progress-content.js` | 2,784,020 / 3,024,940 bytes; page 43,245 px tall; phase strip 597 px from the top |
| `trace.html` / `trace-content.js` | 7,234,475 / 7,182,422 bytes |
| Keyed blocks in the page | 487 |
| Files rewritten while idle (real observer, 8 samples over 24 s) | `progress-version.js` only (277 bytes); both pages and both content scripts untouched |
| One appended trace line, real observer, progress page | 5 blocks replaced (`observer`, `story-head`, the one visit, `coverage`, `story-tail`), 482 kept; `performance.getEntriesByType("navigation").length` stayed 1; a page marker set before the update survived; `scrollY` 14,624 before and after; the open visit stayed open |
| Same line, trace page | "Commands" tile 260 to 261 and "Refused" to 7 without a navigation; `scrollY` 3,000 before and after; no leftover script elements |
| Heartbeat only | the "data age" line went from "32 sec ago · stale" to "current" with no block replaced |
| First cut of the blocks | one appended line replaced 78 blocks, because each event printed its journal's whole-file hash; with the hash left to the coverage row, 4 to 5 blocks |
| Story build, warm, best of 5 | 0.212 s (0.225 s before); reading every structured record costs nothing measurable because unchanged files are reused after one `stat` |

## Whether a `file:` page may load a sibling script

Headless Chrome 157.0.8103.79, isolated profile, a page with the progress page's content security policy loading
`probe.js` from its own folder:

| `script-src` | Result |
|---|---|
| `'unsafe-inline' 'self'` | loaded |
| `'unsafe-inline'` (the old policy) | blocked |
| `'unsafe-inline' file:` | loaded |

A real `progress.html` at version A, opened as a file beside scripts at version B, showed version B and "Page updated
in place: 5 sections changed" in the dumped DOM. Safari and Firefox were not measured.

## Checks run

- `test/shiploop-progress-render.test.py` 36, `test/shiploop-progress.test.py` 40, `test/shiploop-progress-data.test.py`
  44, `test/shiploop-trace.test.py` 59, `test/shiploop-status-display.test.py` 16, `test/shiploop-e2e-run-trace.test.py`
  28: all pass.
- The catalog's `affected` group for the changed files: see the commit message for its count.
