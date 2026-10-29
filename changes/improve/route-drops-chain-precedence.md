---
bump: patch
---
The ShipLoop ask-agent route no longer says chain precedence ends at producer completion: ShipLoop's implement stage
runs one step at a time in a worker and binds no chain (design T section 9.1, 2c-1).
