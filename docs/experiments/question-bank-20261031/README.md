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

## QB3: do terse answers cut the cost, and is the saving the bank's or the cap's? (registered after QB1's token counts, before any judge result)

**Order of events, stated so the reader can weigh it.** QB1's 160 subject calls finished and their token counts were read
(from the envelopes' usage; no judge involved) before QB3 was designed. No judge call, of QB1 or of QB3, had returned when
this section was committed. QB1's judge calls are unchanged (six arms) and do not include Qt or Bt.

**Why.** QB1's R3 asks a fixed bank to cut output tokens to 0.75 of the shipped ledger's or less. The token counts already
show the full-sentence bank misses that clause. Mean output tokens per run, 32 runs per arm (reasoning tokens; uncached input
tokens): A 636 (242; 3,102), B 2,153 (448; 3,336), Bq 2,160 (431; 3,367), Bs 2,170 (389; 3,366), Qb 1,854 (372; 3,306), Sb
1,995 (442; 3,316). So Qb is 0.86 of B and Sb 0.93, against a ceiling of 1,615 for 0.75; and the ledger's wording changes
nothing (Bq and Bs are within 1% of B). Where the tokens go: the bank's 20 answers average 24 words (median 22; 93% are over
12 words), the ledger's `default` field 22 words and its `question` 15, and the `summary` every arm writes 200 to 270 words.
The saving left is answer length, and a cap on it is the cheapest test of the owner's "lower token expense". The surveyed
literature points the same way but is outside this repository's measure (Ghosh et al., arXiv 2605.20149: a checklist prompt
used fewer tokens than a raw or a clarifying-question prompt; Goel et al., arXiv 2610.37830: a fixed checklist answered first,
on smart contracts).

**Arms.** **Qt:** Qb plus one sentence, "Keep each `answer` to 12 words or fewer." **Bt:** B plus one sentence, "Keep every
field of a row to 12 words or fewer." Bt is the control: without it, a saving of Qt over B could be the cap's, not the bank's.
4 cases and samples 1 to 4 give 16 runs per arm (`jobs-qb3.tsv`, 32 subject calls). `qb3.py build` makes the prompts from
QB1's and checks each differs from its base by the one sentence.

**Judge.** Per case and sample pair (samples 1-2 and 3-4), the eight outputs of B, Qb, Qt and Bt, shuffled with the seed
`qb3-<case>-<pair>`, X1's judge text, Opus, quotes checked by script (`judge3/`). B and Qb are QB1's own samples 1-4, so each
comparison is graded in one call.

**Rules** (decided now; the tests are QB1's, on 16 runs per arm, tokens to the nearest 10):
- **R6, the cap cuts the bank's cost (Qt against Qb):** output tokens at most 0.80 of Qb's with p < 0.05, recall at least
  recall(Qb) - 0.03, default agreement at least agreement(Qb) - 0.02, and noise share at most noise share(Qb) + 0.05.
- **R7, the bank against the ledger at equal terseness (Qt against Bt):** output tokens at most 0.85 of Bt's with p < 0.05
  and recall at least recall(Bt) - 0.03. If it fails, the saving belongs to the cap, not to the bank.
- **R8, replacing B in intake item 9:** Qt, and separately Bt, replaces B only if recall is at least recall(B) - 0.03, output
  tokens at most 0.75 of B's, agreement at least agreement(B) - 0.02 and noise share at most noise share(B) + 0.05. If both
  hold, Bt is the smaller change (B plus one sentence) and is preferred unless R7 holds.

**Cannot settle:** everything QB1 cannot; the cap is one number (12 words) read off the lengths above, not tuned; 16 runs per
arm cannot separate differences of a few points of recall; a shorter answer may carry less for the next stage (the spec),
which nothing here measures.

## QB4: what an attended intake sends to a person (exploratory; registered before its first call; no judge)

**Why.** QB2's frame is unattended, so its outputs contain no person routes (0 of 340 item grades). The owner's other half of the
question is: when something conflicts or is ambiguous, derive the answer from the environment or ask the person. QB4 gives arms Bp
and Qp a person who can answer one short batch of questions, with a rule to route an item to that person only when the repository
and the skills cannot settle it and two readings lead to different work, and then reads which rows go to the person.

**Setup.** QB2's prompts with two sentences changed (the frame sentence and the RULES bullet; `qb4.py` asserts nothing else
differs), the same request, workspace, tools and subject (Terra xhigh), 4 outputs per arm, 8 calls (`jobs-qb4.tsv`). No judge: the
person-routed rows (`route` person in the ledger, `basis` person in the bank) are read directly and classified by hand against QB2's
items into those a decision settles (J5 OldTracker, C1 right away against batch, O1 the bulk contract, N1 the performance bound, the
missing cap of J4, the missing window of R2) and those the repository, the skills list or general knowledge settles (a wasted ask).

**Predictions** (to be scored against, not rules): at least 2 of 3 person-routed rows concern items a decision settles; fewer than 1
wasted ask per output; Qp sends more rows to the person than Bp, since its bank puts a question on every K12 and K13 item.

**Cannot settle:** 4 outputs per arm; the classification is by hand; the rule text in the frame is mine; a real person's answers
are not simulated, so what happens after the question is not shown.

## Results

### QB2 (exploratory; 20 outputs, 340 item grades, 0 unverified judge quotes; `scores-qb2.json`, `qb2/judge/`)

Per arm, 5 outputs each (`python3 qb2.py score`). "Right" is the judge's correct = yes; "silent" is an assertion made without
evidence or a flag; "commands" are shell commands the model ran.

| Arm | covered | right | partial | wrong | silent per output | person per output | output tokens | uncached input | commands | items | noise |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B (as shipped) | 1.00 | 0.56 | 0.44 | 0 | 1.60 | 0 | 3,676 | 29,688 | 7.6 | 15.4 | 2.6 |
| Bp (B + K12, K13, look-up line) | 1.00 | 0.73 | 0.27 | 0 | 0.40 | 0 | 4,122 | 32,830 | 9.8 | 16.6 | 3.0 |
| Qp (bank of 27 questions + line) | 1.00 | 0.74 | 0.26 | 0 | 0.00 | 0 | 4,298 | 33,228 | 11.0 | 17.6 | 3.8 |
| Sp (the same as statements) | 1.00 | 0.80 | 0.20 | 0 | 0.00 | 0 | 4,331 | 34,989 | 13.6 | 18.0 | 3.8 |

Share of each group's items answered right (B, Bp, Qp, Sp): installed skills 0.33, 0.93, 0.73, 0.93; slang 0.90, 0.90, 0.80, 1.00;
the unknown name OldTracker 0.00, 0.40, 0.80, 0.60; references 0.33, 0.33, 0.40, 0.33; conflicts 1.00 in every arm; constraints 0.80,
0.80, 0.87, 0.87; open decisions 0.20, 0.50, 0.60, 0.80. Route mix over 85 item grades per arm (environment, knowledge, default,
person, silent): B 22, 16, 39, 0, 8; Bp 36, 10, 37, 0, 2; Qp 43, 10, 32, 0, 0; Sp 45, 10, 30, 0, 0.

Exploratory exact one-sided permutation tests on each output's share of 17 items right (5 against 5): Bp over B +0.164, p 0.004
(every Bp output above every B output); Qp over B +0.174, p 0.012; Sp over B +0.230, p 0.004; Sp over Bp +0.066, p 0.024; Qp over Bp
+0.010, p 0.496; Sp over Qp +0.056, p 0.115. Silent assertions, B against Qp: 1.6 against 0.0, p 0.024; B against Bp: p 0.111.

Predictions, scored: **P1 false** (the conflict items, the filter drift included, and the false "usual window" were right in all
five outputs of every arm, B too). **P2 holds for Bp and Sp, not for B** (until-loop right in 2 of 5 outputs, back-chain 1 of 5,
ralph-style 2 of 5) **or Qp** (ralph-style 1 of 5). **P3 false** (Qp and Sp write more than Bp, 4,298 and 4,331 against 4,122
output tokens). **P4 true but empty** (no arm sent anything to a person; the frame is unattended, so QB2 cannot show when an
intake should ask). **P5 true** (9.8, 11.0 and 13.6 commands against 7.6).

Reactions worth reading, from the judge's verified quotes. Given the same list of installed skills, B understood "until loop"
from general knowledge ("an until loop whose exit requires green tests and evidence against a running server", graded partial)
and tied it to nothing; Bp, Qp and Sp tied it to the host's skill (graded right, route environment). For OldTracker, B and Bp
called it context, not scope, without saying that nothing defines it (graded silent and partial); Qp wrote that its identity
does not change this work; Sp wrote that it and the timing terms are not defined in the repository. All four arms pointed to the
existing resolved-ticket template and outbox for "the same kind of heads-up", and none said that no template exists for closed
tickets (R1 right in 0 of 20 outputs) or that the outbox key suppresses an identical notification only while it is still pending
(R3, 1 of 20); none connected "snappy" to the data file being saved on every change (N1 partial in every arm). What the files
show about the cost of the requested change was missed by every wording.

Limits: one request, one repository, one judge, five outputs per arm; coverage is at its ceiling, so only correctness separates
the arms; intake read the repository, which the real stage leaves to discovery; the person route and the web search were not
exercisable; the judge's expected-handling text was written by the session that built the arms.

(QB1 and QB3 results are appended below when their judge calls return.)
