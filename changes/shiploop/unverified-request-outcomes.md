---
bump: minor
---
A done product-acceptance result now lists, in `unverified`, each request outcome no executed check observed, with its reason, owner and due stage (an empty list says every outcome was observed). ShipLoop refuses a missing list, an incomplete or placeholder entry and a due stage that is not a later stage, and prints each entry at its due stage, the whole list at handoff and a table in the report.
