---
bump: minor
---
`init`, the direct entry, now refuses to start a run in an empty folder that is not a Git repository and prints the `workspace start` command to run instead: `workspace start` makes the folder a repository, works in a separate worktree and returns the finished work to the folder, which `init` does not. A user who explicitly asked for an in-place or non-Git run passes the new `--in-place`. A folder with any content, a Git repository, a folder inside one, an existing run, and every other refusal `init` already had are unchanged. The navigator reference and the consumer-delivery reference now state the same rule: `workspace start` is the entry for new work, and `init` only for an in-place or non-Git run the user explicitly asked for.
