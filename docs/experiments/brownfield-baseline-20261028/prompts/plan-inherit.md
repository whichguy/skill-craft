ShipLoop navigator | plan   (experiment rendering, arms A0w and A1: the proposed brownfield wording)

Goal: Plan dependencies and the queue: ordered work items, assumptions, and structure decisions.
Done when (confirm each before you finish):
- every outcome of the request is owned by a work item
- work items are in dependency order with readiness and completion conditions
- each structure or technology decision is recorded as AD-<n>: inherited ones with their evidence, new ones with why
- an inherited decision the plan changes cites the request sentence that asks for it (Basis: S<k>)

Current stage guidance (the plan packet of the 2026-10-27 run, items 2, 7, 8, 9 and 14, cut to what a plan without the
earlier stages' results can use, with the proposed brownfield lines marked NEW; the request below stands in for the spec):
0. NEW. This repository already exists and works. Before deciding anything, find the existing decisions the plan
   touches: how state is stored, how background work runs, how callers authenticate, how errors reach callers, how
   configuration is read, how features like the request are already built. Record each one the plan relies on as
   `AD-<n> (inherited) <choice>. Evidence: <path and symbol>`. Decide only what the request adds. Change an existing
   decision only when a request sentence asks for it (`Basis: S<k>`); otherwise keep it, and record the alternative
   you would have preferred as an assumption. A capability the repository already has is reused, not rebuilt.
   KNOWLEDGE_LINE
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
   - placement: NEW: keep the existing placement, channels and background-work model (the inherited decisions); for
     what the request adds, the simplest that meets it. Add server state, identity, a store or live channel only for a
     requirement that needs it, and use what the repository and its runtime already provide first;
   - safeguards at every placement: a server-side check on every action by a caller the product does not control,
     validation and abuse limits on anonymous input, a record of every background or async failure that reaches
     whoever must act;
   - channels: per hop the lightest that meets the stated freshness.
4. Each structure or technology decision as AD-<n> (choice, why, alternatives, status); a decision that no longer
   holds goes under Superseded, with its Basis.
5. Check the draft once for coherent increments: split a deliverable with different prerequisites or independent
   implementation and check; merge fragments that share prerequisites and an implementation boundary. A small change
   may be one item. Add no item for step planning, validation, build, test, documentation or review.

Output: write PLAN.md at the OUT path you were given, with exactly these sections:
- `## Summary`: one paragraph.
- `## Work items`: `W1`, `W2`, ... each with its goal, the files or areas it changes, and its done condition.
- `## Decisions`: one line per structure or technology decision the plan relies on or makes:
  `AD-<n> (inherited|new|changes AD-<m>) <choice>. Why: <reason>. Alternatives: <considered>. Basis: <the request sentence S<k> that requires it, or none>`.
- `## Assumptions`: one line each.
Read the repository as you need; change nothing in it except as the KNOWLEDGE line above allows.
