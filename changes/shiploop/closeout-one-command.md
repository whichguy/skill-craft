---
bump: patch
---
An inner stage that finishes with outcome done now closes with one shell command: the callback with `check`, then the
loop's satisfied report, then the callback, each part running only if the one before succeeded. A refused check stops
the command before the report, so the loop stays open for the fix. The two model turns that used to follow a check's
yes are gone. Send-back and blocked keep their route: report the loop blocked, then run the callback.
