# discovery: re-cut draft (worker A)

## 1. Goal (R1)

Inspect the repository, its environment and its baseline tests, and record the facts in HOME/environment.md, the
current-system account in RUN/notes/current-system-baseline.md, and the baseline run in `evidence_refs`.

## 2. Duty

1. Run the initial baseline first (Initial repository baseline guide). Inspect only enough to find the starting
   directory, its instructions and a safe existing command. Then run the full suite on the unchanged checkout, or the
   smoke suite when the full one is impractical. Selecting a command or citing an old pass does not count. Record the
   command, cwd, checked content and target, result, coverage limits and the output file in `evidence_refs`. When no
   suite exists, record that as missing coverage.
2. Classify the baseline in `summary`: passed, failed, missing coverage, setup or access block, uncertain, or expected
   repair RED. Only a pass is healthy. Change no product source, test, dependency definition or configuration to turn
   it green. A failed baseline lets discovery finish but leaves dependent feature work unready.
3. Inspect Git and worktree state, instructions, relevant code, tests, docs, consumers and project knowledge. Record in
   HOME/environment.md, each with its source locator:
   - ## Targets and runtimes: the development, test, integration and delivery boundaries, and the runtime and
     dependency versions;
   - ## Commands: the configured linters, formatters, type checkers and test runners;
   - ## Platform facts: conventions, canonical code and test examples, MCP and API contracts, reusable libraries.
   Mark each entry as binding requirement, observed practice or proposal. Install and provision nothing.
4. Find how a change reaches its consumer. Decide whether returning to the source branch triggers CI, a deploy, a
   publication or another effect, and whether that return must precede a required consumer check. Record the route
   and its uncertainty in HOME/environment.md ## Targets and runtimes. Inspecting the route does not authorize a
   return, a deploy or an early handoff.
5. Locate existing specs and quality policies, record their scope and status in `summary`, and screen the applicable
   non-functional requirements (Requirements definition guide).
6. Check the repository index, README and AGENTS for skill links and plausible skill contracts before proposing an
   implementation (Repository-local skill guidance). Record fit or no fit under HOME/environment.md ## Skills with its
   locator. For a selected skill, record its entrypoint, input and default sources, product contract and revalidation
   condition. Edit no skill package.
7. After the baseline, check the triggers of Discovery investigation guidance, and again when evidence conflicts or a
   dependency emerges. When one applies, write the plan and its outcome to RUN/notes/discovery.md: question, evidence
   route and order, owner, permitted effects, shared time or attempt bound, stop condition. Otherwise inspect
   directly.
8. Every environment read follows the Recursive discovery policy. One investigation allowance covers discovery and
   research together. Reaching it stops exploration, not the run: record the open gaps as assumptions or open items in
   `summary` and submit.
9. Resolve internal terms, background, requirements and decisions beyond the checkout with Connected knowledge
   discovery: find the available MCP readers (for example Slack or Teams, internal sites, design docs, private Git),
   use scoped search and read, and follow hits to the supporting content. Record terms and conflicting claims with
   provenance, access and coverage gaps, and safe locators in RUN/notes/discovery.md. Keep private queries and content
   off public surfaces. A reader is not a product runtime dependency.
10. Establish the current-system account (Current-system baseline guide). Read README first. Reuse and revalidate an
    adequate account, or recover one from docs, code, tests and authorized read-only observations. Write it to
    RUN/notes/current-system-baseline.md with its as-of identity, coverage, conflicts, source locators and intended
    durable home, and put that path in `evidence_refs`. A missing ShipLoop index does not mean a new system. Keep the
    incoming change separate, and leave consequential gaps unready for dependent work.
11. For affected local or remote flows, apply Service discovery guidance and record the findings in
    RUN/notes/discovery.md:
    - observability: the existing event owners and sinks to reuse;
    - where service boundaries matter: trace consumer needs through business services to the actual MCP, API and
      runtime capabilities, identities, schema and state;
    - cache, invalidation and async questions, without inventing infrastructure;
    - unproven access or caching: the safe interim policy-enforced read route, or a denial (privileged direct access
      is not a fallback);
    - a schema or projection delta: the preserved state and its reconciliation or read-back check;
    - an async flow: its processor and recovery owner and the boundary between acceptance and completion, or record
      them as unknown (a status poller alone establishes neither), and gate only that flow;
    - retained application state: follow the Runtime state placement section.
    Safe, scoped, authorized reads may resolve a gap. An unavailable or partial observation is not absence. Turn
    unknown ownership or coverage into a scoped probe and a conditional file or test change, and gate only the work
    that depends on it.
12. Establish the current target and effective identity, and use that target for dependent remote reads. Distinguish
    the discovery operator, the deployed runtime and the end user. Record each unknown role or authority, with the
    consumer it affects, under HOME/environment.md ## Access and accounts.
13. Record the existing interaction baseline (Interaction design guide) in RUN/notes/current-system-baseline.md:
    actors, channels, incoming and outgoing events, connection lifecycle, state ownership, and what the runtime and
    the project's layers already offer for each. For affected UI, record the available design guidance and its
    identity, version or digest, or the repository-guidance fallback. No UI does not skip machine interactions.
14. Answer each open question from intake in `summary` with a source, or keep it as an unknown with an owner.
15. Before you submit, apply Discovery evidence handoff: link each consequential decision from HOME/README.md to its
    exact section, then reopen each link and its observations as a fresh reader would. Put in `evidence_refs` every
    file this stage wrote and each source used, with scoped prerequisites and due revalidation.

## 3. Checked by

Nothing beyond the exit conditions and the shared mechanical checks.

## 4. Guides to keep

- Discovery investigation guidance (research-loop.md#plan-the-investigation): item 7.
- Connected knowledge discovery (project-knowledge.md#connected-knowledge-discovery): item 9.
- Current-system baseline guide (current-system-baseline.md#establish-or-refresh): item 10.
- Service discovery guidance (service-discovery.md#select-scope): item 11.
- Repository-local skill guidance (testing-and-documentation.md#reusable-product-skills): item 6.
- Discovery evidence handoff (project-knowledge.md#discovery-evidence-handoff): item 15.
- Environment and source-return discovery (environment-lifecycle.md#discover-before-planning-code): item 4. Today's
  text never cites it; item 4 now does.
- Delivery authority guidance (delivery-authority.md#ask-at-the-first-concrete-boundary): item 4 ("does not
  authorize"). Unsure: drop if item 4 reads clearly without it.
- Policies the prose names (printed by the POLICIES lookup, not STAGE_REFERENCES): Initial repository baseline guide
  (item 1), Requirements definition guide (item 5), Interaction design guide (item 13). Renderer lines kept: Recursive
  discovery policy (item 8), Navigator adapter (item 8; the adapter defines the allowance).
- Drop (never cited): Access-readiness policy (research owns access, research item 4), Persistent project-context
  guidance, House-style guidance, UI planning ownership when applicable. Unsure about House-style guidance
  (house-style.md#extract-the-house-style): discovery may be where the house style is first extracted; if so, add to
  item 3 "Record the house style (House-style guidance) under HOME/architecture.md ## Conventions" and keep it.

## 5. Fidelity map (R5)

| Today's sentence (short) | New home |
|---|---|
| D1 Inspect repo, Git/worktree, instructions, code, tests, docs, environment, consumers, knowledge. | Item 3 |
| D2 Identify development, test, integration, delivery boundaries. | Item 3 (## Targets and runtimes) |
| D3 Locate conventions, versions, canonical examples, MCP/API contracts, reusable skills/libraries. | Item 3 (## Platform facts), item 6 (skills) |
| D4 Separate binding, observed, proposals; record facts, conflicts, gaps; install nothing. | Item 3 |
| D5 Before planning, whether source return triggers CI/deploy/publication; prerequisite for a consumer check. | Item 4 |
| D6 Record route and uncertainty in environment notes; inspecting does not authorize a return. | Item 4 (HOME/environment.md ## Targets and runtimes) |
| D7 Locate specs and quality policies, scope/status; screen NFRs (Requirements definition guide). | Item 5 |
| D8 Repository-local skill guidance: inspect index/README/AGENTS skill links before proposing implementation. | Item 6 |
| D9 Record fit/no fit; for a selection its entrypoint, inputs, contract, revalidation in evidence_refs and notes. | Item 6 (HOME/environment.md ## Skills) |
| D10 Inspect skill packages without editing; preserve the knowledge recording/index policy. | Item 6 (no edit); index policy: item 15 and the shared knowledge-home lines |
| D11 Use the Initial repository baseline guide. | Item 1 |
| D12 Minimum inspection to identify starting directory, instructions, safe command. | Item 1 |
| D13 Run full suite when practical, smoke otherwise, on unchanged content. | Item 1 |
| D14 First verification activity; actual execution required. | Item 1 ("first", "does not count") |
| D15 Record command/cwd, content, target, result, coverage limits, locator in evidence_refs. | Item 1 |
| D16 Classify failure/missing coverage/block/uncertainty/expected RED before planning; not healthy. | Item 2 |
| D17 Preserve the observation; do not edit source/tests/deps/config to turn it green. | Item 2 |
| D18 May finish with a failed baseline; dependent work not ready. | Item 2 |
| D19 Discovery investigation guidance after baseline: triggers first and again on conflict. | Item 7 |
| D20 When one applies, retain plan and outcome: question, route, owner, effects, bound, stop. | Item 7 (RUN/notes/discovery.md) |
| D21 Otherwise the direct path. | Item 7 |
| D22 Connected knowledge discovery for terms, background, requirements, decisions beyond checkout. | Item 9 |
| D23 Find MCP readers, scoped search/read, follow hits. | Item 9 |
| D24 Slack/Teams, internal sites, private Git are examples. | Item 9 |
| D25 Resolve terms and conflicts with provenance; keep gaps and safe locators; private off public. | Item 9 |
| D26 A reader is not a runtime dependency. | Item 9 |
| D27 Current-system baseline guide after the initial baseline. | Item 10 (order: item 1 runs first) |
| D28 README first; reuse/revalidate or recover an account. | Item 10 |
| D29 Retain as-of identity, coverage, locators, durable home; baseline in evidence_refs. | Item 10 (RUN/notes/current-system-baseline.md, the guide's own example path) |
| D30 Missing ShipLoop index is not a new system. | Item 10 |
| D31 Keep incoming changes separate; gaps unready. | Item 10 |
| D32 Service discovery: owned observability, reuse event owners and sinks. | Item 11 |
| D33 Trace consumer needs through services to capabilities, identities, schema/state. | Item 11 |
| D34 Safe scoped reads may resolve gaps; partial is not absence. | Item 11 |
| D35 Cache/invalidation and async questions without inventing infrastructure. | Item 11 |
| D36 Unproven access/caching: interim read route or denial; no privileged fallback. | Item 11 |
| D37 Schema/projection delta: preserved state and read-back check. | Item 11 |
| D38 Unknown ownership/coverage becomes a scoped probe; gate only dependent work. | Item 11 |
| D39 Async flow: processor/recovery owner and acceptance-vs-completion boundary or unknown; poller insufficient. | Item 11 |
| D40 Gate that flow only. | Item 11 |
| D41 Retained state: Runtime state placement section. | Item 11 |
| D42 Current target and identity; pass to dependent reads. | Item 12 |
| D43 Distinguish operator, runtime, end user; retain unknown roles and affected consumer. | Item 12 (HOME/environment.md ## Access and accounts) |
| D44 Discovery evidence handoff: index links exact section; reopen as a fresh reader. | Item 15 (HOME/README.md is the index) |
| D45 Retain evidence_refs with scoped prerequisites and due revalidation. | Item 15 |
| Develop: record conventions, versions, reusable code; edit no product file. | Items 2 and 3 |
| Test: run the existing suite first on the unchanged checkout; classify, don't fix. | Items 1 and 2 |
| Deploy: how a change reaches its consumer; source-branch return triggers. | Item 4 |
| Tools: record linters, formatters, type checkers, test runners. | Item 3 (## Commands) |
| Renderer: Environment discovery requirement "Mandatory for this stage's relevant environment reads." | Item 8; propose the renderer drop the line (shiploop_navigator.py, ENVIRONMENT_DISCOVERY_REQUIREMENTS) |
| Renderer: one investigation allowance spans discovery and research; reaching it stops exploration, not the run. | Item 8; renderer drops the sentence |
| Renderer: Planning phase intent "Establish the current system, original user intent, constraints, unknowns; observations do not become approved requirements." | Goal and item 3 ("binding requirement, observed practice or proposal"); propose the renderer drop the line (shiploop_navigator.py, the `purpose` dict) |
| INTERACTION_DESIGN 1: during discovery, research, spec, planning, step planning, use the guide. | Item 13. Stage list CUT (R3) |
| INTERACTION_DESIGN 2: identify actors, channels, events, connection lifecycle, state ownership; baseline/delta. | Item 13 |
| INTERACTION_DESIGN 3: affected UI: read design guidance, record identity or fallback. | Item 13 |
| INTERACTION_DESIGN 4: establish or preserve component, interaction, skin premises, async feedback, deployment fit. | Moved to spec item 9 and plan item 8 (decisions); discovery records the baseline only (item 13) |
| INTERACTION_DESIGN 5: prefer existing capabilities; no UI does not skip machine interactions. | Item 13 |
| INTERACTION_DESIGN 6: locators and decisions in work-item context and evidence_refs, for cold recovery and Improve; no nested review. | Discovery has no work items: CUT here (R3), kept in plan item 8. Improve mention CUT (R3). "No nested review": CUT, discovery has no review route |
| INTERACTION_DESIGN 7-11: state and information lifecycle decisions. | Moved to spec item 9 (decisions). Item 13 keeps sentence 10 (map to what the runtime offers) |
| INTERACTION_DESIGN 12-18: placement, channels, safeguards, cache. | Moved to plan item 8 (architecture decisions) |
| _PLANNING_HANDOFF 1: preserve statements, decisions, constraints in summary and registered material. | Items 2, 5, 14 (summary) and every file item |
| _PLANNING_HANDOFF 2-3: plan and step-plan consolidation; sole directive. | CUT (R3) |
| _PLANNING_HANDOFF 4: register every planning file and source as absolute evidence_refs. | Item 15 |
| Done-when 2 (intake questions answered or kept with owner). | Exit condition; item 14 says where it goes |

## 6. Size

- Today: 10,971 characters.
- Proposed: 6,831 characters (62%).

Measured on the default render (ask-agent, planning_review stage, backchain_passes one). Today: prompt(stage) without STAGE_RULES, plus the Develop/Test/Deploy/Tools considerations and the stage-specific renderer lines this draft folds or cuts (Planning phase intent, the environment-discovery and investigation-allowance lines, plan's experiments lines). New: sections 1-3 of this file. Exit conditions are excluded from both.


## Tightened (pass 2)

Duty size (inline): 6,688 -> 5,600 characters (-17%). Goal: 'Inspect the repository and baseline tests; write the facts to HOME/environment.md and the baseline run to `evidence_refs`.'; short goal: 'discover the repository and baseline'.

Text now in `DUTIES['discovery']` (placeholders such as the Backchain item and item commit rule are filled at render):

```
1. Baseline first (Initial repository baseline guide): find the starting directory, its instructions and a safe
   command, then run the full suite on the unchanged checkout (the smoke suite if the full one is impractical).
   Choosing a command or citing an old pass does not count. `evidence_refs`: command, cwd, target, result, coverage
   limits, output file. No suite: record missing coverage.
2. Classify the baseline in `summary`: passed, failed, missing coverage, setup or access block, uncertain, or
   expected repair RED. Only a pass is healthy. Change no product file to turn it green. A failed baseline lets
   discovery finish and leaves dependent feature work unready.
3. Inspect Git and worktree state, instructions, code, tests, docs, consumers and project knowledge. Record in
   HOME/environment.md, each with a source locator and marked binding requirement, observed practice or proposal:
   - ## Targets and runtimes: development, test, integration and delivery boundaries; runtime and dependency
     versions;
   - ## Commands: linters, formatters, type checkers, test runners;
   - ## Platform facts: conventions, canonical code and test examples, MCP and API contracts, reusable libraries,
     house style (House-style guidance).
   Install and provision nothing.
4. Find how a change reaches its consumer (Environment and source-return discovery): whether the source-branch
   return triggers CI, a deploy or a publication, and whether it must precede a consumer check. Record route and
   uncertainty under ## Targets and runtimes. Inspecting a route authorizes no return, deploy or early handoff.
5. Locate existing specs and quality policies (scope, status in `summary`); screen the applicable non-functional
   requirements (Requirements definition guide).
6. Check the repository index, README and AGENTS for skill links before proposing an implementation
   (Repository-local skill guidance). Record fit or no fit under ## Skills with a locator; for a chosen skill, its
   entrypoint, inputs and defaults, contract and revalidation condition. Edit no skill package.
7. After the baseline, and again when evidence conflicts or a dependency emerges, check the Discovery investigation
   guidance triggers. If one applies, write the plan and outcome to RUN/notes/discovery.md (question, evidence route
   and order, owner, permitted effects, bound, stop condition); otherwise inspect directly.
8. Every environment read follows the Recursive discovery policy. One allowance covers discovery and research;
   reaching it stops exploration, not the run: record open gaps as assumptions or open items in `summary`.
9. Resolve internal terms and background beyond the checkout with Connected knowledge discovery: find the MCP readers
   (Slack or Teams, internal sites, design docs, private Git), search, and follow hits to the content. Record terms
   and conflicting claims with provenance, access and coverage gaps, and safe locators in RUN/notes/discovery.md.
   Keep private queries and content off public surfaces; a reader is no runtime dependency.
10. Establish the current-system account (Current-system baseline guide): read README first, reuse and revalidate an
    adequate account or recover one from docs, code, tests and authorized read-only observation. Write
    RUN/notes/current-system-baseline.md with as-of identity, coverage, conflicts, locators and durable home; cite it
    in `evidence_refs`. A repository without ShipLoop knowledge is not a new system. Keep the incoming change
    separate; consequential gaps leave dependent work unready.
11. For affected flows apply Service discovery guidance; record in RUN/notes/discovery.md:
    - observability: event owners and sinks to reuse;
    - service boundaries: consumer needs traced through business services to the real MCP, API and runtime
      capabilities, identities, schema and state;
    - cache, invalidation and async questions, inventing no infrastructure;
    - unproven access or caching: a safe policy-enforced read route, or a denial (privileged direct access is no
      fallback);
    - schema or projection delta: preserved state and its read-back check;
    - async flow: processor and recovery owner and the acceptance/completion boundary, else unknown (a status poller
      establishes neither); gate only that flow;
    - retained application state: the Runtime state placement section.
    Safe authorized reads may resolve a gap; an unavailable or partial observation is not absence. Turn unknown
    ownership into a scoped probe and a conditional change, gating only dependent work.
12. Establish the current target and effective identity; use it for dependent remote reads. Distinguish discovery
    operator, deployed runtime and end user. Record each unknown role or authority and its consumer under
    ## Access and accounts.
13. Record the interaction baseline (Interaction design guide) in RUN/notes/current-system-baseline.md: actors,
    channels, events, connection lifecycle, state ownership, what the runtime and project layers offer. Affected UI:
    the design guidance and its identity, version or digest, or the repository fallback. No UI still has machine
    interactions.
14. Answer each intake open question in `summary` with a source, or keep it unknown with an owner.
15. Before submitting, apply Discovery evidence handoff: list each consequential decision in `evidence_refs` with its
    section locator, and reopen each locator as a fresh reader. Also list every file written and source used, with
    scoped prerequisites and due revalidation.
```

Map: every numbered item and every obligation of the first re-cut is kept, in the same order, so the loop Work lines can still cite "DO 1-n". Cut or merged in this pass: restatements of what the shared layout already says (result shapes, loop mechanics, commands), explanatory "why" clauses, and repeated qualifiers ("a recorded X, not a Y" pairs kept once); lists were joined into one clause where each part kept its destination. Nothing moved to another stage. The text stayed close to its first re-cut size because those duties were already one fact per clause; a further 40% would drop an obligation, which the brief forbids.
