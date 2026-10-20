---
bump: minor
---
- **Stop rule:** Improve now completes at the first pass that finds only trivial changes or none (`required_trivial_reviews: 1`). It
  no longer needs two consecutive trivial passes. A material or unresolved pass still continues the loop. Why: in a live
  run, the second confirming pass took about a fifth of all Improve passes and found nothing.
