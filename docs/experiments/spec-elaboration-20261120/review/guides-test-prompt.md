You are reviewing the design of a small experiment before its author asks the owner for a go-ahead to run it. You
report; you change nothing. Read only; write no file. Be adversarial: the author wants to know what is wrong with it
before any money is spent, and would rather hear "do not run this" than run something that cannot be read afterwards.

## What is proposed

Section 39 of `docs/spec-elaboration-journal.md` (the last section; it is in the working tree and not yet
committed). It registers a test with two arms of a real ShipLoop run that starts from one sentence and is ended when
its specification has been accepted. Its pieces, all in `docs/experiments/spec-elaboration-20261120/`:

- `guides_test.py`: the driver (`prepare`, `run`, `collect`).
- `overlays/guides-read.json`: arm B's one sentence, applied to a built copy of the plugin.
- The yardstick it reuses: `cases.json` (the case `csv-user-import`), `labels/sets.json`, `grade.py`, `label.py`.
- `guide_reads.py` and `qualcheck.py`, which the driver imports.

It leans on the repository's E2E harness and on another study's scripts: `test/shiploop_e2e/run.py` (`--prompt`,
`--continue-from`, `--plugin-dir`, `--source checkout`, the `<output>/stop` file, `--baseline`, `--max-budget-usd`),
`test/shiploop_e2e/overlay.py`, `test/shiploop_e2e/brownfield.py`, `test/shiploop_e2e/hosts.py`, and
`docs/experiments/sdlc-structure-20261119/build_arm.py` and `stage_stop_samples.py`.

## Why it is proposed

Read sections 26, 28 (with its dated qualifications) and 38 of the same journal, and
`evidence/readings/guide-reads.txt`, `guide-reads-bench.txt` and `coverage-by-category.txt`. In short: a bench that
gave ShipLoop's spec stage one sentence and no repository drew out specifications many times longer than real
deliveries write; later it was found that the real deliveries had started from requests of 76 to 322 words, and that
their builders almost never open the reference guides the spec stage names, where nearly every bench session did.
The owner then said, in his words: "I think fuller specs is actually what I really wanted, although clarity is also
helpful", breadth of coverage, "I'm open to all ideas", and asked whether the reference material added to ShipLoop
"to help prompt the spec definition" is effective. Asked whether to plan a small real-ShipLoop test of the spec
guides on a one-sentence request, he said "Yes, plan it".

Two standing rules of the owner's bear on it: engineering rigour is the expected standard even for a small request,
and product capability the request does not need is overbuilding (commit e18cbce9ec577a61a8cdea353c6794804b09f1d9);
and experiments start small and say at each step whether there is enough to conclude early.

## What to do

Part 1, will it answer the question. Decide whether a result from this design can be read. In particular:
- Is the one sentence the right manipulation for "is the reference material effective when used"? Say what a
  positive result and a null result would each fail to distinguish.
- The request and the base: one sentence that presupposes users and admins, started in `fixtures/node-base`. Does
  that make a fair case of "a vague request", and does `--prompt` with `--continue-from` change what the builder is
  told or how ShipLoop treats the run compared with a catalog case that has a base? Read `run.py` to find out.
- The stop point, the text handed to the judge (the accepted specification, `architecture.md`, the spec stage's
  submission) and whether that is comparable with what the bench's judge was given.
- The measures (needed items touched and covered, the sorters' sets, plain counts) and the bar, for three samples an
  arm on one driver and two on the other. Is "the lowest of B above the highest of A" sound here, too strict, or too
  loose? Could the bar be met by something other than breadth?
- Confounds between the arms other than the sentence, including anything in how the two plugin copies are built.

Part 2, the apparatus. Read `guides_test.py` line by line against the harness code it calls and find what will break
or silently mislead: wrong assumptions about where a run's files are for a continued run, races around the stop
file, the 6 dollar cap ending a Claude run before the stop, a section's heading being found in the stream for a
reason other than the builder opening the guide (the packet's own text, the Improve skill's text, the product's
files), the timestamp comparison in `collect`, the copy into `results/` and what `grade.py` then reads. Check the
overlay's text against `DUTIES["spec"]` and against the labels a real spec packet prints for its guides.

Part 3, smaller or better. Is there a smaller first step that would answer the same thing? Is there something cheap
that should be added now because adding it later would cost a second round (for example a third arm with the
sections' questions inside the packet, or Sonnet at medium, which the owner is also weighing)? Do not propose more
than the question needs.

Part 4, the six predictions and the "what each outcome would say" list. Name any that cannot fail, that are scored
on the wrong measure, or that would be read the same way whatever happened.

You may run read-only commands (git, grep, python that only reads). Do not run the harness, a model, or anything that
starts a server. Do not open anything under the user's home configuration folders.

## What to return

Numbered findings, most serious first. For each: a severity (P1: the result would be wrong or unreadable; P2: it
weakens the result; P3: minor), the evidence with `file:line` or the command you ran, and a change in one or two
sentences. Then one line, exactly one of: `VERDICT: RUN AS IS`, `VERDICT: FIX FIRST` (list the findings that must be
fixed) or `VERDICT: DO NOT RUN` (say why). Then the three changes you would make if you could make only three.
