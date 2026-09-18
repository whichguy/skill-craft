# Research result contract

## Result shape

Use the packet's outer `shiploop-state` Markdown fence and exact completion
call. `research_state` is a nested object in that result, not a separate state
file to edit. The packet selects the schema from the durable run version:

- **Legacy (no `system_context_protocol_version`):** exactly `questions` and
  `sources`. Each question has only `id`, `question`, `origin`, `status`,
  `answer`, `sources`, `revalidate`, `rationale`.
- **Version 1:** those fields plus `system_context`; each question also has
  `parents`, `contract_refs`, `role_refs`, `interface_refs`. The complete row
  shapes appear below. Do not add this extension to a legacy run or remove it
  from a versioned one. An unknown version is a blocker, not legacy.

All keys shown are required; use empty arrays only when supported by the
inventory and the rules below. Text fields must be nonempty. IDs are stable
safe identifiers; references are arrays of IDs, not prose or objects.
`survey_ref` alone is nullable, or exactly `{platform_id, name}` from the frozen
survey. `required` is a JSON boolean. `consumer_steps` contains stable planned
consumer step IDs, not a claim that those steps already exist or have run.

| Field | Permitted values and obligations |
|---|---|
| Question `status` | `resolved`, `open`, `blocked`, `not-applicable`. A resolved answer cites source IDs; any other status explains the gap or inapplicability. `origin` names the **prompt**, **spec**, or **discovery** that raised it. |
| Source `authority` | `primary`, `local`, `secondary`, `probe`. Record the inspected revision or observation time, actual support and limitations. |
| Context `version` | Integer `1`. |
| Context `scope` | String `local-only` or `integrated`, not a list or environment name. `local-only` cannot omit an applicable surveyed platform; `integrated` needs interface and interaction inventories. |
| Observation `kind` | `code`, `state`, `system`, `environment-role`. Cover all four, including justified unavailable/inapplicable facets. |
| Observation and role `status` | `observed`, `blocked`, `not-applicable`. `observed` requires source references. An environment-role observation names at least one role. |
| Interface and interaction `status` | `resolved`, `blocked`, `not-applicable`. `resolved` requires source references. A resolved interaction cannot reference an open/blocked question. |
| Interaction `risk` | `low`, `medium`, `high`; justify investigation depth from consequences, not a numeric depth quota. |
| Interaction `required` | `true` or `false`. A required interaction cannot be `not-applicable` and needs nonempty `consumer_steps`. |

This is a **shape illustration, not evidence**: its blocked rows intentionally
cannot establish convergence. Replace example IDs and prose before initial
submission. The two-interface example does not require a service for a local
task. The packet's smaller local-only example does not excuse integrated work.
For a surveyed platform, cover every applicable platform in role `platform_refs`
and every selected surveyed interface with its exact `survey_ref`. Unsurveyed
local interfaces can have `survey_ref: null`. Both interface endpoints require
roles; the interaction covers the union of those roles and at least one question.
Source rows below illustrate the full source shape, not an inspected source.

```json
{
  "questions": [{
    "id": "RQ-1",
    "question": "What supported operation crosses the selected boundary?",
    "origin": "prompt discovery: selected interaction needs evidence",
    "status": "open",
    "answer": "The contract and its applicability still need inspection.",
    "sources": [],
    "revalidate": "Before using this boundary or after an interface change.",
    "rationale": "The answer may change the implementation and its checks.",
    "parents": [],
    "contract_refs": ["IC-1"],
    "role_refs": ["ROLE-1"],
    "interface_refs": ["IF-caller", "IF-callee"]
  }],
  "sources": [{
    "id": "SRC-1",
    "reference": "Example only: replace with an inspected safe reference",
    "authority": "local",
    "version_or_observed_at": "Example only: replace with the inspected revision or time",
    "supports": "Example only: state the fact the inspected source supports",
    "limitations": "This example proves no capability or live authority"
  }],
  "system_context": {
    "version": 1,
    "scope": "integrated",
    "rationale": "Example selected boundary; replace with surveyed scope evidence.",
    "observations": [
      {"id":"OBS-code","kind":"code","status":"blocked","summary":"Existing code still needs scoped inspection.","source_refs":[],"role_refs":["ROLE-1"],"interface_refs":[]},
      {"id":"OBS-state","kind":"state","status":"blocked","summary":"Existing state ownership still needs inspection.","source_refs":[],"role_refs":["ROLE-1"],"interface_refs":[]},
      {"id":"OBS-system","kind":"system","status":"blocked","summary":"System boundaries still need inspection.","source_refs":[],"role_refs":["ROLE-1"],"interface_refs":[]},
      {"id":"OBS-role","kind":"environment-role","status":"blocked","summary":"Environment authority and isolation are not established.","source_refs":[],"role_refs":["ROLE-1"],"interface_refs":[]}
    ],
    "roles": [{
      "id": "ROLE-1",
      "label": "Example selected role",
      "status": "blocked",
      "permitted_actions": "Unknown; no external actions authorized by this example.",
      "isolation": "Unknown; inspect the selected target and data boundary.",
      "platform_refs": [],
      "source_refs": [],
      "revalidate": "Before relying on this role for an operation."
    }],
    "interfaces": [
      {"id":"IF-caller","kind":"client","identity":"Example caller identity","survey_ref":null,"role_refs":["ROLE-1"],"source_refs":[],"idiom":"Supported client idiom still needs inspection.","status":"blocked","revalidate":"On client or contract change."},
      {"id":"IF-callee","kind":"service","identity":"Example callee identity","survey_ref":null,"role_refs":["ROLE-1"],"source_refs":[],"idiom":"Supported callee idiom still needs inspection.","status":"blocked","revalidate":"On service or contract change."}
    ],
    "interactions": [{
      "id": "IC-1",
      "caller_interface_id": "IF-caller",
      "callee_interface_id": "IF-callee",
      "role_refs": ["ROLE-1"],
      "operation": "Example selected operation identity",
      "question_refs": ["RQ-1"],
      "source_refs": [],
      "input_output": "The actual input and output envelope are unknown.",
      "state_semantics": "State ownership and update semantics are unknown.",
      "failure_semantics": "Error, partial-effect and recovery semantics are unknown.",
      "idiom": "Supported library and invocation convention need evidence.",
      "risk": "medium",
      "depth_rationale": "The selected boundary may affect state; investigate that consequence.",
      "status": "blocked",
      "required": true,
      "consumer_steps": ["S1"]
    }]
  }
}
```

## Replacement rules

For `research-apply`, read the current `research-evidence.md` through the
packet's selected reference/context reader. Build the complete replacement in
the printed inbox, preserving untouched records. The example is not the current
inventory. Never patch the script-owned evidence file or omit unresolved rows
to fit the context window.

Preserve all previous question/source IDs, and all role/interface/interaction
IDs. These identity fields cannot change under the same ID:

| Record | Immutable fields | Where a refinement belongs |
|---|---|---|
| Source | `reference`, `authority` | Update supported facts, limitations or observation/version details; a different source gets a new ID. |
| Role | `label` | Refine permitted actions, isolation, status, evidence or revalidation. |
| Interface | `identity`, `survey_ref` | Refine `idiom`, status, evidence or revalidation. |
| Interaction | `caller_interface_id`, `callee_interface_id`, `operation` | Refine `input_output`, `state_semantics`, `failure_semantics`, `idiom`, evidence or applicability. |

A genuinely different identity gets a new ID while prior records remain.
Do not disguise a frozen-survey change as a new research row; use the existing
revisit/pause route when the baseline or authority must change.

Maintain links in both directions: if `IC-1.question_refs` adds `RQ-2`, then
`RQ-2.contract_refs` must include `IC-1`, and vice versa. All referenced IDs must
exist in the same complete replacement. Question `parents` must form an acyclic
graph. A linked open/blocked question also keeps its interaction unresolved.

Schema rejection leaves the action unfinished. Correct the inbox result and
retry the exact callback, or read `next` if acceptance is uncertain. Never
change the version marker, weaken checks, or mark a gap resolved just to pass
validation. Acceptance proves record consistency, not source truth, permission,
test success, or research completion.
