# Architecture decisions

How the user administration product is built. What it must do lives in `spec.md` (R-<n>); a structure or technology
choice is never a requirement. Decisions are numbered AD-<n>. Product decisions (PD-<n>) are in `spec.md`.

Status of this file: written at the spec stage with **no repository, discovery or research result available**. The
stack, the API conventions and the data store are therefore not yet known. Each decision below says what it assumes;
the plan reopens it against the real repository at discovery and either confirms it or replaces it with a new AD.

## Decisions

### AD-1: The import runs synchronously in one request, in one transaction

- **Serves:** R-6, R-9, R-3.
- **Decision:** the import operation validates the whole file and, if valid, creates every user inside one database
  transaction, all within the request that carried the file. The caller receives the final outcome in the response.
  No job queue, no status polling, no background worker.
- **Why:** R-6 is all-or-nothing (PD-1). One transaction gives that directly, and a response that is the outcome means
  an acknowledgment cannot mean "accepted but unprocessed", so no crash-between-ack-and-commit recovery exists to specify.
- **Assumption:** the file limits of R-3 keep one import inside the host's request-time and request-body limits. Those
  limits and the R-3 numbers are not known (OG-2). If the chosen R-3 limits do not fit, this decision is reopened and
  the spec gains an asynchronous-completion requirement; do not raise the limits past the host's hard limits.
- **Alternatives not taken:** an asynchronous job with a status endpoint (adds states, recovery and polling the request
  does not need at a bounded size); row-by-row commits (contradicts PD-1).

### AD-2: Import operation contract

- **Serves:** R-1, R-2, R-6, R-8, R-12.
- **Decision:** `POST /api/admin/users/import`, `multipart/form-data` with exactly one file part named `file`. The
  response body is JSON. Route naming and error envelope follow the product's existing API conventions if discovery
  finds any; the shape below is the default.

| Outcome class (spec) | HTTP status | Body |
|---|---|---|
| `created` | 201 | `{"outcome":"created","created_count":<n>}` |
| `rejected` (file-level) | 422 | `{"outcome":"rejected","created_count":0,"file_errors":[{"code":…,"line"?:…,"column"?:…,"limit"?:…,"found"?:…}]}` |
| `rejected` (row-level) | 422 | `{"outcome":"rejected","created_count":0,"error_count":<total>,"truncated":<bool>,"errors":[{"row":…,"line":…,"field"?:…,"code":…,"first_row"?:…}]}` |
| `rejected`, size over limit | 413 | same body as file-level, code `file_too_large` |
| `unauthenticated` | 401 | `{"outcome":"unauthenticated"}` |
| `forbidden` | 403 | `{"outcome":"forbidden"}` |
| `failed` | 500 | `{"outcome":"failed","created_count":0}` |

- A body without a `file` part, or with more than one, is `rejected` with file-level code `missing_file` (422).
- The response never echoes cell contents other than in the `errors` entries' `row`, `line`, `field`, `code` (R-11).
  The message text shown to the admin is composed by the client from `code`.

### AD-3: The user store's uniqueness constraint is the concurrency arbiter

- **Serves:** R-5, R-9.
- **Decision:** uniqueness of the normalised email (PD-4) is enforced by a unique constraint in the user store, in
  addition to the up-front existence check. A constraint violation at commit rolls the whole import back and is
  reported as `email_taken` for the row that collided.
- **Why:** a check-then-insert alone races with a concurrent import or a single-user create (the spec requires one
  to win and the other to create nothing). A lock held by one process does not protect against another writer.
- **Assumption:** the store supports unique constraints and transactions. Unverified until discovery names the store.

### AD-4: Parsing is server-side only, with bounded memory

- **Serves:** R-2, R-3, R-11.
- **Decision:** the server is the only parser; the client never parses or validates cell contents. The file is read into
  memory only up to the R-3 byte limit (stop reading at limit + 1 byte), parsed, and discarded when the request ends.
- **Why:** one authority for validation; a client check cannot be trusted and a duplicated one drifts.

### AD-5: Audit records go to the product's existing audit mechanism

- **Serves:** R-10.
- **Decision:** reuse the product's audit/security-event mechanism if discovery finds one; otherwise an append-only
  `user_import_audit` table in the same datastore. The audit write for a `created` import is in the same transaction
  as the user inserts; for every other outcome it is written after the outcome is decided.
- **Assumption:** the existing mechanism, if any, is unknown (OG-5).

### AD-6: The import page uses native controls

- **Serves:** R-12, NFR-1.
- **Decision:** a native `<input type="file">` is the control; drag-and-drop is an enhancement over it, never the only
  path. Result state is held in component memory only. The stack, component library and design tokens are the
  product's own, found at discovery; absent any, the NFR-1 starting appearance applies.
