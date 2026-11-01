---
bump: patch
---
In a `--backchain-passes converge` run, the plan packet and the repair/revise route print the `Backchain passes:
converge` marker line, so the Backchain child keeps its two-review gate now that Backchain's own default is the
first trivial review. Packets of `one` (the default) and `none` runs are unchanged.
