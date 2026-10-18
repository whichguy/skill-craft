---
bump: minor
---
A packet's printed head now holds what its stage guidance cites, and every stage a revise sends an item back through says
it is a revisit (packet review 2026-10-17, F3 and F5). Before, the head cited guides by label without a path, ran "the
packet's plan-return" and "the printed `backchain-check`" from file-only lines, and a redone test spec searched the run
for its own earlier result and resubmitted it unchanged.
- Guides: each guide and policy the stage text names prints as `<label>: GUIDES/<file>#<section>` in the References block,
  after the symbols (a lookup block; a guide whose path the duty already prints is not repeated). The file keeps the
  stage's other guides where they were.
- Backchain: the planning guide, the resources or the audit resource, the loop-resource status (only where the text cites
  its "Loop resources" line) and the graph check print with the paragraph or line that cites them, ahead of the list of
  results the stage builds on.
- Release stages: the return route, the plan-return, review-return and return commands print in the head of
  release-plan, release-check, release and handoff; the delivery contract's lines (necessity, authority, obligations)
  print in the head of the stages whose done the release gate refuses on them (release-plan through handoff).
- Implement (inline): the step's own criteria print by value under the Step line; the quoted hand-off names them by ID,
  so the text prints once. The Improve hand-off still quotes them whole.
- Revisits: after a revise, the first head of step-plan, test-spec and implement prints four lines: why it is back (the
  revise result's summary and path), its previous accepted result (or none), the IDs the redone step plan and test spec
  added, removed or changed, and "Keep unchanged rows with their IDs". The Done-when "carried over" line names the
  stage's own previous result.
- Room: the pass, floor and ratchet rules are one shorter line each (every clause kept), and document and verify name
  the step-plan path list once ("every step-plan path, plus ...") instead of repeating it.
