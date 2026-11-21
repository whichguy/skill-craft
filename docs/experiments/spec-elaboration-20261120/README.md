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

## Drivers

The owner named both: **the latest Sonnet at effort high** and **GPT-6.2 Sol at reasoning effort medium**. Every
subject call runs headless in its own empty directory outside any repository, with the host's own customizations
off — `claude -p --safe-mode` (no CLAUDE.md, skills, plugins, hooks, MCP, commands or agents; verified on the
smoke call: no plugin command reached the session and no hook fired) and `codex exec --ignore-user-config` in a
throwaway `CODEX_HOME` that links only `auth.json`. Each call writes `spec.md` (and `passes.md` for B) and nothing
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
