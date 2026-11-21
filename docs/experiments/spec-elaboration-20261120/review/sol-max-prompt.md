You are reviewing a proposed change to a prompt, and the evidence offered for it. You report; you change nothing.
Read only; write no file. Be adversarial: the author wants to know what is wrong before the owner is asked to decide.

## What is proposed

ShipLoop is a delivery harness in this repository. Its `spec` stage turns a request into a specification. The stage's
instruction text is `DUTIES["spec"]` in `skills/shiploop/scripts/shiploop_prompts.py` (rendered by `duty("spec")` and
`prompt("spec")` there).

The proposal is to insert one block of 386 words into duty 2 of that text, after duty 2's first paragraph. The block
is in `docs/experiments/spec-elaboration-20261120/arms/Q-shiploop-spec-lenses.insert.txt`. The stage text with the
block in place, under a frame used only for the experiment, is `arms/Q-shiploop-spec-lenses.md` in the same folder;
`arms/P-shiploop-spec.md` is the same without the block.

## The evidence offered

A side experiment: `docs/experiments/spec-elaboration-20261120/` (start with its `README.md`) and its journal,
`docs/spec-elaboration-journal.md` (thirteen sections; sections 8 to 13 carry the conclusions). Evidence files are
under `evidence/`, verdicts under `grades/`, clause audits under `audits/`, the specifications the sessions wrote
under `results/`. The instrument is `run.py`, `grade.py`, `timeline.py`, `codex_isolation.py` and `cases.json`.

A last round (round 6: the block inside the stage text against the stage text without it) is running as you read and
has no result yet. Judge the proposal and the evidence as they stand without it, and say what result from that round
should change the recommendation.

## What to do

Part 1, the block as text that will sit in the stage. Read `DUTIES["spec"]` whole, and the duties of the stages on
either side of it (`research`, `test-strategy`, `plan`) far enough to know what they assume about the specification.
Then find, in the block:
- anything that contradicts, duplicates or weakens a duty already in the stage (name the duty and quote both);
- any sentence two readers would read differently, or that a model would plausibly carry out in a way the author did
  not mean (say how);
- anything likely to make a session write more than the request calls for, or loop, or stall;
- anything the stages after `spec` would trip on (for example a requirement count, an ID form, a section they read);
- whether duty 2 is the right place for it, given how the stage's code and tests refer to duties
  (`test/shiploop-packet-*.test.py`, `test/shiploop-quality.test.py`, `test/shiploop-guidance.test.py` and whatever
  else pins `DUTIES["spec"]`), and what else would have to change with it (the references under
  `skills/shiploop/references/`, the change note under `changes/shiploop/`).
For each, give the exact words you would change and the words you would put.

Part 2, the evidence. Read the journal's sections 8 to 13 against the files they cite, and check the numbers
yourself from `grades/`, `audits/` and `evidence/` where a claim rests on one. Find:
- any claim the cited file does not support, or supports less strongly than the sentence says;
- any error of counting, of comparison (unlike cells compared, a mean against a single draw read at the wrong band)
  or of reasoning;
- any other explanation for a result that the journal does not consider and that the data in the folder could
  support or rule out;
- any way the instrument itself could have produced the result (the checklist in `cases.json` was written by the
  same author as the arms; the judge prompt is in `grade.py`; subjects ran with their own tools).
Say which conclusions you would call established, which interim and which unsupported.

Part 3, the recommendation. In the author's place, would you put this change to the owner? State the strongest case
against it. State what round 6 would have to show for you to support it, and what would make you withdraw it.

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
READ: <the files you read>
RAN: <the commands you ran, or none>

P1 means the proposal or a stated conclusion is wrong or would cause harm as written. P2 means it is materially
weaker or riskier than stated. P3 means it would be better otherwise.
