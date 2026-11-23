You are an independent design reviewer. Work read-only in this folder: an export of the ShipLoop source
(`skills/shiploop/`, ShipLoop 2.7.1), the tests that pin the rules concerned (`test/`), the stage replay suite
(`test/shiploop_e2e/stage_suite/`), the study journal (`docs/shiploop-end-of-inner-loop-journal.md`), a map of how the spec and
the plan can change (`docs/design/spec-to-plan-map.md`) and the design under review
(`docs/design/step-plan-rewrite-design.md`). Cite a file and symbol for every factual claim and mark anything you did not
verify.

The owner has decided the direction, and it is not under review: when a step finds that a requirement must change and no
owner note covers it, the item goes back to step-plan, and step-plan rewrites the requirement and re-plans. Review whether
this design does that correctly, completely and with the smallest change.

The owner's standing rules: prefer the plain rule when a guard has no right catch on record; scripts own navigation and the
model does one step; a packet must stand alone, because context may be cleared between stages; no iteration caps; the
drivers are Sol 6.2 at medium and Sonnet 5.5 at medium; every test must be able to change a decision.

Questions:

1. Trace the whole route in the code, from the stage that finds it to the accepted amended plan and the commits after it.
   Does each stage from test-spec to document actually get to send back with this reason, and does the redone step-plan
   packet hold what it needs on both drivers, with the context cleared? Where can it still dead-end or lose the change
   (the send-back summary's bound, the Improve review of step-plan and its import, fix forward with done steps, the
   step-plan knowledge commit, the next step's gate baseline, test-spec)?
2. The proposed duty 10 text: is it right, complete and free of contradiction with the released owner-note clause and the
   other duties, word for word? Give exact text if it should differ.
3. Items 2, 3 and 4 (the sender's wording, later items, the references): needed, sufficient, or noise? What else states a
   different rule for the same finding?
4. Item 5 (the requester sees every rewording): is the comparison right (baseline commit, step-marked lines, reconcile,
   retired entries, cosmetic edits, no checkout)? Is it worth its code, or is there a smaller way for the requester to be
   told reliably, given that a Sol session's last message does not repeat the done packet and the report is made by script?
5. Item 6: is leaving `STAGE_FILES` alone and adding no gate right? What is the strongest case for a gate here, and its
   false refusals?
6. The deciding check: can it fail for the right reasons and pass for the wrong ones? Is the scenario valid (does it hold a
   real spec, a done step, a plausible reason)? What would you change, at the same size?
7. What did the design miss?

Answer in short sections, one per question, most important first inside each.
