# QB5: confirming the terms-and-references line on requests QB2 was not designed on (2026-10-31)

Consumer: the owner, who must decide whether intake item 9 gets a terms-and-references line; later, a session that makes that change,
which reads the rules and the Results below to see whether the evidence cleared the bar. Follows the question-bank study
([../question-bank-20261031/README.md](../question-bank-20261031/README.md), journal
[docs/shiploop-intake-question-bank-journal.md](../../shiploop-intake-question-bank-journal.md) §8, decision D2), which found in QB2 that adding a
terms-and-references catalog line and a look-it-up-first sentence to the shipped intake raised the share of items answered right from
0.56 to 0.73-0.80 on one request, five outputs per arm, and called for a pre-registered confirmation on more requests before anything
ships.

The owner, 2026-10-31, answering the question "run the pre-registered confirmation of the terms line on more requests, then a live A/B,
before it can ship?" with "Do this for me". This file covers the first half, the exercise-level confirmation. The live A/B and any change
under `skills/` wait for its result and are not part of it.

This file was written and committed **before** any scored subject or judge call. Three smoke calls (below) checked the routes and are not
scored. The rules are never edited; results are appended under "Results".

## What is already known

QB2 (one 281-word dictated request over the help desk fixture, 17 items, 5 outputs per arm, Terra 6.1 xhigh, Opus judge): items right per
output B 0.56, B plus K12, K13 and the sentence 0.73 (exact p 0.004), silent assertions 1.6 against 0.4 per output, installed skills
right 0.33 against 0.93, an unknown name right 0.00 against 0.40, output tokens 3,676 against 4,122. The conflicts line (K13) added
nothing, because B already found the conflicts. QB2 had one request, one repository and a rubric written by the session that built the
arms, and cannot say whether the gain is the K12 line or the sentence.

## Question

Does adding the K12 line and the look-it-up-first sentence to the shipped intake resolve more of a long, loosely worded request on three
requests and three repositories it was not designed on, at modest cost; and is the gain the line, the sentence, or both?

## Design

- **Requests.** Three dictated-style requests (`cases.py`), 10 to 11 sentences each, over three fixtures of `test/shiploop_e2e/fixtures`
  other than the help desk: `node-base` (a user store and HTTP server: add and remove users), `node-orders` (a work meter with a hard
  limit: let batch jobs run past it) and `node-records` (a text helper: squash null, undefined and whole records). Each names installed
  skills QB2 did not use (improve, in-parallel, code-review, schedule, loop, simplify, ask), slang (yolo, boring, footgun, bikeshed,
  dogfood, rubber-duck, cursed regexes), an unknown name (Kestrel, Heron, the Orchard style guide), phrases that point at things the
  request does not state ("the usual page size", "the usual port", "the usual five thousand tick limit", "the old trim helper", "the way
  it does now"), claims the code contradicts (a paginator that "handles a short last page properly": it floors the page count and drops
  the last partial page; a limit of five thousand: it is 10,000; a reset "the way it does now": nothing resets automatically; a helper
  that "the old trim helper did": none exists), conflicts, constraints and open decisions.
- **Items.** 14 + 14 + 13 = 41 (`cases.py`), each with the part of the request it concerns and what a good intake does about it, written
  before any output existed. The repository facts given to the judge were read from the fixtures on 2026-10-31; the absences were searched.
- **Arms** (X1's exercise frame with the tools on and the host's twelve-skill list in the packet, as in QB2; prompts in `prompts/`):
  **B** item 9 as shipped; **Bk** B plus the catalog line K12 (terms and references) and the look-it-up-first sentence; **Bk12** B plus the K12
  line only; **Bsen** B plus the sentence only. Their wording is QB2's, minus K13, which QB2 showed to be unneeded.
- **Samples.** 5 per request and arm: 60 intake calls (`jobs.tsv`), Terra 6.1 (`gpt-6.1-terra`) at xhigh through Codex, isolated as in
  QB1 to QB4, the fixture copy as the working directory, read-only shell.
- **Judge.** Claude Opus (`ask opus`), one call per request and sample index holding the four arms' outputs, blind and shuffled with the
  seed `qb5-<request>-<sample>`, QB2's judge text, quotes checked by script (15 calls, `judge/`).
- **Measures** (per output, from the judge's grades whose quotes a script verified): the **share of the request's items answered right**
  (correct = yes), coverage, partial and wrong shares, **silent assertions** (an assertion made without evidence or a flag), rows routed to a
  person, shell commands run, output tokens, uncached input tokens, items raised and noise.

## Rules (decided now)

Tests are the harness's exact one-sided permutation test (`stats.permutation_p`) on each output's share right, rounded to two decimals,
15 outputs against 15.

1. **C1, resolution:** Bk raises the mean share of items right over B by 0.10 or more, with p < 0.05.
2. **C2, consistency:** Bk's mean share right is above B's in every one of the three requests.
3. **C3, silent assertions:** Bk has fewer silent assertions per output than B, with p < 0.05.
4. **C4, cost:** Bk writes at most 1.25 times B's mean output tokens.

If C1 to C4 all hold, the terms line is **confirmed on the exercise**; the next steps are the owner's: a change note, the shape check of the
ledger extended from K1-K11 to K12, and a live A/B like the one that shipped the ledger. If C1 and C2 hold and C4 fails, the cost goes to the
owner as a trade-off. If C1 or C2 fails, the QB2 gain does not generalise and item 9 stays as shipped. **Components (exploratory, no rule):**
Bk12 and Bsen against B and against Bk with the same test, to see whether the line, the sentence or both carry the gain.

**Predictions** (to be scored against, not rules): P1 the gain sits in the installed-skill and unknown-name items (B at 0.5 or less on
skills, Bk at 0.8 or more); P2 the unknown-name items go from 0.2 or less to 0.5 or more; P3 the referent items that are false premises
(no default page size, a limit of 10,000 not 5,000, no trim helper) are found about equally by every arm, as in QB2; P4 conflict items do not
differ; P5 the sentence alone (Bsen) carries most of the skill gain; P6 Bk writes 10% to 20% more output tokens than B.

## What this cannot settle

Three requests and the expected handling of 41 items were written by the same session that built the arms, from files it had read; one
subject (Terra xhigh), one judge whose calibration drifts a few points between batches (hence every comparison inside one call); intake
reads the repository, which ShipLoop's real intake leaves to discovery; no web search tool, so the `research` route is not exercised; fixtures
are tiny. It does not measure what a live run does with the terms it resolves; that is the live A/B.

## Smoke calls (not scored), 2026-10-31

One arm-Bk output per request through `run.py`'s `call_codex`: users 46.4 s, 7 shell commands, 3,660 output tokens; meter 35.1 s, 5 commands,
3,176 tokens; records 39.5 s, 5 commands, 3,160 tokens; each ended in a fenced `shiploop-state` result.

## Reproduce

```
python3 qb5.py build && python3 qb5.py jobs
QB_WORK=<scratch> python3 run.py jobs.tsv --limit=codex=4
python3 qb5.py judge && QB_WORK=<scratch> python3 run.py jobs-judge.tsv --limit=opus=5
python3 qb5.py score
```

`run.py` and `stats.py` are the question-bank study's, copied. Codex event streams, stderr and the judge prompts are not committed; each
envelope keeps the call's token usage and the shell commands the model ran.

## Results

(appended after the runs)
