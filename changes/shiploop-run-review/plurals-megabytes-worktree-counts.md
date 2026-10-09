---
bump: patch
---
The Run Review page and export read better and say more: a counter is no longer "1 refusals" (the header line, the Refusals card and
the run facts count in the right number, as does the exporter's "1 child, 1 review pass"), a size over 1000 KB prints in MB, and the
unreturned product's checks are exported and shown as how many pass in the worktree ("passes 4/4 checks in the worktree") instead of a
yes or no. A run exported with the earlier boolean `worktreeChecks` is refused; export it again.
