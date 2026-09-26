---
bump: minor
---
A blocked result must now say who can unblock it: `blocked_by` is `user` (a
decision only the user can make), `access` (a sign-in or permission the user must
grant) or `external` (a service outside the run). Anything the run can fix itself
(a missing tool, a failed install, a broken baseline, a failing test) is refused
as blocked and repaired in the stage instead. The run's status reason and the
keepalive log start with that category. Saved runs are unaffected.

Discovery now checks access for every planned verification surface (the deploy
target and each post-deploy browser, API or remote check), proves a route the run
can use without the user, and asks for any missing sign-in once, up front. For
Salesforce, browser checks open the page through `sf org open --url-only` from the
org's existing CLI authentication instead of asking the user to log in.

Also fixes 0.31.1 writing its callback-attempt counter into a saved run that is
refused as retired.
