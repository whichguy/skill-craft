---
bump: patch
---
The output of `workspace plan-return` and `review-return`, and the refusal of a blocked `return`, is now held to one print limit in all, not one per path list, so a very long list is cut at a path and the rest counted while the last line stays the next command. `review-return` counts the paths it excluded and no longer lists them a second time beside the excludes a review decided.
