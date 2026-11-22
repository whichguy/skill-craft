R-3 as it read when N1 was written (2026-11-22T20:54:02Z):

### R-3 Durable migration and rollback

Basis: 2026-11-22 request (S6-S8). Before accepting HTTP traffic, migrated records missing due are assigned from their stored creation and priority and saved atomically, even with the flag off. Preserve existing due, ticket IDs, metadata, audit and outbox. A restart with no missing deadlines skips the migration write. Startup fails if the backfill cannot persist. Verify with disposable files and a second restart at different hours. The 1.4.0 service starts on the new file and lists every ticket. Legacy rewrites drop due, so retaining assigned values through a rollback requires reconciling a saved copy when restoring the new release. Rehearse with 5433862 on the candidate's actual file. No production file is available to this run.
