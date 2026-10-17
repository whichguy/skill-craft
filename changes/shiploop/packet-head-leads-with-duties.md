---
bump: patch
---
The head printed for a packet longer than 16,000 characters now leads with the stage's duties and rules. Before, the head
left them in the packet file: for all five such packets of a node-fix-bug item (step-plan, implement, test, verify,
carry-forward) the duties began 10,400 to 15,000 characters into the file, so a model that read only what was printed
never saw what to do. The order is now goal, status block, duties, result template, pointers, loop command; the quoted
knowledge files and hand-offs are dropped from the head first when it would pass the limit.
- The ask-agent opener reads "Execute the prompt in a fresh context." where it read "Clear and then execute the
  prompt.", which contradicted the rule that no packet pauses for a context clear.
- The Improve packet says to invoke the improve skill at every Improve stage and not from memory of an earlier one. In
  the last live run the model invoked it for 1 of 4 stages.
- The head closes with `=== end ShipLoop head ===`, so a reader can tell a whole print from one cut by a pipe. The
  E2E harness reads a head to that line (`counters.head_or_why`, `flow.py`) and still reads saved heads of the older
  layout to the status block.
- The head's footer and SKILL.md no longer tell the model not to re-read "the Improve card"; the Improve stage's packet says
  to invoke the skill every time.

Two smaller wording changes ship with it. The opener of every packet now reads "Execute the prompt in a fresh context."
(it said "Clear and then execute the prompt.", which contradicted the packet's own rule never to pause for a context
clear). The Improve packet now tells the model to invoke the improve skill at every Improve stage, not from memory of an
earlier one. The E2E harness readers follow the new head to its closing line.
