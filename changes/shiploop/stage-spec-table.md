---
bump: patch
---
ShipLoop's 34 stages are now described in one table (`scripts/shiploop_stage_spec.py`): each
stage's goal, the conditions that confirm it, and its fixed considerations for developing,
testing, delivering and the assistive tools (linters, test runners) the script runs around it.
The stage sets that decide Improve reviews, lint gates, test runs, prompt blocks and "Read first"
lists are derived from that table. Packets and run behaviour are unchanged.
