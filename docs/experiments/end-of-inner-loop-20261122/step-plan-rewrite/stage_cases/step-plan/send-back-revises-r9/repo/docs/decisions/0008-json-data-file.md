# 8. The state in one JSON data file

Date: 2025-06-30
Status: Accepted

## Context

Every restart (each deploy, and the host's monthly patching) lost every ticket. A database server is not available on
the hosts we run on, and the state is small: a few thousand tickets a year.

## Decision

We will keep the whole state (tickets, the audit log and the outbox, with the next ticket number and event id) in one
JSON document at `DATA_FILE`.

- The store saves after every change: the document is written to a temporary file in the same folder, which then
  replaces the data file (a rename), so the file is always a whole state.
- The service loads the file at start. Loading checks every record and keeps only the fields it knows; a file that fails
  a check stops the service with the reason.
- `src/persistence.js` is the one module that knows the format. Its record functions name every field the file keeps,
  for saving and for loading alike, so a field added to a ticket is added there too, or it is lost at the next restart.
- The format has a version (1). A change to the format must keep loading the files the previous version wrote: they are
  the data of a running service. A field older files do not have takes its default when they load.
- Without `DATA_FILE`, the state lives in memory only, as before.

## Consequences

- A restart keeps everything, and a backup is a file copy.
- Every change rewrites the whole file, which is fine at our size and would not be at a hundred times it.
- One process owns the file. The command line and the weekly report only read it.
