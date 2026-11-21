# User Administration — Architecture

Structure and technology decisions for `spec.md`. No repository was available when these were written, so every decision is **proposed** against unobserved code; each names what to confirm. Product behaviour stays in `spec.md` and uses no `AD-` prefix.

## Decisions

### AD-1 Interface: one upload request, one result response (serves R-1..R-6, R-9, R-10)

- **Status:** proposed; route names and framework follow the existing admin API conventions once observed.
- **Decision:** the import is a single authenticated request carrying one file in a field named `file`, returning the common response contract in `spec.md`. A second admin-only request returns the template (R-10). The screen reads the configured `IMPORT_MAX_ROWS` and `IMPORT_MAX_BYTES` from the server (R-9 shows them), so the displayed limits cannot differ from the enforced ones.
- **Alternatives rejected:** a two-step "validate, then confirm" flow (needs the upload held between requests: new state, new expiry, new access rules, for no gain over all-or-nothing); a JSON body of rows (moves CSV parsing and its limits into every client).
- **Confirm / revalidate:** the existing route, auth middleware and error format; if the product's API style differs, change the transport here, not the behaviour in `spec.md`.

### AD-2 Reuse the existing stack, user-creation code and a maintained CSV parser (R-2, R-3, R-4, R-7)

- **Status:** proposed.
- **Decision:** the importer lives in the product's existing server codebase and language, calls the same user-creation rules and validators as single-create (so there is one place for them), and parses CSV with the platform's maintained parser in strict mode rather than hand-written splitting. The parser is wrapped so the R-3 behaviours (BOM, CRLF, blank-line skipping, `row` vs `line`, malformed-quote line) are the product's contract and not the library's defaults.
- **Alternatives rejected:** a separate import service or job runner (no boundary is demanded, A-7); copying the validators (they would drift).
- **Confirm:** the parser's handling of the FX-6b multi-line record and FX-10 unterminated quote against its primary documentation or a probe before relying on its line numbers. Unverified claim, not a fact.

### AD-3 Atomic commit with a storage-level uniqueness guarantee (R-2, R-5, R-8)

- **Status:** proposed; depends on G-3 and G-7.
- **Decision:** all inserts and the success audit record happen in one transaction on the user store. Uniqueness is enforced by a unique index over the lower-cased email, not only by the pre-check, so the pre-check gives good messages and the index gives correctness (409 `conflict` on violation, rolled back). Outgoing effects are issued after the commit, never inside it (R-7).
- **Alternatives rejected:** per-row inserts with compensation (partial states, contradicts A-4); a lock around imports (does not stop single-create from racing, and is not a guarantee).
- **Confirm:** that the store supports multi-row transactions and what isolation it gives; whether a unique index on normalised email exists, and whether existing data already violates it (then a cleanup decision is needed first). If the audit sink is a different store, the same-step rule becomes "write the audit record first as pending in the user store", to be redesigned then (revalidation trigger).

### AD-4 Visual direction for the import screen (serves NFR-6)

- **Status:** to be completed by the plan; this entry fixes only the premises.
- **Decision:** inherit the admin area's identity and tokens if one exists (G-6). Otherwise use the light expressive starting point: light canvas with a dark option following the system setting, the Gemini-style light look with Material 3 Expressive principles, native controls (file input, button, table) before custom ones, an icon set shared with the admin area. The plan records the concrete tokens (type scale, spacing scale, the two palettes, shape hierarchy), the focal point (the drop target and the result), and the single visual signature here as follow-up lines.
- **Revalidate:** on first sight of the real admin UI.

### AD-5 Synchronous processing (serves A-7, NFR-1)

- **Status:** proposed.
- **Decision:** process in the request. The limits (G-5) keep the work small enough for one request.
- **Revisit trigger:** if the NFR-1 probe shows a file at the chosen limit does not finish inside the platform request ceiling, move to an asynchronous design; that changes R-9's Working state and adds an operation record, a worker, and an owner for abandoned work (see `GUIDES/service-discovery.md` Asynchronous cooperation), and is a product decision because it changes what the admin sees.

## Platform claims awaiting proof

| Claim a decision depends on | Source or probe needed | Used by |
| --- | --- | --- |
| The platform can enforce a request-body size limit and refuse before reading the whole body | the web framework's primary documentation, then a probe with FX-1q | AD-1, AC-3.4 |
| The user store gives multi-row transactions and unique-index violation errors that identify the clashing row | store documentation, then AC-5.3's storage probe | AD-3 |
| The CSV parser reports record start lines for multi-line quoted records | parser documentation, then FX-6b and FX-10 | AD-2 |
| Uploads spooled to a temporary file are deleted when the request ends or the client disconnects | framework documentation, then the AC-8.2 temp-directory listing | R-8 |

None of these is relied on as fact in `spec.md`; each is checked by the case named.
