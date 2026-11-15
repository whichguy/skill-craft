1. **Goal**

Preserve previously declared pending outcomes across legitimate revisions without confusing host declarations with verified observations.

2. **Material issues**

- **Qualify terminal false closure, not merely accepted deletion.** `check_restated` excludes `product-acceptance`; `check_submitted` accepts `[]`; `primary.check_unverified` returns immediately for an empty list. This establishes an admission gap, but not an executed terminal reproduction. Follow the new action after `add-work` through actual `check`/`complete` callbacks and handoff, inspecting persisted state and report. A run ending with explicitly retained open items is not itself false closure. See [shiploop_unverified.py — admission rules:122](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_unverified.py:122) and [shiploop_primary.py — listed-row validation:216](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_primary.py:216).

- **The provisional repair needs a legitimate removal rule.** Simply admitting revisited `product-acceptance` into `check_restated` would prohibit removing every prior row: none can be due at product acceptance. That prevents silent disappearance, but also rejects a genuinely observed outcome or authorized scope withdrawal at that revisit. Specify these exits before coding. The unmarked list has no equivalent of delivery-contract correction machinery; a new keyword or nonempty reference would not solve that semantic problem.

- **Use the latest restatement, and expose it to the submitter.** `current_list` already reads accepted history across revisions. Preserve that behavior: restarting from the original acceptance list could resurrect settled outcomes; filtering to only current-cycle actions could lose pending ones. If enforcement changes, also update the revisited acceptance template and packet, which currently provide a placeholder rather than the retained list. See [shiploop_unverified.py — current_list:76](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_unverified.py:76) and [shiploop_navigator.py — template selection:5535](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:5535).

- **Keep declaration-only behavior outside the claimed fix.** Due-stage deletion deliberately represents settlement without checking summary truth. Marked contracts separately retain required obligations and reject missing/nonpassed observations, but their evidence and correction references also remain host claims. Tightening those semantics is unnecessary for a narrow replay repair. See [shiploop_consumer_delivery.py — project:483](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_consumer_delivery.py:483).

3. **Minor nits**

- Say “revisited acceptance after `add-work`,” distinguishing it from idempotent replay of an already accepted action.
- “Copy unchanged” overstates `check_restated`: preservation checks normalized `(requirement, outcome)` identity, not equality of every field.
- The three specified commit messages support this scope: retain recorded-drop semantics, preserve step-relative testing, and leave the dropped intent-aggregation candidate retired.

4. **Open unknowns**

- Whether either unmarked scenario reaches persisted terminal completion through all real callbacks.
- Which existing mechanism can represent an authorized correction to an unmarked pending row without treating prose as machine-verified authority.
- Whether revision changes the declared candidate: marked observations are invalidated by declared contract changes, not automatically by every `add-work`.

I inspected code and full commit messages; I ran no tests, changed no files, and delegated nothing. Concurrently authored tests are not execution evidence.

5. **If I were implementing tomorrow**

1. Complete the two unmarked CLI qualifications and the marked two-outcome control; record exact source identity and terminal artifacts.
2. Include negative controls for omission, partial/declined replies, lower-layer-only evidence, and scope removal without correction. Verify refusal leaves acceptance unchanged.
3. Include positive controls for fresh observation, retained unanswered rows, authorized correction, latest-list settlement, absent legacy lists, and unchanged first-time `unverified: []`.
4. Only if reproduced, extend existing admission and packet/template handling narrowly. Preserve due-stage settlement and explicitly resolve early-observation/correction behavior.
5. Update R07 with bounded findings: what continuity is enforced, what remains declaration-based, and what remains unqualified.