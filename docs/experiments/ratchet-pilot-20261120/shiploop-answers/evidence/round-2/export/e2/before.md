R-3 as it read when N1 was written (2026-11-22T20:35:29Z):

### R-3 Historical data and rollout

Basis: 2026-11-22 request (S6–S8), docs/decisions/0008-json-data-file.md. Startup backfills only missing deadlines from the stored priority and creation, before serving. Existing deadlines and business state survive the same atomic save and future reads, with no migration audit or notification. Default rollout starts the new version with exposure off, verifies the file and restarts enabled. A failed migration prevents startup. Verify restart with changed hours and a mixed legacy file. Verify 1.4.0 at 15a4ad2 starts and lists every ticket from a candidate-written file. 1.4.0's later save strips unknown fields. Retain a pre-rollback file to recover deadlines by ticket ID without replacing current ticket state.
