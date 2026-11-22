### R-3 Compatible migration and rollback

Basis: help desk rollout request (S6–S8) and data file decision 8.
- The requester decided that startup with DUE_TIMES=on must generate missing due times from each ticket's creation time and saved priority, save the resulting file, and then serve. Existing tickets missing due never require manual preparation.
- Migration preserves deadlines already set, ticket ids, status, update time, audit, outbox and counters. Exercise a mixed legacy/current file before listening and retry under changed hours.
- The file remains version 1 and one process owns all mutations. Start the unmodified 1.4.0 server on a candidate file and read all tickets through its HTTP API. Document that writes by 1.4.0 drop the new metadata.
