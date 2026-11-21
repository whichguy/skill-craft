# Invoice Reminders: architecture decisions

Structure and technology decisions for the product specified in `spec.md`. The spec holds what the product must do;
this file holds how it is built. Decisions are numbered AD-<n>. No repository existed when these were written, so
each is a proposal made from the spec's requirements; none is observed.

## Decisions

### AD-1 One-shot run command started by an external scheduler

- **Decision:** the reminder pass is a command that runs once and exits (`run`), started by an external scheduler
  such as cron; it is not a resident daemon with its own timer.
- **Rationale:** serves R-8 and R-3 with the least machinery: a missed or crashed pass is simply followed by the next
  one, no process supervision or in-process timer drift. Alternative considered: a long-running service with an
  internal timer; rejected because it adds supervision, restart and clock concerns for a once-a-day job.
- **Serves:** R-3, R-6, R-8. **Pending:** implementation; scheduler installation is G-6.

### AD-2 Durable ledger with a unique key, plus a process-lifetime run lock

- **Decision:** reminder state lives in a durable transactional store, one record per `(invoice_id, offset)` enforced
  by a uniqueness constraint; an attempt record is committed before the send is submitted and updated after. The
  single-run lock is an operating-system exclusive lock on a lock file that the OS releases when the process ends,
  not a lock record that must be cleaned up.
- **Rationale:** gives R-6's crash detection (in-flight attempt visible) and R-8's no-stale-lock behaviour.
  The storage engine and the lock primitive are chosen at plan time once the runtime is known (AD-4).
- **Unverified claim:** that the chosen platform's exclusive file lock is released on abnormal process exit is not
  yet confirmed against primary documentation or a probe. The plan must verify it on the target runtime (kill a
  lock holder and acquire from another process) before relying on it; the check is AC-8.3.
- **Serves:** R-6, R-7, R-8, NFR-1. **Pending:** implementation and the probe above.

### AD-3 Ports for the invoice source, the email sender and the clock

- **Decision:** the engine depends on three narrow interfaces: invoice source (list eligible candidates; read one
  invoice), email sender (submit one message, return accepted or failed or unknown), and clock (today's date in a
  timezone). Reference implementations: a file-based invoice source (fixtures such as S-0), a recording fake email
  sender with scriptable failure and kill hooks, and an injectable clock. Production adapters for the real invoice
  system and email provider are added when G-1 and G-2 are resolved.
- **Rationale:** B-1 and B-2 are external and unresolved; ports let R-1 to R-10 be built and checked now, and let
  every S-n scenario replay exactly (NFR-5). No service is added; the ports are in-process interfaces.
- **Serves:** R-2, R-4, R-5, NFR-5.

### AD-4 Runtime, language and configuration format (open)

- **Decision:** not made. No repository, stack or deployment target exists, and the request does not name one. The plan
  chooses the runtime, the configuration document format and the ledger engine, subject to: reading secrets from the
  process environment (NFR-2), a terminal that honours `NO_COLOR` (NFR-6), IANA timezone support (R-1) and
  an exclusive-lock facility (AD-2).
- **Status:** open for the plan stage; it blocks no spec requirement.
