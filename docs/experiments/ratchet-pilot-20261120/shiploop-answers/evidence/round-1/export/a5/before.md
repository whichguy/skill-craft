### R-3 Legacy migration

- While the service is stopped, backfill missing due from each stored creation time and priority. Preserve existing due, all other state, and schema version. A retry leaves completed work intact. Verify stored-file snapshots and rerun with different hours.
- Default 2026-11-22: `npm run backfill:due` is an explicit offline command. With the feature enabled, startup refuses any incomplete stored ticket set before listening. Verify the refusal and successful startup after backfill.
