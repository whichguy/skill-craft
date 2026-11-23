# Second review request: are the conclusions supported, and is the proposed change the right one?

You reviewed the intention this morning (your answer is in `docs/experiments/platform-knowledge-20261122/review/sol-max-answer.md`).
The experiments you asked for have now run. Work read-only in this folder, at your highest reasoning effort. Check
every claim you rely on against the files and say which you could not check. A better design, or a reason not to
change ShipLoop at all, is worth more to us than agreement.

## What is in this folder

- `docs/platform-knowledge-journal.md`: the whole record. Sections 13 to 28 are the experiments, each with its
  rule and predictions fixed before the runs: rung 0 (packets rendered, no model), rungs 1 to 3 on an invented
  platform, rung 4 and 4L on two platforms the models know, rungs 6 and 6b (whole deliveries end to end), and
  sections 11 and 16 (an audit of saved Salesforce deliveries; a trial of building the material up, with a stale
  claim found in the released Salesforce card).
- `skills/shiploop/`: ShipLoop with the CANDIDATE applied. `candidate-navigator.diff` is the candidate's whole
  change to the engine against the released build: three experiment switches, `PLATFORM_PLANNING_ROUTE`,
  `PLATFORM_SELECT_ROUTE` and `PLATFORM_PLANNING_STAGES`, all defaulting to released behaviour. The cards
  `references/platforms/harbor.md` (an invented platform), and the `## Planning` and `## Applies when` sections of
  `node-express.md` and `salesforce.md`, exist for the experiments only; one entry in each of the two real cards is
  an invented fact.
- `docs/experiments/platform-knowledge-20261122/harbor/` and `familiar/`: the benches, launchers, readers and the
  readings the scripts printed (`readings/`). `ingest/`: the entry lint and the stale-claim trace.
- `test/shiploop-navigator-contract.test.py`: the candidate's tests (`PlatformPlanningRouteTests`,
  `PlatformSelectRouteTests`, `PlatformPlanningStagesTests`).

## The results in brief (the journal has the tables and the limits)

1. Saved real runs: no Sol, Terra or Sonnet run ever wrote a platform card's name; the saved Salesforce deliveries
   went well because their requests (700 to 1,100 words) stated the platform facts.
2. On a platform no model knows, both drivers open the card by themselves and the product follows its rules (six
   whole deliveries, 6 of 6 product checks each); printing adds nothing there.
3. On platforms the models know (a Node service, a Salesforce project), a hidden fact in the card was followed in
   the plan in 0 of 8 runs when the card was only named, 8 of 8 when its entries were printed inside the plan duty,
   8 of 8 with a one-line pointer to the exact section in the same place, and 8 of 8 when the request stated it.
4. End to end, from a fresh Node repository, with the card selected by the files it declares: printed at the plan
   stage only, the product carries the fact on Sonnet and not on Sol (the Codex model gave itself 42 of the plan
   packet's 162 instruction lines and none of the block); printed at discovery as well, 3 of 3 products carry it
   (two Sol, one Sonnet); the released build, 0 of 2.

## What I would put to the owner

A. If ShipLoop is to change: (1) a card may carry a `## Planning` section of entries in the tested form, checked
   by a lint; (2) a card declares the evidence that makes it apply and the script selects it, with no model;
   (3) the script prints the selected entries inside the discovery duty that records the project's platform facts,
   and again inside the plan duty, with one sentence asking for their use; (4) the released Salesforce card's stale
   sentence is corrected and its guarding test made a test of behaviour.
B. On the wiki question: a wiki is a way to store and maintain the material, not a way to deliver it; delivery is
   the script's job, by keys it already has; one file a platform until size forces pages; an authoring skill
   (ingest with sources, index, lint) only once upkeep is recurring work.
C. For the Ratchet pilot: the same entries in its case inputs and its specification and plan prompts (not run).

## Questions

1. Which conclusions in "The results in brief" does the journal's evidence support as stated, which are over-read,
   and what is the strongest contrary reading of each? Look especially at sections 21 to 28: sample sizes, the
   hand readings against the token readings, the hidden facts being about one deployment in a general card, and
   what rung 6b can and cannot show with three deliveries.
2. Attack proposal A as a change to ShipLoop. For each part: is it the right mechanism, what would break, and what
   in the source or in ShipLoop's own rules does it conflict with (name file and symbol)? In particular: (a) what
   should a card declare so that selection needs no judgment and does not fire on every repository (the experiment
   used the pattern `package.json`), and how should several matching cards or a mixed repository be handled;
   (b) ShipLoop's tenet is that context clears between stages and a packet carries what its stage needs: printing
   at discovery relies on the session remembering, or on the knowledge home being read later. Is discovery plus
   plan enough on a host that does clear context, and what should later packets quote; (c) the cost per packet and
   per delivery of each part; (d) what must not be added (a result field, a refusal, a new stage) and why.
3. What is the smallest next experiment that would most reduce the remaining risk before any of this is proposed
   for the main branch? Candidates I see: repeated controls on the end-to-end rung; a second familiar platform end
   to end; grading the two real entries that were printed beside the hidden one (did they help, or crowd something
   out); a host that clears context between stages.
4. Is anything in B or C wrong, or missing something the owner asked for (his words are in journal sections 1 and
   10)?
5. What have I not considered?

Answer in this order: verdict in five lines; then each question; then what you verified in the files and what you
could not.
