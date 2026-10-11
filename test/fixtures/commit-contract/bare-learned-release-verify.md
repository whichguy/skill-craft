docs(shiploop): record build-a-small-checkers knowledge at release-verify

Learned
- A review of the HTTP layer found `new URL(req.url, base)` throws on a request target like `//[`; any thin node:http server needs that parse guarded.
- node --test with the spec reporter prints each TC id, which ShipLoop's id check needs.

Key considerations
- Rule defaults chosen where the request is silent: men forward-only, kings both ways.

Open for the next run
- Real browser rendering of index.html was never observed.
