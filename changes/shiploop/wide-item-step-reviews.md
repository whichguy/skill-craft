---
bump: minor
---
A wide work item keeps its Improve review after each step. An item is wide when its steps work on separate paths:
joining every two steps that share a declared path (a step with none takes the item's) leaves more than one group.
- Each step of a wide item that changed a file is reviewed over its own change, with the one-step hand-off.
- A step whose own change is empty gets no review.
- An item of one group keeps 2.17.0's single review after its last step, over the item's whole change.
- This amends the owner's 2026-10-26 rule `item`. On Sonnet 5.5 battleship, one review of a three-part item (rules
  module, server, page) missed the three defects that its per-step baseline had fixed: a `GET //` crash, unvalidated
  options and a stale fire reply. Sonnet makes one finding pass per review, so the number of reviews sets its depth.
- Every packet's Improve schedule sentence, the glossary (new row "wide item"), the README, navigator.md and
  improve-stages.md say so.
