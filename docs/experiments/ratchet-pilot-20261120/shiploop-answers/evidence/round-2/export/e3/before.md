R-3 as it read when N1 was written (2026-11-22T20:34:08Z):

### R-3 Backfill safely

An offline command fills missing due fields from each stored ticket's creation time and priority, preserves previously assigned due values and saves through atomic replacement. Enabled startup refuses incomplete persisted data.

Acceptance: start from 1.4.0-shaped JSON, refuse early enablement, backfill twice with changed settings, and reopen via HTTP. Verify preserved audit and outbox.
