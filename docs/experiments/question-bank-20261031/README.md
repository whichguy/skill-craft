# QB1: a fixed question bank against statement wording at intake (2026-10-31)

Consumer: the owner, who asked whether questions can flesh out a request in more detail, and at lower token cost, than
statements about how to clarify it, and whether a question bank should replace those statements; later, a session that
changes intake duty item 9, which reads the rules and the Results below to see what a change must beat.
Follows: X1 ([../key-questions-intake-20261030/README.md](../key-questions-intake-20261030/README.md)) and X1-T
([../question-record-20261031/README.md](../question-record-20261031/README.md)), which measured ShipLoop's statements
(arm A) against the K1-K11 catalog with a question ledger (arm B), and
[docs/shiploop-question-record-verdicts-and-plan-2026-10-31.md](../../shiploop-question-record-verdicts-and-plan-2026-10-31.md).

The owner, 2026-10-31: "whether questions, given a prompt, could actually cause a prompt to get more flushed out in
detail and actually have a lower token expense. I'm kind of curious if there's a question bank that we should use rather
than using statements about how to clarify a prompt", and "We're going to use Codex as the harness and Terra 6.1 Extra
High as the model."

This file was written and committed **before** any scored subject or judge call. Two smoke calls (below) checked the
routes and are not scored. The rules are never edited; results are appended under "Results".

## What is already known (so this experiment adds, and does not repeat)

- X1-T, Terra 6.1 at xhigh, four vague requests, 38 decisions (the choices the full request pins that the vague one
  leaves open), 16 runs per arm. **Recall** is the share of those decisions an output raises as a question, records a
  default for, or states as a boundary, graded blind by Opus with a quote that a script finds in the output.
  Arm A (the shipped statements, before the catalog): recall 0.513, 656 output tokens (268 of them reasoning), 2,019
  characters. Arm B (catalog and ledger, now intake duty item 9, shipped in ShipLoop 1.25.0): recall 0.981, 2,175 output
  tokens (492 reasoning), 7,707 characters. Arm C (ledger without catalog): 0.681, 1,239 tokens. Raising effort from high
  to xhigh moved A by 2 points. Reproduce the token table with `python3 x1t_tokens.py` (output in `x1t-tokens.txt`).
- B's catalog words three of its eleven lines as questions (K1, K2 and K11 end in a question mark) and the other eight
  as noun phrases or embedded clauses (K3-K10), and its mechanism has the model **write the questions itself** (`questions` rows: id, category, question, changes, route,
  default, blocks). Nobody has tested the same content worded as questions against statements, or a fixed list of
  questions the model only answers, in this repository or, as far as the graded literature report finds
  ([../key-questions-intake-20261030/question-evidence.md](../key-questions-intake-20261030/question-evidence.md)), outside it.
- Reasoning effort is not the lever at intake (X1-T); a route sentence moves runtime questions toward `experiment` but
  misses its bar (XR, f616aaea); research probes ran in 1 of 6 runs and were not adopted (XI, 2ae6200e).

## Questions

- **Mechanism.** Does a fixed bank the model answers by id cover as many of a vague request's open decisions as the
  generated ledger B, at fewer output tokens?
- **Form.** With the content held identical, does question wording cover more, or cost fewer tokens, than statement
  wording? Asked of the fixed bank (Qb against Sb) and of the shipped mechanism (Bq against Bs).

## Subject, judge and cases

- **Subject: Codex `gpt-6.1-terra` at `model_reasoning_effort=xhigh`** ("Terra 6.1 Extra High", the owner today). Called
  as X1-T called it (`run.py`): `codex exec --json --ephemeral --ignore-user-config --skip-git-repo-check -s read-only`,
  a throwaway `CODEX_HOME` per call that links only `auth.json`, stdin closed, an empty directory outside any repository.
  No tools or files in the exercise (X1's frame: "answer from the request alone"); `turn.completed`'s usage is kept.
- **Judge: Claude Opus** (`ask opus`, the runner's default profile; the smoke call served `claude-opus-5-5`, verified),
  X1's judge text unchanged, one call per case and sample pair holding the twelve outputs of all six arms, shuffled with
  the seed `qb1-<case>-<pair>` and relabelled O1..O12, arms hidden. A decision counts only if the judge's quote is found
  in that output (X1's `norm`). Every arm of a comparison is graded in the same call, because X2b found a judge's
  calibration moved 1.3 points between batches.
- **Cases:** X1's four (battleship, csv-report, seat-reservations, user-listing), 38 decisions. The full prompts the
  judge reads as the reference are unchanged since X1-T judged (checked against 8e5d6f47).
- **Samples:** 8 per case and arm, 32 per arm. A and B samples 1-4 are X1-T's own xhigh outputs, reused where they are;
  samples 5-8 of A and B and all samples of the four new arms are new (160 subject calls, `jobs.tsv`), run 5 at a time.

## Arms

| Arm | Intake duty item 9 | Who writes the questions | Wording of the K lines or bank |
|---|---|---|---|
| A | none (X1's shipped intake before the catalog) | n/a | n/a |
| B | the K1-K11 catalog and a question ledger, as shipped | the model | mixed: 3 lines end in a question mark, 8 do not |
| Bq | as B | the model | all eleven lines as questions |
| Bs | as B | the model | all eleven lines as imperative statements |
| Qb | a fixed bank of 20 questions, answered in `answers` rows (`id`, `basis`, `answer`) | the bank | questions |
| Sb | the same 20 items as imperative statements, answered the same way | the bank | statements |

`bank.py` holds the bank: each of the 20 items is one clause of the catalog (K1.1, K1.2, ... K11.2), worded twice, so no
item asks for anything the catalog does not. `basis` is the request sentence that settles the item (S1, S2), or inspect,
research, experiment, default, person (B's five routes) or na (the answer would change nothing built, checked or
delivered). `build.py` builds the prompts from X1's committed prompts for A and B and checks that each new prompt equals
its base byte for byte once its edit is undone. Prompt size in characters (mean of four cases): A 3,468; B 6,082; Qb
5,727; Sb 5,762; Bq 6,190; Bs 6,183. The only difference between Qb and Sb is the wording of the item and of the three
words that name it ("question" or "item", "answer" or "settle").

## Measures

Per run, by script except the judge's coverage grade (whose quotes a script checks):

- **recall**, **agreement** (committed defaults that agree with the full request, over agree plus conflict, pooled) and
  **noise share** (the judge's count of items that would change nothing built, checked or delivered, over all items);
- **output tokens** (Codex `usage.output_tokens`, which includes reasoning), reasoning tokens, uncached input tokens
  (input minus cached), characters, seconds;
- rows written, their basis or route mix, and **person** (rows left to a person, which an unattended run records as
  defaults);
- **covered decisions per 1,000 output tokens** (pooled).

## Rules (decided now)

Tests are the harness's exact one-sided permutation test (`stats.permutation_p`, the `decide` rule since a9e398e9) on the
per-run values, with p < 0.05 for a gain. At 32 runs per arm the exact test is intractable at full precision, so recall is
tested rounded to two decimals and output tokens to the nearest 10; `check_coarse.py` shows that leaves X1-T's p-values
unchanged (largest change 0.00006).

1. **R1, form in the fixed bank (Qb against Sb).** *Coverage:* question wording raises coverage if recall(Qb) - recall(Sb)
   is 0.05 or more with p < 0.05; statement wording raises it if the gap is 0.05 or more the other way with p < 0.05;
   otherwise no difference of 5 points. *Cost:* question wording is cheaper if mean output tokens(Qb) is at most 0.85 of
   Sb's with p < 0.05, statement wording likewise the other way; otherwise no difference of 15%.
2. **R2, form in the generated ledger (Bq against Bs).** The same two readings.
3. **R3, mechanism.** Let X be whichever of Qb and Sb has the higher mean recall (a tie within 0.005 goes to the one with
   fewer output tokens). The fixed bank replaces the generated ledger in intake item 9 only if all four hold against B:
   recall(X) is at least recall(B) - 0.03; output tokens(X) are at most 0.75 of B's; default agreement(X) is at least
   agreement(B) - 0.02; noise share(X) is at most noise share(B) + 0.05. Otherwise B stays as shipped. (B is live in
   1.25.0 and held up in the live A/B, so a replacement must keep what it did and cut the cost.)
4. **R4, the anchors replicate.** A's and B's recall are each within 0.05 of X1-T's xhigh (0.513 and 0.981). If not, the
   subject or the judge has drifted and every comparison is read with that flagged.
5. **R5, a ceiling.** If every arm's recall is 0.95 or more, coverage cannot separate the arms, and the verdict rests on
   cost (R3's token clause) and on the harder test QB2.

**Exploratory, not decision-bearing:** which bank rows carry the coverage (the judge's quotes located in the rows, then
the smallest set of rows that reaches 95% of Qb's recall); the basis and route mix; a reading of two outputs per arm.

## What this cannot settle

No tools and an empty repository (X1's frame), so `inspect` and `experiment` routes cannot be exercised; four requests,
38 decisions, one subject, one judge. No downstream test: that a bank's answers reach the spec as the ledger's do (X2b:
carried 0.776 to 0.897) is unmeasured. The bank was written after X1's catalog and ground truth were read; content parity
with the catalog by construction (each clause once) is the guard. **QB2**, a long loosely worded request in a real
workspace with skill names and community jargon in it, scored by script, is planned next; its rules go into this file in
a commit of their own before its first scored call.

## Smoke calls (not scored), 2026-10-31

- Terra: `gpt-6.1-terra` at xhigh answered "Reply with the single word PONG." in 3.4 s through `run.py`'s `call_codex`
  (6 output tokens; 14,010 input of which 12,032 cached: the Codex harness itself is about 14k tokens).
- Opus: `ask.sh opus --json` answered the same in 8 s; envelope `served_model` `claude-opus-5-5`, `model_verification`
  verified, profile `agent`.

## Reproduce

```
python3 build.py && python3 jobs.py
QB_WORK=<scratch> python3 run.py jobs.tsv --limit=codex=5
python3 judge.py && QB_WORK=<scratch> python3 run.py jobs-judge.tsv --limit=opus=4
python3 score.py
```

Codex event streams and stderr are not committed; each envelope keeps the call's token usage.

## QB2: a long, loosely worded request, with the tools on (exploratory; registered before its first scored call)

The owner asked to take a big prompt and see what behaviours different wordings of the intake guidance draw out, and said
mid-task that their prompts lean on installed skills and internet jargon, which should be looked up before anyone is asked
(memory `resolve-user-jargon-before-asking`). QB1 can show neither: its requests are one or two sentences, there is no
repository to read and no skill list. QB2 is a descriptive probe, not a decision: five outputs per arm on one request cannot
carry an adoption rule.

**The request** (`qb2_case.py`: 13 sentences, 281 words) is written in the owner's dictated style over the help desk
fixture (`test/shiploop_e2e/fixtures/node-tickets`, copied to a scratch directory outside any repository so that no
instruction file loads). It names the installed skills `until-loop`, `backchain` and `ralph-loop` (the last as
"ralph-style"); uses the slang "vibes" and "slop"; names "OldTracker", which appears nowhere; points at "the same kind of
heads-up as when it's resolved" and "the usual window ... for the weekly report" (the report has no window); says "right
away" and "batch it", "idempotent" and "409 if already closed"; claims the filters "work together, the way the docs say" (the
docs say so; the code lists a ticket when any filter matches); and asks for a bulk call that has no contract.

**Items:** 17 (J1-J6 terms, R1-R3 references, C1-C3 conflicts, B1, D1, A1 constraints, O1, N1 open decisions;
`qb2_case.py`), each with what a good intake does about it and whether the repository, the skills list or general knowledge
settles it (14 "env") or only a decision does (3). The repository facts given to the judge were read from the fixture on
2026-10-31; the absences (OldTracker, a report window, a bulk endpoint) were searched recursively.

**Subject and judge:** as QB1 (Terra 6.1 xhigh through Codex; Opus judge, blind, shuffled, quotes checked by script) but the
working directory is a copy of the fixture, the shell is read-only, and the model is told to change nothing and start no
server. One judge call per sample index holds the four arms' outputs. ShipLoop's real intake leaves repository facts to the
next stage (discovery); QB2 lets intake read, so that what each wording would settle from the environment is visible.

**Arms** (X1's frame, the host's skill list added to the packet; prompts in `qb2/prompts/`): **B**, item 9 as shipped (K1-K11);
**Bp**, B plus catalog lines K12 (terms and references) and K13 (conflicts and premises) and one look-it-up-first line (the
installed skills, then the repository and its documents, then a search; record the best reading and its confidence as the
default; `person` only when two readings remain that lead to different work); **Qp**, a fixed bank of QB1's 20 questions plus 7
for K12 and K13, answered by id, with the same line; **Sp**, the same bank as statements. 5 samples per arm: 20 calls
(`jobs-qb2.tsv`).

**Measures**, per output, from the judge's grades (quotes verified by script): coverage of the 17 items; correct (yes, partial,
no); route (environment, knowledge, default, person, silent); wasted person routes (an item sent to a person that the
repository, the skills list or general knowledge settles); silent assertions; shell commands run; output tokens; uncached
input tokens; items and noise.

**Predictions** (to be scored against, not rules):
- P1. B covers the conflict and false-premise items (C1-C3, R2) and J5 less often than Bp, Qp and Sp, because nothing in its
  text asks for them.
- P2. Every arm settles the three skill-named items (J1, J2, J4) from the host's list in at least 4 of 5 outputs, since the
  packet lists them.
- P3. Qp and Sp write fewer output tokens than Bp.
- P4. No arm routes more than one environment-settled item per output to a person.
- P5. Arms with the look-it-up-first line run more shell commands than B.

**Cannot settle:** one request, one repository, one judge, five outputs per arm; intake reads the repository, which the real
stage does not; no web search tool, so the `research` route cannot be exercised (a term only a search settles can only be
read from the model's own knowledge); the unknown term (OldTracker) tests flagging, not lookup.

**Smoke call (not scored), 2026-10-31:** one Bp output on this request, run through `run.py`'s `call_codex` with the
workspace as the working directory: 43.1 s, 6 shell commands (it read the decision records, README, docs/api.md, the weekly
report, package.json and the app, store, query, notifier, worker, audit, outbox and template sources, and searched the
repository for `OldTracker`, `window`, `bulk` and `retry`), 3,904 output tokens (340 reasoning), 25,912 uncached input tokens,
a fenced result with all 13 categories and 17 questions routed `inspect` or `default` (none to a person). The route works.
`run.py` gained an optional fourth jobs column (the working directory) and a `commands` list in the envelope after the QB1
pre-registration commit; QB1's calls do not use either.

**Reproduce:** `python3 qb2.py build && python3 qb2.py jobs`; `QB_WORK=<scratch> python3 run.py jobs-qb2.tsv --limit=codex=4`;
`python3 qb2.py judge`; `QB_WORK=<scratch> python3 run.py jobs-judge-qb2.tsv --limit=opus=4`; `python3 qb2.py score`.

## Results

(appended after the runs)
