---
bump: minor
---
The plan result now carries an `assumptions` list, and the navigator enforces
it. A done plan submitted through `complete` or `improve-complete` is refused
unless every load-bearing assumption is listed as evidenced, probed or open.
Every local evidence path must exist, a probed entry must cite a nonempty saved
output file, and each open entry must name a work item in the plan's queue. The
Plan Improve loop exits only when no open entry could be settled by a bounded
probe now. Research lists its assumptions in its decision note as the plan's
starting point, without a gate. The model still decides whether to experiment;
the gate makes a decision not to probe visible.
