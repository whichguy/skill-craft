---
bump: patch
---

The ShipLoop whole-skill subcall uses ShipLoop's `improve-start` command when
the packet prints one: write the named opening file and run it instead of
writing the start contract and starting the runtime by hand.
