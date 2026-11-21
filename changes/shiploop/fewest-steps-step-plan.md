---
bump: minor
---
Step plans now use the fewest steps an item allows. One step is the default. A step holds at most 12 criteria and
6 product files (it was 4 and 3), separately confirmable behaviours share a step, and a larger item is cut at a
module or layer boundary into the fewest steps of that size.

Why: every step pays its own test, document, review and commit round. The same item planned as one step instead of
two to four finished 19 to 44% sooner on Claude Sonnet 5.5 (high) and 30% sooner on Grok 4.6 (xhigh) in inner-loop
slices, with the same results on checks the model never saw. On GPT-6.2 Sol (medium) the gain depended on the item.
On the largest recorded item no such check was lost on either model that built it.

What to expect: fewer and larger step commits and step reviews for the same work, and step counts and times that
no longer compare directly with runs of earlier versions. The two numbers are a budget the planner fits, not a
limit ShipLoop enforces. Evidence: `docs/shiploop-sdlc-structure-journal.md`, round 6 and its guard round.
