# Final semantic review — ShipLoop plan on main 5d3628b

Read-only review of the updated plan against `main-5d3628b0/reference-code-map.json` and committed main source. No tests or experiment-overlay review were performed.

## Actionable corrections

1. **Disambiguate optional per-step paths from required item paths (R01/T5).** Current prose says “the schema still tolerates omitted paths,” which could be read as item-level `paths`; item-level paths are required on a done step plan. Say explicitly: “The prompt asks every step to declare its changed paths, but the step schema permits omitting per-step `paths`; item-level `paths` remains required. The 4-criteria/3-product-file limit is producer guidance, not a validator gate.” This is a real prompt/schema mismatch: `_normalise_steps` calls step paths optional and says inline route does not read them, while the prompt asks them. The 4/3 language is present in emitted producer text and its packet-content test only.
   - Exact anchors: `skills/shiploop/scripts/shiploop_navigator.py:2550-2558` (`_normalise_steps`); `:2636-2647` (required item-level paths); `:2730-2769` (`_check_step_sizing`, no cardinality check); `skills/shiploop/scripts/shiploop_prompts.py:1289-1294` (4/3 and per-step path instruction); `test/shiploop-packet-completeness.test.py:351-360` (asserts emitted wording).
   - Map IDs: `step-schema`, `step-plan`, `step-sizing-packet-test`.

2. **Narrow the “no caps” summary to its actual layers.** The table is directionally right but omits the host-specific Grok continuation cap, and “step Repeat's separate failure rule” can sound like a script-enforced attempt counter. State: “There is no default Until Loop iteration limit, no refused-run count that stops work, and no send-back-count cap. Grok's host continuation cap is 8. Inline implement still has a seven-genuine-attempt same-failure threshold expressed in the prompt; the script does not count those attempts. Test commands have a 600-second per-command timeout and no total run time budget.” Keep `state.md.revisions` described as a count, not a limiter.
   - Exact anchors: `skills/shiploop/scripts/shiploop_loops.py:60-61, 105-157, 560-565` (no iteration limit and repeat text); `skills/shiploop/scripts/shiploop_stage_spec.py:68-76, 89-92` (no send-back cap; seven attempts is model-applied, not counted by script); `skills/shiploop/scripts/shiploop_test_loop.py:24-29, 80-85, 1194-1195` (refused-run tally, 600-second timeout, no total budget); `skills/shiploop/scripts/shiploop_keepalive.py:415-421` (Grok cap 8). The current plan's map has `sendback-policy` and `loop-repeat`; the `CONTINUATION_CAPS` anchor is not currently among its 111 excerpts, so add an excerpt/map row if citing this qualification in the map.

3. **Limit revised-bound closure to the specific producer fields.** The current table is correct; avoid wording elsewhere that implies a universal result-size bound. `_check_producer_bounds` bounds work-item context, open assumptions per item, and step task/proof/named criteria. Improve import calls that same helper on revised results before subsequent gates; the focused test exercises an overlong revised task and an in-bound import.
   - Exact anchors: `skills/shiploop/scripts/shiploop_navigator.py:3130-3176` (`_check_producer_bounds`); `:8849-8858` (Improve revised result); `test/shiploop-actual-improve-cli.test.py:1550-1569` (focused regression).
   - Map IDs: `producer-bounds`, `improve-revised-bounds`, `revised-bounds-test`.

4. **Qualify T33 reuse as subject to R08's semantics-version risk.** “Unchanged receipt may be reused” is valid for the covered same-tree mechanism but sounds unconditional beside the reproduced pre-fix receipt defect. Suggested disposition: “Covered mechanism for an unchanged candidate; reuse across judge-semantic changes remains open under R08.” Do not change the intentionally pending tests field.
   - Exact anchors: `skills/shiploop/scripts/shiploop_test_loop.py:1131-1165` (`_reused`); `:1379-1450` (`_proof_records` and `step_proof`); `test/shiploop-test-loop.test.py:2239-2255` (candidate reuse) and `:2421-2458` (step-Proof reuse).
   - Map IDs: `candidate-reuse`, `step-proof`, `test-reuse`, `test-reproof`.

## Claims that read correctly as written

- R08 is partial, and the plan now separates the fixed failed-tally case from reproduced mixed-error and pre-fix-receipt cases. Preserve the helper-probe scope and the statement that callback fixtures remain pending.
- The table correctly says revised Improve results now run producer bounds.
- The Improve first-trivial policy and the separate verify gate are not conflated in the map; current dispositions do not need changing on this review.
