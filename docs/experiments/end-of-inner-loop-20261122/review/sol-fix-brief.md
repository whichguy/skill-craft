You are an independent design reviewer. Work read-only in this folder: an export of the ShipLoop source
(`skills/shiploop/`), the tests that pin these rules (`test/`), the study journal (`docs/shiploop-end-of-inner-loop-journal.md`),
the fix design (`docs/design/fix-design.md`), a map of how the spec and plan can change (`docs/design/spec-to-plan-map.md`)
and the owner-notes candidate's prompt changes (`docs/design/owner-notes-candidate.diff`, another session's work the
owner accepted today; it lands on main before this fix). Use maximum effort. Cite a file and symbol for every factual
claim and mark anything you did not verify.

## What is being decided

The owner read the journal and answered "Yes, fix them" to three defects. The fix design covers two of them:

1. carry-forward's duty writes spec.md against `STAGE_FILES`, with no step gate (defect 1);
2. `_settled` closes an open item by ordering alone (defect 3).

Defect 2, a requirement change found mid-step, is handed to the owner-notes candidate's session, and its no-note half is
put to the owner.

The owner's standing rules: change something only for a measured difference in outcome; prefer the plain rule when a
guard has no right catch on record, and offer the guard as an option; ShipLoop's loops have no iteration cap; scripts
own navigation, the model does one step; a packet must stand alone, because context may be cleared between stages; the
drivers to serve are Sol 6.2 at medium and Sonnet 5.5 at medium. Measured: a Sol session's model receives a refusal's
first line reliably, and less of the rest.

## Questions

**Part A. Defect 1 (the duty change).**
1. Is the proposed bullet right and complete? Is there any other text, gate or test that would still make carry-forward
   edit spec.md, or leave the stage inconsistent (packet text, references, the Improve review of carry-forward, the
   end-of-work review, the knowledge gate at carry-forward's accept)? Is "open item below, or corrective work in item 2"
   enough for a gap, given how those two already work?
2. Is the wording compatible with the candidate's duty-2 and loop-rule exception in the diff, word for word? Suggest
   exact text if not.
3. Does removing the spec write lose anything a later reader of spec.md needs, beyond what document already writes?
4. Is leaving out a script gate the right call, given that the candidate rewrites a requirement at carry-forward for a
   carried owner note? If there is a small check that refuses every other spec.md change without blocking that route,
   describe it and its false-refusal cases.

**Part B. Defect 3 (open items).**
5. From the code, what exactly does an open item mean between the stage that records it and the stage it is due at, and
   can a row be dropped today without anyone noticing? Find every reader of `open_items` and `_settled` and say what
   each would do if a due stage dropped a row.
6. A census is running to see whether real obligations are dropped (variant A, the guard; variant B, nothing). If
   variant A: design the minimal correct guard. In particular:
   - how a due stage says an owed item became queued work (no existing disposition fits);
   - which due stages can be checked (those with an `assumptions` field) and what to do for the others;
   - the exact first line of the refusal;
   - what breaks (existing tests, the review import, a send-back that resets a step's items, the candidate's notes
     ledger);
   - fail-first tests.
   If variant B: what would you record and why.

**Part C. Scope and material difference.**
7. Is handing defect 2 to the candidate's session, with the no-note half left to the owner, right? Should the no-note half
   stop and ask, or let step-plan rewrite the requirement and re-plan (the owner's rule "if we do update the spec, we
   would definitely need to incrementally update the plan" is in the journal's header)? Give your recommendation with the
   strongest case against it.
8. What would make any of these changes immaterial or harmful, and what is the cheapest live check that would show it?

Answer in short sections: Part A (1 to 4), Part B (5 to 6), Part C (7 to 8), then anything the design missed.
