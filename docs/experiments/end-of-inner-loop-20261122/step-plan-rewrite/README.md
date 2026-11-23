# Step-plan rewrites a requirement: the deciding check's apparatus (2026-11-22)

Design: `docs/experiments/end-of-inner-loop-20261122/step-plan-rewrite-design.md`, revision 1 (after Astra's review). It serves one
decision: ship that wording, or revise it. **No model has run on anything here.** Base: 1966c4c00b6fb83d8edfd4dfd877585cc83fc916
(its `skills/`, `test/` and `scripts/` are byte-identical to the release c06157c947ce9646bbe7528110a12b68ed8fbca8, ShipLoop 2.7.1).

| File | What it is |
| --- | --- |
| `case.json` | the one place for the requirement, the clauses, the new text, the send-back and the planted fact |
| `make_scenarios.py`, `notes-source/` | make `stage_cases/` from the committed replay; every change to the copy is listed in its docstring |
| `stage_cases/step-plan/send-back-revises-r9/` | cells T and C: a send-back that says a requirement must change |
| `stage_cases/step-plan/replay-ticket-comments-late-send-back/` | cell P: the original Proof-only replay less the retained run's absolute paths; `proof-scenario-diff.txt` is the whole difference |
| `check_paths.py`, `paths.txt` | every `/Users/` path a sample of T or P could be shown; no model |
| `render_packet.py`, `packets/` | the packets a build prints for both, and what they must hold; no model |
| `read_samples.py` | the registered measures over a live run's output |
| `prove_reader.py`, `reader-proof.txt` | the reader on hand-made samples and sentences, and broken one part at a time |
| `dry-runs.txt` | the four launch plans, accepted |
| `overlay-first-draft/` | a side file, not used: the design's first wording as an overlay, with its packet diff. Superseded by revision 1 |

## The scenario (T and C)

The original's spec has one requirement for the whole item, R-8, and the done step S1 serves it, so it holds no requirement served by
unfinished steps only. The minimum was built: R-8's notification bullet is cut in two, and what the delivered MESSAGE says becomes R-9.
C3 and its case TC_Comments_Notify, already the message's criterion and case, name R-9. The steps are reordered so that the interrupted
step is the one that serves R-9.

R-9 whole, in the built tree's `docs/shiploop/spec.md` (the same bytes in the baseline and at step-plan):

```
### R-9 Comment notification message
Basis: request S6; src/templates.js, src/notifier.js and CONTRIBUTING.md. Pending implementation and checks:
- The message delivered for a comment carries the comment's author and content in its body. Confirm by a worker delivery test that reads both from the delivered body.
- Its subject begins with the ticket ID in square brackets, as every other notification's does. Confirm by the same test.
- A message that cannot be delivered is retried and then dead under the existing outbox rules, and the comment itself stays. Confirm by a failing-notifier test.
```

- **Clause to change:** "carries the comment's author and content in its body" (first bullet). **Siblings that must survive byte for
  byte:** the second and third bullets. The Basis line may take the source.
- **New meaning:** the message's body is exactly `<author> commented on <ticket> (no preview).` and holds none of the comment's content.
  The text "no preview" is nowhere else in the built tree. The request says only "that agent is notified of the comment" (S6); no other
  requirement says what a comment's message holds.
- **The fact,** in the product's own `docs/operations.md`, in the run's baseline commit, two lines planted under Notifications:
  "The relay also puts every notification it sends on the wall display in the help desk lobby, where visitors read it. Ticket ids, ticket
  titles and people's names may stand in a notification; no other text that someone typed may." It is independent of the draft and of
  every test: the draft does what R-9 says today and passes its step's recorded Proof.
- **Sending stage:** implement, at S2, as the original. Its result (`RUN/results/<action>.md`, `evidence_refs: ["docs/operations.md"]`),
  449 characters:
  > R-9 must say instead: the message's body is exactly `<author> commented on <ticket> (no preview).` and holds none of the comment's
  > content. Fact: docs/operations.md (Notifications) says the relay shows every message on the lobby wall display, where visitors read it,
  > and no text someone typed but a ticket's title may be in one; R-9's "carries the comment's author and content in its body" breaks that.
  > S2's draft stays in the worktree; lint exit 0.
- **No owner note.**

| Step | Criteria | Requirement of its accepted cases | State |
| --- | --- | --- | --- |
| S1 store and persistence | C1 | R-8 (TC_Comments_Store, TC_Comments_Persist) | done, committed |
| S2 the message | C3 | **R-9** (TC_Comments_Notify) | interrupted; draft of `src/templates.js` uncommitted |
| S3 the HTTP API | C2, C4 | R-8 (TC_Comments_API); C4 is searched | not begun |

No case of a done step names R-9, so fix forward freezes nothing about it.

## Packet check (released text, no model)

`python3 render_packet.py released` (`packets/released.json`): for both scenarios the packet holds the revisit line with the send-back's
summary whole (`REVISIT_SUMMARY` is 600; 449 and 297 characters, not cut; the summary is also printed once more, under "Last accepted
transition"), the sending result's file, S1's row to copy, the spec's outline with every R-n, and duty 10; no owner note is owed; what
`shiploop next` prints is the packet file. 35,010 characters (T and C) and 34,873 (P), paths of this machine included.
When T's commit exists: `python3 render_packet.py branch --ref <commit>` (`--ref` was not run here: it adds and removes a detached
worktree), then `diff packets/released--<scenario>.md packets/branch--<scenario>.md` shows what T's text changes and nothing else.

## Cells and commands

One fresh session per cell and driver, six samples. Nothing below has been run but `--dry-run` (`dry-runs.txt`, all accepted, exit 0).

```sh
W=/Users/dadleet/src/skill-craft/.claude/worktrees/step-plan-rewrite-5eb186
X=$W/docs/experiments/end-of-inner-loop-20261122/step-plan-rewrite
R=/Users/dadleet/e2e-runs/spr-20261122-9a927c
T_REF=<the branch's commit, in full>
C_REF=c06157c947ce9646bbe7528110a12b68ed8fbca8

# T and P (the branch's build), Sol 6.2 medium
python3 -B "$W/test/shiploop_e2e/stage_suite/stages.py" live step-plan/send-back-revises-r9 step-plan/replay-ticket-comments-late-send-back --cases-dir "$X/stage_cases" --host codex --model gpt-6.2-sol --effort medium --samples 1 --jobs 2 --timeout 1800 --ref "$T_REF" --out "$R/TP-sol"
# T and P, Sonnet 5.5 medium
python3 -B "$W/test/shiploop_e2e/stage_suite/stages.py" live step-plan/send-back-revises-r9 step-plan/replay-ticket-comments-late-send-back --cases-dir "$X/stage_cases" --host claude --backend anthropic --model claude-sonnet-5-5 --effort medium --samples 1 --jobs 2 --timeout 1800 --ref "$T_REF" --out "$R/TP-sonnet"
# C (ShipLoop 2.7.1), Sol 6.2 medium
python3 -B "$W/test/shiploop_e2e/stage_suite/stages.py" live step-plan/send-back-revises-r9 --cases-dir "$X/stage_cases" --host codex --model gpt-6.2-sol --effort medium --samples 1 --jobs 1 --timeout 1800 --ref "$C_REF" --out "$R/C-sol"
# C, Sonnet 5.5 medium
python3 -B "$W/test/shiploop_e2e/stage_suite/stages.py" live step-plan/send-back-revises-r9 --cases-dir "$X/stage_cases" --host claude --backend anthropic --model claude-sonnet-5-5 --effort medium --samples 1 --jobs 1 --timeout 1800 --ref "$C_REF" --out "$R/C-sonnet"

# read all six
python3 -B "$X/read_samples.py" "$R/TP-sol" "$R/TP-sonnet" "$R/C-sol" "$R/C-sonnet" --json "$X/samples.json"
```

The reader tells the cells apart by the scenario (P) and by `--ref` (C is the full release hash above; anything else is T), so give C the
hash and not `main`. `stages.py`'s own PASS or FAIL is only a script check on the exact text: it fails a valid paraphrase. The reader
decides.

**Minutes and cost.** Stage-suite step-plan samples on record: 0.9 to 1.3 min (gpt-6.1-terra xhigh, the two late-send-back replays,
8 samples) and 1.5 to 2.0 min (gpt-6.1-sol medium, `ui-backend-control`, 6 samples). In today's whole deliveries the time from the
stage accepted before it to step-plan's was 0.5 to 1.8 min on Sol 6.2 medium and 1.0 to 2.6 min on Sonnet 5.5 medium. Each sample
also builds the plugin and the seed. No stage-suite record of Sonnet, and no dollar figure for a single stage: whole Sonnet 5.5
deliveries recorded 6.23 to 13.22 USD for 23 to 41 accepted actions, so a fraction of a dollar to about a dollar for one stage is an
estimate, not a record. Codex reports no cost.

## The reader

`read_samples.py ROOT ... [--json OUT]`. Its docstring defines the measures; each is `yes`, `no` or `read` (what a script cannot decide
is read by hand, never failed). Beside the design's measures it prints the refusals before acceptance, whether fix forward passed on the
first callback, the minutes, host, model, effort and build, every sentence that is new in the R-9 entry, the criteria that state the new
text and their steps, and STOP lines (another requirement, a sibling, an added, removed or retired R-n; in P any change to spec.md; the
retained run's knowledge files changed, see below).

Proof (`reader-proof.txt`): 37 hand-made samples, 20 sentences and 2 cases of the retained-run guard read as expected, and each of
14 single breaks of the reader is noticed. Samples #1, #2 and the P one (#35) went through the real commands (until loop, `check`,
done, `complete`), so the scenario is shown to accept a right amendment, and fix forward to refuse one that drops the done mark.
On real output: over the saved 2026-11-13 pilot (`~/e2e-runs-sp/20261113/replay-q1-pilot`, gpt-6.1-terra xhigh, ShipLoop 1.34.0) it reads
the four samples of the P scenario as met: spec.md byte-identical, the failing Proof changed, no product file changed, no refusal.

## What this replay cannot show

- **The sender.** The builder injects the send-back through `navigator.apply` without its gates. Whether a model at implement or document
  would find the fact, send back, write the summary this way or leave spec.md alone is not tested; neither is document's marker.
- **What follows step-plan.** The live stop counts a producer parked at Improve, so the planning review, its import, the knowledge commit
  that makes the rewrite the baseline, test-spec, the rebuilt step, carry-forward and the report are not reached.
- **Frequency or reliability.** One sample per cell, one scenario, one kind of fact. A pass says the wording can work on each driver.
- **A natural case.** R-9 and the fact were made for this check, and the send-back states the new text exactly; a real one may be vaguer.
- **The harness's opening line** (both cells, `run.seed_prompt`, not editable here) says the stages before step-plan were recorded
  "without doing them, so the request itself is the specification". A real run does not say that, and it speaks against the spec file.
- **Whether the new check discriminates.** The reader finds a criterion that states the new text on a step still to run; it does not run the
  amended Proof against the draft, so a Proof that would pass either meaning is seen only by reading it.
- **What Sol was given.** The archived packet is what ShipLoop printed. On Codex the model can see less: read the sample's rollout
  (`home/.codex/sessions`) for what it had.

## Noted

- **Absolute paths of a retained run.** The original names eight files of
  `/Users/dadleet/e2e-runs-multipass/20261031/mp-codex-ticket-comments/...` in 13 places (eight of them in its step-plan packet), and that
  run still exists: a model could read its later results, or edit its knowledge files instead of the sample's. They are gone from T and P,
  the same way in both (`make_scenarios.py`, 5): worktree files are repository-relative, the two planning notes are laid into RUN/notes, the
  baseline log is named by environment.md. In P nothing else differs (`proof-scenario-diff.txt`: ten values of scenario.json, each only its
  paths, and the two notes); with the shorter text its packet prints the item's context and the six concerns whole, where the original's
  cut the one and left out a line of the other. `check_paths.py` finds no path outside the sample in either packet, the opening prompt,
  either checkout, the run directory or a commit (`paths.txt`). What is left: the builder's own `.stage-suite/route.json`, beside the
  checkout, names the scenario's four overlay folders here in the worktree; nothing the model is given names that file. `case.json` still
  holds the sha256 of the retained run's three knowledge files and the reader prints a STOP when one changes, as a second guard.
- **A flake of the product's own tests.** The seed runs expectation E2 (`node --test test/api.test.js test/validate.test.js`) on the base.
  In 2 of about 320 builds here (one looked at) an HTTP test failed and the run hung past ShipLoop's 60 s, validate-existing did not settle and the build
  stopped before any host starts. A live sample would read NOT RUN, with no model call: run that cell again under a new `--out`.
- **The step-plan packet's files line** still lists only architecture.md and environment.md as what this stage writes, and the until loop's
  contract allows "only this action's result draft and docs/shiploop/" and forbids editing a recorded command.
