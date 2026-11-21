# Admin User Management: Architecture

How the product is built. What it must do lives in `KNOWLEDGE/spec.md` and is not restated here. Decisions are
`AD-<n>`. No repository was available to this run, so every decision below is **proposed**, made without
observing the existing stack, and must be reconciled with the real system by planning before it is relied on.

## Decisions

### AD-1 Synchronous request and response; no background job

- **Serves:** R-6, R-7, R-8 (the response is the result, PD-6).
- **Decision:** the import runs inside one HTTP request. The response is returned only after the outcome is durable. No queue, worker, job record or status endpoint.
- **Basis:** the limits (524,288 bytes, 1,000 rows) keep the work small; acceptance meaning is simplest when response equals completion (guide: add no queue where request/response meets the requirement).
- **Alternative not chosen:** an asynchronous job with a status endpoint (needed only for larger files).
- **Revalidate when:** F-1000 does not finish within the runtime's request time limit (R-14), or the row limit is raised.

### AD-2 All-or-nothing write through the store's own atomicity and uniqueness

- **Serves:** R-5, R-6, R-8, R-15.
- **Decision:** creation of all rows is one atomic change in the user store, and uniqueness of the normalized email is enforced by the store itself (not only by a read-then-write check), so concurrent imports cannot both create an address; a collision at commit maps to 409 `concurrent_conflict`.
- **Basis:** an application-level check alone cannot close the race that AC-5.4 describes.
- **Unverified (must be checked before R-6 is ready):** that the actual store offers a multi-row atomic write and a uniqueness guarantee on the normalized email, and how it reports a collision. No primary documentation or probe has been consulted; no store was identified.
- **Alternative not chosen:** per-row writes with compensating deletes (leaves a window where partial state is visible).

### AD-3 Bounded in-memory handling of the upload

- **Serves:** R-3, R-10, R-13.
- **Decision:** enforce the 524,288-byte limit while reading the file part, hold the content only in memory for the request, and parse it with a purpose-written or vetted CSV reader that implements the rules of R-2 (quotes, BOM, LF/CRLF, malformed cases). If the framework spools uploads to disk, the spool file is deleted at request end on every path, including failure.
- **Basis:** the size bound makes memory use small and keeps R-10 simple.
- **Unverified:** how the chosen framework buffers and spools multipart uploads, and whether a library's CSV dialect matches R-2 exactly; the fixtures in `spec.md` decide, not the library's defaults.

### AD-4 The server is the only validator

- **Serves:** R-4, R-5, R-7, R-12.
- **Decision:** all file and row validation lives in one server-side component that takes bytes plus an email-existence lookup and returns the R-7 result. The page sends the file and renders the returned codes as text; it does not parse or validate CSV.
- **Basis:** one source of truth for the rules; the page cannot disagree with the API.
- **Alternative not chosen:** client-side preview and validation (a second copy of the rules to keep in step).

### AD-5 Import page visual direction

- **Serves:** R-12, R-16, R-17.
- **Decision (conditional):** if the product's admin area has an established identity or design tokens, the page reuses them. Otherwise it starts from the light expressive profile: a light canvas with a dark theme option, tonal rounded surfaces, a restrained saturated accent, a humanist or geometric sans-serif from local fonts with fallbacks, one icon set, short purposeful motion that respects reduced motion. The drop zone and then the result carry the strongest weight.
- **Source:** `GUIDES/platforms/ui.md#light-expressive-starting-point`.
- **Pending:** planning records the concrete tokens (palette values, type and spacing scales, shape hierarchy, icon set) here once the existing UI toolkit is inspected. A guide's adjectives are not the decision.
