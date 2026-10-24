---
bump: patch
---
The Improve handoff's top line now says `ROUTE` is the Improve skill's short route core, which has
every pass's rules and names the file for recovery, `final_result` and the review inputs, so a
review reads about 9.7 KB of route per stage instead of 47 KB. The handoff's `Review passes:` line
no longer speaks of two consecutive trivial passes: the loop ends at the first pass that finds only
trivial changes or none. `improve-context.md` points at the files the inline and ask-agent route
text moved to.
