---
bump: patch
---
An Improve handoff prints the exact lint command for the action it reviews, so a reviewer's `shiploop lint` runs
instead of being refused.
- While an Improve stage runs, `shiploop lint` lints the reviewed action and accepts only that action's ID. Every
  other command in the Improve files names the Improve stage's own ID, and the handoff printed no lint command, so
  reviewers used the Improve ID and were refused ("<Improve ID> is not the current action").
- When the run lints, each handoff's Commit section now ends with "Lint after your last edit (report-only; its --action
  is the reviewed <stage> action, not this Improve stage): <command>", as producer packets print theirs. The implement
  review's focus points to it. `shiploop lint` is unchanged: it still refuses the Improve stage's own ID.
- Why: in two DeepSeek flash brownfield E2E runs on 2026-10-28, all 7 lint refusals were this one, at implement (4),
  carry-forward, system-test-author and release-plan reviews.
