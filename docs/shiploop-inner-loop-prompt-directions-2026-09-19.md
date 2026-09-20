# ShipLoop inner-loop prompt directions

## Decision and plan

Adopt a small clarification in the existing documentation contract and v3
activity prompts. Keep script-owned navigation, stage identities, reference
selection, callbacks and result schemas unchanged. This is a prompt change,
not a new validator, review loop, dependency or policy file for workers to load.

The Backchain/Plan Dispatcher audit demonstrated missing-input failures,
successful processes returning error envelopes, stale positive evidence, and a
diagnostic score overriding the intended acceptance decision. ShipLoop already
requires boundary checking, independent expectations, fresh evidence and concise
documentation. The incremental gaps are explicit file/class/function scope,
selective tombstone comments, response-contract checking, and a direct reminder
to keep diagnostics separate from acceptance.

1. Extend the existing Documentation section with responsibility-level contracts
   and selective tombstones. Keep useful warnings at surviving decision points;
   revalidate them and avoid dead code or boilerplate for every deletion/helper.
   Following the user's clarification, precision and necessary contracts, errors
   and caveats take priority over advisory word, character or token limits.
2. Clarify existing boundary and verification rules using the audit failures.
   Required evidence remains required; an unavailable optional diagnostic does
   not invalidate an otherwise supported result. Reuse existing evidence records.
3. Put compact reminders in the v3 implementation constitution and verify duty
   that the script already returns. Keep detailed guidance in the existing
   reference; do not copy whole reference bodies into every packet.
4. Check current prompt/reference routing, recovery, packet size and documentation;
   obtain independent review, regenerate only the ShipLoop plugin view, then run
   the repository's hermetic inventory using its existing core and three CI shards.

## Evidence and tradeoffs

- Local source: Backchain's [post-publication findings](https://github.com/whichguy/plan-orchestrator/blob/c6f03a97ea2bf78cb8ce12e6561238fc2736a6f3/docs/script-audit-2026-09-19.md#post-publication-improve-review)
  and [navigation contract](https://github.com/whichguy/plan-orchestrator/blob/c6f03a97ea2bf78cb8ce12e6561238fc2736a6f3/docs/script-map.md#script-ownership-and-function-flow).
- [Google's review guidance](https://google.github.io/eng-practices/review/reviewer/looking-for.html)
  distinguishes comments explaining decisions from module/class/function usage
  documentation and warns against overengineering and unnecessary tests.
- [PEP 257](https://peps.python.org/pep-0257/) provides a Python-specific example
  of documenting relevant arguments, results, errors and side effects. Its syntax
  is not imposed on other languages.
- [YAGNI](https://martinfowler.com/bliki/Yagni.html) targets speculative capabilities;
  maintaining understandable, changeable code remains worthwhile.

These sources support the direction, not a measured coding-agent quality gain.
Reject a separate tombstone registry, universal docstring checklist, new evidence
schema, new scoring rule, or another graph owner. A relevant regression/decision
link is useful when it prevents a known mistake; mandatory metadata is not.

## Scope and starting evidence

Development began in the source checkout on `main` at `09b0796d858e259afa9a031ba495480a41a6ade6`
with substantial pre-existing changes. Before copies preserved the two
edited source files so this task's delta can be distinguished from those changes.
The sources are `skills/shiploop/references/testing-and-documentation.md` and
`skills/shiploop/scripts/shiploop_navigator_v3_prompts.py`. The generated ShipLoop
plugin view is refreshed by the existing leaf-only generator.

Before edits, the v3 guidance (13), navigator v3 (22), and Backchain guidance (4)
checks passed: 39 tests. The generated ShipLoop view also matched its source.

## Initial implementation validation

For the initial development tree, all 115 hermetic suite entries passed (27 core and 88
ShipLoop across the three existing disjoint CI shards, with no omissions or
duplicates). The final action-walk passed all 13 cases. Local deterministic
checks establish routing and runtime contracts, not live model compliance or a
demonstrated quality/token improvement. No new test framework or wording-only
regression suite is added. Installation, publication and live product execution
are separate boundaries.

The five focused suites passed after the final wording changes: v3 guidance
(13), navigator v3 (22), Backchain guidance (4), packet bounds (7), and iteration
documentation (7), for 53 checks. This task's isolated before/after comparison
confirms all 34 stage identities, reference routes and Improve handoff prompt
strings are unchanged. The shared implementation prompt grows by 536 characters across its 13 existing
stages; verification adds another 242. These are character counts, not token or
end-to-end cost measurements. Reference bodies are still loaded by locator.

Independent review found no correctness or ownership defect. Its proposed
phrase-presence test was not added: routing is unchanged and the current suites
already exercise cold producer/child references and relocation; another literal
assertion would not establish model interpretation. A separate qualitative
reading of four scenarios produced these decisions without a wording defect:

| Scenario | Expected interpretation |
| --- | --- |
| Exit 0, documented response says failed | Diagnose the operation failure; transport status alone is insufficient. |
| Changed artifact, saved positive check, better health but failed requirement | Evidence is stale and the required outcome still fails. |
| Obvious helper, state-owning class, entrypoint module | No helper boilerplate; document class invariants/lifetime and module responsibility/entry points as needed. |
| Remove an invalid alternate-runtime fallback | Warn at the surviving selection point with rationale and replacement/check reference; ordinary deletions need no tombstone. |

This is one independent interpretation check, not a paired model experiment.

During the broad run, another change added Git-history guide locators to `plan`
and `step-plan` in the same source file. Those edits are preserved and excluded
from this task's scoped patch. The final five focused suites passed on the
combined current content after the user's precision clarification. The broad
inventory began before those final edits, so its evidence is supplemented by
that focused rerun; it is not claimed as an immutable-snapshot run.

At initial completion, source hashes matched the focused-rerun candidate. Both generated
counterparts matched their source byte-for-byte; the leaf package check and scoped
whitespace check passed. Broad checks emitted non-failing packet-size advisories;
they remain diagnostics and were not used to trim necessary guidance.

The initial before copies, scoped patch, raw logs and source/log hashes were
retained outside Git. Those observations describe the development tree above;
they do not replace validation of the delivery candidate below.

## Delivery validation

The user subsequently authorized commit, merge and push. The shared checkout's
local `main` had diverged and retained unrelated edits. Delivery therefore uses
an isolated branch from remote `main` at
`c62ff979ab32ea29d0cc99aae0ca83b20abc9c3f`, applying only this task's two-file
patch and report, then regenerating the two affected ShipLoop plugin files.
The shared checkout and its unrelated commits and edits are preserved.

Before applying the patch, the delivery base passed v3 guidance (21), navigator
v3 (22), and ShipLoop package parity. The patch applied without conflicts.
Delivery candidate checks passed:

- `bash test/run-all.sh --group smoke`: 24 core and 6 ShipLoop suite entries.
- `python3 -B test/shiploop-v3-guidance.test.py`: 21 tests.
- `python3 -B test/shiploop-navigator-v3.test.py`: 22 tests.
- `python3 -B test/shiploop-backchain-guidance.test.py`: 4 tests.
- `python3 -B test/shiploop-packet-bounds.test.py`: 7 tests.
- `python3 -B test/shiploop-iteration-docs.test.py`: 7 tests.
- ShipLoop leaf package parity, scoped whitespace checks, and independent review.

The 61 focused checks supplement the current smoke gate. AST comparison against
the delivery base confirms that only the existing implementation constitution
and stage duty strings changed; module functions and navigation catalogs are
identical. A fresh full runtime qualification was not repeated for this prompt
and reference change; the earlier full-run evidence remains separately labeled.
Git publication is verified separately after committing and merging this
candidate. Installed skill checkouts are outside this Git publication.
