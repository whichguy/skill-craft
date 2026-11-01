---
bump: minor
---
The skill card is the native procedure only: five steps on `scripts/backchain.py` (prepare, plan, freeze, loop,
finish), the plan contract and the invariants. The development checkout's harness material moved to
`references/harness.md`. A fresh request's runs read about 39 % fewer bytes in full (232 KB to 141 KB): the Until
Loop runtime document is no longer required reading, and lens cards are read on demand (`backchain.py lenses
T07 T35`). The install text names the `skill-craft` plugin.

By default a Backchain review loop now completes at its first trivial review (`required_trivial_reviews: 1`); a
cycle that repaired anything is non-trivial, so a fresh review always follows a repair. `Backchain passes: one`
still runs one review/fix/check cycle, and the new `Backchain passes: converge` keeps two consecutive trivial
reviews. A review may remove an edge or step its own run generated when it finds it unjustified; inherited content
stays.
