# U5 part A: render tooling (packets.py text render, render_diff.py, packet_anatomy.py)

Consumer: the integrator, who folds this row into `docs/shiploop-efficiency-journal-2026-10-16.md`, and every unit worker that
runs G-RENDER (`packets.py --offline ... --text-dir`, then `render_diff.py OLD NEW --unit Un`).

| Field | Value |
|---|---|
| Date | 2026-10-17 |
| Status | firm for the tooling (offline, no model); the head-table values are interim: they are today's heads on main, and U1 (merged branches) and U7 (allocation) re-baseline them in their own commits |
| Snapshot | main `da9e2e75` (skill-craft 2.5.0 / ShipLoop 1.5.0) plus the commit of branch `feat/shiploop-eff-U5a-1d5098`; no file under `skills/`, `agents/` or `plugins/` changed, so no packet changed by one byte |
| Fixture | offline walk of step case `node-fix-bug` (`test/shiploop_e2e/step_cases.json`), inline and ask-agent; the saved live packets of the Salesforce chess run 2 (`SP/pk/live`, 18 files, read only) for the anatomy exit |
| Run-dir length | 83 (a normal install) and 163 (the live run), CLI path 96 (plugin-cache install) |
| Unit | U5 part A (part B: `metrics.py`, `arms.py`, `clear.py`, `step_cases.json`, obligation and journal tests, fixtures, N5) |
| Evidence | `docs/experiments/shiploop-eff-journal-rows/U5a-evidence/` (anatomy before and after on the live packets, the four head-table renders, the `render_diff.py` exit demonstration); `test/shiploop_e2e/packet_head_table.json` |

## What was built

- `packets.py --offline CASE --text-dir DIR [--delegation ...] [--run-dir-length N] [--cli-path-length N]`: each packet as
  `<NN>-<stage>.printed.txt` and `.whole.txt` plus `manifest.json` (case, route, lengths, `text_format`, sizes, commit). The
  run directory and the CLI path have exactly the requested length (a real directory chain of that length; the CLI path is a
  symlinked package root, so the references still resolve). The text is fixed: ids from a counter, the run directory and the
  package root as `/home/render/w...` and `/home/install/i...` of the same length, the checkout root as a 63-character install
  root, the interpreter as `/usr/bin/python3`. Whole or head is decided on that text. `offline_packets` (the default walk the
  other suites use) keeps this machine's paths and random ids.
- `render_diff.py OLD NEW --unit Un`: every added and removed line with its size, per stage and per form (printed, whole); exit
  1 when an added line has no entry in `packet_changes.json` for a named unit (prefix; stages; routes; exactly one of `offset`
  (removed lines of the same stage that pay for it, one removed line pays for one entry) or `approval` (the decision)), or a
  printed text passes `packet_head_table.json`, or the table has no value (`--no-head-table` skips it by name); exit 2 when the
  renders were made with other options or the allowlist is malformed. `--emit-table DIR [--write]` records a render's sizes.
- `packet_changes.json`: one empty list per unit U1 to U35, one key per line, so units that add entries edit different lines.
- `packet_anatomy.py`: reads the quoted knowledge files, the hand-off values (open items, lists, quoted cases, followed
  requirements), the consumer-delivery block and the excerpt marker; the printed head (References, result template and
  pointer lines no longer count as the stage duty; the numbered duties under a one-sentence opening are the duty); the packets
  branch top lines (index pointer, owner rule, `GUIDES/` paths) and the final layout (pointer lines, style line, loop block that
  ends at "Call an exit condition satisfied only when", `HEAD_END`); `--glob` (read a text-dir) and `--max-unclassified` (exit 1).

## Exit items (part A)

| Item | Result |
|---|---|
| 3 (anatomy): at most 5% unclassified on `SP/pk/live/` (was 49.3%) | met: 0.2% (1,470 of 662,400 bytes); the base file measures 49.1% (325,409 bytes) on the same 18 files; `packet_anatomy.py SP/pk/live --max-unclassified 0.05` exits 0. Also 0 unclassified bytes on all 96 render files of the head table (4 keys, printed and whole, 12 packets each) and on the 192 files of `SP/eff2/final-verify` (main and merged tree, 83 and 163, both routes); the base file leaves 1.1% to 1.8% on main's renders and 4.1% (printed) to 5.4% (whole) on the merged tree's |
| 3 (render): `--run-dir-length 83` and `163` render reproducibly | met: two renders at each length are byte-identical (`diff -r`, 25 files each); the same text under another `TMPDIR`, and from a second copy of the tree (`git archive` of `skills` and `test/shiploop_e2e` into a directory with a longer name) all 25 files are byte-identical but the manifest's commit; every `--run-dir` in the text is exactly 83 (163) characters; every CLI path exactly 96 |
| 5 (render_diff): non-zero on a planted extra line, zero on an allowlisted change | met: planted line in a real implement head, empty allowlist: exit 1, line and size named; the same line with an approval entry: exit 0 with `--no-head-table`, exit 1 with the table (it passes the implement ceiling by 50); a shortened line with an offset entry and the shipped table: exit 0 (`render-diff-exit-demonstration.txt`) |
| 3, audit probes at `2686b427` (375,278 / 276,270 / 79,647) | not part A |

## Head table seeded from main (printed characters, CLI 96)

| Key | step-plan | implement | test | verify | carry-forward | largest |
|---|--:|--:|--:|--:|--:|--:|
| inline/83 | 19,692 | 15,053 | 14,891 | 15,555 | 15,915 | 19,692 |
| inline/163 | 20,892 | 15,933 | 15,852 | 16,135 | 17,115 | 20,892 |
| ask-agent/83 | 21,374 | 16,167 | 14,891 | 15,754 | 17,118 | 21,374 |
| ask-agent/163 | 22,574 | 17,047 | 15,852 | 16,334 | 18,318 | 22,574 |

These are measured with the CLI padded to 96 and the install root fixed at 63 characters, so they are not the plan's bare-CLI
numbers (`fv_heads.py`: step-plan 19,395 / 21,077 at 83): about +300 on step-plan from the CLI path and the fixed root. Main
already has step-plan over the 20,000 host cut for ask-agent at 83 and for both routes at 163.

## Suites

Run once each from the worktree (`SHIPLOOP_PROGRESS=off python3 -B test/<name>.test.py`), all exit 0: `shiploop-e2e-packet-anatomy`
(27 tests, 9 new), `shiploop-e2e-render-diff` (43 tests, new), `test-groups` (29; the pins moved from 87 to 88 ShipLoop suites,
140 to 141 in all, and the E2E family list gains the new suite), `ci-policy` (10), `shiploop-packet-completeness` (32),
`shiploop-packet-recut` (16), `shiploop-step-packets` (8), `shiploop-e2e-commit-counters` (105), `shiploop-e2e-slice` (28),
`shiploop-status-display` (15), `shiploop-e2e` (427; flow.py imports `packets.py`). The six fast ones were run again after the
last edit. `git grep` callers of the changed symbols: `offline_packets` (completeness, recut, step-packets, commit-counters),
`archive_packets`/`build`/`write_report` (slice, flow.py), `packet_anatomy` (its own suite). The default `offline_packets`
output is identical to the base's modulo ids and temp names (both routes, whole and printed; checked against the base file).

Skipped: the rest of the E2E family (`shiploop-e2e-environment`, `-baseline`, `-quality`, `-fidelity`, `-reorientation`,
`-runrecord`, `-chess-salesforce`, `-platform`, `-sf-guard`): they do not import `packets.py`, `render_diff.py` or
`packet_anatomy.py`, and `run.py`, `metrics.py`, `clear.py` were not touched (G-FOOT by the caller rule: `git grep` of the
changed symbols). No G-QUICK run (the unit's exit does not ask for it). `bash test/run-all.sh` and the full tier: not run.

Fail-first (revert only the source change, run the test, restore): the base `packet_anatomy.py` fails the new anatomy
tests (27 tests: 61 failing subtests and 3 errors); 6 mutations of `packets.py` (padding off by one, ids not fixed, CLI not
padded, run dir off by one, checkout root not canonicalised, head decided on the real text) are each caught by 1 to 5 tests; 11
mutations of `render_diff.py` (nothing unallowlisted, table never exceeded, missing table value passes, offset never short, a
removed line pays twice, other-option renders compared, every unit applies, offset and approval both, short prefix, offset need
not name a removed line, blank lines listed) and 8 of `packet_anatomy.py` rules are each caught by 1 to 7 tests.

## Key learning

1. A packet render is not comparable across checkouts as it stands: the temporary directory name, the ids, the checkout root
   (reference paths, the red-check script, the loop runtime) and the interpreter all print into it, so head sizes depend on the
   worktree's path length and two renders never diff clean. G-RENDER needs the fixed text; the 83/163/96 lengths then mean one
   thing on every machine.
2. The anatomy tool was blind to a whole class of live packets: the quoted knowledge files, hand-offs and consumer-delivery
   block were 49% of the bytes of the Salesforce run's packets, and in a printed head the References block, result template and
   pointer lines were counted as the stage duty. Its limit test (3% on the engine's own walk) could not see it because the
   walk has no knowledge files.
3. A head table that CI does not enforce is only as good as the commit that edits it: U1 and U7 re-baseline it with
   `render_diff.py --emit-table DIR --write` in the commit that journals the values; no other unit raises it.

Related commits: `da9e2e75` (base), `a7c1fdb2` (baseline row of the audit-fix run), `2686b427` (the audit probes' commit).
