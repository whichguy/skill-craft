---
bump: patch
---
The sandbox write-grant probe and its repair message now come from
`scripts/host_write_grants.py`, shared byte-identically with Ask Agent;
`shiploop_grants.py` only supplies ShipLoop's wording. The message and exit
code 3 are unchanged apart from the probe file name. A managed chain now also
freezes Ask Agent's `scripts/host_write_grants.py`, so a chain bound before this
release must be bound again.
