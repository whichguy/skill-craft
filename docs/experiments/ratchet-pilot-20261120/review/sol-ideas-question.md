Max-effort design review (run at effort max, read-only; do not edit anything, do not launch any model session, no length limit on the answer). Everything you need is in this folder: read all three files before answering.

FILES
- pilot-journal-sections-20-to-24.md: the "Ratchet pilot" journal, the part that matters here (amendments 7 to 14 and notes received from two other sessions). Findings are numbered F23 to F47.
- elaboration-journal-sections-37-to-52.md: the journal of a sister study ("Spec elaboration") on ShipLoop's released specification stage, the part from today. Its last section (52) registers an experiment that may be running now.
- texts-under-test.md: the prompt texts themselves (the specification text, the plan text, the question paragraphs that were tried), ShipLoop's twelve key questions and fifteen plan concerns as released, and the requests used.

BACKGROUND IN ONE PARAGRAPH
ShipLoop is a script-driven software delivery loop for coding agents (intake, discovery, spec, plan, build, test and so on, each stage a session that gets a packet of instructions). "Ratchet" was the owner's idea of a lighter loop; the pilot concluded not to build it as a loop, and has since been used as a cheap bench for specification-writing texts, measured through built products, tests against planted defects, and held-out checks. The owner's current question, in his words: "how much we might be able to leverage existing ShipLoop reference material in Ratchet ... If we know key categories or key questions that need to be considered, that might actually help give us better breadth and coverage (possibly even better depth) for when we elaborate the incoming prompt or we're trying to elaborate the spec." He has also said he wants fuller specifications, that clarity helps too, and that he is open to all ideas.

WHAT HAS BEEN FOUND TODAY (details and numbers are in the files)
1. A specification text that forbids the writer to decide what the request leaves open, and has it mark such points "Open:", beat two earlier texts on built products (fewer clauses that reject a correct product, as many planted defects caught, cheaper), on two models.
2. A question taken from ShipLoop's catalog is answered when the stage is given a section to fill, and leaves no trace as one more instruction: 14 of 14 with a section across two sessions, two models, two hosts; 0 of 2 without.
3. At the plan stage the answers became requirements (one of which caught a planted defect that eight other runs missed); at the specification stage they stayed a list, and a list drew a requirement out of the clauses until the section was told to name the clause that states each entry.
4. Nothing tried makes a specification measurably fuller or a test suite measurably stronger: one catalog question in spec or plan (strength 23 to 26 of 27 against 24 to 26 for the baseline), the same in a section, a matching catalog question on a request with one stated detail removed (the baseline already raised the missing detail as an open point, 6 of 6), and in the sister study guide text in the packet, a sentence to read the whole packet, and a section answering all twelve key questions (judged coverage within the released stage's own run-to-run swing; "a general question gets a general answer").
5. Run-to-run spread is as large as most differences seen: the same text gives 24 to 26 of 27 defects caught, 20 to 24 clauses.
6. Side findings: a test that starts a test runner from inside a test run runs nothing and exits 0 unless the child's environment is cleaned; on the Codex host the Sol model gives itself only part of a command's output, so instructions delivered through a command may not reach it whole.
7. The sister study has just registered a further experiment: five questions particular to the kind of change, on two fresh one-sentence requests whose checklists were written blind (its section 52).

THE QUESTION
The owner asks: before we move forward, is there any other consideration or idea we should experiment with? Think about this as deeply as you can. I want your own view, not agreement. In particular:

A. What do these results really establish, and what do they not? Name any flaw in the reasoning, in the instruments (planted defects on one case; judged checklists on vague sentences; a removed-detail instrument; word-match counts) or in the conclusions drawn. Where is a null result more likely to be an instrument that cannot see the effect than an effect that is not there?

B. What considerations have not been weighed at all? Think about where in a delivery loop breadth actually pays (intake, specification, plan, test design, review of the built product), about who answers a question (the same session that wrote the draft, a fresh session, a script that checks an answer), about when (before drafting, after drafting as a review against the draft, after the build as a check against the product), about the kind of question (general, particular to the change, generated from the request or from the repository, derived from past defects), about the cost of being wrong in each direction (a missed requirement against an invented one), and about what a real requester would want to be asked.

C. Propose experiments. For each: the idea in two sentences; the smallest version that could return in minutes for a few dollars; what is measured and what the ground truth is; the result that would change a decision and the one that would not; the main threat to its validity. Rank them by information per dollar and say which you would run first, which you would not run, and why. Prefer designs with objective ground truth over judged ones, and designs that can show harm as well as benefit.

D. Is there a reading of the evidence under which the right move is to stop experimenting on this question and change something else (the test stage, the check on a built product, the way open points are carried to a human)? Argue it as strongly as you can, then say whether you believe it.

E. Anything in the prompt texts themselves (texts-under-test.md) that would explain the results, or that you would change before any further experiment.

Constraints to respect in what you propose: no stack-specific rules in ShipLoop (it is generic); small experiments before large ones, each with its rule written before it runs; one run a cell shows nothing (see point 5); a count over a specification rewards whatever is counted, so "more items covered" is not by itself a result; held-out checks are never shown to a model session.
