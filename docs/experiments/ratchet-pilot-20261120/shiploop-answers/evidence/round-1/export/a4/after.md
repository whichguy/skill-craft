### R-3 Production data and rollback

The requester decided (N1) that startup with DUE_TIMES=on fills every missing due time from the ticket's own creation time and priority, saves the file, and then starts serving.
Basis: November 22, 2026 rollout and rollback request. Startup preserves existing due times, ticket activity, audit history, IDs and outbox. Verify write before listening, repeated startup with changed settings and disabled startup on legacy data. The unmodified 1.4.0 must start and list every ticket from a file written by the candidate. Live deployment is operator-owned (docs/operations.md).
