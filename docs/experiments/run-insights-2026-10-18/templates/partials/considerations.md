<!-- partial: considerations. The eight domain-neutral considerations, word for word from the implement-step fix plan's
references/implement-guidance.md (branch shiploop/implement-prompt-2d6ecc, 45894aff; ported by A0), with N5's send-back in place of revise. File only: the implement
packet prints considerations-titles in its head and this text in its appendix, as decision 18 does for Code craft. -->
=== Considerations (full text) ===
Answer each in `considerations`: the concrete handling and its anchor, or why the step does not touch it. "Handled",
"reviewed" and a bare "N/A" are not answers.
1. Whole step [criteria · ## Structure]: everything the assigned criteria need at the step's boundary: the change and
   its connections (entry points, registration, wiring, configuration, permissions, content, documentation a criterion
   requires), placed per ## Structure. Note changed usage or operations for the document stage.
2. Interactions [criteria · ## Interfaces and boundaries · interaction AD-n] that the step affects or its criteria need.
   People: what they see and do; waiting, error and empty states; accessible use. Systems: contracts, untrusted input
   and its validation, who may do what, sensitive output, slow, failed or repeated messages, compatibility with
   existing consumers. Work outside the step: send back (N5).
3. Building [## Stack · ## Commands]: a valid artifact, built or validated the project's way; no tool or dependency
   without a present need, and record any added.
4. Deploying [## Targets and runtimes · ## Access and accounts · ## Platform facts · ## Real-boundary checks]: target,
   order, per-environment settings, staged or reversible activation where the risk warrants, the check after, the
   undo. Only effects the run's recorded authority covers; preparing or recording a release action does not authorize running
   it.
5. State [## Structure · storage AD-n · ## Non-functional requirements]: what the step reads, creates or changes, with
   owner and shape before and after; compatibility with stored state; ordering, atomicity, concurrent updates. Any
   transition it needs is prepared, applied only where authorized, safe to rerun, recoverable from a partial failure. Invent no
   storage.
6. Operating [## Non-functional requirements · ## Conventions · ## Platform facts]: what an operator can see and
   diagnose; cost, limits, capacity; independent work in parallel where the platform allows it and it pays; secrets and permissions
   over time; retention, cleanup, owner.
7. What exists [## Structure · ## Conventions · ## Skills · ## Platform facts]: reuse unchanged, combine or extend
   before creating, in the repository and in the environment's services (identity, storage, queues, scheduling, caching,
   logging, search, notification); duplicate none; keep current behaviour working; follow the example.
8. Proof [## Commands · ## Harnesses and suites]: what demonstrates each assigned criterion now.
