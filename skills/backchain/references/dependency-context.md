# dependency-context.json

Source-neutral intermediate between **dependency-review** (native or EVSI) and the elaborator.

```json
{
  "source": "native" | "evsi-nbq" | "user",
  "questions": [
    {
      "text": "…",
      "priority": "high|medium|low",
      "affected_steps": ["S5"],
      "possible_graph_change": "…",
      "source_needed": "context|inspect|user"
    }
  ],
  "resolved_facts": [],
  "evidence": [],
  "assumptions": [],
  "meta": { "considered": 0, "kept": 0 }
}
```

Rendered markdown (`dependency-context.md`) is injected as `{{DEPENDENCY_CONTEXT}}`.

**Question ≠ fact:** only `resolved_facts` / `evidence` may treat a state as already true.
**Assumption ≠ evidence:** items in `assumptions` are unevidenced guesses. They must not drive
`from: null` closes or D* steps that pretend the guess is already true. An inferred world-state
need still requires a predecessor that would produce evidence, or `unresolved`.
