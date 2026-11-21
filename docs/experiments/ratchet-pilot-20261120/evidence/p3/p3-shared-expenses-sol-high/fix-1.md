## Fixed

- C-18 — Group creation accepted a 16,400-character ID from the JSON body, but Node's HTTP parser rejected the follow-up request target with 431 before routing. The server now allows a 64 KiB request parsing budget and limits new IDs to 48 KiB after percent encoding, leaving room for the route and headers. The failing ID now returns 201 on creation and 200 on the balances route.

## Disputed

none

## Discoveries

- Node applies its incoming header size limit to the request target as well as the headers. | Observable: Before the fix, a 16,400-character ASCII ID created with 201 produced 431 on its balances route. | Why: Creation carries the ID in the body, while later operations carry it in the request target.
- New IDs are limited to 48 KiB of percent-encoded bytes. | Observable: An ID consisting of 4,096 moon emoji works on all group routes and survives restart. Appending one ASCII character makes creation return 400. | Why: A finite request budget needs room for the operation path and headers, and percent encoding can expand an ID.
