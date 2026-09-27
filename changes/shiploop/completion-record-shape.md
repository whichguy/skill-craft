---
bump: patch
---
A ShipLoop record without exactly one `shiploop-state` JSON fence is refused with its path, the fence count and the expected shape, instead of a bare "exactly one fence" message.
