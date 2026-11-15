1. **Goal**

Prevent previously recorded outcomes from disappearing without an explicit, attributable disposition while preserving legitimate observation, correction, and deferral routes.

2. **Material issues**

- **Verdict: A is a justified bounded repair; B is incomplete and unnecessarily restrictive.** The retained evidence supports three terminal reproductions, with no execution errors; the corrected positive controls also passed. A closes the *unattributed omission* mechanism in all three cases. It does **not** prevent a host from submitting a false `observed` declaration. Describe the result as **structural attributable closure**, never semantic authentication. [Qualification evidence and limitations](/Users/dadleet/.codex/visualizations/2026/10/18/01a14c60-cd70-7921-b457-5cf870234201/r07-20261115/qualification/handoff.json)

- **Require settlement for every removal, including at its due stage.** Make the invariant explicit: `settled_keys == prior_keys - current_keys`, where prior means the latest chronological `current_list`. Apply it to revisited product acceptance and every later submitted restatement, including voluntary restatements. Require `unverified` alongside `settled`; a settlement-only result must not bypass comparison. Preserve the separate routing rule: product acceptance may settle prior rows; elsewhere, only rows whose **previously recorded** due stage equals the current stage may disappear. The existing checker deliberately excludes product acceptance and permits due-stage omission. [shiploop_unverified.py — check_restated:122](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_unverified.py:122)

- **Strengthen the regression assertions before claiming success.** Currently, `r07_terminal` returns false on *any* subsequent refusal. Under A, the partial-deletion negative could pass because handoff later removes the legitimately observed surviving row without supplying `settled`, while the original acceptance bug remains. Assert that the targeted `check` and `complete` both refuse **at the attempted deletion**, with the expected continuity reason and unchanged accepted state. Update legitimate downstream removals to supply their own settlements. [shiploop-callback-contract.test.py — r07_terminal:2033](/Users/dadleet/src/skill-craft-r07-20261115/test/shiploop-callback-contract.test.py:2033)

- **Identity needs one additional guard: uniqueness of pending rows.** Reject duplicate normalized keys in newly submitted `unverified` lists as well as in `settled`. Otherwise set comparison collapses distinct rows. Reuse the existing normalization; whitespace-only edits preserve identity, substantive outcome edits constitute removal plus addition and require settlement of the old key. Do not add fuzzy matching or new IDs. Historical duplicate keys remain an ambiguity to handle explicitly, rather than silently choosing a row. [shiploop_unverified.py — _key:98](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_unverified.py:98)

- **Nested references require actual plumbing.** Existing evidence validation examines only top-level `evidence_refs`; root expansion handles those and assumption evidence. Merely naming the nested field `evidence_refs` will not validate it. Extend those existing paths to settlement references, require nonempty text lists, and reject placeholders. Preserve existing locator semantics: absolute local paths receive existence checks; URLs and other locators are not authenticated. [shiploop_navigator.py — evidence validation:3679](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:3679), [root expansion:9127](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:9127)

- **Reporting must preserve disposition and chronology.** Show the accepted action/stage, basis, and references. A `user-correction` means withdrawn/corrected, not observed or passed. Read recorded settlements across accepted history; comparing only the current product-acceptance list against the latest list loses settlements made during acceptance revisits. If an outcome reopens, show it as currently pending despite its historical settlement. Never manufacture settlement records for older omissions. [shiploop_unverified.py — html_section:195](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_unverified.py:195)

**No simpler existing representation meets the same requirements.** Summary plus top-level evidence lacks an exact outcome-to-disposition mapping. Assumptions describe different objects. `delivery_assessment` already provides stronger structure for marked delivery contracts, but adapting it to generic unverified outcomes would require more machinery than A. Keep those existing gates independent.

3. **Minor nits**

- Define “optional” precisely: omitted or empty when nothing disappears; required and exactly covering removals otherwise.
- Define `observed` as the outcome actually established on its required surface, not merely an attempted check or lower-layer pass.
- Avoid “copy unchanged” unless checking all seven fields. Current continuity primarily preserves identity and due-stage constraints.
- Update wording that says `[]` means every outcome was observed: after an authorized correction, it means none remains listed as unverified.

4. **Open unknowns**

- The qualification does not yet exercise generic early settlement or generic `user-correction` through the proposed field; the correction control exercises the existing marked-contract route.
- Historical malformed or duplicate rows may make exact matching ambiguous. Keep historical loading permissive; do not turn this repair into migration or retrospective revalidation.
- A cannot establish whether cited evidence supports the outcome, whether the observation is current, or whether the user authorized withdrawal.

**Owner-decision boundary:** recording attributable dispositions fits the stated R07 authorization. Requiring genuine early observations to wait—as B does—changes product behavior. So would allowing settlements at every stage, overriding delivery-contract correction/replanning gates, treating a declined check as withdrawal, or prohibiting terminal handoff with honestly retained open items. Those require a new owner decision.

5. **If I were implementing tomorrow**

1. Keep A’s four-field settlement shape and write the exact comparison and routing rules beside the existing continuity checker.
2. Add decisive controls: both reproduced revisit deletions, due deletion, missing/extra/duplicate/overlapping settlements, renamed outcomes, invalid references, and forbidden off-stage removal.
3. Add positive controls: early observation, explicit withdrawal, mixed settle/carry, due deferral, handoff with pending rows, latest-list revisits, reopening, first acceptance `[]`, and unchanged carry.
4. Wire result canonicalization, done-only admission, reference handling, revisit templates/packets, and truthful reporting. Preserve historical loading and existing delivery gates.
5. Verify save/load and actual CLI routes, then affected established suites; add the required change note and record the bounded claim.

I verified the baseline, source, relevant history, and retained qualification artifacts. I ran no tests, edited no files, and delegated nothing.