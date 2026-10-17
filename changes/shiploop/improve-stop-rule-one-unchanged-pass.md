---
bump: minor
---
ShipLoop's Improve child now ends on one trivial pass that leaves the content unchanged, measured by the bundled runtime, in place of two consecutive trivial passes (owner decision 2026-10-16, SPEC S-10 carve-out).
- The child's start contract lists the stage result file under the run directory as a `candidate_paths` entry, so an edit to a plan, step-plan or test-spec result (which lives outside the worktree) counts as a change. Its exit and repeat conditions no longer name two reviews or a streak. The stage loops' contracts are unchanged and never carry `candidate_paths`.
- The import takes one review reference (the final pass's `review-<n>.md`) where it took two, or one for an unchanged first pass. It refuses a terminal or stopped packet from the older runtime (a trivial streak, or `unchanged_first_pass`) by name, and a packet not run at the unchanged-content gate. The change gate and the restart route now key on a completion on the first pass.
- The Improve handoff's pass and evidence lines say the runtime ends the review on a pass that changed nothing and that the import takes the final pass. Backchain's `converge` gate text says the bundled runtime measures the plan unchanged instead of counting.
- ShipLoop's Improve tests and fixtures use Git worktrees, which the gate needs.
