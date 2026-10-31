# AS1, 2026-10-31: does the Apps Script card's Testing section change what test-strategy declares?

A cheap stand-in for a live Apps Script round: one stage per sample, a Node project in place of a Google deployment, no
account and no `clasp`. It measures whether a model follows the card's text. It does not measure Google's runtime.

## The claim

`skills/shiploop/references/platforms/apps-script.md` has a `## Testing` section that says to name a deployed project as a
test-strategy target that keeps state (`keeps_state: "yes"` and a `base_state_route`), because a test that calls the
deployment reads the deployment and never the checkout. ShipLoop's packets at test-strategy, plan, prepare and step-plan
point to a card's `## Testing` section once KNOWLEDGE/environment.md names the card
(`shiploop_navigator._platform_testing_lines`). AS1 asks whether, with that pointer, test-strategy records the deployment
as a target that keeps state more often than without it.

History that shaped it: the section was first added as "Testing deployed code" (`dc312cd1`) and no packet pointed to it.
Fixed in `c468b25c62012b95dbe11fa199032719d0b34501` (the B arm). The owner held its release and then released it before AS1 ran (see "Release decision" below).

## What the pieces are

- **Case** `gas-deployed-target` in `test/shiploop_e2e/step_cases.json`, fixture `fixtures/local-target-gas`: an Apps Script
  project (`appsscript.json`, V8, server files in `src/` sharing one global scope). `scripts/deploy.js` stands in for
  `clasp push` and copies the project to a folder named by `LOCAL_TARGET`; the tests load the server files from that
  folder, as requests to the web app would. The seeded KNOWLEDGE/environment.md names `GUIDES/platforms/apps-script.md`
  under "Targets and runtimes". **No prose in the case, the README or the environment note says the deployment keeps state** (a hint remains in
  `scripts/deploy.js`: see "Known limitations"). The first experiments of
  2026-10-24 (E1, E3) scored 1.0 in every arm because the case gave the answer, and `decide` then reports a ceiling.
- **Slice** `--seed-at test-strategy --stop-after test-strategy`: the host starts at test-strategy and ends once that
  stage is accepted.
- **Arms**: A is `55a2726d8f0983aa94c547f98a452360945c0bad`, the build before the card section. B is
  `c468b25c62012b95dbe11fa199032719d0b34501`, the text that shipped in 2.25.0 / 1.24.0; `e9aed82d` later corrected two
  statements in it (expectations cannot show a deployed change; the mutation check records its reason only when every
  focused command is left out), and B does not run that correction. `skills/`, `agents/` and `plugins/` differ between A
  and B in that one card file.
- **Scorer** `test/shiploop_e2e/probes/target_state_declared.py`: 1 when the last accepted test-strategy result with outcome
  `done` has a `targets` row for the deployment with `keeps_state` yes; the rows are printed beside the value so a 0 shows what was declared.
  It sits in `probes/`, so it moves neither the evaluator digest nor the qualification snapshot. The cost: its bytes are
  in no digest, so the experiment record's two commits are what fix the arms, and an edit to the scorer after a round is
  not detected by a digest.

## Checked with no model

- `experiment.py verify AS1`: the scorer tells a deployment row that keeps state from a stateless one, from a checkout-only
  declaration, from a checkout target marked stateful, from a result with no `targets`, and from no result.
- test/shiploop-e2e-experiments.test.py: the seeded packet at test-strategy points to the card, and the case and fixture
  contain no statement that a target keeps state; A and B differ in the card alone.
- By hand on 2026-10-31, the same seeded packet rendered with each arm's build: A prints no `Platform testing guide` line
  and its card has no `## Testing`; B prints `Platform testing guide: GUIDES/platforms/apps-script.md#testing`.

## Known limitations: read before running

Found by an independent review on 2026-10-31 and not fixed, because each fix edits a fixture or a top-level harness file,
and since `cefff5ed` every fixture file is in the oracle digest and so in the qualification snapshot ("a neutral fixture
edit invalidates comparison"). Moving them is the owner's decision.

- **A weak hint remains.** `scripts/deploy.js` has a `--clean` flag and a comment that it "empties the deployment
  first", and the case's final check uses it. A model that opens the file can infer that the deployment holds earlier
  content. The no-statement test reads the case, README, scripts and environment note for a few phrases and does not
  catch this. It would push A toward 1.0 and blur the comparison.
- **Samples share one target folder.** The case sets no `seed_state`, so `LOCAL_TARGET` is unset and every sample
  writes `os.tmpdir()/local-target-gas`. Under `--jobs 4` concurrent samples overwrite one another, and a final
  check's `--clean` can wipe another sample's deployment. Under `--jobs 1` one sample's leftovers are visible to the
  next. `queue` has no hook between samples, so run one at a time with `experiment.py run AS1 --arm A --sample N` and
  remove `$TMPDIR/local-target-gas` between them, or fix the fixture first (a per-checkout default folder in
  `deploy.js`, or a `seed_state` that allows an empty target).
- **`node --test` also runs `test/deployed.js`**, a loader, and reports it as a passing test. Cosmetic; the original
  `local-target` fixture does the same.

## Run it (a Codex Terra 6.1 xhigh host with hooks on, the current default subject)

```sh
python3 test/shiploop_e2e/experiment.py verify AS1
python3 test/shiploop_e2e/experiment.py queue AS1 --arms A,B --jobs 4      # 8 one-stage samples
python3 test/shiploop_e2e/experiment.py score AS1
python3 test/shiploop_e2e/experiment.py decide AS1 A B
```

## Reading the result

`decide` applies an exact one-sided permutation test, p below 0.05, to the two arms' samples (D5, `a9e398e9`; the earlier
A/A split-half rule is gone). With 4 binary samples per arm only 4 against 0 reaches it: 4 against 1, or 3 against 0,
gives p 0.071 and reads inconclusive. More samples per arm would widen what can be decided; that is the owner's call.
- **ceiling** (every sample of both arms 1): the packet's own `targets` field and its rule already get the model there;
  the card section adds nothing measurable at this case. Per the 2026-10-24 journal, change the case before adding samples.
- **floor** (every sample 0): the section does not help at this case, or the model declares the deployment under a name the
  scorer's pattern misses; read the printed `rows` before concluding.
- **supports**: B above A at p below 0.05 (4 against 0 at this size). It shows the text is followed on this stand-in. It does not show anything about
  Google's runtime (web-app identity, OAuth, `clasp`), and one case and one subject model is one case and one model.

Whether a result counts as the live round the release preflight asks for is the owner's decision. Nothing has run.

## Release decision (2026-10-30, US Pacific)

- **The owner released the card text before AS1 ran.** Owner, in the document-stage review session: "Release anyway".
  This came after the quality review told them the release would ship c468b25c and dc312cd1, which they had chosen to
  hold until live evidence existed.
- **What shipped:** skill-craft 2.25.0 / ShipLoop 1.24.0 (release commit 9a2567b9), with the Apps Script card's Testing
  section.
- **What is still open:** AS1 has not run, so no live evidence covers the card text. Its result now tests a released text,
  not a held one.
