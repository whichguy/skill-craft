### R-3 Data preparation and rollback

Basis: November 22, 2026 request for production-file preparation and startup/readability by 1.4.0. See docs/decisions/0008-json-data-file.md for the file and single-writer model.

- C-5: A dark start from a genuine version 1 fixture writes missing due times from the stored created and priority fields before serving. Reopening under changed policy keeps previously assigned values. Verify the on-disk file and API, including a dark-created ticket and unchanged audit/outbox history. November 22, 2026 default: preparation runs automatically on startup.
- C-6: Start the genuine 1.4.0 release on a copy of the candidate-written version 1 file and enumerate all IDs through HTTP. An old writer discards fields it does not recognize, so keep a backup when rolling back. Exercise only synthetic local data.
