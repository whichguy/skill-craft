R-3 as the newest commit of the spec at or before N1 (2026-11-23T03:55:06Z) holds it, unverified:

### R-3 Persist historical deadlines before serving

- Based on S6–S8. Default of 2026-11-22: the upgraded service assigns missing deadlines on startup independently of display. It derives each from the stored creation timestamp and priority, preserves existing deadlines and saves atomically before accepting requests. Tickets created during the disabled phase also save their deadline. Test the actual data file before listening and after edits and restarts. A failure to persist prevents startup.
- Keep the old document version. Start the release 1.4.0 HTTP service on a file produced by the candidate and compare all ticket IDs and legacy fields. Audit, outbox, IDs and existing ticket fields survive the backfill. Operators own actual production rollout. The old writer's treatment of new fields limits rollback and is documented.
