# Group E-close: carry-forward, system-test-author, system-test, product-acceptance

Reviewer: E-close, 2026-10-31. Read-only: no model calls, no E2E runs. The corpus is the 96 traced runs in
`stage-health.txt`. Scratch extractor: `/private/tmp/claude-501/-Users-dadleet-src-skill-craft/ddd28884-3bee-490a-b072-5207d26ab322/scratchpad/refusals.py`.

### carry-forward — verdict: no-change
Signals: 73 runs, 88 packets. 2 real refusals (1 retired, 1 live) and 9 check-only (6 retired, 3 live). Median 0.5 min, 91 min in total.
Findings:
- The six check-only "work item W<n>'s context is n characters; the limit is 2,500" refusals and the real "headline … at most 100 characters" refusal are retired. 232689c5 turned those caps into print budgets. All six came from DeepSeek runs (ds-flash-978478, v2170-ds, pa-ds, bf-ds-user-listing). Live in current code: no.
- The live refusals are cheap. "carry-forward needs skill" fired once real and once check-only in v2180-sonnet; the next attempt was accepted 6 s later. "Fix the due stages" fired twice check-only in pa-ds-battleship, where A1 named `carry-forward` at carry-forward itself. Live: yes. Neither is worth more text: the prompt already says "the later outer stage".
- All 86 of 86 accepted carry-forward results decided `skill: none`. Item 3, the skill procedure, is 3,321 of the duty's 6,104 characters. The "none" reasons in the 9 multi-item runs are sound (nothing repeated, or a test already captures it). Live: yes.
- The carry-forward regression-message guard misclassifies non-conventional test paths (4893e521). That is F11, a limit already decided without a fix; df6b91e2 rejected the Apex-pattern patch. Live: yes, but decided.
Proposal: none. The 86/86 count is 4× the 20/20 Astra cited when the owner kept the skill decision at carry-forward (design T 2b-3, 7b2d57b7). The revisit trigger the owner set, "a skill reused within one item", has not occurred. Moving item 3.3–3.6 into the Repository-local skill guidance would save tokens only. Archived runs cannot test it, because no run reached a create.
Gain / risk: —
History respected: 232689c5, 7b2d57b7 (owner: "Go with C", skill decision stays per item), 4893e521, df6b91e2.

### system-test-author — verdict: side-test
Signals: 71 runs, 81 packets. 5 real refusals and 1 check-only, all live and all from DeepSeek JSON-shape errors, each repaired in 0.4 min or less. Median 0.4 min, 64 min in total. The real defect only surfaces downstream, at system-test.
Findings:
- **The default suite gets marked `host_dependent`.** In 3 of 3 Salesforce runs on Codex Terra 6.1 high, the first system-test-author result marked the org-native test command `host_dependent: true`. In each case the command string was identical to a step-plan row flagged `regression: true`. The pv9hf_8a run did it twice. System-test then refused on drift 4 times, and each refusal led to a send-back. Live: yes. Item 6 says "(browser, device, account, service)", which invites marking a suite that needs an org even when the default suite needs that org too. Evidence:
  - `~/e2e-runs/2026-10-31/shiploop-gym-salesforce-91y7tnl1/gym-published-baseline-03`, results nav-366b6413 → nav-f93f6951;
  - `…/shiploop-sf-qualified-pv9hf_8a/development-01`;
  - `…/shiploop-sf-fidelity-repair-htoehblp/…/battleship-candidate`.
- Each loop cost 1.3–4.1 min and 4–7 packets, including an Improve child; 06a7473d measured 247 s. Quality also degraded. In battleship-candidate's second result the model kept `host_dependent` and changed the native suite from `focused` to `check`, so ShipLoop no longer counts its ten IDs. In the other two runs the mark was simply dropped.
- The gate works for its intended case. Five browser `host_dependent` rows in 4 non-SF runs (DeepSeek and Sonnet, e.g. `BATTLESHIP_BROWSER=1 node --test test/system.test.js`) had their own commands and caused no drift. In an offline replay over every archived system-test-author result, "host_dependent row equals an accepted regression command" matches exactly the 4 later-refused results and nothing else.
Proposal (candidate, pending the test):
- (a) Item 6 wording. Replace "A row whose cases need a host tool (browser, device, account, service) gets `"host_dependent": true`" with: "A row whose cases need a host tool the project's default regression command does not need (a browser, a device, an account the default suite never uses) gets `"host_dependent": true`; a case the default regression command already runs is never host_dependent, whatever runtime it needs."
- (b) Optional. At system-test-author `complete`, refuse a `host_dependent` row whose command equals a step-plan regression command, naming both exits: drop the mark, or give the host-only cases their own opt-in command. This moves the refusal to the stage that can still change commands.
Gain / risk:
- Gain: removes a send-back loop for any project whose default suite needs an external runtime (a hosted platform, a service, an emulator), and stops the downgrade to `check` that loses counted IDs.
- Risk: (a) could un-mark a genuinely optional tool. The browser countercase measures that.
Side test:
- Question: does the reworded definition stop marking the default suite, without un-marking optional host tools?
- Corpus:
  - script arm: the archived system-test-author results (replay already done: 4 hits, 0 false);
  - model arm: the 3 archived first system-test-author packets from the SF runs, plus one neutral hosted-runtime fixture whose default suite needs an authenticated runtime, with an optional-browser countercase. 06a7473d asked for exactly this fixture.
- Measure, per result:
  - a default-suite command marked `host_dependent`;
  - the browser countercase marked;
  - a native suite downgraded to `check`.
- Decision rule (predeclared): adopt (a) if mis-marking falls from at least 3/5 to 0/5 on every hosted-runtime input and the countercase stays marked 5/5 in both arms. Adopt (b) only with a replay showing 0 false hits and the owner's approval, because 06a7473d routed D1 to owner_review.
- Cost: 4 inputs × 2 arms × 5 frozen-input trials = 40 Terra 6.1 high calls (about 1M tokens); the replay costs nothing.
History respected:
- ba908889 (gate design: system IDs are only known at system-test-author; the marker is the owner's);
- 06a7473d (D1 not admitted; "preserve truthful classification, native proof and the existing optional-host-tool isolation gate"). The candidate keeps all three and makes the classification match what the gate enforces.

### system-test — verdict: no-change
Signals: 57 runs, 65 packets, 7 real refusals (all live), 4 send-backs. Median 0.2 min, 29 min in total.
Findings:
- 4 refusals and all 4 send-backs are the host-dependent drift above. Their cause is upstream at system-test-author; this stage behaves as designed. The drift refusal's remedy (opt-in command or skip) cannot apply when the marked row is the default suite, and the model chose send-back each time. The system-test-author fix makes this case unreachable. Live: yes.
- 2 × "system_commands are allowed only on a done system-test-author result" (pa-ds-battleship, bf-ds-user-listing, both DeepSeek), each repaired in 0.1 min. Live: yes.
- 1 genuine failure: hooks-after-ticket-escalation, `npm test` failed with ECONNRESET; the model fixed it and was done 0.3 min later. This is the gate working.
Proposal: none.
History respected: ba908889, a3b2f975.

### product-acceptance — verdict: improve
Signals: 57 runs, 63 packets. 3 real and 3 check-only refusals, all the primary `lower_layer_check` rule and all live. 2 add-work outcomes. Median 0.2 min, 31 min in total.
Findings:
- **The refusals push later-phase rows out of `unverified`.** I traced how each refused attempt was resolved. In 4 of the 5 runs the refused row was a release-phase obligation, and the next accepted attempt, 5–10 s later, no longer listed it:
  - config-control R-2: "Guarded return to the original branch remains due at release";
  - battleship-candidate R-4: "source root return still due";
  - bf-ds-ticket-assignment R-11: moved to open item A2 at release-verify;
  - pa-ds-battleship R-7: moved to an open item at release-verify.

  In the first two the outcome now exists only in `summary`. Item 3 forbids exactly that: "An outcome stated only in the summary has no end state". Live: yes. This adds to the parent's classification (no lower-layer case exists) rather than contradicting it.
- The same pattern appears without any refusal. A regex over the 57 final done results finds about 19 that state a later-phase step only in `summary`. I spot-checked 6 of them, all the source-checkout return, e.g. bf-codex-r1-user-listing R-4 and A-user-listing-s2 R-4. The duty contradicts itself: item 3 says "not yet due, listed in `unverified`", while item 6 says "A missing delivery prerequisite is named in `summary`". The return is release's own step, checked by its receipt and by release-verify's clean-copy rerun (e9ec4733). No unit test can show it, so the f9d1f4cf bar cannot be met for it.
- **The Backchain paragraph is printed but never used.** All 60 archived product-acceptance packets print the full Backchain route paragraph (1,441 characters) plus resource lines. No result requested a review; 4 say outright that none was needed. The stage has `edits=frozenset()`, so the paragraph's repair/revise half can never apply. Live: yes.
Proposal:
1. Item 3: after "Carry in the open items earlier stages recorded (system-test-author, system-test).", add: "ShipLoop's own return of the worktree to the source checkout is release's, checked by its receipt and release-verify's rerun: name it in `summary` for release-plan, not in `unverified`."
2. Add product-acceptance to `INLINE_AUDIT_STAGES`, on every route since the stage edits nothing, so it prints the one-line optional audit instead of the route paragraph. Item 7 stays.
Gain / risk:
- (1) makes the duty agree with item 6, the gate and what runs already do, and removes the refusal trigger behind 4 of the 6 refusals. Risk: a model could stretch "return" to cover a real consumer outcome, and the chess failure f9d1f4cf fixed was a deferred primary outcome. The wording names only ShipLoop's own return. Check after landing: primary-gate refusals and summary-only return lines, both from `stage_health.py` and the regex.
- (2) saves about 1.2k characters per packet. That is a token gain only, so it ranks below quality.
History respected:
- f9d1f4cf (primary bar kept for product outcomes);
- 488ffbd9 (condition-review paragraph not adopted; not re-proposed);
- d9fefb11 (no new final stage, no stronger gate);
- fac85d6a and the owner's 2026-10-11 concision decision (one-line audit at stages that build no graph);
- e9ec4733.

**Group top picks**
1. **system-test-author `host_dependent` definition** (side test, then the item-6 wording; the system-test-author-time check only with owner approval). This is the one live defect in the group: 3/3 runs on the current subject model, a send-back loop each, and a quality loss when the suite became `check`. Cost: 40 frozen-input Terra calls and one neutral fixture; the replay is already done.
2. **product-acceptance item 3 return sentence, plus the one-line Backchain audit.** This removes a contradiction in the duty behind 4 of 6 refusals and about 19 summary-only rows, and trims about 1.2k characters per packet. Cost: two text edits, an offline render diff and the packet test suites. No model call is needed before landing; recheck in the next batch's `stage_health.py`.
