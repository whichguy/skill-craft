# Third review request: a common repository and a local one. Is the design right, and what must be tested before it ships?

You reviewed this study twice (your answers are in `docs/experiments/platform-knowledge-20261122/review/sol-max-answer.md`
and `sol-max-answer-2.md`). Your second answer asked for the project's own knowledge file to be tested before any
change to ShipLoop. That has run, and the owner has since stated an aim that changes the question. Work read-only in
this folder, at your highest reasoning effort. Check every claim you rely on against the files and say which you
could not check. A simpler design, or a reason not to change ShipLoop at all, is worth more to us than agreement.

## What is in this folder

- `docs/platform-knowledge-journal.md`: the whole record. Sections 30 to 43 are new since your second answer.
- `skills/shiploop/`: ShipLoop with the CANDIDATE applied; `candidate-navigator.diff` is the candidate's whole change
  to the engine against the released build (experiment switches that all default to released behaviour; the newest
  is the stage value "spec" of `PLATFORM_PLANNING_STAGES`, with `PLATFORM_SPEC_USE` and `_after_requirements_duty`).
  The card `references/platforms/harbor.md`, and the `## Planning` and `## Applies when` sections of `node-express.md`
  and `salesforce.md`, exist for the experiments only; one entry in each of the two real cards is an invented fact.
- `docs/experiments/platform-knowledge-20261122/harbor/` and `familiar/`: benches, launchers, readers, and the
  readings the scripts printed (`familiar/readings/`). `familiar/packets/pk-nodeplain-spec-live.md` is the spec
  packet as the read-live arm prints it.
- `test/`: the candidate's contract tests and the fixtures the newer rungs start from.

## What is new since your second answer (the journal has the tables and the limits)

1. **The project's own knowledge file, released behaviour** (sections 32, 33): a hidden fact written as one bullet
   under `## Platform facts` in the product's `docs/shiploop/environment.md` reached the plan in 8 of 8 plan-stage
   slices (two platforms, Sol medium and Sonnet medium) and the product in 3 of 3 whole deliveries. Each session read
   the file in its first seconds and wrote the fact into the spec as a requirement.
2. **Size and shape of that file** (sections 37, 39): forty real Salesforce facts with the hidden one in the middle,
   as one list and as an index with seven topic pages. The hidden bullet was given in full in 8 of 8. The token of
   record reached the plan in 2 of 4 (list) and 4 of 4 (index); by hand the rule was weighed in 8 of 8 and its
   intent kept in 7 of 8. Every index run read every page, so the pages cost 120% of the list's characters.
3. **A starter copy in a brand-new repository** (section 36): 3 of 3 products pass.
4. **The owner's aim** (sections 38 and 41, his words): a common repository of platform facts that ships with
   ShipLoop like a marketplace, and a local one in the project's repository. Asked whether a project should get the
   shared facts as a copy or read them live each run, he answered "Read live". The two repositories exist "to keep
   scope separated out".
5. **The read-live arm** (section 42): the selected card's planning entries are printed at the spec stage only,
   with a lead (read from the guide at this run; the project's own facts win; write a requirement with its proving
   check for each that bears; copy none into the project's file). T1, a brand-new repository: 3 of 3 products pass
   (the released route scored 0 of 2 there). T2, the project's own facts contradict the shared entry: 3 of 3
   products carry the local header and none sets the shared one. The block was given to the model in 6 of 6. No
   shared text was copied into the project's file in 6 of 6; the Sonnet deliveries cite shared entry ids in their
   own notes.
6. **A control is running while you read** (section 43, rung 11): the project's file names the shared card, the
   build is the released one, nothing is printed. In T2 all three sessions opened the named card by themselves
   before the block arrived, which no earlier whole delivery had been set up to show.
7. Section 40 is outside the design (test sessions on one host search the account's connectors).

## What I would tell the owner (attack each)

A. The local repository needs no change: the project's own `## Platform facts` is read in the first seconds of every
   delivery, weighed, and carried as a requirement.
B. A common repository that is only shipped is not read on a platform the model knows. To read it live the script
   has to hand it over, and the place that works on both drivers is the spec stage: printed at the plan stage only,
   the Sol session never gave itself the block; printed at discovery it works but asks for a copy in the project.
C. Precedence can be one sentence for now ("the project's own facts win"): 3 of 3.
D. Scope stays apart without enforcement: no shared text was copied, and the requirement names the shared entry as
   its basis.
E. Shape: one list in the local file up to forty facts; an index with pages buys nothing at that size.
F. Selection is the unsolved part. The test selected by a file pattern the card declares. Under two repositories the
   plain answer is that the local repository names the shared sets it uses.
G. Upkeep: a printed shared entry is obeyed, so the common repository needs the entry form, sources, dates and a
   lint; one sentence of the released Salesforce card is already stale (section 16).
H. Not shown: Salesforce end to end; forty entries printed in a packet; a host that clears context between stages; a
   wrong shared entry; the Ratchet pilot.

## Questions

1. Which of A to H does the journal's evidence carry as stated, which is over-read, and what is the strongest contrary
   reading of each? Look especially at the sample sizes (one Sonnet sample a test), the hidden fact being a
   deployment fact written into a general card, T2's sessions having read the card themselves before the block, and
   the scope rule I registered wrongly (section 42).
2. The delivery point. Is printing at the spec stage the right way to hand over a shared entry, set against (i) the
   released route with the card named in the project's file (rung 11, running: say what each of its outcomes should
   change), (ii) a live file written beside the knowledge home in the run's worktree and never committed, (iii)
   discovery with a marked record? Say what breaks in each, with file and symbol where the source decides it
   (`skills/shiploop/scripts/shiploop_navigator.py`: `_platform_planning_lines`, `_after_requirements_duty`,
   `platform_cards`, `_platform_testing_lines`).
3. Selection and precedence as a product. What should the local repository hold so that the script knows which
   shared sets apply, and to which target? Should precedence be a sentence, or a merge by entry id in the script?
   What happens when the local fact is the stale one and the shared entry is right?
4. "Read live" against reproducibility. A delivery now depends on the version of the shared repository at run time.
   What should a run record so that a later reader can tell which shared entries it was given?
5. The smallest set of tests that must pass before this becomes a default, in order, and which you would run first.
   Say what result would make you answer "do not ship it".
6. Anything in sections 32 to 43 that is miscounted or overstated.

Lead with the verdict. Keep the answer under about 2,500 words.
