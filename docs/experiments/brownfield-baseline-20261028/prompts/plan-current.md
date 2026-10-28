ShipLoop navigator | plan   (experiment rendering, arm A0: the current wording)

Goal: Plan dependencies and the queue: ordered work items, assumptions, and structure decisions.
Done when (confirm each before you finish):
- every outcome of the request is owned by a work item
- work items are in dependency order with readiness and completion conditions
- each structure or technology decision is recorded as AD-<n>

Current stage guidance (the plan packet of the 2026-10-27 run, items 2, 7, 8, 9 and 14, cut to what a plan without the
earlier stages' results can use; the request below stands in for the spec):
1. Plan backward from desired outcomes to their producers. Order readiness, implementation and integration so no
   consumer runs before its prerequisites. Each item gives ready and done conditions, candidate scope, proving check.
2. Code or stored data added: write the namespace and data entries with an AD-<n> per decision:
   - every execution environment the code runs in or reaches (local checkout, remote runtime, hosted platform, each
     service);
   - per environment: current library structure (packages, modules, prefixes, exported surfaces, where similar
     responsibilities live), name resolution, and what new code imports, is called by or shares names with;
   - a home namespace and visibility per new responsibility across all items, and how new names avoid collisions;
   - data storage per environment: existing and destination schema, owner and change mechanism; for a new schema its
     store, keys, field types, constraints, relationships, version, migration and storage policy.
   Plan no empty package or directory for a hypothetical future.
3. Decide the interaction structure; record each decision as an AD-<n>:
   - placement: the simplest that meets the request. Add server state, identity, a store or live channel only for a
     requirement that needs it, and use the runtime's native storage, identity, cache, workflow and notification
     services first;
   - safeguards at every placement: a server-side check on every action by a caller the product does not control,
     validation and abuse limits on anonymous input, a record of every background or async failure that reaches
     whoever must act;
   - channels: per hop the lightest that meets the stated freshness.
4. Each structure or technology decision as AD-<n> (choice, why, alternatives, status); a decision that no longer
   holds goes under Superseded.
5. Check the draft once for coherent increments: split a deliverable with different prerequisites or independent
   implementation and check; merge fragments that share prerequisites and an implementation boundary. A small change
   may be one item. Add no item for step planning, validation, build, test, documentation or review.

Output: write PLAN.md at the OUT path you were given, with exactly these sections:
- `## Summary`: one paragraph.
- `## Work items`: `W1`, `W2`, ... each with its goal, the files or areas it changes, and its done condition.
- `## Decisions`: one line per structure or technology decision the plan relies on or makes:
  `AD-<n> <choice>. Why: <reason>. Alternatives: <considered>. Basis: <the request sentence S<k> that requires it, or none>`.
- `## Assumptions`: one line each.
Read the repository as you need; change nothing in it.
