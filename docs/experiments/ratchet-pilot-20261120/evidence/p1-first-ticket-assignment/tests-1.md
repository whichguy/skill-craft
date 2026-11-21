## Failing now

- C-9 — Both conflict messages end with `: only open and in-progress tickets can be assigned` instead of ` and cannot change assignee`.
- C-12 — A missing assignee returns `assignee is required: an agent, or null to unassign`.
- C-13 — A non-string assignee returns `assignee must be a string`.
- C-44 — Clearing an assignee records `ticket.assigned`.
- C-48 — Assignment keys end in the agent name. Reassigning Dana after Sam leaves two pending events instead of three.
- C-51 — The delivered body says `Ticket T-0001 "VPN drops" is now assigned to you.`
- C-57 — Startup accepts untrimmed, overlength and control-containing stored names. It rejects non-strings and the empty string with `tickets[0].assignee is not a non-empty string`.
- C-63 — A padded query for Dana Lee returns an empty page despite an exact match after trimming.
- C-64 — Whitespace-only, tab-containing and overlength assignee queries return HTTP 200 with empty pages.
- C-68 — The table places `ASSIGNEE` between `PRIORITY` and `REQUESTER`.
- C-71 — CLI `show` goes from `updated` to `History` without an assignee field for either a named or an unassigned ticket.
- C-73 — The added `node:test` cases contain no assignment persistence or assignment CLI coverage.
- C-186 — The table prints `-` for an unassigned ticket.

## Discoveries

- Interior U+0085, U+2028 and U+2029 are accepted under the ASCII-control definition of single-line text. | Observable: PUT each character between `Dana` and `Lee` and read the unchanged interior character in the returned assignee. | Why: The service accepts all three, and “single-line” can also be read as excluding Unicode line separators.
- The public retry schedule ends before the five-minute ceiling can be reached. | Observable: The fourth failure schedules an 8000 ms retry and the fifth sets `nextAttemptAt` to null. | Why: C-154 checks the four delays through HTTP and runs the original focused backoff test for the ceiling.
- The in-memory delivery list is observable through the exported `createService` interface on `notifier.delivered`. | Observable: Start the service with no notification file and read the delivered record after an enabled worker tick. | Why: The HTTP outbox exposes delivery state, while the list records the rendered message.
- A keep-alive connection already in flight can delay SIGTERM exit until the connection goes idle and times out. | Observable: Send SIGTERM after receiving HTTP 100 Continue, finish the request and observe a 200 response several seconds before exit. | Why: The worker stopped and state was saved, while shutdown took about four seconds with the connection kept alive.
