---
bump: minor
---
Each step's commit is the iteration's commit stage, and the step advances only once it lands (design T section 9.1,
2b-4).
- It runs in the call that accepts the step's last stage (document's complete, or its review's import), so it commits
  the tree those gates ran on, as one commit on the step's base. Inside a step nothing else commits.
- When Git refuses the commit, the call is refused and nothing is saved. The change stays in the checkout, and the same
  callback, run again once the cause is fixed, commits it. Before, the step moved on uncommitted.
- A pending record (`RUN/iterations/<item>.json`) is written before the commit. A call that stopped after Git committed
  is retried without a second commit, and a commit something else made inside the step is refused, naming
  `git reset --soft <base>`, which keeps the changes.
