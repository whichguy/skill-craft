---
bump: minor
---
Backchain is retired (owner decision 2026-11-16): ShipLoop no longer has a Backchain child or the `--backchain-passes`
option, and a saved run that still records `backchain_passes` is refused with the fresh-run hint. Default runs change
only by losing the sentences that said no Backchain child was requested. Every Backchain stage keeps the planning
guide's dependency audit and the record-only `backchain-check`, whose structural check now ships inside ShipLoop
(`scripts/backchain_graph.py`) and whose graph format is the planning guide's new "Plan graph format" section.
