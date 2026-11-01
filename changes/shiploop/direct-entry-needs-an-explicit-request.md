---
bump: patch
---
The card's start section now says when the direct entry (`init`) applies: only when the user explicitly asks for an in-place or non-Git run, and naming the current directory is not such a request, because `workspace start` returns the finished work there. A session that starts in an empty directory and is asked to build "in the current directory" read the old sentence as permission to work in place and began with `init` (no Git repository, nothing committed). In a 40-session check on Codex Terra at xhigh with such a request, the published card began with `init` in 17 sessions and this wording in none; a request without that wording, and an existing Git repository, began with `workspace start` on every card tried (60 of 60).
