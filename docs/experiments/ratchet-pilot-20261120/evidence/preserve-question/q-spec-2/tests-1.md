## Failing now
none — all 28 commands (C-1..C-22, U-1..U-6) exit 0 on the product as it stands and each prints its item id.

## Discoveries
- `list --raw` currently writes a fifth column (assignee) after the title; C-20 allows it, and the acceptance test checks only the first four columns | Observable: `node bin/tickets.js --data F list --raw` | Why: for an unassigned ticket the fifth cell is empty (a trailing tab), which a spec reader might not expect; not asserted either way.
- Acceptance files are named `acceptance/*.acc.js`, not `*.test.js`, because `npm test` (`node --test`) discovers every `*.test.js` in the tree and would run them (and C-22 would recurse into itself) | Observable: `npm test` runs only the files under test/ | Why: the first run of C-22 recursed and hit its timeout.
- A whitespace-only or control-character agent in the `assignee=` query filter is not tested (plan Decision 6 says 200 and empty list, the spec is silent) | Observable: `GET /tickets?assignee=%20` | Why: C-15 does not say how a value that could never be a valid name is treated.
- Re-assigning the same agent with surrounding spaces (`" dana "`) is treated as the same agent (a no-op) in the C-7 test, because C-3 says the name is trimmed | Observable: PUT `{"assignee":" dana "}` on a ticket assigned to `dana` returns it unchanged | Why: C-3 and C-7 together imply it but neither says so.
- `PUT` with a valid body on a resolved or closed ticket is 409 even when the name is 64 characters; a body that is invalid on a closed ticket (400 or 409) is not tested | Observable: PUT `{"assignee":""}` on a closed ticket | Why: the order of the 400 and 409 checks is not in the spec.
