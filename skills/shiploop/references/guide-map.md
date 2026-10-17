# Guides by stage

Split from the ShipLoop skill card (`../SKILL.md`). Read at discovery, research, spec and planning, and when a packet names one of these guides.

## Planning and coding guides

Follow [cross-run knowledge reuse](project-knowledge.md): discover
README, AGENTS, existing environment/decision documents and prior-run references,
then plan the new delta. Read the repository's `SHIPLOOP.md` knowledge index if
present (it is the host's file; ShipLoop never commits it) and keep its linked
documents useful across runs. Old one-off approvals and receipts in
run state are not imported; a current applicable user-approved standing policy
may be reused only after [delivery-authority revalidation](delivery-authority.md).
During discovery, research, and spec, apply
[requirements definition](requirements-definition.md): locate existing
specs, reconcile current explicit instructions with their applicable conditions,
and define verifiable non-functional requirements. Preserve unaffected intent
and retain material unknowns; carry the resulting criteria into plans and checks.
Use [current-system recovery](current-system-baseline.md) to initialize
a README-led baseline when an existing repo or remote system lacks one. Reuse and
revalidate sufficient prior knowledge; retain the prior as-of baseline, incoming
delta and maintained product knowledge through planning and the normal handoffs.
Recovered observations do not become approved requirements.
Use the [stage readiness and completion map](testing-and-documentation.md#stage-readiness-and-completion)
to distinguish definition done, tests planned/authored, due verification and final
delivery. Preserve each affected clause's required surface and due phase in the
existing requirement/case records; a supporting local pass cannot close a
required deployed interaction.
Use [reference handoffs and destinations](project-knowledge.md#reference-handoffs-and-destinations)
to keep the selected product sections and test locators correlated across plans,
results and Improve's own contract, without confusing package, repository and run files.
For item planning, coding and verification, use the
[coding decision guide](coding-guidance.md#select-guidance). Keep a compact
accepted plan and load only the applicable engineering practices and the platform
cards the guide lists for the surfaces this work touches. Retain decision and check locators through the
existing result/review notes; the guide does not change stage order or edit authority.
Use [house style](house-style.md) to extract the repository's evidenced
coding conventions at discovery, carry each item's nearest exemplars as a match
contract from step planning through build and verification, and keep the record current.
During discovery and planning, use [service discovery](service-discovery.md#select-scope)
to assess owned observability for local or remote flows and, when relevant, follow
MCP/API boundaries into schema, query, cache and asynchronous service needs.
Retain current decisions and affected file/check locators in indexed project
notes and item context; load only the applicable sections.

## Repository knowledge home

Planning knowledge outlives the run. Stages keep three living files in
`docs/shiploop/` in the product repository up to date: `spec.md` (the living spec,
stable `R-<n>` IDs), `environment.md` (targets by alias, working commands, harnesses
and suites, the test-ID convention, platform facts, the standing release procedure)
and `architecture.md` (stack, structure, conventions, interfaces, real-boundary checks
and numbered `AD-<n>` decisions). A run's other records are fields of its stage
results, quoted to the stages that consume them. The three files have named sections
(`knowledge_home.SECTIONS`); at the closes ShipLoop prints one
`ShipLoop knowledge notice:` line per file that lacks sections, naming them (a count,
never a refusal). An older home's `README.md`, `test-strategy.md` and `features/`
folders are left in place and no longer required, written or named.
At `prepare`, `release-plan` and `release-verify`, ShipLoop
refuses `done` until that close's files exist,
refuses a living spec or architecture whose uncommitted version drops an earlier committed
ID (an edit a review already committed through `improve-commit` is not seen), and commits exactly
`docs/shiploop/`. After any other accepted stage that changed `docs/shiploop/`,
ShipLoop runs the same ID check and commits it too, so never
commit it yourself. The `release-verify` commit is always made: its body is the
result's `lessons` (`Learned`, `Key considerations`, `Open for the next run`) and the
open items still left. Intake and discovery packets quote the last three commit
messages and that lessons commit, found by its subject. After a working-tree return
that commit is not on your branch: the report prints its exact message to commit. The
next run starts from these files; see
[repository knowledge home](project-knowledge.md#repository-knowledge-home).

## Access, testing and environments

For a concrete external dependency, follow the packet's
[access-readiness policy](research-loop.md#early-access-readiness):
try a safe existing connection first, promptly surface a proven user-auth need,
and retain its request and recheck condition in the existing notes. After the
user replies, verify access and finish the current duties before its callback;
authentication alone neither completes the phase nor authorizes deployment.

For testing, prefer the lowest-overhead sufficient tool, such as `curl`; always
consider an available authorized browser for rendered behavior or browser-specific
authentication. Follow the packet's [consumer testing guide](testing-and-documentation.md#lightweight-and-browser-checks).
HTTP success or a login screen cannot replace the required consumer observation.

Use the packet's [environment lifecycle policy](environment-lifecycle.md)
to discover actual development/test/delivery areas and promotion routes. Plan
required preparation producers before dependent feature work; carry their notes
and remaining promotion obligations into the outer release phases. Reuse ready
environments, keep authority distinct, and do not impose a fixed environment ladder.

## Navigator guide

Use [the navigator guide](navigator.md) for the flat SDLC diagram,
ownership diagram, state example, Improve binding, constitution, work-item
ordering, recovery and completion examples. Planning includes backward
prerequisite review; the host must place producers before consumers in the
ordered work queue.
