# Destination contract (protocol)

**Discover destination contract** when the ask is **hosted** (deploy, live
URL, web app, remote runtime). Answer these five slots from discovery —
**do not invent a vendor hook**. Read-only. Do not write the product to
“fix” a live error.

1. **identity** — how is a new environment created or selected?
2. **claim** — how does product code attach so inbound work is claimed?
3. **reserved** — which routes / methods / names does the platform already own?
4. **success** — what does a claimed response look like vs yield / empty?
5. **misread** — how do you tell “handlers ran, none claimed” from “platform down”?

**Read** (session order; first hits win): user text → matching session MCP
descriptions / `llmGuidance` → provisioned tree (runtime/bootstrap/README)
→ optional live `status` / HEAD. Unanswered slot = `unknown` or fail-closed
and ask. Worked instances (one destination’s answers) live in
[destination-instances.md](destination-instances.md), not as this protocol.

**Print always when hosted:**

```text
env-discovered: <dest-class>: identity=…; claim=…; reserved=…; success=…; misread=…
env-discovered: none(no hosted destination)
```

**Fold** the five bindings into the request string (BUILD constraints), next
to `verify_cmd exactly` / `setup exactly`. Not a fourth argv kind. Typed
user text still wins.
