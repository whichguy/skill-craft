**Findings — not approved.** HEAD and all nine hashes match the frozen candidate. The worktree is clean.

1. **P1 — Cached completion bypasses settlement file-existence validation.** At [shiploop_navigator.py:10364](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:10364), reuse rechecks continuity but skips `_check_submitted_evidence`. Reachable trigger: obtain a passing `release-check` answer with a settlement citing `RUN/observation.txt`, remove that file, then complete unchanged. Run-directory files are excluded from the checkout fingerprint, so the answer still matches; settlement shape passes and the pending outcome disappears despite its missing reference. Root expansion does not check existence.
   
   Reapply the existing evidence check before reuse. Smallest validation: real check → delete only the nested reference file → complete must refuse specifically for missing evidence, preserving accepted state. Retain the unchanged-file reuse control.

2. **P2 — A rejected cached answer remains reusable “yes” evidence.** The new guard at [shiploop_navigator.py:10364](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:10364) raises without invalidating or replacing the matching answer. The protocol records the callback refusal, but `checks/<action>.md` still says `yes` for the same key, and `matching_yes` continues returning it. This is reachable through the candidate’s existing same-version cached-answer negative fixture.
   
   Record the current admission refusal or explicitly invalidate that answer. Smallest validation: extend [the cached refusal test:2139](/Users/dadleet/src/skill-craft-r07-20261115/test/shiploop-callback-contract.test.py:2139) to inspect the retained answer and verify it cannot remain a matching yes. This is an evidence-consistency defect; the guard currently prevents advancement.

The three primary negative fixtures now assert refusal at the attempted deletion and unchanged state. Improve import, chronological continuity, stage admission, normalized identities, and historical-omission reporting appear consistent by inspection. Some positive fixtures cite only the generic “a note this stage wrote” evidence, so they establish mechanical acceptance, not coherent observation or correction evidence.

No tests, agents, edits, or external actions were performed. Findings are static control-flow conclusions, not executed reproductions. Python compatibility was inspected only; qualification logs and the parent’s suite results were not independently verified.

