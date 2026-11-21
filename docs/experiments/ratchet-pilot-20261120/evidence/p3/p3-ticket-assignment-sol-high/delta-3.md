# Delta 3

## What I used and tried

- Read the request, current specification, all three build and test reports, the earlier deltas, and the plan. Compared them with the README, API reference, operations guide, and relevant decisions and checks. There were no fix or referee reports in `ratchet/`.
- Started with `PORT=0 npm start`, a state symlink and a separate notification sink. Exercised creation, assignment, same-agent retry, handoff, clear, combined and unassigned filters, and lifecycle refusals and reopening. Tried the 64/65 ASCII, 32/33 emoji, 64/65 actor, 200/201 title, 1,024/1,025 body byte and 0/1 and 100/101 page size boundaries. Tried wrong types, blank and control-containing names, bad JSON, malformed UTF-8, split emoji bytes, and encoded and repeated query values.
- Ran the human list, raw list, history and weekly report on the live snapshot. Compared LF and Unicode-aware record counts and decoded raw names with separators, literal escape tokens and ordinary backslashes. Restarted on the same snapshot and checked that a pending notice reached the original recipient with its assignment-time title. Checked startup refusal for a notification sink alias and verified malformed snapshot diagnostics through a symlink in startup, the CLI and the report.
- Retargeted the state link while the process was running, compared both snapshots, restored the link and retried. Also blocked a direct state file replacement with a directory at the destination and compared a failed assignment with failed title and lifecycle writes. Restored the file, tried subsequent assignments and checked the audit, outbox and saved state. Stopped the service processes by PID.
- `node --test acceptance/run.cjs` passed all 247 checks. The initial concurrent `npm test` run stalled after an API test received a plain-text response where it expected JSON. I stopped that run by PID. Separate reruns with the TAP reporter and with plain `npm test` each passed all 151 tests.

## Added clauses

- **C-214** — product keeps to it: yes. Assignment returned HTTP 500 while the link pointed elsewhere. Both snapshots stayed byte-for-byte intact, and the retry committed after the original mapping was restored.
- **C-215** — product keeps to it: no. A title edit returned HTTP 500, but reads showed the attempted title. After storage was restored, a successful assignment persisted the edit and its audit entry, and queued a notice with that title.
- **C-216** — product keeps to it: no. Resolving an assigned `in_progress` ticket returned HTTP 500, but reads showed it as `resolved`. After storage was restored, reassignment returned HTTP 409. A later successful write persisted the failed transition and its requester notice.
- **C-217** — product keeps to it: yes. The service started with the target and its parent directory missing, created the snapshot on the first write, and saved the assignment where both paths could read it.
- **C-218** — product keeps to it: no. LF splitting and the weekly report counted nine tickets, and the fourth field preserved its embedded U+2028. A Unicode-aware splitter counted ten. The README calls the delimiter a newline and leaves LF framing and embedded title separators implicit.
- **C-219** — product keeps to it: yes. The README's single-pass rule recovered the exact names from the raw fifth field, including all three separators, literal `\u2028` and `\u005c`, and an ordinary backslash.
