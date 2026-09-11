# Survey, research, and spec actions

These are separate durable actions because a small context should not need to
hold discovery, source research, and a final product contract simultaneously.
They occur once per frozen planning baseline:

1. Survey and write environment.md.
2. Research uncertainties and write research.md.
3. Freeze a checkable spec.md plus lifecycle.md.

Use the exact action/result commands from the action protocol. If a user
decision or external prerequisite blocks progress, pause with a specific reason
instead of creating an uncheckable spec or inventing facts.
For a cold start, begin with the minimal typed machine record in
[the survey guide](../survey.md#minimal-valid-local-greenfield-machine-record)
and adapt it rather than guessing booleans, lists, or conditional fields.

## Survey

The survey result body becomes environment.md. Write a concise prose brief,
then exactly one H2 named machine and one fenced JSON object. The JSON is
structured content within authoritative Markdown. It is not a separate
environment.json authority.

Inventory, with evidence:

- repository kind and augmentation status; current product tree and relevant
  README/AGENTS guidance when it exists;
- concrete repository, product, writer, platform, and official-doc references
  with a one-line constraint-oriented why;
- available in-scope tools and MCPs, one read-capable mcp_considered token,
  non-secret handles/initiation facts, and unresolved questions;
- human-facing surfaces, their existing design/convention constraints, and
  whether an early design-producing step will be needed;
- destination writer, runtime/library conventions, safe product paths,
  reserved paths, syntax-lint oracle, live destination identity oracle, and
  routing/entrypoint probe where a destination is involved.

When a destination artifact has more than one potential writer, designate
exactly one use and record overlapping mutation tools in dont_use. They are
conflicts, not backups. If the designated writer cannot operate, pause and
obtain direction; do not silently switch writers.

For a writer-backed product, research and preserve the following before plan:

1. Which writer operation owns read, create, mutate, validation, and publish;
   do not use a familiar tool merely because it exists.
2. Required runtime/module/wrapper mechanics and existing local/destination
   patterns. Reuse before adding another stack.
3. Reserved versus product paths. Product changes never go into a writer-owned
   or overwrite-prone tree.
4. The user-facing route or invocation, reserved routes, a routing-level
   confirmation probe, and the distinction between a cheap bound-call probe
   and live acceptance.
5. Writer lint/validation for file-local syntax and writer list/status or
   preflight for live identity. Destination rules outrank a generic formatter
   when they conflict.

Never record credentials, API tokens, signed-in account addresses, or volatile
delivery URLs. Record expected account role, safe status probes, and source
pointers instead.

## Research

Research the uncertainties discovered by survey before authoring the spec.
Prefer primary documentation, existing repository conventions, and the named
writer's own descriptions. The result records source pointers, what was
learned, assumptions, and a reason when research genuinely does not apply.

Research is not an excuse to create product files, mutate a destination, or
re-survey an already frozen environment. A material discovery after freeze is
handled by an explicit pause or later pending-only replan.

## Spec

Write spec.md with exactly one line each, outside fences and blockquotes:

~~~text
done_sentence: <one checkable delivery sentence>
checkable: true
~~~

The spec result also supplies lifecycle:

~~~json
{
  "acceptance": ["observable acceptance criterion"],
  "preparation": "none | dag | outer-before",
  "publish": "none | dag | outer-loop",
  "quality": true,
  "reason": "why work belongs in these locations"
}
~~~

The spec states scope, exclusions, user-facing outcome, acceptance, risks, and
the placement rationale. It does not invent a testing framework, external
permission, writer, endpoint, or source fact.

- preparation outer-before means a named readiness action must complete before
  the DAG walk; dag means preparation is an early DAG step; none means no such
  work is implied.
- publish dag means a declared sequence step; outer-loop means an authorized
  delivery action after coverage/quality; none means no publication action.
- quality true means outer quality needs its quality review plus integration
  checks; quality false still requires mandatory acceptance/integration checks.
  The chosen integration check is implementation policy, not a fake user quote.

The spec is frozen after completion. A later plan revision cannot silently
change its done sentence or baseline. Product README and optional AGENTS.md
work are product DAG artifacts when needed, not survey writes or session state.
