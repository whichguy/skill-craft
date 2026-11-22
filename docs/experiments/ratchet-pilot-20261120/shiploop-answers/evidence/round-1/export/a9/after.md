### R-3 Backfill and rollback

Basis: request S6-S8, docs/operations.md and decision 0008. The service is the sole file writer.

Requester decision N1: On startup with DUE_TIMES=on, the service computes each missing deadline from the ticket’s saved creation time and priority, atomically saves the file, and then serves requests. Missing deadlines alone never prevent startup, and operators do not prepare the file by hand.

Backfill preserves existing deadlines and leaves audit, outbox and updated values unchanged. If the atomic save fails, startup cannot serve the unsaved state. Keep version 1 and all tickets so actual release 1.4.0 starts on the candidate’s file and lists every ticket. A legacy rewrite drops the optional field. Preserve a copy of the deadline-bearing file before running 1.4.0.
