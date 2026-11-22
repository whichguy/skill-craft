Max-effort design review (run at effort max, read-only; do not edit anything, do not launch any model session, no length limit on the answer). Everything you need is in this folder.

WHAT IS HERE
- skills/shiploop/: ShipLoop as released. SKILL.md is its card; scripts/ holds the navigator and every stage's text (shiploop_prompts.py holds the duties of each stage; shiploop_stage_spec.py the stage rules; shiploop_concerns.py the plan's concerns); references/ holds the guides a stage may open.
- docs/ARCHITECTURE.md: the repository's layers.
- Four journals of measurement, all recent: docs/shiploop-sdlc-structure-journal.md (does the stage structure earn its keep; model and effort comparisons), docs/ratchet-pilot-journal.md (a lighter loop tried and rejected, then a bench for specification texts measured through built products; findings F1 to F47), docs/ratchet-parallel-journal.md (tests written beside or before the build), docs/spec-elaboration-journal.md (what makes a specification fuller; real deliveries read from archives; sections 37 to 52 are today's).

THE OWNER'S QUESTION, in his words
"We are trying to create a generic SDLC prompt and scripts, how could we make this more effective? What ideas should we try based on learnings?"

ShipLoop is that generic SDLC prompt and scripts: a script-driven delivery loop for coding agents on several hosts (Claude, Codex, Grok and others), where scripts own navigation and hand the model one stage's packet at a time, context is cleared between stages, and only script-run checks decide that a stage is done. It must stay generic: no stack-specific rules. The owner's priorities when judging a change: quality of the delivered product first, then tokens, then time. He wants changes only for a material, measured difference.

WHAT I WANT FROM YOU
Read the card and stage texts first, then the journals' findings (skim for "Finding", "F", "Status", "not shown", "firm"), then answer. I want your own view, argued from the evidence in these files, not agreement with any journal.

1. THE LEARNINGS THAT SHOULD DRIVE DESIGN. From the four journals, which findings are solid enough to design on, which are over-read, and which contradict each other? Give the ten or so that matter most, each with its evidence and its limit. Call out anything the journals conclude that their own numbers do not support.

2. WHERE EFFECTIVENESS IS BEING LOST TODAY. Reading ShipLoop's actual stage texts and scripts against those learnings: where does it spend tokens or time on something the evidence says does not pay; where does it rely on prose where the evidence says only a filled form or a script check changes behaviour; where can a stage report success with hollow evidence; where does an instruction probably not reach the model at all (see the finding that on one host the model gives itself only part of a command's output)? Cite the file and the duty.

3. IDEAS TO TRY, RANKED. For each idea: what changes in the prompt or the scripts, in two or three sentences; why the evidence predicts it helps, and the strongest reason it might not; the smallest experiment that could show it, with objective ground truth where possible (built products against held-out checks, tests against seeded or planted faults, a request with a known answer sheet), the measure, the baseline spread to beat, and its cost class (minutes and single dollars, or hours and tens); what result would make you drop it. Rank by expected gain in delivered quality per unit of cost, and separate (a) changes to what the model is told, (b) changes to forms the model must fill, (c) new or stronger script checks, (d) changes to structure or order of stages, (e) changes to how work is routed between models and efforts, (f) changes to what the human sees and is asked.

4. WHAT TO REMOVE. A generic loop gets better by subtraction too. Which duties, guides, stages or checks does the evidence say to delete or merge, and what would you measure before deleting each?

5. THE EVALUATION ITSELF. The measurements so far are small (one to three runs a cell), on a few cases that current models mostly build right, and several instruments turned out unable to see what they were built to see. What is the cheapest evaluation design that would let this team tell a real improvement from noise within an afternoon, and what should it stop measuring?

6. THE ONE THING. If only one change could be made to ShipLoop this month, what is it, and what is the evidence?

Constraints: generic, no stack rules; small experiments before large ones, each with its rule written before it runs; one run a cell shows nothing; a count over a specification rewards whatever is counted; held-out checks are never shown to a model session; no caps on loops or on prompt length for their own sake.
