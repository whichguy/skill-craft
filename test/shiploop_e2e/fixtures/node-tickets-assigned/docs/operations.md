# Operations

How the service runs in production, and what to look at when something is wrong. The settings are in the
[README](../README.md#configuration).

## Process

One Node.js process per host, behind the internal load balancer, started with `npm start` by the host's service manager.
It logs to standard error, one line per event; `LOG_REQUESTS=1` adds a line per request. `SIGTERM` stops it cleanly: the
worker stops, the server finishes the requests in flight and the state is saved.

`GET /health` answers `{ "status": "ok" }` while the process serves requests.

## The data file

With `DATA_FILE` set, the whole state (tickets, the audit log and the outbox) is one JSON document, rewritten after every
change through a temporary file and a rename ([decision 8](decisions/0008-json-data-file.md)). A crash leaves either the
state before the change or the state after it.

- Back it up by copying it; the copy is consistent, because the file is only ever replaced whole.
- At start the service checks every record. A file it cannot use stops it with a message that names the record, for
  example `data/tickets.json: tickets[3].priority is not a priority`. Fix the record, or restore the backup.
- Ticket numbers are never reused: the file keeps the next number, and a file whose next number is not above every
  ticket's is refused.
- The file grows with the audit log, which is never trimmed. At the help desk's volume that is a few megabytes a year.

## Notifications

A change that should tell someone something (a ticket received, a ticket resolved) enqueues a notification in the outbox
as part of the change ([decision 6](decisions/0006-notification-outbox.md)). The worker runs every `WORKER_INTERVAL_MS`
and delivers the notifications that are due: with `NOTIFY_FILE` set, it appends one JSON line per notification to that
file, which the mail relay tails.

- **Pending** notifications are waiting to be delivered. A failed delivery is tried again 1 s later, then 2 s, 4 s and
  8 s after the next failures (never more than five minutes).
- **Dead** notifications failed five times. The worker logs a warning for each. They stay in the outbox until the data
  file is restored or edited; look at `lastError`.
- **Sent** notifications stay too, as a record.
- A notification has a key. While a notification with a key is pending, enqueueing the same key again changes nothing,
  so a ticket resolved, reopened and resolved again within a few seconds sends one "resolved" notification, not two.

`GET /admin/outbox` lists them all by state. With `WORKER_INTERVAL_MS=0` the worker does not run and notifications stay
pending; that is how to look at what a change enqueues.

## The command line and the weekly report

`bin/tickets.js` and `scripts/weekly-report.js` read the data file and never write it, so they are safe to run beside
the service. The support leads' report runs every Monday at 07:00 from the operations host's crontab:

```sh
DATA_FILE=/srv/tickets/data/tickets.json node /srv/tickets/scripts/weekly-report.js --json > /srv/dashboard/weekly.json
```
