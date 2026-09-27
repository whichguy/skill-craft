---
bump: minor
---
After a verified workspace return, ShipLoop returns its own later knowledge commit (for example at release-verify) by the same route when everything changed since that return is `docs/shiploop/` or `SHIPLOOP.md`, keeping the earlier reviewed dispositions; handoff no longer finds a stale receipt and asks the model for a manual follow-up. Anything else changed, or a moved source, leaves the follow-up to handoff as before.
