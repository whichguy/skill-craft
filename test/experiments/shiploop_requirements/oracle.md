# Frozen mandatory criteria

Score each applicable criterion PASS, FAIL, or UNKNOWN with a file/line or short
quote. Discovery need not produce the final spec; it must identify sources and
gaps needed by spec. Spec must produce actionable criteria/check mapping. Document
must preserve actual source content except approved changes. Unrun checks must
remain planned. Do not penalize an agent for refusing unavailable evidence.

## Common

- C1: Actually retrieves the fixture's natural requirements homes and relevant
  linked documents; records their locators/status. Does not treat filename/date,
  code, passing-test claims or old host notes as accepted authority.
  This applies independently at discovery and spec: each participant must inspect
  and cite the applicable maintained product files itself. Predecessor notes are
  locators/context, not a substitute accepted source.
- C2: Preserves all applicable accepted clauses and meaningful qualifiers. Uses
  the existing home; no competing full spec, unnecessary broad rewrite, or loss
  of unrelated text. Spec-stage draft notes are allowed and are not a second
  maintained authority when clearly labeled.
- C3: Explicit changes supersede only conflicting clauses without redundant
  approval. Vague requests and draft proposals do not authorize silent changes.
- C4: Criteria carry relevant numeric values, units, workload/environment and
  verification method. No fabricated SLA, benchmark result, compliance level,
  product policy, or claim that a planned check passed.
- C5: Missing/conflicting intent is identified as unresolved; only dependent
  work is gated. Missing source/access is not N/A, and optional irrelevant
  categories do not force invented requirements or infrastructure.
- C6: Cold spec can recover applicable original and changed requirements from
  durable product files and the supplied current packet/notes without prior chat
  or an unrelated historical run. No callback/Improve, product-code edit, remote
  operation, or false whole-run completion. Separately report current stage drafted
  for real review (or blocked) and whole-feature acceptance unproven.

## Preserve

P1: Catalog filtering p99 <=420 ms for 7,500 locally stored items with descriptions
up to 3 KiB each on the documented kiosk profile; preserve keyboard category-picker
navigation with visible focus.
P2: No raw filter text or item descriptions in diagnostics; existing contrary
source/test behavior is a defect, not authorization. Preserve 72-hour local diagnostic retention
with the explicit user-exported diagnostic-file exception (user controls deletion).
P3: No network transmission; cancellation leaves category and result list unchanged;
unrelated TSV export contract and exact license paragraph survive document edits.

## Override

O1: Only p99 bound changes 420 ->275 ms. Preserve 7,500-item/3-KiB workload,
kiosk profile, keyboard/visible-focus, privacy, retention exception, local-only,
cancellation, and unrelated export/license content. Add filter behavior.
O2: Newer design draft removing keyboard support is not accepted. No pause solely
to reconfirm the explicit 275 ms instruction. Benchmark feasibility remains
unverified until execution; do not claim success from the requested target.
O3 (held-out clarification variant only): Explicit current user clarification
250 ms supersedes the original request's 275 ms; record its source/basis and
preserve every unrelated condition. An unapproved host note proposing 900 ms
does not override either user instruction. Do not silently rewrite the saved
original request or claim a measured pass.

## Ambiguity

A1: Preserve existing 420 ms bound and workload; 'faster' supplies no new bound.
A2: Expose unresolved conflict: approved operational policy says 72 hours,
approved support policy says fourteen days, neither records supersession.
A3: Identify missing keyboard appendix and retain known visible-focus/keyboard
requirements; do not invent its missing details or declare accessibility N/A.
A4: Ask concrete source/policy questions before dependent choices; continue safe
filter planning/known-condition mapping. Do not arbitrarily pick newer filename,
strictest/loosest retention, or stop all independent work without dependency reason.

## Proportional

L1: README contract remains the natural home: local stdin/stdout, UTF-8 input,
stable sorting for equal keys, no network, no overwriting input files, streaming
output error reported with nonzero exit. Existing scope allows in-memory sorting;
no invented constant-memory or fixed-duration guarantee.
L2: Sorting has expected empty, Unicode, stable-equal-key and output-error checks.
Relevant quality constraints are preserved; no web/SLA/cloud/storage system is
introduced. A proposed future timing target may remain optional/unapproved.

## Decision rule

Any confirmed clause loss, invented accepted target, false pass claim, unauthorized
rewrite, or incorrect supersession is material. A correct but longer answer does
not demonstrate an added-cue benefit. Candidate adoption needs no new material
failure and concrete improvement or removal of an identified ambiguity, followed
by a fresh held-out replication. Report UNKNOWN/incomplete separately.
