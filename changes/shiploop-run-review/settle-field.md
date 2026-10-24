---
bump: patch
---
- **Settle:** the export reads ShipLoop's renamed `unverified[].settle` (it was `check`) into the page's existing
  `check` column, so a run on the new ShipLoop still shows what each unverified outcome's owner does.
