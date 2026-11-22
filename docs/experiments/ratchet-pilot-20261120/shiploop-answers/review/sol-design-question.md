You are reviewing a design before any code is written. The design is DESIGN.md in this folder. It proposes a small change to ShipLoop, a script-driven software delivery skill: a requester can answer one of the "defaults" a specification recorded, and if the answer arrives before the plan is accepted, the stage then current must rewrite that requirement and prove it to the script.

What is in this folder, all of it read-only for you:
- DESIGN.md: the design under review.
- route-map.md: a map of the existing mechanisms, written from the code by another reader. Treat it as claims to check, not as truth.
- engine/: the engine modules the design touches (shiploop_navigator.py is large; search it by symbol name).
- references/: the engine's reference text, its glossary, and the E2E specification whose clause S-14 is the unattended rule.
- earlier/: the design and your own earlier review of the released list of defaults that this builds on, the owner-notes design, and the two test files that pin the list and the notes.

Rules the owner has set and the design must keep: ShipLoop runs unattended (it records a default and continues; it asks only when nothing can proceed; nothing waits on a person; no stage pauses); no loop gets a limit; one supported version (no shims, no migrations: a saved run must still load); a new gate records its known ways round; keep it simple, and prefer a plain rule to a guard no run has shown to be needed.

Please be adversarial and concrete. Check claims against the code in engine/ and name the symbols you read. I want:

1. A verdict in one line: build as designed, change first, or do not build.
2. Faults in the mechanism, most serious first. For each: what breaks, where in the code (symbol names), and the smallest change that fixes it. Look especially at: the three call sites of the defaults gate and whether an answers gate fits each (the gates of complete and check in _evaluate, the reuse of a matching earlier yes in dispatch, the import of a review's result); the hold of a callback for a note that arrives after its packet printed (NotesHeld, to_hold, mark_held) and how it meets a gate that also refuses; _validate_current_state and _canonical_result for a new done-only result key allowed at two stages; the owner-note record gaining a field (who reads the record, who validates it); how "the stage current at the next accepting callback" behaves when a review child is active (active_improve), when the run is blocked or paused, and when a planning reconcile reruns the spec and changes the list a note is bound to; packet head budgets for a new required block.
3. Faults in the behaviour a user would meet. Is the window (test-strategy and plan) right? What does a user experience when the answer is late by one stage? Is telling a late stage to leave the requirement alone sound when nothing enforces it? Does anything here ask, wait or pause, against the unattended rule?
4. Your answers to the five open questions in section 5 of DESIGN.md.
5. The test plan in section 4: is reading R2 (at least five of six deliveries pass the eight held-out checks, where 11 of 20 pass without answers) a fair first rung? What would you register instead?
6. What you could not verify from the files here.

Write plainly. Number every finding. Do not rewrite the design document; say what to change.
