# Closing review

Read the request, specification, `ratchet/fix-1.md`, acceptance cases, README, API reference, operations runbook and storage decisions. The packet contained no plan or build, test or referee reports.

Ran 31 existing acceptance checks, including all 15 use cases and the check that runs `npm test` on the current release and unmodified 1.4.0. Started the service on system-assigned ports, including through `npm start`. Exercised all four default deadlines, overrides across restarts, priority and lifecycle changes, overdue membership one millisecond before, at and after the deadline, page sizes at and beyond their limits, malformed input, and timestamp and identifier boundaries. Checked CLI and weekly report output, audit and outbox behavior, disabled preparation, activation, and rollback and recovery with 1.4.0. Ran the runbook's verification command against a partially prepared file and again after preparation. It reported the missing ticket before preparation and succeeded afterward.

## C-239 — Saving deadlines preserves the production file's read access

product keeps to it: no

With umask `022`, preparing a `0600` file produced a `0644` staging copy and a `0644` published file. After resetting the prepared file to `0600`, an enabled priority edit widened it to `0644` again. With umask `077`, preparing a `0640` file removed its group read access.

## C-240 — Failed preparation removes its staged copy of the production data

product keeps to it: yes

Forced the rename to fail after staging began. Startup exited with status 2 before listening. The original bytes and directory listing matched their state before the attempt, and a retry saved the deadline successfully.
