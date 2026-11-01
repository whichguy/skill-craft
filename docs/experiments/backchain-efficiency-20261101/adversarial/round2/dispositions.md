# Dispositions of the round-2 adversarial review (codex:gpt-6.1-sol@medium, 2026-11-01)

Reviewed change: skill-craft 26d4785541fedbfba91bb32e61d525ed8f4a19f2 against
090e37f5b222486c258e39c88a2d8e7557b939ef, the fixes of round 1's F1-F5 and F8. The reviewer had the change packet
`change.md` (49,791 bytes, SHA-256 `e2d910cd7309452ac4371715c2273ce47bea22b93bbdce9c52f8057ad4d14e80`: a header
quoting round 1's claims, then `git diff` of `skills/` and `changes/` between those commits; tests, journal and evidence
left out) and the brief `evidence.md` (SHA-256 `0c52054097e1df4ba2e522726312a4f7ade2548d56c78ba48c03cb773f2d0c53`).
It returned five findings (`findings.json`, SHA-256
`cffa4be4960da4906a18da8fff533971d78aa33b324f09609cb2e07b83f104aa`; `findings.md`). Originals are under
`/Users/dadleet/src/backchain/results/backchain-efficiency-20261101/adversarial/round2/`.

Each finding became a test in skill-craft `test/backchain-toolkit.test.py` before its fix. The final test file run
against 26d47855 fails 8 times in 5 tests, each in the finding it targets; after the fixes all 34 tests pass.
Details and the fixing commit are in `docs/backchain-efficiency-journal-2026-11.md`, Round 5.

| ID | Severity | Disposition | Test | Where |
|----|----------|-------------|------|-------|
| R2-F1 | high | Fixed. `finish --review` refuses (could not run, nothing written) a review that does not assess the final candidate: `candidate.output_sha256` must be the final candidate's sha256, which the last `record` printed, `findings` a list, and `coverage.source_review_status` `complete` or `incomplete`. An identity-only shell, the inherited candidate's assessment after a revision, and a review with no source status were each accepted on 26d47855. | `test_finish_refuses_a_final_review_that_is_not_of_the_final_candidate` (3 fail-first) | `command_finish` |
| R2-F2 | high | Fixed, by replacing the count. `record` now runs inside a callback: it reads the loop's packet from the receipt (refusing when the loop is not started or has ended), stamps the cycle with that callback's number, and refuses when the previous callback submitted anything but the last report `record` wrote in it. `finish` requires a recorded cycle for every callback the terminal packet counts. A hand-written callback is found by the next `record`, or by `finish` when it is the last; an extra record cannot pad it. | `test_a_callback_submitted_without_record_is_found` (fail-first: `record` after a hand-written callback 1 succeeded) | `command_record`, `packet_problems`, `receipt_problems` |
| R2-F3 | high | Partly fixed. `checks` must hold non-blank strings (a list of nulls or blanks passed on 26d47855). Whether the strings describe real lens, source, bounds and chunk inspection is not mechanically checkable without a structured checks format, which would be an unmeasured prompt-format change; it stays the reviewer's claim, and the cohort's blind grading of the plans measures what the reviews achieved. Decided by judgement, recorded here and in `references/convergence.md`. | `test_record_binds_the_assessment_to_the_candidate_it_reviewed` (2 fail-first subtests) | `review_problems` |
| R2-F4 | medium | Fixed. Rewording or dropping an input of a provisional edge still changes that edge, but an edge that ends with more inputs than it had needs `allow_new_edges`. | `test_a_provisional_edge_gains_inputs_only_with_allow_new_edges` (1 fail-first) | `bound_errors` |
| R2-F5 | medium | Fixed in the text, measured live in the cohort. With caller bounds the contract's work text says a review may remove an inherited edge or step only where the bounds make it provisional, instead of "never an inherited one"; the card and the convergence reference say the same. The reviewer's live experiment, a source-aware callback whose only necessary repair removes an inherited provisional edge, is the cohort's bounded source-edge repair case, in both arms. | `test_the_contract_lets_a_review_remove_what_the_bounds_make_provisional` (1 fail-first) | `contract_for` |
