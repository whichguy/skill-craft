# Closing look

Reviewed the original request, `spec.md`, `plan.md`, the build, test and fix reports, `README.md`, and the service and test source. This workspace contained no referee report. All 12 tests passed with `node --test`.

Started `server.js` on ephemeral ports with temporary data files and exercised it through HTTP. Replayed the README examples, checked duplicates, wrong input, minimum amounts, a settlement tie and query strings, and tried ASCII and Unicode IDs at and above the published limit. Compared raw request targets with `fetch` for dot-only IDs. Sent malformed UTF-8, a BOM, amounts around the safe-integer boundary and beyond floating-point range, and truncated HTTP uploads. Left a committed response unread, restarted, and retried the expense. Verified 20 overlapping expenses on one process after a forced stop and restart. Then tried overlapping processes on one file and a save through a symbolic link.

## Additions

- **C-89 — Documented encoded ID limit**. product keeps to it: yes. A 48 KiB segment worked on all three group routes for both ASCII and emoji IDs, remained usable after restart, and received 400 on creation with one byte added.
- **C-90 — Instructions for accepted IDs subject to URL normalization**. product keeps to it: no. Both `.` and `..` returned 201 on creation. The README gives the general encoding rule, which led to 404 with `fetch` even with `%2E` escapes. Both groups returned 200 when the raw request targets were sent verbatim.
- **C-91 — Query strings preserve routing**. product keeps to it: yes. Both POSTs and both GETs worked with query strings, including requests addressing a group with a literal `?` in its ID.
- **C-92 — Malformed UTF-8 rejection**. product keeps to it: yes. Both POSTs returned 400 without changing the store. Startup rejected a snapshot containing an invalid byte and preserved its bytes.
- **C-93 — Incomplete uploads leave the store intact**. product keeps to it: yes. Closing each POST after sending valid JSON but fewer bytes than declared left the ID and expense number available.
- **C-94 — Amounts beyond exact representation capacity leave the store intact**. product keeps to it: yes. `1e400` was recorded exactly. `1e999999999999999999` returned 500, left persisted bytes intact, and left the next number available.
- **C-95 — Overlapping processes preserve acknowledged writes**. product keeps to it: no. Two processes on different ports using the same file both returned 201 with `{"expense":1}`. Restart recovered one contribution, leaving balances `{"Ava":2,"Ben":-2}` where the two acknowledged expenses together yield `{"Ava":3,"Ben":-3}`.
- **C-96 — A symbolic link preserves the identity of an existing store**. product keeps to it: no. An acknowledged expense replaced the link with a separate file. Restarting from the original target and from the configured link path recovered different balances.
- **U-20 — Reconnecting after an unread expense response**. product keeps to it: yes. After leaving the first response unread and restarting, the balance included the expense. Repeating the expense returned `{"expense":2}`.

The specification leaves duplicate-key handling and BOM tolerance open. Deeply nested extra fields are already covered by the requirement to ignore extras. The capacity clause leaves the supported range and error status open while requiring the failed expense to leave no record.
