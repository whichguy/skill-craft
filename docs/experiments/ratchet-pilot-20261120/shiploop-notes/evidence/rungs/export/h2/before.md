R-3 as the newest commit of the spec at or before N1 (2026-11-23T02:19:10Z) holds it, unverified:

## R-3 File migration and rollback

On startup, the single service writer fills missing deadlines from each stored ticket's created timestamp and current priority. It atomically persists a changed snapshot before listening, even with visibility off, and never updates already assigned values. Preserve version 1, identifiers, history, outbox and existing fields. Verify a legacy fixture, a restart with changed hours, and a real 1.4.0 startup on the candidate file with every ticket visible. Before a binary rollback, backup the enriched file because the old writer discards fields it cannot retain.
