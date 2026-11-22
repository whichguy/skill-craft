### R-3 Compatible migration and rollback

Basis: help desk rollout request (S6–S8) and data file decision 8.
- Before serving, add and persist any missing due using the record's existing priority and creation time even when visibility is off. Preserve deadlines already set, ticket ids, status, update time, audit, outbox and counters. Test a mixed legacy/current file, observe disk before serving and retry under changed hours.
- The file remains version 1 and one process owns all mutations. Start the unmodified 1.4.0 server on a candidate file and read all tickets through its HTTP API. Document that writes by 1.4.0 drop the new metadata.
