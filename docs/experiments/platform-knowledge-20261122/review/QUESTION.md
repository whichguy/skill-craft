# Review request: how should a platform's key considerations reach a model while it plans?

You are reviewing an intention and a candidate design before anything is built or run. Work read-only in this
folder. Use your highest reasoning effort. Check every claim you rely on against the files here and say which
claims you could not check. Disagree where the evidence supports it; a confirmation of the candidate is worth less
to us than a better design or a reason not to build anything.

## What is in this folder

- `skills/shiploop/`: ShipLoop as released. It is a delivery harness: scripts own the stage order and print a
  "packet" of instructions for each stage; a model does one stage at a time and submits a result the script checks.
  Start with `SKILL.md`, then `scripts/shiploop_prompts.py` (the stage texts), `scripts/shiploop_navigator.py`
  (`platform_cards`, `_platform_testing_lines`, the packet assembly), `scripts/shiploop_concerns.py` (the fifteen
  plan concerns) and `references/` (the guides; `references/platforms/` holds eleven "platform cards").
- `docs/platform-knowledge-journal.md`: the record of this question so far. Section 3 is a count made today from
  1,354 saved run folders; `docs/experiments/platform-knowledge-20261122/card_reads.py` is the tool and
  `evidence/` its output. Sections 4 to 6 are my reading, my candidate and my proposed test.
- Earlier measurements the journal cites: `docs/shiploop-architecture-rubric-results-2026-09-26.md`,
  `docs/shiploop-run-insights-plan-2026-10-18.md`, `docs/spec-elaboration-journal.md` (sections 38, 43, 47 to 53,
  58), `docs/ratchet-pilot-journal.md` (sections 22 and 26; findings F43, F50 to F52).
- `docs/experiments/ratchet-pilot-20261120/ratchet.py`: the Ratchet pilot's loop (one-pass build, then tests,
  fixes and a closing look), which the owner also wants served by the same material.
- `existing-wiki/wiki-suite/`: a wiki plugin the owner built earlier for one host, on Karpathy's "LLM Wiki" pattern
  (pages the model writes and keeps up, an index read first, operations ingest, query and lint).

## The owner's intention, in his words

1. "I want to consider a reference file that talks about design principles and considerations when actually using
   instances of certain technology aspects [...] key considerations that need to be considered if you're building in
   the Salesforce platform [...] to just make sure that whatever model we're using doesn't skip over these key
   notions."
2. "How we would incorporate this kind of notion into both Ratchet and Shiploop, and how we could build up that
   reference file that could be used to help during planning? I don't want to do something that's overwhelming or
   polluting the context [...] I don't know if something like a wiki is better."
3. "I want to test to see if the cards load it and I wonder if the wiki style would pollute context less, but
   requires key identifiers and pointers in order to pick up the other items. I worry the file cannot be loaded in
   context but we would need to have a karpathy style wiki skill used by shiploop (and helper scripts to make it
   fast)."

Standing rules of the owner that bind any answer: ShipLoop's scripts and core texts stay generic (no technology's
names or file conventions outside `references/platforms/`); scripts own navigation and the model does one step;
context is cleared between stages, so a packet must carry what its stage needs; no limits on ShipLoop's loops; no
size caps on model text; a change must show a measured difference; the two models that drive deliveries now are
GPT Sol at medium effort (on Codex) and Claude Sonnet at medium effort.

## What the record shows (details and limits in the journal)

- Platform cards exist, and the route that loads one starts with the model writing the card's name at discovery.
  In 316 real runs that were asked for that name, no run driven by Terra, Sol or Sonnet wrote one (0 of 290); Grok
  wrote one in 14 of 17. A card that is named is always opened and read whole. Of 8 finished Salesforce deliveries
  on Terra, 6 were built with no line of the Salesforce card shown to the model, including one where ShipLoop's own
  script had matched the card (its mutation-skip reason names it).
- In an earlier test (64 plans, Sonnet, four hosted environments) a card that was read did not move the overall
  score; it raised what it was specific about (fit to the host 0.59 to 0.91) and lowered other things (personal
  data 0.88 to 0.58).
- A question put as a section to fill is answered every time, and did not make a specification fuller. What moved
  builds in the neighbouring studies was an answer from the requester written into the specification, a fresh
  reader, and checks a script runs.
- On Codex the model shows itself nearly all of a packet's instructions in the early stages and little of the list
  of references that follows them.

## The candidate (journal section 5)

Keep storage and delivery apart. Delivery: the script, not the model, selects the material by keys ShipLoop
already has (platform, stage, the fifteen concern names, the concerns the plan marked as applying) and prints the
matching lines by value in the packet at the stage that decides, beside the concern rows the plan must fill; a
discovery gate that requires `Platform guide: <card>` or `none` covers a new build with no files to detect; one
command lets the model pull a whole page. Storage: one file a platform until it outgrows what a stage can carry,
then a folder of small keyed pages with an index compiled by a script. The authoring side of the Karpathy pattern
(ingest a source into pages, lint them) could be a separate skill later.

Alternatives on the table: leave it as it is; gate the name and let the model read the whole card (as Grok does);
a wiki the model pulls from by an index, as the owner suggests; print the whole card at the plan stage.

## The proposed test (journal section 6)

Real ShipLoop runs stopped at the plan's acceptance, on Sol medium and Sonnet medium, comparing the released stage,
lines printed by value beside the concern rows, and an index with a look-up duty. Read: whether the applicable
lines were shown to the model, how much platform text was shown in all, the plan's decisions against a checklist
written blind from the card, the generic concern rows, time and tokens.

## Questions

1. Is the intention sound as stated, given this evidence? If the honest answer is "the material is not what limits
   these deliveries", say so and say what would show it.
2. What is the simplest design that would make a platform's key considerations reach the plan on both drivers?
   Attack the candidate: what in it is over-built, what fails in practice, what conflicts with ShipLoop's source
   (name the file and symbol), and what it would cost a packet in characters at each stage.
3. Wiki or card: at what size or condition does splitting a platform's material into keyed pages pay? What must
   the keys be for a lookup to need no judgment from the model? Is a separate wiki skill warranted now, later or
   never, and what of the existing `wiki-suite` is worth keeping?
4. How should the material be built up and kept true (the owner's "how we could build up that reference file")
   without it growing into text nobody can check?
5. The test: is it the cheapest experiment that can separate the routes? What should be measured, what rule
   should be fixed before any run, and what could make it mislead (a bench against real runs, judges that reward
   mentioning a consideration, a checklist written from the card)? Offer a cheaper first rung if one exists.
6. Check `card_reads.py` and its output: is any count in journal section 3 wrong or read too widely?
7. What have I not considered? Other designs, other evidence in these files that cuts against the candidate, and
   anything in the owner's three statements that the candidate fails to serve (the Ratchet pilot included).

Answer in this order: verdict in five lines; then each question; then a short list of what you verified in the
files and what you could not.
