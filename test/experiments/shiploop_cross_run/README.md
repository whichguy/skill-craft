# Cross-run knowledge and request-isolation check

Date: 2026-09-16. Scope: the navigator's new-request entry and project-knowledge
policy, not product implementation or real remote delivery.

## Observed defect and chosen change

Before the change, public `init` against an existing run ignored the new prompt
and reprinted the old action or completion. A concurrent managed-init regression
using different prompts returned `[0, 0]` instead of one successful initialization
and one explicit conflict. The initial cross-run suite also failed for changed
prompts across navigator v1/v2, managed and legacy, and for absent knowledge
locators. These were observed failures, not inferred from wording alone.

The remedy is a small run-identity guard plus a fixed, optional repository
`SHIPLOOP.md` index locator. New requests use fresh run directories and retain
only their incoming prompt. Discovery/planning consult maintained project docs
and selected historical evidence; document/carry-forward/handoff retain useful
facts beyond disposable run storage. The graph and state schema are unchanged.

Alternatives considered: automatic artifact import with manifests/digests,
automatic run archival/rotation, and another persistent scheduler/registry.
Deferred: they add copying, retention, privacy and ownership rules without being
necessary to prevent prompt substitution or make repository knowledge reachable.
References permit reuse of existing environment/design/decision documentation
without promoting old graph state or approvals into current authority.

## Independent interpretation method

A separate fresh-context reader received only source-file locations and four
fictional scenarios. It read the current SKILL, project-knowledge policy and
prompt catalog and described next actions, applicable history, durable writes
and ambiguities. It did not initialize runs or perform those actions. This was
source-guided qualitative interpretation, **not** an execution benchmark or a
full returned-packet replay. Public-CLI tests separately cover packet routing.

The intended checks were: correct init-versus-recovery selection, use of the new
prompt, prior-doc discovery, evidence revalidation, no inherited scope/authority,
no phase skipping, exact callback ownership, and persistent knowledge retention.

| Scenario | Reader interpretation observed |
| --- | --- |
| Completed “create checkers”; new “make checkers visually drag”; index links environment/design/tests | Select a fresh run, pass the new text, finish intake via its callback, then revalidate existing game context in discovery. Do not rebuild the game or import the old queue. |
| Current discovery; no index; README links `docs/env.md`; prior managed `.shiploop/environment.md` exists | Read both environment sources as current candidate versus history, resolve stale/conflicting facts, create a small index instead of duplicate environment docs, finish assigned Improve before the callback. Do not initialize another run. |
| Current plan; sandbox deleted; historical one-time production approval; old multiplayer TODO; current request source-only drag | Keep the plan source-only and incremental. Do not recreate an unnecessary sandbox, deploy on the old approval or add multiplayer silently. Name meaningful local visual verification and pass the plan to its existing Improve successor. |
| Continue interrupted drag request; exact run locator missing; another completed run visible | Recover the exact run/identity from bounded locators or report the gap. Do not initialize a replacement or resume the unrelated completed run. |

All four interpretations retained the important boundaries. The reader correctly
declined to invent an exact callback without a current packet. It also noted
that source-only visual changes still need a meaningful local visual oracle;
source-only does not mean source inspection alone proves the behavior.

## Deterministic checks and limitations

`python3 test/shiploop-cross-run.test.py` covers matching retries, changed
prompt/repository rejection and no mutation across protocols; completed-run
recovery; default `.shiploop` collision and nested fresh runs; current-prompt
isolation; missing/untrusted index contents; knowledge locators across cold,
paused, blocked and done packets; and repository knowledge surviving removal
of a temporary prior-run fixture. The protocol suite also tests concurrent
different requests, while the dry-run suite checks locators along real graph
transitions and recovery routes.

During implementation these tests caught a compatibility detail: old modes store
repository identity as `repo_root`, while navigator uses `repo`. Both are now
handled. They also exposed an extra trailing newline on fresh navigator `init`;
fresh init and cold `next` now print identical packets without changing state.

No test proves that an arbitrary host writes truthful knowledge, reads all
relevant documents or revalidates a real deployment correctly. The script
enforces identity and routing; the host retains semantic responsibilities. No
remote setup, credential grant, publication, graph node, or extra Improve
counter was introduced. Independent code review found no correctness defect
and requested the prior-run-removal fixture, which was added to the suite.
