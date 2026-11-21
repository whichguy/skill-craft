# Delta 2

## What I used and tried

- Read the request, current specification, cycle-one and cycle-two build and test reports, the first delta, and the plan. Compared their discoveries with the README, API reference, operations guide, assignment decisions, and relevant implementation and acceptance coverage. There were no fix or referee reports in `ratchet/`.
- Started the service via `PORT=0 npm start` and used disposable state and relay files. Created tickets, assigned and cleared them, repeated a normalized assignment, combined the three list filters, and followed a cursor after its anchor changed owner. Tried empty, wrong-type, over-limit and control-containing names, 64 versus 65 ASCII characters and 32 versus 33 emoji, escaped and malformed UTF-8, punctuation, duplicate query keys, and a split multibyte upload. Checked actor, intake field, request body, page size and startup setting boundaries. Edited and transitioned tickets, tried assignment on inactive tickets, and assigned again after reopening.
- Ran the human and raw CLI, ticket history and weekly report. Restarted on saved and legacy snapshots, delivered pending notices, and used a relay key to look up the corresponding actor and assignment-time title. Tried a snapshot with malformed UTF-8 in its title, a hard-linked sink at startup, and a symlink introduced at the sink while the service was running. Tested a state file selected through a symlink with a separate relay, and read raw CLI output containing Unicode line separators with Python's `splitlines()`.
- Stopped the service processes by PID. `npm test` passed all 142 tests.

## Added clauses

- **C-208** — product keeps to it: yes. Splitting the four emoji bytes across two HTTP chunks preserved `Daña 😀` in the response, the filter and the pending notice.
- **C-209** — product keeps to it: yes. Startup, the CLI and the weekly report each reported the snapshot path and UTF-8 error for an invalid byte in a title. The source bytes were unchanged.
- **C-210** — product keeps to it: yes. The alias left the assignment notice pending with the path conflict in `lastError`. After removing the alias, attempt two delivered the same key to a separate sink.
- **C-211** — product keeps to it: no. The assignment replaced the symlink with a new snapshot. The worker sent the new owner's notice, but the CLI and a restart on the original target showed the old assignee. The original target also lacked the new notice's outbox record.
- **C-212** — product keeps to it: no. Each name containing an embedded U+0085, U+2028 or U+2029 was accepted and searchable. For each name, Python's `splitlines()` returned four rows from a three-ticket listing.
