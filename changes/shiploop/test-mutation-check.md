---
bump: minor
---
The test stage's done gate now runs a mutation check after the candidate run passes (owner decision 2026-10-11:
"code tests after the build phase, not just run empty tests"). ShipLoop makes at most 8 deterministic one-token
mutants of the item's changed product lines (comparisons, boolean literals, `+`/`-`, integer literals; comments and
strings skipped), applies each alone in a temporary worktree of the candidate, runs the focused commands, and refuses
done when mutants ran and none was killed. The refusal names each surviving mutant (`file:line`, the change) and counts
toward the refused-run cap; `complete --check-only` runs it without counting. Every check writes
`tests/<action>-mutation<N>.md` with each mutant and the kill count. The base run still counts a load failure of an
added file as RED (on new code nothing can run on the base); the mutation check is what proves the assertions.
Evidence: the Checkers run on 88d412e9 had every TC id "missing" on the base (load failure of rules.js) and its
mutation score fell 0.86 to 0.66 against the 17-stage run (n=1).
