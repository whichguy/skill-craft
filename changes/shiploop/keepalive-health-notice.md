---
bump: patch
---
ShipLoop now says when its keepalive is not working: if a host session prints a
second packet and the keepalive has never bound that session to the run, the
command warns once on stderr and names the fix for that host (for example,
restart Grok so its leader loads the plugin hooks).
