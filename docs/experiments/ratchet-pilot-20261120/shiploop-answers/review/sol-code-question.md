You are reviewing code before it is tried on real runs. It implements DESIGN.md in this folder (sections 2 and 3 are the design, section 4 lists what your own earlier design review changed; that review is your-earlier-design-review.md). The change lets a requester answer one of the "defaults" a ShipLoop specification recorded: a bound owner note (`note --default <row>@<8 hex>`); if it is there when the `test-strategy` producer submits its done result, that result must carry `answers` rows and the script checks them; a later answer is held for a new run.

What is here, read-only:
- changes-to-existing-files.diff: the diff of every existing file that changed.
- changed/: every changed or new file whole (the new module is changed/skills/shiploop/scripts/shiploop_answers.py; the new tests are changed/test/shiploop-answers.test.py), plus the unchanged engine modules they call.
- base/: the three largest changed engine files as they were before the change.

The owner's rules: ShipLoop runs unattended (nothing asks, waits or pauses; no loop gets a limit); one supported version (no shims; a run saved before the change, a run parked in a review, and a note file without the new field must load); keep it simple; a gate records its known ways round.

Be adversarial and concrete, and check against the code, naming the symbols you read. I want:

1. A verdict in one line: ready for real runs, fix first, or rework.
2. Defects, most serious first. For each: the input or state that triggers it, what goes wrong, where (file and symbol), and the smallest fix. Look especially at: `shiploop_answers.standing`, `waiting` and `owed` (in time, replaced, late, superseded; the parked review; a reconcile that keeps or replaces the spec); the one inbox read per admission in the navigator's `dispatch` and whether the hold, the gate and the delivery truly share it; the three gate calls (`_evaluate`, the reuse of a matching earlier yes, the review import) and whether any path accepts a done `test-strategy` result without proving an owed answer, or refuses a result that owes none; the owner-notes reader and writer with the new optional binding (a malformed binding, an old note file, the hold and delivery of bound against unbound notes); `_canonical_result` and loading of saved runs; the done packet and report marks; anything that could make an unattended run with no answers behave differently from before.
3. Places where the code does something the design does not say, or fails to do something the design says.
4. Tests that are missing or that assert less than their names claim (name the test).
5. What you could not verify from these files.

Write plainly. Number every finding. Do not rewrite files; say what to change.
