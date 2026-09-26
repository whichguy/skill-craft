---
bump: patch
---
A review loop with a gate of two or more trivial reviews now completes after its first review when that review is trivial and satisfied, and the bundled Until Loop runtime sees from Git that the workspace content (tracked and untracked files, excluding ignored and runtime files) is unchanged since `start`. A second pass would only have reviewed the same tree. The complete packet reports `progress.unchanged_first_pass: true`. Any change, or a workspace outside Git, still needs two consecutive trivial reviews.
