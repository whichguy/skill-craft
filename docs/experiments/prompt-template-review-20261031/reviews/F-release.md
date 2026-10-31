# F-release: release-plan, release-check, release, release-verify, operations, handoff

Reviewer scope: the rendered duties (`shiploop_prompts.PROMPTS`), the packet blocks around them (`shiploop_navigator`),
`stage-health.txt`, every refusal for these six stages in the 96 traced runs (re-extracted per run, with timestamps), the
packets those refusals answered, the release-plan Improve findings in `docs/shiploop-improve-value-evidence/findings.json`
(8246289f), and the returned `work/docs/shiploop/environment.md` of every archived case. Read-only; no model calls.

Overall: these six stages cost 247 of the corpus's wall minutes (about 4.3 per run) and draw 9 real and 11 check-only
refusals over 383 packets, all repaired within seconds. Their gain is in quality: two defects recur, one in the durable
record a user inherits and one in how a gated obligation reaches the model.

### release-plan — verdict: improve
Signals: 57 runs, 59 packets, ref 2 (1 headline cap retired by 232689c5, 1 live), chk 1 (live), median 0.3 min, total 44 min.
Findings:
- The packet prints a rollback block it calls "copy-ready for the plan's rollback". Its working-tree line holds a literal
  `<kept paths>`, so the command cannot run as written — evidence: `shiploop_workspace.rollback_lines` (text from 55bee172);
  printed in the release-plan head of `~/e2e-runs-qr/20261031/B-ticket-assignment-s2/.../packets/sent/e48d0354adc75287.md`.
  Live in current code: yes.
- The placeholder outlives the run. Of the 62 returned environment.md files that carry this recipe, 51 still have
  `-- <kept paths>` inside the command, including all 9 of 9 qr runs from 2026-10-31. The 11 filled ones include all three
  runs whose release-plan Improve flagged it (gate-2132-f7ba78-grok-hello, pilot-ollama-dsflash-993a9d-hello,
  ds-flash-978478-battleship). No stage is asked to fill it, so it gets fixed only when a model or its review happens to
  notice. Operations' "the rollback works" never caught it — evidence:
  `grep -l -- '-- <kept paths>'` over `~/e2e-runs*/**/work/docs/shiploop/environment.md`, `findings.json` rows for those
  runs. Live: yes.
- Minor: the "Return plan: <path>" line prints before plan-return writes the file. Two results cited it and were refused
  with "evidence_refs cite files that do not exist" (trace-verify-4fd9f1 hello chk; v2180-sonnet-battleship-36036c ref).
  Live: yes.
- Not proposed: (a) a consumer check that passes with zero tests (3 Improve findings). `judge()` has refused a runner
  `check` row that ran no test since d7388043, so those findings corrected the record's present/absent claim, not a false
  pass. (b) A candidate SHA that the stage's own knowledge commit makes stale (6 findings). All of them came from
  DeepSeek runs, and Improve fixed each one.
Proposal (mechanism, with one clause in release-check):
1. `rollback_lines`: when `return-plan.md` holds decided rows, print the working-tree recipe with the keep rows
   (shell-quoted) in place of `<kept paths>`. Before that, the line reads "`<kept paths>` are the keep rows release-check's
   review-return decides" and the header drops "copy-ready" for that line.
2. `workspace review-return` prints the filled rollback recipe next to the expected return.
3. Release-check duty 5: "Compare review-return's expected return **and filled rollback** with the procedure in
   KNOWLEDGE/environment.md; if they differ, correct the procedure and rerun plan-return."
4. Rider: while `return-plan.md` is absent, print "Return plan (plan-return writes it at release-check): <path>".
Gain / risk: every isolated run's durable knowledge gets a rollback that runs on any project. This matters most for a
dirty-start working-tree return, where this recipe is the only rollback. It also removes a recurring Improve finding
class. Risk: a long kept list makes a long command (allowed, since there are no caps), and paths need shell quoting.
Follow-up returns already keep `docs/shiploop`.
Verification (script, offline): a hermetic test of `rollback_lines` on a fixture plan. Then a replay over the 122
archived `return-plan.md` files: render the command and run `git apply -R --check` in a temporary clone of the returned
checkout at the receipt commit. Adopt if at least 95% of plans with a receipt render a command that checks clean.
History respected: 55bee172 and 8eb93c21 (script-printed, tested recipes), 54651813 (G33-3 plain `git`; state a rule
before a gate depends on it), 8246289f (the release-plan Improve schedule stays as it is).

### release-check — verdict: improve (only the rollback clause above)
Signals: 57 runs, 65 packets, ref 1, chk 3 (all live), median 0.5 min, total 54 min.
Findings:
- Two slips added an `assumptions` field (pa-ds-battleship-4ed4e3 chk; hooks-before-ticket-escalation ref). These are the
  only two firings of that refusal across all stages in the corpus, and the refusal names its exit. Live: yes.
- Two cited `RUN/return-plan.md`, a path that does not exist; the plan sits at the workspace root
  (bf-ds-user-listing-09c33b, both chk). This is a model typo. Live: yes.
Proposal: duty 5 clause from release-plan; nothing for its own refusals.
Gain / risk: see release-plan.
History respected: 8eb93c21, e39160ae (review-return owns the return-plan decisions).

### release — verdict: no-change
Signals: 57 runs, 84 packets, ref 0, chk 1 (live), median 0.4 min, total 32 min.
Findings:
- One "unverified drops R-6" (bf-ds-user-listing-09c33b, chk). An entry was due at release in 4 packets and 1 was refused.
  The placement fix under release-verify covers it. Live: yes.
Proposal: none of its own.
History respected: d84d30a9.

### release-verify — verdict: improve
Signals: 57 runs, 59 packets, ref 2, chk 5, 1 add-work, median 0.4 min, total 48 min.
Findings:
- The restatement gate's instruction never reaches the printed head. In all 63 packets of the corpus that had to restate
  `unverified` (all over the 16,000-character print limit), the "Restate the list in your result's unverified…" line sits
  in the `unverified` block. That block is FILE_ONLY (tier set in 2e1e3061; d84d30a9 later put the instruction there and
  added no duty clause). The head carries only the prefilled template key, and no duty mentions the field. First
  submissions were refused in 8 of the 63: release-verify 3 of 7, release 1 of 4, handoff 4 of 52 — evidence: per-packet
  scan of `packets/sent` head versus full file, joined to `trace.jsonl` refusals. Live: yes.
- Models write the result without reading the template or the tail. In the 2026-10-31 Codex run, the model read
  `sed -n '14,70p'` of the handoff packet, built the JSON from scratch, was refused, and added `"unverified": []` —
  evidence: `~/e2e-runs-qr/20261031/B-ticket-assignment-s2/transcript.md` turns 357-366. n=1, but it explains why the
  template prefill does not prevent the refusal.
- Other refusals: 2 malformed assumption rows in one Salesforce run (a shape refusal, 50 s), 1 flaky product test
  (ECONNRESET) in the clean copy, 1 invalid JSON. None is a prompt defect.
Proposal: split `_unverified_lines`. The instruction sentence becomes a P1 block placed right after the duties; the rows
stay FILE_ONLY, because the template already carries them. No new words: the sentence exists today. If a static duty
clause is preferred, use: "When the packet lists unverified outcomes, restate `unverified`: drop one due here that you
observed (name the observation in `summary`), move the due stage of one you could not observe later, and copy the rest
unchanged; `[]` when none stays open."
Gain / risk: removes most of a 13% first-submission refusal rate (43% at release-verify), and the drop-or-move decision
is made while observing rather than after a refusal. Risk: the head grows by about 250 characters, and head-order pins
need updating.
History respected: d84d30a9 (the rule and its gate are unchanged), 54651813 (state each gate before it refuses).

### operations — verdict: no-change
Signals: 57 runs, 58 packets, 0 refusals, median 0.2 min, total 35 min.
Findings:
- No refusals. On local-only cases the stage is short; the duty serves deployed services, for which the corpus has no
  evidence. Its "the rollback works" check missed the placeholder in 51 of 62 files. The fix is a runnable recipe
  (release-plan), not more model-judged wording.
Proposal: none.
History respected: 5e30bd9d (release operation ownership and recovery).

### handoff — verdict: improve
Signals: 57 runs, 58 packets, ref 4 (3 restatement, live; 1 headline cap, retired by 232689c5), chk 1 (restatement),
median 0.3 min, total 34 min.
Findings:
- Restatement refused in 4 of 52 handoff packets (v2180-sonnet, bf-codex-r1-user-listing, ds-flash-978478,
  qr B-ticket-assignment-s2), each time with the instruction only in the FILE_ONLY tail. Duty 4 names
  "product-acceptance's `unverified` list" only as content for `summary`, never as a field to restate. Live: yes.
Proposal: the same P1 placement as release-verify. If a duty clause is chosen, duty 4 starts: "Restate `unverified` from
the packet's list: drop an outcome you observed here (name the observation in `summary`), copy every other entry
unchanged, `[]` when none stays open. `summary` lists every open item still unverified (that list and every other
stage's result)…"
Gain / risk: as for release-verify.
History respected: d84d30a9, feb935de (the gate fired live and was repaired).

## Group top picks

1. **A runnable rollback recipe** (release-plan packet, `workspace review-return`, and a clause in release-check duty 5).
   51 of 62 returned environment.md files keep a non-runnable `-- <kept paths>` command, and no stage is asked to fill
   it. Cost: about 30 lines in `shiploop_workspace`, one duty clause, one hermetic test, and an offline
   `git apply -R --check` replay over 122 archived plans. No model calls; confirm at the next E2E round.
2. **The restatement instruction in the printed head** (release, release-verify, handoff). 8 of 63 first submissions are
   refused today. Cost: one block-tier and order change plus head-order and packet pin updates. Confirm in the next
   round's `stage_health.py`. Predeclared: adopt if restatement refusals fall to at most 1 in the next 20 restatement
   packets.
