---
bump: minor
---
ShipLoop commits every file it is asked to commit. Before, any file whose text matched the credential screen (a line such
as `Auth: sf login (alias de)` or `signature: static` was enough) was unstaged and left out of the item commit, the
knowledge-home commit, the Improve review's commit and the late-file commit that `plan-return` makes, and a notice told
the model to reword the file and commit it. A file left out that way kept the return off the user's branch (the return
fell back to the working-tree route) and left the model a hand-commit to do, which the packets forbid.
- `plan-return` no longer takes a `fresh` list of skipped paths, and no output says "Not committed, they look like they
  hold a credential".
- The Return route sentence reads "plan-return commits files left uncommitted, so commit nothing for the return." The
  exception for a file it reports as not committed is gone.
- Paths ShipLoop never commits are unchanged: run evidence, protected paths and the caller's exclusions.
