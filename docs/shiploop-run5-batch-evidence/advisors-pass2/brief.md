# Review brief, pass 2: will the run-5 batch break or mislead a normal run?

## Context
ShipLoop is a script-driven SDLC harness for coding agents. A Python navigator prints one stage packet at a time:
- planning: intake, spec, test-strategy, plan, prepare;
- per work item: step-plan, test-spec, validate-existing, implement, test, document, verify, carry-forward;
- release: system-test, product-acceptance and the release stages.
The model does the stage and submits a JSON result. CLI gates refuse a result that breaks a rule, and each refusal
names the fix ("the named exit").

The run-5 batch is one release, 2.9.0. Its next live run is a raw chess app on Salesforce: Grok 4.7, Sonnet
coordinator, 5 h cap.

Rules:
- Fix only what breaks or misleads a normal run (KISS).
- Keep ShipLoop text generic; platform detail lives only in `references/platforms/`.
- One term per concept.
- One supported version.

## Read
- **Repository:** `/Users/dadleet/src/skill-craft/.claude/worktrees/shiploop-templates-6d625a`, at HEAD on branch
  `feat/shiploop-templates-6d625a`.
- **Batch journal:** `docs/shiploop-run5-batch-journal-2026-10-24.md`, which holds each change's question, change and
  evidence.
- **Commits to review**, with `git -C <repo> show <sha>`. The four renames R1-R4 are excluded: a retired-term scanner
  and the suites cover them.
  - `52789f8f` F1: test layers (`test_layers`, `targets`, `harness_runs`, criterion `confirm`), in
    `skills/shiploop/scripts/shiploop_test_layers.py` and `shiploop_navigator.py` `_check_submitted_layers`;
  - `145aefbb` F2 rest, F3, I2 and I1, covering:
    - the file-guard refusal (`test_loop.guarded`, navigator `_check_focused_guards`);
    - per-command `target` and `stateful_targets`;
    - `_remote_base`;
    - `mutation.split_remote`;
    - the RED-unobserved block;
    - the look-back subject cap;
  - `f9d1f4cf` F6: the spec's `primary` and each unverified row's `requirement` and `lower_layer_check`, in
    `skills/shiploop/scripts/shiploop_primary.py`;
  - `91d7364a` F5: the `Regression test:` line at the end-of-work Improve commit, in navigator `_regression_refusal`;
  - `66703f48`: Apex test classes in `skills/shiploop/references/path-classes.json`;
  - `5c0e8f5f`: the known-dodge table `test/shiploop-loophole-gates.test.py`;
  - `f820b4ea` and `484f4a67`: harness dodge counters in `test/shiploop_e2e/metrics.py`.
- `commits.txt` in this folder lists all 21 commits.

## Questions
1. **Correctness.** Find a bug that would break or mislead a normal run, for example:
   - a gate that refuses a valid result;
   - a refusal whose named exit is itself refused, or cannot be met on some platform;
   - a refusal loop with no way out;
   - a base-run or mutation classification that reads RED or remote wrongly;
   - a crash on a missing or old-shaped field.
   Give the file and symbol, and a concrete input that fails.
2. **Interactions between changes**, for example:
   - F3's stateful targets with I2's platform-card remote rule and the mutation check;
   - F6's primary rule with add-work (can a run loop adding work it cannot satisfy, for example when the platform has
     no unit runner for a primary outcome?);
   - F5 on the improve-pass path;
   - F1's `confirm` with the Salesforce card (Apex tests run only in the org).
3. **Over-building.** Name any gate, field or prose that costs a normal run turns without catching an observed
   failure. The journal's "Overcomplication review" row lists what is already cut or watched.
4. **Genericity.** Is there platform or domain wording in generic ShipLoop text?

## Output
- A list of findings, each with: severity (P0 breaks a normal run, P1 misleads or costs a normal run, P2 minor),
  `file:symbol`, the failing scenario, and the smallest fix.
- No style nits.
- Say "no finding" for a question with none.
- Mark a finding you could not confirm by reading the code as unconfirmed.
