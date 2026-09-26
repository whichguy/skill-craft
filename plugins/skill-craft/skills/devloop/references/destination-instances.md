# Destination contract instances

The `/devloop` handshake asks five **protocol** slots (identity, claim,
reserved, success, misread) — see
[destination-contract.md](destination-contract.md). This file binds
**answers** for destinations we have already inspected. Do not copy these
nouns into the skill as required handshake text.

| dest-class | identity | claim | reserved | success | misread |
|---|---|---|---|---|---|
| mcp-gas-deploy | MCP `create` (title + localDir) | `__events__.doGet` or `/** @trigger doGet */` + `loadNow: true` under `common-js/` (`_main` + `__defineModule__`) | bare `/exec`, `/_debug` | truthy `HtmlService` / `ContentService` (null = yield) | JSON `No doGet handler claimed the request` with `totalHandlers>0` and `failedCount=0` = yield / missing **claimer**, not platform down |

Example print after discovery (not a card fixture):

```text
env-discovered: mcp-gas-deploy: identity=MCP create; claim=__events__.doGet or @trigger + loadNow; reserved=/exec /_debug; success=truthy HtmlService; misread=claimed-the-request + totalHandlers>0 is yield
```
