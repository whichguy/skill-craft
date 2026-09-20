# Native trial model selection

The user selected Claude Sonnet, Grok for OpenCode, and Codex Luna with xhigh
reasoning during the monitoring campaign. Grok's native CLI lane retained its
Grok model. Record actual effective models, not only command-line requests.

U17 M2's first Codex parent had effective gpt-5.6-luna/xhigh, but direct child
turn records showed gpt-5.6-terra/max despite Luna startup session metadata. The
local configuration had separate `agents.default_subagent_model` and
`agents.default_subagent_reasoning_effort` values of Terra/max. The operator
interrupted the owned run; parent CLI stop and child turn-aborted events are
retained. It is not a completed Luna-worker result.

The separately preregistered U17 M2b correction keeps the frozen U17 skill and
M2 work, adds the user's explicit model/effort instruction to the parent and
worker assignments, and uses per-invocation parent and child-default overrides:

```text
-m gpt-5.6-luna
-c model_reasoning_effort="xhigh"
-c agents.default_subagent_model="gpt-5.6-luna"
-c agents.default_subagent_reasoning_effort="xhigh"
```

These configure the test parent; delegation still uses native subagent tools.
No global model setting is changed. A custom agent definition can override
model or effort after default resolution, so actual parent/direct/nested worker
turn metadata must still be inspected. Ask Agent's broad general-purpose policy
continues to apply. The [official subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents)
documents this precedence.

Retain M2's model mismatch, nested specialist/inherited-context deviations and
interruption. M2b is a separate attempt, not a replacement success. Model,
configuration and prompt differences prevent a causal wording-only comparison.
See the [registered correction](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/codex/U17-M2b/operator/REGISTRATION.json>)
and the [campaign results - completed M2b lifecycle and retained reporting defects](INTEGRATION-RESULTS.md#u17-native-observations).

M2b completed. The safe [effective-model projection](</Users/dadleet/Documents/Codex/experiments/ask-agent-integration-20260918T182741Z/codex/U17-M2b/evidence/effective-models.json>)
records native turn-context model/effort for the parent and both direct workers:
all used Luna/xhigh. Both fresh launches used `fork_turns=none`; neither child
spawned a further worker. Model selection and core native lifecycle were observed,
while final reporting deviations remain separately recorded. Matching models
does not establish full parent-child capability parity.
