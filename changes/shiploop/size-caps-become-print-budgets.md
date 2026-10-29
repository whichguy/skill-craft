---
bump: minor
---
ShipLoop no longer refuses the model's own text for its length. A step's task, Proof and criteria, a work item's context, its open assumptions and concern rows, a step's notes, the test layers and a result headline were each refused past a size (3-5 refusals per run in the brownfield before-runs, each costing a rewrite). The gates accept any length. A packet still prints such a field whole within its print budget; past it the packet prints what fits and names `RUN/fields/<action>-<field>.md`, which ShipLoop writes before it prints and which holds the field as written. A headline stays one line and is cut for display only. A test now fails when a new size constant has no kind (print budget, display cut or guard) or a refusal states a limit.
