---
bump: patch
---
- **ShipLoop route terms:** the ShipLoop route files and the card's ShipLoop section call the Until Loop's record
  (`CHILD/packet.json`) the receipt, never a terminal or child packet, and the parent's `complete` the callback, as
  ShipLoop's glossary now does.
