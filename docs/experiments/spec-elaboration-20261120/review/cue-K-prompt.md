You are reviewing a proposed change to a prompt, and the evidence offered for it. You report; you change nothing.
Read only; write no file. Be adversarial: the author wants to know what is wrong before the owner is asked to decide.

## What is proposed

ShipLoop is a delivery harness in this repository. Its `spec` stage turns a request into a specification. The stage's
instruction text is `DUTIES["spec"]` in `skills/shiploop/scripts/shiploop_prompts.py` (rendered by `duty("spec")` and
`prompt("spec")` there), followed by the RULES block the same file prints with it.

The candidate is two sentences, 75 words, inserted into duty 2 of that text after duty 2's first paragraph. They are in
`docs/experiments/spec-elaboration-20261120/arms/K-shiploop-spec-default-bounds.insert.txt`. In the same folder
`arms/K-shiploop-spec-default-bounds.md` is the stage text with them under a frame used only for the experiment,
`arms/P-shiploop-spec.md` is the stage text without them, and `arms/M-shiploop-spec-members.md` carries a second wording
that differs from K in one clause of the second sentence (an unresolved bound is recorded as an open gap, where K takes
the best default and records it as an assumption).

The author's present leaning, which you should test and not assume: put only the second sentence, reworded so that it
covers a limit the requested behaviour cannot work without and not a limit that need not exist, and only after an E2E
round on a built product.

## The evidence offered

A side experiment: `docs/experiments/spec-elaboration-20261120/` and its journal `docs/spec-elaboration-journal.md`.
Read the README's last three parts ("The smaller attempt: re-aimed before it ran", "Amended before round 7", "Result of
rounds 7 and 8") and the journal's sections 19 to 22. Sections 14 to 16 hold your predecessor's review of an earlier,
longer block and what followed from it. Evidence is under `evidence/round-7/` and `evidence/round-8/`, the item labels
and sets under `labels/`, verdicts under `grades/round-7`, `grades/round-7@gpt`, `grades/round-8`, `grades/round-8@gpt`,
and the 48 specifications under `results/round-7/` and `results/round-8/`. The instrument is `run.py`, `grade.py`,
`label.py`, `codex_isolation.py`, `cases.json` and `queue-6.sh`.

Evidence from another session, on built products: section 20 of `docs/ratchet-pilot-journal.md` as it stands in commit
0f044772fc0b8664ade3ef25eef86255e6fe7f41 (a branch, not `main`; read it with `git show 0f044772fc0b8664ade3ef25eef86255e6fe7f41:docs/ratchet-pilot-journal.md`), its findings F23 to F26.

Two rules of the owner's that bear on it: commit e18cbce9ec577a61a8cdea353c6794804b09f1d9 (engineering rigour is the expected standard even for a small
request; product capability the request does not need is overbuilding), and the stage's own RULES line for unattended
runs ("take the best default and record it as an assumption; a person-only step is an open item").

## What to do

Part 1, the sentence as text that will sit in the stage. Read `DUTIES["spec"]` and the RULES whole, and the duties of the
stages after it (`test-strategy`, `test-spec`, `plan`, `implement`, `product-acceptance` and whatever writes the final
report) far enough to know what each does with an assumption recorded in the specification and with an acceptance line
that states a default bound. Then find:
- anything in the sentence that contradicts, duplicates or weakens something the stage already says: duty 4's open gap
  for a user decision, duty 6's "Invent no bound", duty 9's "record a default for an open choice as an assumption in
  `summary`", duty 10's source for a platform claim, the RULES. Name the duty and quote both;
- whether "a limit the request leaves to choice" is the cause of this: three of the four K specifications of the
  waitlist request give the waitlist a cap (10, 10 and 20) that the request never mentioned, where the released stage
  wrote "Assumed none" and "No bound is invented ... Treated as unbounded". Give the words that would keep a default for
  a limit the requested behaviour cannot work without (a file's size limit, an input's maximum length, a timeout) and
  would not invite a limit that need not exist;
- what the later stages do with such a default: does a test hold the product to it, does anything show the assumption
  to the owner at the end, and is either what an assumption should get. Name the duty or the code;
- whether the first sentence should go (it showed nothing in either arm) and whether the second stands alone;
- whether duty 2 is the right place at all. The stage already says to take a default; the two drivers read duty 4 and
  the RULES differently. Would changing duty 4, duty 6 or duty 9, or the RULES line, be the smaller and truer fix than
  adding a sentence to duty 2? Say which and give the words;
- what else would have to change with it (`test/shiploop-packet-*.test.py`, `test/shiploop-quality.test.py`,
  `test/shiploop-guidance.test.py` and whatever else pins `DUTIES["spec"]`; the references under
  `skills/shiploop/references/`; the change note under `changes/shiploop/`).
For each, give the exact words you would change and the words you would put.

Part 2, the evidence. Read the journal's sections 19 to 22 against the files they cite, and check the numbers yourself
from `grades/`, `labels/` and `evidence/` where a claim rests on one. Find:
- any claim the cited file does not support, or supports less strongly than the sentence says;
- any error of counting, of comparison or of reasoning, including in how the bands were set (the floor of 2 from four
  repeat pairs), in reading two cue arms against one control, and in two rounds standing for an arm;
- any other explanation the journal does not consider and the data could support or rule out. Three to weigh: the
  judge credits deciding; these sessions had no repository, research result or selected baseline, so a limit is more
  often unknown here than in a real run; the two sorters' labels define the target set;
- whether "on limits Sol follows duty 4 and Sonnet the RULES" is what the released stage's specifications show or the
  author's story. Read P specifications of both drivers in `results/round-7` and `results/round-8` for how each treats
  a limit;
- whether section 22's count of what K decided (of 20 gains: 12 defaults for a limit the released stage also says
  exists, 3 waitlist caps, 2 platform limits, 1 set, 2 no difference) is right, against
  `evidence/round-8/K-target-items-round-7.md` and `-round-8.md` and the specifications.
Say which conclusions you would call established, which interim and which unsupported.

Part 3, the recommendation. Given the pilot's evidence that a clause the writer marked as its own choice failed on a
correct product two times in five, would you put this to the owner, and in what words? State the strongest case
against it. Say exactly what an E2E round would have to show before it ships (which kind of case, which host, which
measure, against what), and what result would make you withdraw it.

## How to report

End with exactly this structure and nothing after it:

FINDINGS
1. [P1|P2|P3] part 1, 2 or 3 | where: <file and the words or the section>
   problem: <what is wrong, in one to three sentences>
   evidence: <what you read or computed that shows it>
   change: <the exact rewording, the correction, or the check to run>
(more findings in the same form, most important first)
ESTABLISHED: <the conclusions you would call established>
INTERIM: <those you would call interim>
UNSUPPORTED: <those you would call unsupported>
VERDICT: <put it to the owner as it is | put it to the owner after these changes: ... | do not put it>
PROPOSED TEXT: <the exact sentence or sentences you would put into the stage, and where; or none>
READ: <the files you read>
RAN: <the commands you ran, or none>

P1 means the proposal or a stated conclusion is wrong or would cause harm as written. P2 means it is materially
weaker or riskier than stated. P3 means it would be better otherwise.
