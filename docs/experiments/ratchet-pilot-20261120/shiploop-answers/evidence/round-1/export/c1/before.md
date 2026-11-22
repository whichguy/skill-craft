R-3 as it read when N1 was written (2026-11-22T19:13:37Z):

### R-3 Existing state and rollback

Basis: 2026-11-22 response-time request (S6-S9).
- Default 2026-11-22: startup persists only missing values from each ticket's recorded creation and priority before serving, with or without the flag. Restart with different settings to prove existing values survive. Migration keeps audit, outbox, update times, counters and IDs.
- Actual release 1.4.0 starts and lists on the resulting file. Check against the repository's 1.4.0 snapshot. Its writer drops unrecognized ticket fields on save.
