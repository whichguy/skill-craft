# Passes

Starting point: one sentence, "Let admins upload a CSV to bulk-create users." The working directory held no product
code, so existing behaviour could not be read; it is covered by parity clauses marked unconfirmed.

## Pass 1: the ground
Added U-1 to U-11: the ordinary import, the same at its edges (largest file, repeat, empty), the unhappy paths (bad
rows, unusable file, non-admin, interruption, concurrent imports), a script caller, the new user, the operator. Wrote
the clause each plainly needs (C-1 to C-8, C-27 to C-30, C-42 to C-44 in first form). Found nothing on: i18n of the
page, because the request gives no language.

## Pass 2: what each sentence takes for granted
"admins" took for granted a definition of admin, a way to establish it, and an answer for everyone else
(C-3, C-4, C-5, C-69). "upload a CSV" took for granted a format, encoding, header, delimiter, quoting, size, empty file,
and several-file cases (C-7 to C-26, C-70). "bulk-create users" took for granted which fields a user has, which are
required, how new users get access, what role they hold, what "already exists" means, and what the admin is told
(C-27 to C-47). Then put each new clause through the same question: row numbering (C-21), blank records (C-20),
the whitespace definition (C-28), how the duplicate rule treats case (C-68). Nothing found on: password handling beyond
C-47, because the request names no credential and the file is not to carry one.

## Pass 3: where the parts meet
Pairs walked: import and import; import and single-user creation; upload and revocation of admin rights; upload and
session expiry; creation and message sending; double submission; the same file twice; a dropped connection and a
commit; the report and the listing. Added C-5, C-48 to C-50, C-52 to C-57. Considered and left out: a per-admin lock
on running imports (C-55 and C-54 already keep data correct).

## Pass 4: the runtime's own rules
Runtime taken to be a web application behind a proxy, with a user store and mail. Added the size limit that the
front end must not undercut (C-23, C-26), the request time budget and the consequence that mail is sent after the
response (C-25, C-48), the anti-forgery rule (C-6), the transport of status codes for scripts (C-58), content type
labelling by browsers (C-70), and log hygiene (C-61, C-62). Figures that are our own or unconfirmed are marked in their
clauses (30 s, proxy limits, the status codes).

## Pass 5: what must not change, what must never happen
Added C-64 to C-67 (existing users untouched, single-user creation unchanged, rollback, pre-existing data), C-40 and C-41
(rules of normal creation and any account cap apply on this path too), C-46 (no privilege through a file), C-59
(file not kept), C-60 (echoed text is inert), C-63 (accessibility). Considered and left out as features the request does
not cover: an undo, an import history page, a downloadable template, an error-report download, per-import role
selection, updating existing users from the file, rate limiting.

## Pass 6: grind
Read the whole specification as the builder. Fixed: C-23's reasoning claimed a maximal row fits the size cap, which is
false for multi-byte names; C-21 and C-20 disagreed about a blank record before the header; C-39 pointed at "a header
problem" without a clause; C-47 was vague about what "same first-access" means; C-58 omitted the no-file case; C-38 had
a bound (100 characters) with no stated reason and no entry for rules from C-40; C-28 left "whitespace" undefined; C-9
bundled parsing details into one sentence. Removed a duplicate clause (the old C-70, repeating C-13, C-15 and C-46).

## Pass 7: grind
Looked for state with no end, silent decisions, and Observables that cannot be seen. Added the rule that rows with the
wrong field count take no part in duplicate detection (C-35) and the clause that the file is judged by content, not
name or type (C-70). Every decision the request leaves open is now in a clause with Source: choice. Checked numbering:
U-1 to U-11 and C-1 to C-70, no gaps.

## Pass 8: grind (the pass that added nothing)
Re-read every use case and clause against these questions: can the Observable be seen by someone outside the code; do
two readers read any word differently; does a bound lack its number; does a dimension (admin states, states of an
existing account, reasons for rejection, log fields, file-level problems, recognised columns, HTTP statuses) lack
its members; is any clause two behaviours; does any use case lack an unhappy path; does any decision hide outside a
choice clause. Nothing a builder would otherwise have got wrong turned up, and no edit was made. This is the stopping
pass.
