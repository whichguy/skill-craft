# Native bounded dependency planning

Sequence planning is native ShipLoop work, not a required external Backchain
skill or template load. Make a short forward draft, audit every step backwards,
then import only a validated compatible DAG.

## Sequence result

Provide summary, concise plan, nonempty dependency_review string, and exactly
one of dag or dag_file. Plan repeats the exact spec done_sentence and has
Review Coverage. dependency_review records the forward draft, backwards
prerequisites, supplier/initial-state source, missing producers, unresolved
facts, and cycle check; it may point to a durable draft.

dag is the compatible object. dag_file is an absolute Markdown draft with one
shiploop-state object fence; raw JSON is refused. A draft is not authoritative
until import writes backchain/plan.md, and an edit after resolution is a
conflicting replay.

~~~json
{
  "summary": "Sequence audited before import.",
  "plan": "done_sentence: <exact spec sentence>\n\n## Review Coverage\n<activity>",
  "dependency_review": "Forward S1; backwards inputs supplied by initial state; no cycle.",
  "dag_file": "/absolute/path/sequence-draft.md"
}
~~~

## Bounded method

1. Draft the smallest forward path from established initial state to exact goal.
2. For each step, work backwards: every input needs an upstream exact produces
   value or a real initial-state fact.
3. Add a missing producer or leave it unresolved and pause; never invent facts.
4. Check safe unique IDs, exact need-to-producer links, and cycles.
5. Give every step concrete produces, a stored goal/until/Tools prompt, and a
   meaningful test plan for every produces value.

Seed prompts cite every environment reference and its exact mcp_considered
token. Preserve the exclusive writer in Use, every conflicting tool in Don't
use, and every reserved path in Don't write. UI work needs an early design
producer consumed by a later seed. Mark lifecycle DAG prep/publish activity.

Goal equals spec done_sentence; unresolved is empty before schedule. A step has
id, statement, origin, prompt, produces, and inputs:

~~~json
{"goal":"<exact spec done_sentence>","initial_state":["<established fact>"],
 "unresolved":[],"steps":[{"id":"S1","statement":"One bounded outcome",
 "origin":"seed","produces":["<exact checked outcome>"],"inputs":[],
 "prompt":"/goal\nDo this activity until these conditions are met:\n- <exact checked outcome>\n\nTools:\nWatch with: <frozen mcp_considered>\nUse: <tool>\nDon't use: none\nDon't write: none\nAssume: <facts>"}]}
~~~

If the user explicitly requests an external planner, follow that choice; do
not silently substitute one. If the choice is unclear, pause for it. Its output
remains a non-authoritative Markdown draft and gets the same audit.
Post-inner/outer replan changes only pending steps; each corrective step runs
the full inner loop.
