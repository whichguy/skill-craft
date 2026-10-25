---
bump: patch
---
An Improve review's pass record counts an edit of the reviewed result, not only of the tree. A step plan's or a test
spec's result lies outside the tree (`RUN/inbox/<action>.md`, then `<action>-final-result.md`), so a review that edited
only its result read "tree changed: n".
- Each `pass-<n>.json` records the result's fingerprint, `result_changed` and `edited`, beside the tree's `changed`.
- `passes.md` shows the three columns.
- A review that changed only the result must leave its own `checks.md`, written after its last edit of the result.
  ShipLoop's producer-check summary no longer replaces it.
- The planning experiment exit no longer asks for "the two existing qualifying reviews": one trivial pass ends a
  review.
