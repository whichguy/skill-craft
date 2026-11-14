# Beyond rows (first judgment)

## 1. messaging in W1 (nav-4620879404ae4d0ca212b764b907f042)

- Request: This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSO
- Decision: Outbox and worker notify each actual assignment
- Judge: The request asks only that "The agent a ticket is assigned to is notified", so a new outbox store and background worker is extra infrastructure for a small dependency-free service.
- Worktree: /Users/dadleet/e2e-runs-brownfield/20261029/bf-codex-r2-ticket-assignment/.shiploop-runs/work-20261029-160337-e2cb7e/worktree (present)

## 2. observability in W1 (nav-4620879404ae4d0ca212b764b907f042)

- Request: This directory is an existing Node.js service with no npm dependencies (README.md describes it): a help-desk ticket API, src/server.js, which `npm start` runs on the port in the PORT environment variable, with a command-line tool in bin/. Add ticket assignment. `PUT /tickets/:id/assignee` with a JSO
- Decision: Audit changes and retain outbox state
- Judge: An audit trail of changes and retained outbox state are not needed by any requested outcome; the request asks only for assignment, notification, filtering and listing.
- Worktree: /Users/dadleet/e2e-runs-brownfield/20261029/bf-codex-r2-ticket-assignment/.shiploop-runs/work-20261029-160337-e2cb7e/worktree (present)

## 3. observability in W1 (nav-74e056e50d3245199ca95a06f95d99ec)

- Request: Extend the ticket service with comments on tickets. `POST /tickets/:id/comments` with a JSON body `{"author": "<name>", "body": "<text>"}` adds a comment to the ticket and answers 201 with the comment, which has an `id`, the `author`, the `body` and when it was `created`. An author is a non-empty na
- Decision: audit and existing outbox report
- Judge: The request never asks for comments to be audited, and no requested outcome needs audit entries for them; reusing the existing outbox report for notification failures would be implied, but adding audit records for comments is extra.
- Worktree: /Users/dadleet/e2e-runs-multipass/20261031/mp-codex-ticket-comments/.shiploop-runs/work-20261101-001451-3d3a85/worktree (present)

## 4. messaging in W1 (nav-adfb1ff9ba5f4c1ca85f41821ae02f61)

- Request: Extend the ticket service with comments on tickets. `POST /tickets/:id/comments` with a JSON body `{"author": "<name>", "body": "<text>"}` adds a comment to the ticket and answers 201 with the comment, which has an `id`, the `author`, the `body` and when it was `created`. An author is a non-empty na
- Decision: outbox with worker retry, unique keys
- Judge: The request asks only that "that agent is notified of the comment"; an outbox store with a retrying worker and unique keys adds delivery infrastructure that this request does not need.
- Worktree: /Users/dadleet/e2e-runs-multipass/20261101/r4/R4a0-comments-seeded-old/.shiploop-runs/work-20261101-145344-b634ba/worktree (present)

## 5. observability in W1 (nav-adfb1ff9ba5f4c1ca85f41821ae02f61)

- Request: Extend the ticket service with comments on tickets. `POST /tickets/:id/comments` with a JSON body `{"author": "<name>", "body": "<text>"}` adds a comment to the ticket and answers 201 with the comment, which has an `id`, the `author`, the `body` and when it was `created`. An author is a non-empty na
- Decision: append audit entries and worker failure handling
- Judge: Audit entries are a new logging capability the request never mentions, and the worker failure handling exists only to support the extra outbox worker.
- Worktree: /Users/dadleet/e2e-runs-multipass/20261101/r4/R4a0-comments-seeded-old/.shiploop-runs/work-20261101-145344-b634ba/worktree (present)

## 6. state in W1 (nav-936609aebc1b4bd6958e94bf0962f3ad)

- Request: Build a small single-player Battleship game served by a Node.js HTTP server with no npm dependencies. server.js starts the server on the port in the PORT environment variable (default 3000). GET / serves a playable HTML page titled "Battleship" where the player fires at a computer-placed fleet on a 
- Decision: in-memory Map with idle/capacity prune
- Judge: An in-memory store of games is needed for /api/fire to find the game started by /api/new, but idle and capacity pruning is extra lifecycle machinery that a small single-player game does not need.
- Worktree: /Users/dadleet/e2e-runs/20261026/live-sonnet-battleship-01b9b3/.shiploop-runs/work-20261026-180223-49ce7c/worktree (present)

## 7. config in W1 (nav-2ea9619a404e48c88234fd6153e7a3b6)

- Request: Create hello.py that prints exactly "Hello, world!" when run, plus a unittest test in test_hello.py that verifies that output.
- Decision: .gitignore holds the rules __pycache__/ and *.pyc and nothing else; no runtime configuration file exists or is added
- Judge: The request asks only for hello.py and test_hello.py; adding a .gitignore with __pycache__/ and *.pyc rules is an extra file that neither the print behaviour nor the unittest needs.
- Worktree: /Users/dadleet/e2e-runs/20261026/pilot-ollama-dsflash-993a9d-hello/.shiploop-runs/work-20261026-181830-936fda/worktree (present)

## 8. observability in W1 (nav-287dd5c4be76449db65c62206a29a9a4)

- Request: Extend the ticket service with bulk reassignment and escalation. `POST /tickets/reassign` with `{"from": "<agent>", "to": "<agent>"}` moves every open or in-progress ticket assigned to `from` over to `to` and answers `{"moved": <how many>, "ids": [<their ids in id order>]}`; `from` and `to` must be 
- Decision: Audit assignment and outbox report; worker logs failures
- Judge: Logging worker failures is implied so failed escalations are not hidden, but an assignment audit trail and an outbox report add an audit log and reporting surface the request does not ask for.
- Worktree: /Users/dadleet/e2e-runs-brownfield/20261029/bf-codex-r1-ticket-escalation/.shiploop-runs/work-20261029-154207-70da0c/worktree (present)

