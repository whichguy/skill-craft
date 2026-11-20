---
bump: minor
---
The live progress page and the trace page no longer reload themselves. An open page checks a small version script
in the background (about every five seconds) and, when the run's displayed content changed, swaps only the changed
blocks in place: no flicker, and the scroll position, open sections and search text stay. A page opened as a file and
a page served by `shiploop view --serve` update the same way. The observer now rewrites the two pages only when
their content changes, and writes three small scripts beside them (`progress-version.js`, `progress-content.js`,
`trace-content.js`); `view --serve` serves those too.

The progress page opens with where the run stands (phase strip and current focus) before the visit journal, and folds
the evidence previews and source coverage under a line that counts them by status.

Statuses on the page say what was recorded. A packet shows `sent` and a command `ok` or `refused (exit 2)` instead of
`unknown` or a bare exit code; a visit lists a receipt, check, expectations or test record only when that file
exists, so a stage that never writes one no longer shows it as `missing`; every such record is read for its real
status even past the 160-preview budget (`not embedded`), where it used to show `unavailable`; an Improve pass's events
appear under the visit it reviewed; and when no producer reports execution, acceptance, source return or owner hold, one
line says so instead of four rows of `unknown`.
