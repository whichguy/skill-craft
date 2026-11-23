R-3 as the newest commit of the spec at or before N1 (2026-11-23T02:19:28Z) holds it, unverified:

### R-3 Durable backfill

From each persisted record's creation time and stored priority, calculate any missing due time. Default November 2026: the server runs a repeatable backfill before listening, even with the flag off, so operators can run once with the old API visible and then enable it. If persistence fails, startup fails and the old file remains available. Existing due values, ticket IDs, timestamps, statuses, audit, outbox and counters persist. Check the file during the initial boot and restart with different hours.
