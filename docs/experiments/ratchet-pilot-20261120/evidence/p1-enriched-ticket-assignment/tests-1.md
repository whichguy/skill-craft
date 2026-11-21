## Failing now

- C-64 — The ticket returns to Dana after a handoff or clearance, but only the first notice to Dana remains pending.
- C-87 — A padded name that PUT would trim returns an empty page. A whitespace-only filter returns a 200 empty page instead of 400 `invalid`. A 65-character filter also returns 200.
- C-103 — The table prints the same `-` for an unassigned ticket and a ticket assigned to the agent named `-`.
- C-114 — The single-ticket display omits the current assignee. A ticket saved with Dana Lee as its assignee shows the original fields and history only.
- C-123 — The failed save returns 500, but live reads show the new assignee, the appended audit entry and the queued notification.
- C-133 — Startup accepts stored assignees with 65 characters, an internal tab, surrounding whitespace or an unpaired surrogate. It reports no error for those records.
- C-136 — The operations guide omits the backup and ownership-loss instructions for rollback.
- C-137 — The operations guide omits the previous worker's assignment-notice limitation and the steps for draining or preserving pending notices.
- C-185 — `npm test` discovers five new assignment tests. Their coverage omits assignment persistence and CLI output.
- C-187 — The same-name retry returns 200 after storage access is restored, but the data file still holds the unassigned ticket. The failed request left the name in memory, so the retry is treated as a no-op.
- C-189 — The API reference omits the assignee ticket field, the assignment endpoint and the assignee list filter.
- C-190 — The command-line reference documents four raw columns and omits the fifth assignee column and its empty cell.
- C-191 — The failed save leaves the previous file readable and unchanged. The next distinct assignment receives audit sequence 3 and notification id 3, where both should have been 2.
- C-192 — PUT accepts an escaped unpaired surrogate and returns 200 with it in the ticket. The valid-pair round trip passes.

## Discoveries

- A bare `assignee` query parameter has the same meaning as `assignee=`. | Observable: List a mix of assigned and unassigned tickets with each spelling and compare the returned IDs. | Why: Both spellings select the same unassigned rows. The specification names only the spelling with an equals sign.
- Stored assignee strings should already be canonical, including trimmed edges. | Observable: Start on a version 1 file with `"assignee":" Dana "` and check the startup diagnostic for that field. | Why: The loader accepts this value today. The PUT trimming rule makes the file contract ambiguous unless it explicitly says whether to reject or normalize padded names.
- A clean shutdown can refresh the file's top-level `savedAt` without any ticket, audit or outbox changes. | Observable: Compare the document after the last request with the one saved by SIGTERM. | Why: The first shutdown comparison found a newer `savedAt` on an otherwise identical state.
- The previous release can drop assignees on clean shutdown even if the operator only reads the file. | Observable: Start the previous release on a copy, read the ticket and stop it cleanly without sending a mutation. Then reopen the copy with the assignment release. | Why: The copied ticket came back as unassigned after the old executable rewrote the file.
- The table renders last-change times to UTC minute precision, and `show` displays seconds and milliseconds. | Observable: View a saved ticket in both CLI modes and compare the displayed `updated` values. | Why: The specification requires both displays to show the time but leaves its precision unspecified.
