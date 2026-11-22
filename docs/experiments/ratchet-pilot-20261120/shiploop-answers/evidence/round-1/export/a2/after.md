### R-3 Data preparation and rollback

Basis: November 22, 2026 request for production-file preparation and startup/readability by 1.4.0. See docs/decisions/0008-json-data-file.md for the file and single-writer model.

- C-5: The requester decided that a DUE_TIMES=on startup assigns every missing due from the ticket’s stored creation time and priority, saves the file, and then serves. No manual preparation is required. Use a genuine version 1 fixture, verify the file and unchanged audit/outbox state at first HTTP read, and verify that a restart with changed hours keeps assigned values.
- C-6: Start the genuine 1.4.0 release on a copy of the candidate-written version 1 file and enumerate all IDs through HTTP. An old writer discards fields it does not recognize, so keep a backup when rolling back. Exercise only synthetic local data.
