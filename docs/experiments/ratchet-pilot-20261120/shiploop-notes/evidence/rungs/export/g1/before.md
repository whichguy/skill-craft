R-3 as the newest commit of the spec at or before N1 (2026-11-23T01:45:49Z) holds it, unverified:

### R-3 Historical data and rollback

Basis: response-time request, 2026-11-22 (S6–S9), and decision 0008. On startup the only writer assigns missing timestamps using stored created and priority, saving all of them before listening. This automatic startup process while visibility is off is the 2026-11-22 default. Existing due, IDs, state, audit and outbox survive restarts. A failed save prevents serving. An unchanged 1.4.0 process must read the current version-1 application snapshot and show all tickets. The old writer strips additive fields from subsequent snapshots. Verify both a synthetic persisted backfill and real legacy boot. The production file and promotion remain with the operator.
