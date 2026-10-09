---
bump: patch
---
The Run Review export and page now show more of what a run recorded: each visit's script checks (the records ShipLoop kept, how
many passed or ran red, and where release-verify ran), the outcomes a result left unverified with their owner and due stage, a
Claude run's wrapper scripts and packet use (so glue reads as a lower bound), and the planning window with its two clocks, where
it closed and its Improve share. A stage that only ran `backchain-check` now reads as a graph check instead of "no loop".
