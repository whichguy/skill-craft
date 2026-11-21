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

## Round 4 as it turned out (2026-11-20)

`queue-3.sh` stopped itself at round 4's leak check: 7 of the 8 Sol sessions had read a user-level skill, through
the E2E harness's own throwaway profile. The stop is the check doing its job; what it found is wider than this
experiment.

**What is true of Codex 0.171.0 on this machine**, measured with `codex debug prompt-input`, which renders what a
session's model is shown and makes no model call:
- With `HOME` and `CODEX_HOME` both pointing at a throwaway profile, and even with nothing in the environment but
  `HOME`, `CODEX_HOME` and `PATH`, the prompt input lists the skill roots `/Users/dadleet/.codex/skills` and
  `/Users/dadleet/.agents/skills` and the ten skills in them. Codex takes the account's home from the system, not
  from the environment. So `hosts.CodexHost.env` isolates config, plugins and state, and not skills.
- No feature flag tried removes them: `skip_host_skill_discovery` on, `skill_search` off, `plugins` off.
- Turning each skill off by its `SKILL.md` path does: `-c skills.config=[{path="...",enabled=false},...]` leaves no
  path under the real home in the prompt input (2 roots and 10 skills before, none after; 83,349 characters to
  77,049). `codex_isolation.py` builds that override and holds the check.

**Superseded:** "A smoke call on the fixed runner read nothing outside." It was one session that happened not to
open a skill it had been shown. From round 4c on a round refuses to start unless the no-model render shows a Codex
session none of the user's skills, which is a proof where the smoke call was a sample; the scan of the streams
afterwards stays.

**What round 4 is now.** Its 8 Sonnet sessions are clean and give R6 as registered. Its 8 Sol sessions are a second
draw of the same leaked condition as rounds 1 to 3, which is a measurement nobody planned and is worth having: how
far Sol moves between two draws with the same skills shown. **Round 4c** runs A and D on Sol again with the skills
turned off, and **R7** reads that clean draw against both leaked ones. Nothing else in the plan to conclude
changes: round 5 is still F, L and P, and the audits read only clean specifications.

```sh
sh queue-4.sh          # round 4 judged as it ran, round 4c, round 5, the judge checks, the audits
```

## The band, measured (2026-11-20, before round 5 ran)

R6: a second draw of the same arm moved by up to 6 of 89 on Sonnet (A 46 then 40; D 73 then 71), so **a difference
between two single draws under 12 is not shown**. Every reading above registered as "8 or more" is read at 12: R8
(F within 12 of D), R9 (iterating earns its place at F minus L of 12 or more; 8 to 11 is interim and gets one more
draw of both), R14 (the better of F and L is 12 or more above P). R7 reads clean Sol against the mean of the two
draws with the skills shown; a move over 6 supersedes them. The main effect repeated at +31 on Sonnet and +18 on
Sol within round 4. "The enumeration rule: +12 on Sol" is superseded: +10 against the mean of D's two draws, not
shown. `evidence/round-4/readings.txt`; journal section 8.

## The draft, and the one arm past the stop rule (2026-11-20, before round 6 ran)

The four answers are in (journal section 12): the gain is real and comes from the lenses; one pass, not
iteration; the one-pass form adds no scope; and it beats the released stage clearly on Sol at medium (+19) and
not shown on Sonnet at high (+6). That is the outcome "fold in the lenses as one pass".

The plan to conclude said no further arm. One is added, because the fold-back is not any arm that ran: L and P are
alternatives, and the change proposed for ShipLoop is P with the lenses in it. Putting a text to the owner without
having run it, when the instrument to run it exists, would be asking for a decision on a guess.

- `Q-shiploop-spec-lenses` = `P-shiploop-spec` with one block inserted into duty 2, after its first paragraph:
  386 words, the five lenses as things to think through once before writing the requirements, the scope guard in
  the stage's own terms ("inside the approved scope: add no feature the request's intent does not cover"), and
  the rule that a named dimension lists its members and a named limit gives its value or is recorded as
  unresolved under duty 6. It defers to duty 10 for the source of a platform rule. The block is in
  `arms/Q-shiploop-spec-lenses.insert.txt`; a diff of the two arm files shows nothing else.
- **Round 6**: Q, and a second draw of P, on both drivers, all four cases. 16 calls.
- **R15, the draft against the released stage.** Read against the mean of P's two draws at the same band of 12:
  the draft adds to the stage on a driver at Q minus P of 12 or more; 8 to 11 is interim; inside 8 nothing is
  shown, and a proposal to fold it in would then rest on round 5's L alone and has to say so; at -12 or worse the
  draft hurts and is not proposed. Reported beside it: Q's minutes, output tokens and words against P's, which is
  what the change would cost in every run, and Q against L, which says whether the lenses lose anything by being
  set inside the full duty text.
- **R13 on the deciding rounds.** The second judge (gpt-6.2-astra at high) read only round 4. It now reads rounds
  4c, 5 and 6 as well, beside the registered verdicts: do L over P, and Q over P, keep their sign and rough size
  under a judge of another family.

```sh
sh queue-5.sh          # round 6, then the second judge on rounds 4c, 5 and 6
```

## After the independent review (2026-11-21)

The draft and sections 8 to 13 of the journal went to the latest Sol at maximum effort before anything was put to
the owner (`review/`). **Its verdict was "do not put it"**, and every claim of fact of its that was checked against
the files held. What a reader of this README has to know (journal section 14 has the rest):

- **R14 did not measure what it was read as measuring.** Counting a nuance as touched when it is covered or
  partial, the released stage reaches 87 of 89 on both drivers and the lens arms 86 to 89. L's "+19 on Sol" is
  `partial` turning to `covered`: more decided, not more found. The judge prompt says nothing about a stated
  exclusion or an open item and scored them unevenly, and the released stage's duties tell it to leave some things
  open or out. "It adds to the stage ShipLoop ships" is **not shown**.
- **"The one-pass form adds no scope" is withdrawn.** Its share of clauses labelled extra is lower than the single
  pass's; its count is higher on Sol (48 against 38); and the released stage's scope was never audited.
- **Not isolated:** iteration as the source of scope, the leaked skill as the cause of the single pass's fall on
  Sol, the guard as helping on Sol. 12 is a decision threshold, not an estimate of noise.
- **The checklist and the lenses share an author** and lean the same way. Freezing the checklist stopped
  hindsight edits, not that.
- **The draft block is not to be proposed as written.** Its faults are of one kind: it turns aids to thinking
  into things to write ("what a line turns up becomes a requirement"), and every acceptance line is work for the
  stages after `spec`.

What stands: against the ratchet pilot's single pass the lens arms cover far more; the one-pass package costs
about half the iterating one and loses nothing shown; and the released stage, run alone, already reaches nearly
every nuance on this checklist. The outcome of the plan to conclude is its first: **no fold-back into the released
stage on this evidence.**

## The smaller attempt: re-aimed before it ran (2026-11-21)

The owner said yes on 2026-11-21 to the smaller attempt the journal's section 15 left open: a two-sentence cue in
duty 2 naming the people who run the thing and its unhappy paths, with its own paired check. Before the check was
designed, the specifications already saved were read item by item (journal section 19). The reading changed the
aim. This section registers the check as it will run; when it is committed no model has been called for it.

**What the reading found.** Evidence: `evidence/round-6/operator-unhappy-item-by-item.md`,
`evidence/round-6/requirement-titles.txt`, `labels/stable-shortfalls.txt`.

- On the 21 operator and unhappy-path items the released stage leaves 0 to 3 untouched in a draw (1 and 1 on
  Sonnet, 0 and 3 on Sol); the rest it settles or mentions, and where it only mentions one it has usually left it
  out on purpose or recorded it as open.
- The earlier block's gain on those items was, in all eight of its specifications, a requirement for the
  operator's own controls that the released stage does not write: a staff roster with a Remove action, a global and
  a per-class switch, an operations surface to pause and roll back.
- The owner's rule, recorded 2026-09-27 (commit e18cbce9ec577a61a8cdea353c6794804b09f1d9, and the value audit in
  `skills/rubric-eval/scripts/rubric_eval.py`): engineering rigour is the expected standard even for a small
  request; product capability the request does not need is overbuilding. By that rule those requirements are
  capability nobody asked for. A cue that asks for them is not a candidate, and the cue as first described is not
  run.
- Where the released stage does fall short in both of its draws is elsewhere: 24 of the 89 items on Sonnet, 42 on
  Sol, 18 on both. Several are a set named without its members or a limit named without its value. The earlier
  block closed 14 of Sonnet's 24 (13 under the second judge) and 7 of Sol's 42.

**The cue, re-aimed.** Arm `M-shiploop-spec-members` is `arms/P-shiploop-spec.md` with two sentences added to duty
2 at the place the earlier block went (`arms/M-shiploop-spec-members.insert.txt`; 67 words; the arms differ by
those four lines and nothing else):

> Where an acceptance line depends on a set of states, conditions or inputs, name its members, or the groups with
> distinct observable behaviour, and explain material exclusions. Where one depends on a limit, state the
> applicable bound and the behaviour at it; record an unresolved behaviour bound as an open gap under its R-<n>
> (item 4), and an unresolved non-functional bound under ## Non-functional requirements (item 6).

The wording is the replacement the independent review gave for the last two sentences of the earlier block
(findings 11 and 4), joined, with "of states, conditions or inputs" added so that "set" cannot be read as stored
data. It carries no example, so none can repeat a checklist item. It names nobody who runs the thing.

**The items are sorted before any subject call** (`label.py`). The judge counts an item as covered when a
specification settles it, asked for or not, so a covered count cannot tell rigour from capability. Two models of
different families (claude-opus-5-5 and gpt-6.2-astra, both high), shown the four requests and the 89 items and no
specification, arm or verdict, give each item two labels: `kind` (does settling it mean naming a set's members, or
stating a limit, or neither) and `scope` (needed: the requested outcome's own behaviour or engineering rigour;
beyond: capability the request did not ask for; mixed), the second by the owner's rule in the words of the commit
above. Only items both sort alike are used:

| set | what is in it | reading |
| --- | --- | --- |
| X1 | both say set, limit or both; not agreed beyond | R16, the cue's target |
| X2 | both say needed; not in the target | R17, what must not be lost |
| X3 | both say beyond | R18, capability that must not grow |

The author of the checklist and of the cue sorts nothing. The labels, the sets and the bands are committed before
round 7 starts (`labels/`).

**Bands.** For each set, the band is the largest move in covered count between two draws of one arm on one driver
among the four clean repeat pairs on record (A on Sonnet in rounds 1 and 4, D on Sonnet in rounds 3 and 4, P on
both drivers in rounds 5 and 6), under the registered judge, and never less than 2 (`label.py bands
--upto=round-6`).

**Rounds 7 and 8.** Each runs M and P on both drivers over the four cases (16 sessions a round, 32 in all), with the
Codex pre-flight before and the leak check after, read by both judges (`queue-6.sh`). M is compared with the P of
its own round, so the two share whatever the hour did to them.

**Readings, per driver.** d is M's covered count minus P's on a set in one round.

- **R16, the target (X1).** Shown: under both judges the mean of d over the rounds is at least the band and d is
  above zero in every round. Interim: the mean is above zero under both judges and at least half the band under
  the registered judge. Otherwise nothing shown.
- **R17, nothing lost (X2).** Fails when, under both judges, the mean of d is at or below minus the band and d is
  below zero in every round.
- **R18, no capability added (X3).** Fails when R16's "shown" test is met on X3. Each X3 item M settles and P does
  not is also listed with what the specification says, since the judge sometimes scores a stated exclusion as
  covered.
- **R19, the standing shortfalls.** On the items the released stage covered in neither round 5 nor round 6 (24 on
  Sonnet, 42 on Sol; the lists are fixed in `labels/stable-shortfalls.json`), how many M covers and how many a
  fresh P covers. Descriptive: a fresh P will cover some by chance, which is why M is not compared with the old
  draws.
- **Size.** Words, R-n requirements and output tokens, M against P in the same round. Reported; a mean ratio of
  1.2 or more in words on a driver is named as a cost when the result is put to the owner.
- The whole checklist is reported with its registered band of 12 for context and decides nothing.

**Decision rule.** The cue is put to the owner as a proposed change to duty 2 only if R16 is shown on at least one
driver, is not worse on the other, and neither R17 nor R18 fails on either. If R16 is interim on a driver and
nothing fails, one more paired round is run (round 9) and the readings are taken over three rounds by the same
tests; that result stands. Anything else: no change is proposed, and the result is recorded as the answer to the
owner's to-do. Before a proposal goes to the owner it is reviewed by the latest Sol at maximum effort, as the
earlier block was. Nothing under `skills/` changes without the owner's word, and a change would need its packet
tests, a change note and an E2E round after it.

**What this cannot show.** Whether a built product is better: these are counts over a written specification. The
checklist and the earlier lenses share an author, and the reviewer whose wording the cue takes had read the
checklist. Two rounds are two draws an arm. The standalone frame has no repository, research result or selected
baseline, so the stage is read without what usually precedes it.

### Amended before round 7: the sets as sorted, the bands, and a second wording (2026-11-21)

Nothing had run for the check when this was added except the two sorting sessions, which see no specification.

**The sets** (`labels/opus.json`, `labels/astra.json`, `labels/sets.txt`). The sorters give the same `scope` label
to 82 of the 89 items and the same `kind` label to 74 (gpt-6.2-astra calls 37 items a set or a limit,
claude-opus-5-5 22; only what both call one is used).

| set | items | what they are |
| --- | --- | --- |
| X1, the target | 22 | 13 limits, 7 sets, 2 both; by category edge 7, nonfunctional 5, async 3, interaction 3, unhappy 3, platform 1 |
| X2, the other needed items | 53 | |
| X3, agreed beyond | 4 | a staff view of the waitlist with manual promote and remove; a switch to turn the waitlist off or on per class; turning reminders off per customer, previewing and resending by hand; cancelling a running import and retrying failed rows |

Both sorters call 74 items needed. Of the nine operator items they call four beyond, two needed in part and beyond
in part ("seeing failed requests is failure routing; the off switch and model switching are admin controls"), one
needed, and split on two.

**The bands** (`labels/bands.txt`): X1 2 (the four repeats moved it by 0, -1, +1 and 0), X2 7 (-7, 0, 0, +1), X3 2
(+1, -2, 0, 0), the whole checklist 6. X1's and X3's are the floor of 2.

**Saved rounds read by these sets** (`label.py split`; descriptive, since those rounds were run and read before
the sets existed). Covered on X1, registered judge / second judge:

| | Sonnet | Sol |
| --- | --- | --- |
| P, the released stage, rounds 5 and 6 | 14, 14 / 13, 14 | 6, 7 / 4, 6 |
| Q, the earlier block inside the stage | 17 / 15 | 7 / 8 |
| L, the lenses alone, one pass | 15 / 13 | 15 / 13 |
| F, the lenses alone, iterating | 18 / 16 | 16 / 15 |

On X3 the earlier block took the released stage from 0 of 4 to 3 on Sonnet (2 under the second judge) and from 1
to 2 on Sol (0 to 1).

Sol is where the room is: inside the stage it covers 6 or 7 of the 22, and with the lenses alone 15 or 16. Item by
item, Sol inside the stage leaves 13 of the 15 limits uncovered in both draws, and 12 of those 13 with the
earlier block, whose last sentence let a limit be "recorded as unresolved". Arm M's second sentence offers the
same way out.

**A second wording, arm `K-shiploop-spec-default-bounds`** (`arms/K-shiploop-spec-default-bounds.insert.txt`; 75
words; M's first sentence unchanged, its second replaced):

> Where one depends on a limit, state the bound and the behaviour at it: a platform limit from its source (item
> 10), and a limit the request leaves to choice as the best default, recorded as an assumption (RULES); a
> non-functional bound stays as item 6 has it.

It differs from M in one thing: a limit left to choice gets a recorded default where M records an open gap. That
is what the stage's own RULES say for an unattended run ("take the best default and record it as an assumption; a
person-only step is an open item") and what the owner's rule for unattended runs says (2026-09-27). The stage also
tells the session to mark a user decision as an open gap (duty 4); the two drivers resolve that differently, and
the arms differ in which one the cue points at.

**What changes in the check.** Rounds 7 and 8 run three arms (M, K and P) on both drivers: 24 sessions a round, 48
in all. Each cue arm is read against the P of its own round by R16 to R19 as registered, unchanged. Two things are
added:

- Four of X1's items are non-functional bounds, and the stage says "Invent no bound". For every such item a cue
  arm covers and P does not, what the specification says is quoted and read: a bound with no stated basis is a
  defect, not a gain, and is reported as one.
- Two cue arms are two chances to pass. If both are shown, the one with the larger mean on X1 under the registered
  judge is the candidate, M on a tie. That either passed by chance is one reason a proposal still needs the review
  and, after the owner's word, an E2E round.

The decision rule, the one permitted extension and everything else stand as registered above.

### Result of rounds 7 and 8 (2026-11-21)

48 sessions, all exit 0, after a passing pre-flight each round; the leak check found none in either round; both
judges read all 48 specifications (4 sets of 24 verdict files, none with a missing or unknown item).
`evidence/round-8/readings-M.txt`, `readings-K.txt`, `by-set.txt`.

Covered on the 22 target items, the cue arm against the released stage of the same round, round 7 then round 8:

| | Sonnet, registered judge | Sonnet, second judge | Sol, registered judge | Sol, second judge |
| --- | --- | --- | --- | --- |
| M | 13 v 13, 13 v 12: +0.5 | 11 v 12, 12 v 11: 0.0 | 8 v 7, 8 v 8: +0.5 | 5 v 6, 9 v 6: +1.0 |
| K | 17 v 13, 14 v 12: **+3.0** | 16 v 12, 13 v 11: **+3.0** | 14 v 7, 12 v 8: **+5.5** | 14 v 6, 11 v 6: **+6.5** |

- **R16.** M: nothing shown on either driver. K: **shown on both drivers** (the mean is at or above the band of 2
  and both rounds are above zero, under both judges).
- **R17, nothing lost.** Holds for both arms. K's other needed items are above the released stage's in every cell
  (+2.5 and +4.5 on Sonnet, +5.0 and +1.5 on Sol), inside the band of 7.
- **R18, no capability added.** Holds for both arms: K's means on the four items are 0.0 and 0.0 on Sonnet, +0.5
  and -0.5 on Sol. Read in the specifications, each movement is an exclusion scored one way or the other ("there
  is no cancel control", "No new roster or queue-management screen"), not a control
  (`evidence/round-8/K-capability-items-round-*.md`).
- **R19, the standing shortfalls.** K covers 7 and 5 of Sonnet's 24 where a fresh P covers 1 and 1; 14 and 14 of
  Sol's 42 where a fresh P covers 4 and 8.
- **Size.** K against P: words 1.03 on Sonnet and 1.17 on Sol (under the 1.2 that names a cost), requirements 1.05
  and 1.03, output tokens 1.26 and 1.19. M: 0.98 and 1.08 in words.
- **The whole checklist**, for context: K +4.5 and +8.5 on Sonnet, +10.5 and +9.0 on Sol.
- **The four non-functional bounds, read as registered** (`K-nonfunctional-bounds-round-*.md`). Where K covers one
  and P does not: reminders "at most 60 minutes late" resting on an assumed hourly run (A-4), and in the other
  round a count bound, "maximum reminders ever sent for one invoice = number of offsets"; a reply timeout of 30
  seconds on Sol in both rounds, a configured default inside the platform's 120; and one judge credit on a passage
  that states no bound. None is a performance target with no stated basis.

**Decision rule.** M: no change is proposed. K: R16 is shown on a driver and no harm reading fails, so the cue goes
forward: to the review at maximum effort first, then to the owner.

**What the counts do not say, read after them** (descriptive; the kinds are the sorters', the reading of passages
mine; `K-target-items-round-*.md`, `K-stable-target-items.md`):

- **Only the second sentence did anything.** By the sorters' kinds, covered in rounds 7 and 8 under the registered
  judge, Sonnet then Sol: on X1's 7 sets P 5, 4 and 4, 4; M 5, 5 and 5, 5; K 5, 5 and 4, 4. On its 13 limits P 7, 6
  and 3, 4; M 7, 6 and 3, 3; K 11, 8 and 9, 7. The two sets the released stage leaves unsettled in every draw
  (every condition that stops a reminder sequence; an existing do-not-contact state) stay unsettled under both
  cues in every round under both judges.
- **What K's gain consists of.** Of the 20 times K covered a target item that the P of its round did not (registered
  judge, both drivers, both rounds; 3 went the other way): 12 are a default for a limit the released stage also
  says exists and leaves without a value (the import's size and row limits in all four cells, the prompt's maximum
  length, the reply timeout, the reminder run and schedule); 3 are a cap on the waitlist that the request did not
  mention (10, 10 and 20), where the released stage wrote "Assumed none", "No bound is invented ... Treated as
  unbounded", or left capacity unresolved; 2 are platform limits given their numbers; 1 is a set's members named;
  2 are no difference in substance.
- **The defaults are recorded as the cue asks and differ between draws.** "A-4 | Limits: file at most 1,048,576
  bytes (1 MiB); at most 1,000 data rows ... These are product defaults chosen for an admin-sized batch, not
  platform limits; platform limits are gap G-3." The other three K specifications of that request chose 2 MiB and
  5,000 rows, 256 KiB and 500, and 1 MiB and 1,000.
- **Steady in both rounds:** three items a driver are covered by K in both rounds and by P in neither (the
  import's limits on both; the waitlist cap and the reminder bound on Sonnet; the prompt's length and the reply
  timeout on Sol), two of each three the same under the second judge. M has none.

**Predictions held against it** (journal section 20): M moves Sol's X1 by less than 2: held (+0.5, +1.0). M moves
Sonnet's by 1 to 3: not held (+0.5, 0.0). K moves Sol's by 4 or more: held (+5.5, +6.5). Neither moves X3: held.
