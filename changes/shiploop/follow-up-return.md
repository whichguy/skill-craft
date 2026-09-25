---
bump: minor
---
A product fix committed after the workspace return no longer strands the run.
Run `workspace plan-return` and `workspace return` again: the follow-up starts
from the source state the previous receipt recorded and uses the same route
(working-tree update or another fast-forward). The new receipt keeps the old
one as `previous_receipt`. A source that already holds exactly the follow-up
result (a fix copied in by hand) is recorded without writing; any other source
change made since that receipt still blocks.
