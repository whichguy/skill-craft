# Architecture: admin user management

How the product is built. What it must do is in `spec.md`; each file avoids restating the other. All decisions below are
**proposed** because no repository or stack was available to inspect; each must be revalidated against the host once discovery
can read it. Decisions are `AD-<n>`; product decisions and assumptions in `spec.md` are `A-<n>` and `G-<n>`.

## Decisions

- **AD-1 Synchronous, in-request import (supports R-4, R-5, R-6).** The import validates and commits inside the one request and answers with the
  result. No job queue, worker or status record. Rationale: the row and byte bounds keep the work to one request, and there is no promised
  background work. Revalidate if the value chosen for G-1 cannot finish within the host runtime's request time limit; the alternative is a durable
  operation record with a worker that survives restarts.
- **AD-2 Atomicity through one store transaction with a case-insensitive unique key on canonical email (R-4).** Alternatives: per-row inserts with
  compensating deletes (rejected, they leave a visible partial state), an application lock (rejected, it does not protect other writers).
  Depends on the host store supporting both (G-3). If it does not, escalate to the user rather than weakening R-4.
- **AD-3 Capped streaming read of the upload before parsing (R-6).** The handler stops reading at `MAX_FILE_BYTES + 1` bytes and parses the bounded buffer
  with a CSV reader that follows RFC 4180 quoting. Limits come from injectable configuration, with no compiled-in value (G-1).
- **AD-4 Reuse the host's authentication and role check behind one injectable admin decision (R-1).** No new role model or session mechanism. Revalidate at G-2.
- **AD-5 Audit through the host's existing audit or structured-log facility (R-7).** No new store. If none exists, adding one is a decision for the user (G-5).
- **AD-6 UI built with the host's UI toolkit and tokens (R-8, NFR-6).** If the host has none (G-6), plain HTML and CSS with a small token set for
  spacing, type, a light and a dark palette, and a single icon set; no new framework solely for appearance. The plan records the concrete tokens and the chosen visual direction here.
- **AD-7 Test seams (NFR-9).** Injectable limits, admin decision, store with fault and pause points (for AC-4.2 and AC-4.4), a read counter on the upload body (AC-6.4), and a clock.
