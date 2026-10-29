# Help desk tickets

The ticket service behind the IT help desk. People report problems, agents work them through to closed, and every change
is on record. It is a small Node.js service with no dependencies:

- an HTTP API for tickets ([docs/api.md](docs/api.md));
- an append-only audit log of every change to a ticket;
- notifications to requesters, written to an outbox and sent by a background worker;
- an optional data file, so the service keeps its state across restarts;
- `bin/tickets.js`, a command line for operators, and `scripts/weekly-report.js`, the support leads' weekly report.

## Running

Node.js 22 or later. There is nothing to install: the service uses only Node's standard library.

```sh
npm start                    # node src/server.js, on PORT (4180 by default)
PORT=8080 DATA_FILE=data/tickets.json NOTIFY_FILE=data/notifications.jsonl npm start
npm test                     # node --test
```

## Configuration

Every setting is an environment variable. Unset or empty means the default.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `4180` | the port the API listens on |
| `DATA_FILE` | none | the JSON file the state is saved to after every change and loaded from at start; without it the state lives in memory and is gone when the process ends |
| `NOTIFY_FILE` | none | the file the notifier appends one JSON line to per notification (the mail relay tails it); without it notifications are kept in memory |
| `WORKER_INTERVAL_MS` | `500` | how often the background worker runs; `0` turns it off, and notifications stay pending |
| `MAX_BODY_BYTES` | `65536` | the largest request body accepted |
| `LOG_REQUESTS` | off | `1` logs one line per request on standard error |

A value the service cannot use (`PORT=http`, say) stops it at start with a message naming the variable.
[docs/operations.md](docs/operations.md) covers the data file, the worker and what to do with dead notifications.

## How it fits together

```
src/server.js        puts the service together from its settings and starts it
src/app.js           the HTTP routes; src/router.js and src/http.js are the plumbing
src/store.js         the tickets, the audit log and the outbox, changed together
src/tickets/         ids, the lifecycle (states.js), priorities, request checks, the listing's query
src/pagination.js    cursor pages
src/audit.js         the append-only audit log
src/outbox.js        pending notifications; src/backoff.js times the retries
src/worker.js        the background worker; src/notifier.js and src/templates.js send and word notifications
src/persistence.js   the data file
src/format.js        how the command line prints tickets
bin/tickets.js       the operators' command line
scripts/             the weekly report
```

A request reaches a handler in `src/app.js`, which checks it (`src/tickets/validate.js`) and calls one method of the
store. The store changes the ticket, appends the audit entry, enqueues any notification and saves the data file in one
step. Every few hundred milliseconds the worker delivers the outbox's due notifications. The decisions behind this are in
[docs/decisions/](docs/decisions/).

## Command line

`bin/tickets.js` reads the data file (`DATA_FILE`, or `--data FILE`); it never changes it.

```sh
DATA_FILE=data/tickets.json node bin/tickets.js list --status open
node bin/tickets.js --data data/tickets.json list --priority urgent --raw
node bin/tickets.js --data data/tickets.json show T-0042
```

`list` prints a table. `list --raw` prints one ticket per line with the columns separated by tabs: id, status, priority,
title. `scripts/weekly-report.js` runs `list --raw` and reads these columns by position, so they must keep their
positions.

```sh
DATA_FILE=data/tickets.json npm run report:weekly
node scripts/weekly-report.js --data data/tickets.json --json    # the counts as JSON, for the dashboard
```

## Development

The conventions are in [CONTRIBUTING.md](CONTRIBUTING.md) and the decisions in [docs/decisions/](docs/decisions/).
Changes are listed in [CHANGELOG.md](CHANGELOG.md).
