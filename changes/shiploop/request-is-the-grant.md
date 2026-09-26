---
bump: minor
---
A request that names where to deliver ("deploy it to my Salesforce developer
org") is now the grant for this run: discovery resolves it to exactly one target,
records it, and the run never stops to ask again or plans a work item just to
record approval. ShipLoop asks only when the request leaves it open (no target,
several or no matching targets, an unnamed production or shared target, or a
destructive change), and then once, at intake or discovery, while independent
work continues. Discovery and plan packets now link that guidance.

The keepalive also binds a session from a `shiploop … --run-dir` command itself,
so a model that filters the packet output (hiding the run marker) no longer
loses the keepalive after a pause or block.
