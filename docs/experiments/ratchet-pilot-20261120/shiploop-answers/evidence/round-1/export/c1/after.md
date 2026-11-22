### R-3 Existing state and rollback

Basis: 2026-11-22 response-time request (S6-S9).
- The rollout clarification requires DUE_TIMES=on startup to assign missing values from each ticket’s recorded creation and priority and save them before serving. An existing file with missing values can be used directly. Flag-off startup preserves existing deadlines and assigns no missing ones. Restart with different settings to prove existing values survive. Migration keeps audit, outbox, update times, counters and IDs.
- Actual release 1.4.0 starts and lists on the resulting file. Check against the repository's 1.4.0 snapshot. Its writer drops unrecognized ticket fields on save.
