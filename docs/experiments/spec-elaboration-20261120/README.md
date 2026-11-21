# Spec elaboration: a vague request ground out into a verbose specification

**Registered 2026-11-20, before any call ran.** Owner's ask: a prompt that takes a small, vague incoming request
(an action, maybe an environment) and elaborates it into a verbose specification, "iteratively look[ing] for the
nuance" and recursing to find what the request leaves implicit and how the parts interact. The sample request is
the owner's: a Grok bot in a Salesforce development org. The intent is a small side experiment, then folding the
result back into ShipLoop's `spec` stage.

## What is under test

One prompt, two forms, on the same frozen requests:

- **A-single** (`arms/A-single.md`) — the control, and the current state of the art: the enrich-stage text of the
  ratchet pilot (`docs/experiments/ratchet-pilot-20261120/ratchet.py`, `SPEC_PACKET`, commit e63747a3d), with its
  repository-reading step removed because these cases have no repository. Find use cases, find implied
  requirements, write the specification. One pass.
- **B-recursive** (`arms/B-recursive.md`) — the same deliverable and the same rules about what a clause is, with the
  procedure replaced by six named passes and a stop rule: the ground; what each sentence takes for granted (applied
  again to its own answers — the recursion); where the parts meet; the runtime's own rules; what must not change and
  must never happen; then grind until a whole pass adds nothing a builder would otherwise have got wrong. It also
  writes `passes.md`, so what each pass added is visible.

The two arms share their output form, their clause rules and their ban on code and tests. Only the procedure
differs, so a difference in result is a difference in procedure.

> **Superseded 2026-11-20, after round 3.** Not exactly true. `B-recursive` (and `C`, `D` after it) paraphrased the
> control's rules and dropped two of its sentences: "Add no feature the request's intent does not cover", and "The
> clauses cover every sentence of the request; every implied requirement; every limit, boundary and error case, with
> its exact number; ...". So the recursive arms ran without the control's scope guard, and part of what the
> enumeration rule gained on Sol restores a rule the control always had. See "Corrections" below; `F-guarded` puts
> both sentences back, word for word.

## Drivers

The owner named both: **the latest Sonnet at effort high** and **GPT-6.2 Sol at reasoning effort medium**. Every
subject call runs headless in its own empty directory outside any repository, with the host's own customizations
off — `claude -p --safe-mode` (no CLAUDE.md, skills, plugins, hooks, MCP, commands or agents; verified on the
smoke call: no plugin command reached the session and no hook fired) and `codex exec --ignore-user-config` in a
throwaway `CODEX_HOME` that links only `auth.json`.

> **Superseded 2026-11-20, after round 3.** The Claude half held in all 16 Sonnet sessions. The Codex half did not:
> redirecting `CODEX_HOME` alone left the real HOME visible, and every one of the 16 Sol sessions of rounds 1 to 3
> read a user-level skill from it. From round 4 on a Sol call runs in the E2E harness's own throwaway profile
> (`hosts.CodexHost.env`), and `grade.py leaks` checks every stream. See "Corrections" below.
 Each call writes `spec.md` (and `passes.md` for B) and nothing
else. Subjects keep their full built-in tool set, as the real stage has one; `counts.json` records the tools each
call used, so a coverage difference that came from a web lookup rather than from the prompt is visible.

## Cases and the held-out checklist

`cases.json` is frozen: four requests of one sentence each, chosen for different shapes —

| case | shape |
| --- | --- |
| `grokbot-salesforce` | the owner's sample: greenfield on a platform whose hard limits bind the design |
| `gym-waitlist` | a change to a product that exists, consumer-facing, concurrency-heavy |
| `invoice-reminders` | scheduled outbound work touching money and real recipients |
| `csv-user-import` | file input, partial failure, and a real privilege-escalation hole |

Each case carries a **held-out nuance checklist**: 20 to 27 specific things a well-elaborated specification ought
to state, written from domain knowledge before any arm ran, and never edited after reading an arm's output. 89
nuances in all, each tagged with a category (interaction, edge, unhappy, async, data, permission, operator,
platform, nonfunctional, preserve). No subject call can read `cases.json`; only `grade.py` does. The checklists are
this experiment's own predictions about what matters, and registering them before the runs is what keeps them
honest — they are not a ground truth handed down from anywhere.

## How a round is measured

- **Script-countable, no model** (`grade.py counts`): use cases, clauses, the mix of `Source:` kinds, words,
  numbering gaps, clauses that bundle two behaviours behind "and", recorded passes, minutes, cost, tools used.
- **Judged coverage** (`grade.py judge`): one headless Opus session per specification, reading that specification
  and that case's checklist, returning `covered` / `partial` / `absent` per nuance with the clause id and a quote.
  A verdict already written is never re-judged; a re-reading is a new round, not an edit of this one.
- **Scoreboard** (`grade.py board`): coverage by arm, driver and nuance category beside the counts.

## Registered readings

- **R1, primary.** B-recursive covers more held-out nuances than A-single, pooled over the four cases, on both
  drivers. A pooled gain of **8 or more** of the 89 nuances on a driver shows a difference; **within 4** either way
  shows none; between 4 and 8 is interim and needs a second replicate.
- **R2.** A real gain is concentrated in the implicit categories — interaction, async, platform, operator,
  permission — rather than spread evenly. A gain that is even across categories is more likely to be length than
  elaboration.
- **R3, cost.** B-recursive is expected to cost more minutes and more words. If its coverage gain is under R1's
  threshold while it costs more than twice the minutes, the recursion as written does not earn its place.
- **R4, padding guard.** Coverage per 100 words and covered nuances per clause are reported for both arms. If B
  gains coverage only in proportion to its extra length, and its covered-per-clause falls, it is padding, not
  elaboration.
- **R5, procedure guard.** B is expected to record at least three passes with non-trivial additions in the later
  ones. A driver that writes `passes.md` as a formality (one pass, or later passes that only tidy wording) did not
  carry out the procedure; that row is apparatus, not evidence, and is reported as such.

Nothing here predicts which arm folds back into ShipLoop. What folds back is decided by R1 to R5 together, and the
decision is recorded in `docs/spec-elaboration-journal.md` with its numbers.

## Running it

```sh
python3 -I run.py round-1                     # 16 calls: 4 cases x 2 arms x 2 drivers, resumable
python3 -I grade.py counts round-1            # script metrics, no model
python3 -I grade.py judge round-1             # Opus coverage verdicts, resumable
python3 -I grade.py board round-1             # the scoreboard
```

A round is a directory: `results/<round>/` holds every call's `spec.md`, `passes.md`, stream and `meta.json`
(gitignored, kept on disk for replay); `grades/<round>/` the verdicts; `evidence/<round>/` the counts and the
scoreboard, which are committed. To iterate, change an arm (or add one), run the next round name, and the earlier
round's results and verdicts stay exactly as they were — that is how the same cases are re-run after each change
and the results of each iteration are retained.

## Corrections (2026-11-20, after round 3)

Found while evaluating rounds 1 to 3 from the sessions' own recorded streams; each changes how an earlier number is
read. Detail and evidence in `docs/spec-elaboration-journal.md` section 5.

1. **Every Sol session of rounds 1 to 3 read a user-level skill.** `illustrated-authoring`
   (`~/.agents/skills/`, a document-authoring guide that asks for economical prose) was read by 15 of the 16, across
   all four arms; `agentic-execution` (`~/.codex/skills/`) by 4, all of them recursive-form sessions and none of the
   single-pass ones. The first is the same in every arm, so comparisons between arms on Sol still compare like with
   like; the second is not, and the comparison between drivers was never like with like. `evidence/round-{1,2,3}/leaks.txt`.
2. **The recursive arms never carried the control's scope guard** or its "with its exact number" sentence (above).
   Nothing in rounds 1 to 3 measures how much a recursive specification asks for beyond the request.
3. **`passes.md` is the model's account, not a record.** Sol appends each pass's section as it finishes that pass.
   Sonnet writes pass 1's section, works on as one stream of edits, and writes most of the log afterwards. R5 counted
   sections; the work behind them is real (whole-file re-reads, 20 to 44 edits a session) but the numbered passes are
   partly a retelling on Sonnet.
4. "Sonnet used none [no web search] in any of its 8 calls" is true of round 1 only: one of its four round-3
   sessions searched twice.

## Registered follow-ups (2026-11-20, before any of them ran)

**Arms added.** Each is derived by script from the one before it, so the difference is exactly what is named:

- `F-guarded` = `D-enumerated-only` plus the control's two dropped sentences, word for word. The fold-back candidate.
- `L-lenses-once` = `F-guarded`'s five lenses and its builder's checklist as things to think through, then the whole
  specification written once: no passes, no `passes.md`, no stop rule. It prices iteration itself.
- `S-sectioned` = `F-guarded` with the deliverable laid out by dimension (what it is; use cases; behaviour;
  interface; data; background work; operation; runtime rules; must not change, must never happen), clauses numbered
  straight through. It follows the dimensions the owner listed for the sample request and aims at the three
  categories every arm is weakest in.

**Round 4: a second draw, on clean isolation.** `A-single` and `D-enumerated-only`, both drivers, all four cases.
- **R6, the noise floor.** How far a second draw of the same arm on Sonnet lands from the first (A 46, D 73 of 89).
  Every difference in rounds 1 to 3 was read against a guessed band of 4. If either Sonnet replicate moves by more
  than 4, the band was too narrow, and any difference smaller than twice the larger move is re-read as not shown.
- **R7, what the leak did.** Sol on clean isolation against Sol with the leaked skills, same arm. A move larger than
  the Sonnet move of R6 (or 4, whichever is larger) marks the rounds 1 to 3 Sol numbers superseded; a smaller one
  lets them stand with the leak noted.
- **R1 again.** D minus A within round 4 alone is 8 or more on each driver.

**Round 5: the three new arms**, both drivers, all four cases, compared with round 4's A and D.
- **R8, the guard costs no coverage.** F minus D is inside the no-difference band.
- **R9, iteration against lens content.** L minus A is what the lenses buy in one pass; F minus L is what iterating
  buys on top. If F minus L is under 8 on both drivers while L takes at most 60% of F's minutes, the one-pass form
  is the candidate; if it is 8 or more on a driver, iteration earns its place on that driver.
- **R11, sections.** S helps if S minus F is 8 or more pooled, or if operator, data and platform together (24
  nuances) rise by 4 or more with no other category falling by more than 2.

**The clause audit** (`grade.py audit`): one Opus session a specification puts every clause in one class
(request, needed, decision, extra, empty, wrong), on rounds 4 and 5 and on round 1.
- **R10, scope.** The recursive form adds scope if D's share of `extra` clauses exceeds A's by 5 points or more;
  the guard works if F's share is 5 or more points below D's. The `empty` share is the direct measure of the
  value-free clauses reported for Sol in round 1; the `wrong` share is reported as measured.
- Calibrated before use, on a specification with 8 planted clauses and labels written first: 8 of 8 in their
  planted class, 0 of 10 legitimate clauses flagged (`evidence/cal-audit-result.txt`).

**The judge, checked twice** on round 4's 16 specifications, beside the registered verdicts and never replacing them:
- **R12, a second draw** by the same judge (`--tag=r2`): the mean move per specification and the nuance-by-nuance
  agreement. This is the part of R6's noise that is the judge's.
- **R13, another family** (`--tag=gpt --judge=astra`, Codex gpt-6.2-astra at high, the E2E harness's own judge
  role): whether D over A, and Sonnet over Sol, hold under a judge that shares no family with the better-scoring
  driver. The finding depends on the judge's family if the Sonnet-over-Sol gap shrinks by more than half.

```sh
sh queue-2.sh          # everything above, in order, resumable; stops at once if a session leaks
```

## The plan to conclude (2026-11-20, revised before round 5 began)

The owner asked, ten minutes into round 4, whether the plan to conclude should change. It should: the queue above
answers this experiment's questions, and the conclusion is a narrower thing, a decision on what goes into
ShipLoop's `spec` stage. Measured against that, the queue carried two things the decision does not need and lacked
one that it cannot be made without. `queue-2.sh` was stopped after its round-4 subject calls; `queue-3.sh` carries on.

**Added: the baseline that was missing.** Every arm so far is measured against `A-single`, the ratchet pilot's
enrich text. That is the newest text for this job; it is not what ShipLoop ships. The released `spec` stage is twelve
duties that already ask for async completion and recovery, the life of each piece of state, designed interface
states and bounded non-functional requirements (duties 6 to 9), and it has never been run on these requests. Until
it is, nothing here shows that the elaboration adds to ShipLoop rather than repeating it.

- `P-shiploop-spec` = `shiploop_prompts.prompt("spec")`, word for word as a packet prints it (source and hash in
  `arms/P-shiploop-spec.source.txt`), under a frame that says what is absent when the stage runs alone, with the
  skill's own reference guides in `GUIDES/` as a real run has them. It writes ShipLoop's form (R-n with acceptance
  lines) and may write a second document; the judge is given everything it wrote. The judge was checked on that
  form first: the calibration specification re-laid as requirements scored the same covered-or-not on 27 of 27
  nuances (`evidence/cal-rn-result.txt`).
- **R14, does it add to ShipLoop.** P is a lower bound on the stage inside a real run, which has intake, discovery
  and research before it. The elaboration adds to ShipLoop if the better of F and L exceeds P by 8 or more on a
  driver (or by more than twice R6's measured move, if that is larger); nothing is shown if it is inside that band;
  and if P is at or above them, **no fold-back is warranted on this evidence** and the conclusion is "no change".
  `counts.json` records which guides each P session opened, so a Grokbot score that came from the skill's own
  Salesforce card is visible as that.

**Withdrawn before any call of it ran.**
- `S-sectioned` (R11). Its question, whether asking by dimension lifts the weak categories, is the question P
  answers better: the released stage is already laid out by dimension. And S's layout would not carry over, since
  the stage writes R-n requirements, not this experiment's U-n and C-n. The arm file stays; one command runs it
  (`python3 -I run.py round-5 --arms=S-sectioned`) if the owner wants the dimensions they listed tested as such.
- The clause audit of round 1. It would have re-checked an old claim on sessions that are now known to have leaked.

**Kept as registered:** round 4 (R6, R7, R1), F and L in round 5 (R8, R9), the clause audit of rounds 4 and 5 for
the arms that write C-n clauses (R10), and the two checks of the judge on round 4 (R12, R13).

**How it ends.**
1. Four answers: is the gain real beyond noise (R6, R1), which form (R9), does it overbuild (R10), does it add to
   the released stage (R14).
2. They give one of three outcomes: no fold-back; fold in the lenses as one pass; fold in the iterating form. For
   either fold-back, a drafted change to the stage's duty text that keeps duties 5 to 12 as they are, including
   duty 10's demand for a primary source behind a platform claim, which is stricter than anything these arms ask.
   That draft goes to Sol at max, and this journal to an adversarial read, before either is called ready.
3. The fold-back is a ShipLoop product-behaviour trade-off, minutes and specification length in every run, so it
   is the owner's decision, put with the numbers. After a yes: the change note, the suites, an E2E round on the
   changed stage with its LEARNINGS entry (which is also the first check of this standalone finding inside a real
   run), then the release.
4. **Stop rule.** No further arm is added. An answer that comes back interim at its threshold gets one more draw of
   the same arms, not a new arm.

```sh
sh queue-3.sh          # the revised queue, in order, resumable; stops at once if a session leaks
```
