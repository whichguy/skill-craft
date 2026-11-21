# Closing look

Read the request, the specification, the plan, the three build and test reports, the earlier deltas, the README, the API and operations guides, and the cursor and assignment decisions. There were no fix or referee reports in the workspace. Consulted the HTTP, CLI, persistence and delivery paths when checking the live results.

Ran `npm start` on an OS-assigned port with temporary data and notification files. Created, assigned, transferred, cleared, edited, resolved and reopened tickets. Checked a same-owner retry, a missing ticket, inactive-ticket refusals and unchanged saved state after invalid writes. Tried 1, 64 and 65 ASCII characters, 32 and 33 supplementary characters, exact and one-over body limits, and invalid types, whitespace, line breaks, a lone surrogate, duplicate members and malformed UTF-8. Checked percent and plus encoding, named and empty filters in conjunction with status and priority, page limits and continuation after reassignment.

Ran the CLI table, raw listing, ticket details and weekly JSON report. Restarted with the worker enabled and checked saved ownership, assignment notices for earlier recipients and the requester's resolution notice. Opened a legacy snapshot with omitted owner fields and checked that reads left the file unchanged. Tried altered version 1 copies with malformed bytes, ambiguous owners and ambiguous queued recipients. All 138 tests passed with `npm test`.

## Clauses added

- **C-174** · product keeps to it: no. A ticket with `"assignee": "CurrentOwner"` followed by `"\u0061ssignee": null` appeared unassigned after startup even though its audit still recorded the assignment. On a separate copy, a pending notice with `"to": "CurrentOwner"` followed by `"t\u006f": "OtherAgent"` was delivered to OtherAgent with the original ticket id.
- **C-175** · product keeps to it: no. The API accepted `owner\u202eABC\u202c` and both human-readable commands emitted the actual direction controls, leaving the letter order to the terminal's bidirectional rendering. The raw listing preserved the original name.
- **C-176** · product keeps to it: yes. With a malformed byte in a saved title, startup exited 2 before listening. The CLI listing and weekly report exited with encoding diagnostics and emitted no rows or counts. The snapshot bytes were unchanged.
