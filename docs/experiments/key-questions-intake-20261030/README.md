# Pilot X1: key questions at intake (2026-10-30)

Exploratory pilot for [docs/shiploop-planning-pipeline-2026-10-30.md](../../shiploop-planning-pipeline-2026-10-30.md)
§9.1; journal entry E2 in [docs/shiploop-question-driven-planning-journal.md](../../shiploop-question-driven-planning-journal.md).

**Question.** On an underspecified request, does asking ShipLoop's intake for key questions surface more of the
decisions the user's real request pins, and at what cost? Does a fixed category catalog add to a free-form ask?

**Cases** (`cases.json`). Four E2E cases from `test/shiploop_e2e/cases.json` (battleship, csv-report,
seat-reservations, user-listing), each reduced to a one- or two-sentence request a user might type. The ground truth
is every decision the full case prompt pins that the short one leaves open (9–10 per case, 38 in all), with the full
prompt's choice as the reference. The E2E checks read only full-prompt sentences, so each decision is one the
product is judged on.

**Arms** (`build.py`, `prompts/`). Identical frames; the only difference is duty item 9 and the template fields.
- A: ShipLoop's intake duty as shipped (`shiploop_prompts.duty("intake")` on main `d47d69d4`), template `summary`.
- B: A + item 9 "Key questions" with the K1–K11 category catalog (applies or not, with a reason) and a `questions`
  ledger: id, category, question, changes, route (inspect, research, experiment, default, person), default, blocks.
- C: A + the same item 9 and ledger without the catalog.

**Subject.** Claude Sonnet 5.5 (`claude-sonnet-5-5`, served model verified), effort xhigh, through the `ask` runner
(subscription Claude Code CLI, one fresh headless session per call, run from an empty directory, no tools needed).
Two samples per case and arm: 24 calls, plus one smoke call (`battleship-B-s0`, excluded from scoring).

**Judge** (`judge_build.py`, `judge/`). Claude Opus (`ask opus`), one call per case. It sees the full and the short
request, the decisions with their references, and the six outputs shuffled and relabelled O1–O6 (`judge/mapping.json`
keeps the arm map; seed `x1-<case>`). Per output and decision: covered, a verbatim quote, and whether a committed
default matches the full request; per output: items raised and how many are noise.

**Scoring** (`score.py`). A decision counts as covered only when the judge's quote is found in that output's text
(normalized to lower-case alphanumerics). Recall = covered / decisions. Exact two-sided permutation p over the eight
samples per arm (optimistic: two samples share each case).

**Reproduce.** `python3 build.py <skill-craft>/skills/shiploop/scripts`; `./run_one.sh CASE ARM SAMPLE` per job
(`jobs.txt`); `python3 judge_build.py 1,2`; `./run_judge.sh CASE`; `python3 score.py`.

## Result (2026-10-30; exploratory: n = 2 per case and arm, one subject, one judge)

All 24 subject calls returned a parseable result; all 4 judge calls returned JSON; every judge quote was found in its
output (0 unverified). From `python3 score.py` (`scores.json`):

| Arm | Recall of omitted decisions | Decisions with a committed default | Defaults matching the full request | Items raised | Judged noise | Output chars | Seconds |
|---|---|---|---|---|---|---|---|
| A (shipped intake) | 0.932 (71 of 76) | 66 of 76 | 0.77 | 14.5 | 3.9 (27%) | 7,214 | 70 |
| B (catalog + ledger) | 1.000 (76 of 76) | 76 of 76 | 0.64 | 14.6 | 3.0 (21%) | 16,662 | 139 |
| C (free-form ledger) | 0.986 (75 of 76) | 72 of 76 | 0.74 | 10.8 | 2.5 (23%) | 12,427 | 106 |

- Per case (A / B / C): battleship 0.944 / 1.000 / 0.944; csv-report 1.000 all; seat-reservations 0.950 / 1.000 /
  1.000; user-listing 0.833 / 1.000 / 1.000.
- Missed: A missed BS8 (rules in a module) once, SR2 (port) once, UL4 (one-parameter defaults) once and UL5 (a page
  past the last) twice; B missed none; C missed BS8 once.
- Exact permutation p (eight samples per arm treated as independent, so optimistic): B vs A +0.068, p = 0.077; C vs A
  +0.054, p = 0.231; B vs C +0.014, p = 1.0.
- Conflicting defaults concentrate in interface contracts the short request cannot settle (endpoint and field names,
  output format, exit codes, pagination parameters). B commits a default for every decision, so it commits more
  guesses that differ from the user's real request (3.4 per run, against 1.9 for A and 2.4 for C).
- A's judged noise is mostly the intake duty's own boundary statements on a request that has none (authority limits,
  "nothing is hidden", interaction-state blocks for a command-line tool).
- Routes in B and C: on the brownfield case most questions went to `inspect` before any default (B 31 inspect, 78
  default, 5 experiment; C 23 inspect, 40 default, 2 person, 1 research, 1 experiment over all cases).

**Reading.** On a strong subject the shipped intake already raises most of what a vague request leaves open (93%), so
asking for key questions adds little coverage (+5 to +7 points, inside small-n noise) and costs 1.5x (C) to 2x (B) the
intake's time. The category catalog adds nothing over a free-form ask on coverage, costs about 30% more, and commits
to more intent guesses. What the pilot does not test: a weaker subject (the E2E default, DeepSeek flash, was at its
monthly limit), whether a structured, numbered ledger is consumed better downstream (X2), and real repositories.
