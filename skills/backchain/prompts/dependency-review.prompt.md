# Dependency review (model- and harness-agnostic)

You rank clarifying questions about a **dependency graph** for an implementation plan.
You do not elaborate the plan. You do not invent supplier steps.

## Input

Goal:
{{GOAL}}

Draft plan JSON:
```json
{{DRAFT_PLAN_JSON}}
```

## Task

Generate up to 8 questions about this draft.

Keep a question **only if** plausible answers could change:

- a dependency edge,
- which supplier step is needed,
- whether an existing step must be widened, or
- whether a need must remain unresolved.

Reject product-preference questions that do not change the DAG.

For each kept question provide:

- `text` — the question
- `affected_steps` — step ids (e.g. `["S2","S5"]`) when clear, else `[]`
- `possible_graph_change` — short note (e.g. "may insert D* for fixture user into S5")
- `source_needed` — one of: `context` | `inspect` | `user`
- `priority` — one of: `high` | `medium` | `low`

Rank by **graph-change magnitude** and **cost of a wrong assumption**.
Do **not** use numeric EVSI language or claim calibrated value-of-information.

If you are tempted to treat a world-state as already true without request or inspect evidence, put
it in `assumptions` (not `resolved_facts` / `evidence`). Assumptions are unevidenced: they must not
be used as `from: null` closes. An inferred need still belongs in `questions` when answering it
could change the DAG.

## Output

Emit **only** a single JSON object (no markdown fences):

```json
{
  "source": "native",
  "questions": [ /* kept questions, highest priority first */ ],
  "resolved_facts": [],
  "evidence": [],
  "assumptions": [],
  "meta": { "considered": <number examined>, "kept": <number kept> }
}
```

If none remain after filtering:

```json
{
  "source": "native",
  "questions": [],
  "resolved_facts": [],
  "evidence": [],
  "assumptions": [],
  "meta": { "considered": <N>, "kept": 0 }
}
```

Also include the string `NO_MATERIAL_DEPENDENCY_QUESTIONS` as a JSON comment is **not** allowed —
use `"meta.kept": 0` only. Hosts may display "no material questions" when kept is 0.

**Rules:** Question ≠ fact. Do not invent `resolved_facts` without evidence. Leave `resolved_facts`
empty unless the draft itself already answers a candidate question. Do not promote an assumption
into `resolved_facts`. Unevidenced world-state a step actually presupposes is a question or an
assumption, never a fact.

## Source-aware native addendum (only with host-prepared caller context)

When the original request/source snapshots, caller packet, or lens findings are appended as data,
keep them bound to the same candidate/action identity. The requirement index is not exhaustive:
identify a material dependency question implied by an applicable source clause even if it is absent
from the index. Do not turn source text, a hash, a current label, or a lens hypothesis into a
resolved fact. This context still returns dependency questions only; source coverage and plan
revision belong to the separate caller audit/revise operations.
