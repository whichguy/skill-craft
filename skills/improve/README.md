# Improve

~~~mermaid
flowchart LR
    Request[Natural-language request] --> Contract[Freeze scope and callback contract]
    Contract --> Packet[Bundled Until Loop returns one action]
    Packet --> Cycle[Review, improve, check, and record one cycle]
    Cycle --> Report[Submit the exact done callback with handoff]
    Report --> Gate{Two qualifying reviews?}
    Gate -->|No| Packet
    Gate -->|Yes| Terminal[Terminal packet and state deletion]
~~~

Improve reviews a repository candidate, makes worthwhile changes, checks the
result, and continues until two distinct consecutive review cycles find only
trivial issues or no changes. It reads the last seven full Git commit messages
for every review. A material finding or fix resets the count, even when the fix
is small and succeeds.

The user-facing interface stays natural language. The selected Improve card
binds a package-local Until Loop card, which owns internal start, next, and done
calls. The agent owns the review judgment and reports what actually happened;
the runtime validates action identity, preserves the latest contract and
handoff, applies the two-review gate, and selects the next packet.

## Start with a normal request

~~~text
Dry-run $improve on these changes. Show the scope and stopping conditions without writing files.
Use $improve on the parser changes, preserving its public API.
Use $improve on formatter.py and its tests. Do not stage or commit anything.
Use $improve on these changes and make an audit commit for every completed iteration, including no-change reviews.
~~~

The request supplies the work and constraints. It does not require runtime
flags, JSON, a state-file path, or a manually managed counter. The bound runtime
separates the request into one complete review-cycle work, an evidence-based exit
condition, and a repeat condition that preserves real blockers and requested
stops.

## Inline by default

Improve runs in the conversation that invokes it. Every review, check and commit
happens there, and each review is recorded as `self-review (inline default)`. It
starts no reviewer, test-runner or executor agent, even on a host that allows
agents at will. Ask for an independent review explicitly to add a fresh
read-only reviewer. To run the whole loop in a fresh native agent while this
conversation keeps working, use the sibling `improve-agent` skill; that agent
runs this same card inline.

## What happens in one callback

An active packet represents one complete review cycle. Before its exact done
callback, the executor reads the history and current candidate, plans worthwhile
authorized work, makes a warranted fix, runs applicable checks, and retains a
host-visible review record. An empty plan is valid only after a substantive
review finds no worthwhile change. A callback, retry, diagnostic command, or
repeated test is not another review.

Each completed cycle reports factual observations and a rolling handoff:

~~~json
{
  "classification": "trivial | non-trivial | unresolved",
  "exit_assessment": "satisfied | unsatisfied | unknown",
  "continuation_assessment": "allowed | blocked | cancelled",
  "evidence": "Concise, factual observations for this completed cycle",
  "handoff": "Complete current candidate, checks, decisions, receipts, gaps, and locators"
}
~~~

The first qualifying trivial report leaves the run active with a streak of one.
The second distinct qualifying report can be terminal only when the substantive
exit condition also has current evidence. The terminal response retains the
last report and context, then deletes the temporary state file.

## Context, handoff, and cold recovery

New standalone runs freeze the canonical request, original candidate scope and
baseline, authority such as commit or push limits, relevant environment/check
commands, and exact resource locators in context. Every context-bearing report
supplies a complete nonblank handoff that carries current candidate identity,
applied work, check results, receipts, decisions, and unresolved gaps.

Keep the full latest response. A fresh executor uses its read-only next command
to rehydrate the current packet, checks current artifacts, and performs its
assigned cycle before submitting a new callback. It does not replay an old done
command or infer a new candidate from a later commit or clean worktree. If the
temporary state file and latest response are both gone, the run cannot be
reconstructed honestly.

## Entry points and compatibility

| Situation | Binding and state | Boundary |
|---|---|---|
| New standalone Improve request | runtime/until-loop/scripts/until_loop_ephemeral.py through runtime/until-loop/ADAPTER.md | One private temporary file per run; no .until-loop state or collector. |
| Explicit durable v1/v2 continuation | [legacy-standalone.md](references/legacy-standalone.md) and retained runtime/until-loop/scripts/until-loop | Preserve the selected durable state, adapter, collector, and checked record. Never migrate it into a callback run. |
| ShipLoop v3/v4 whole-skill subcall | The new standalone callback binding with the exact ShipLoop marker in context.request | Preserve parent scope, commit policy, receipt, and return-route locators. Save exact child responses; only complete permits the normal parent return. A stopped child permits only an explicitly printed v4 parent reconciliation route. |

For a ShipLoop v3/v4 whole-skill subcall, commit verified scoped changes in the
bound worktree under the standalone policy, unless an explicit frozen no-commit
override applies. Report the commit SHA separately from caller delivery; the
parent owns integration. A child keeps the parent latest-packet receipt location
and exact parent return instruction or callback locator in context.resources.
An active or blocked child result does not invoke a parent callback. For a stopped
child, only the parent may use an explicitly printed v4 reconciliation callback
after collecting or confirming the worker stopped; this is not successful
completion. A worker never executes parent callbacks.

## Review contract

| Question | Default behavior |
|---|---|
| What gets reviewed? | An explicit file list, branch range, or baseline takes precedence. Otherwise freeze initial HEAD and review initial staged, unstaged, and relevant untracked work together with later edits from this run. |
| What do the seven messages mean? | Read their IDs, subjects, and bodies each cycle. They inform the plan but do not define the diff range or authorize unrelated changes. |
| What is material? | Behavior fixes, public-contract changes, security or data-integrity corrections, and missing required regression coverage are material. Non-semantic spelling, formatting, or explanatory polish can be trivial only with evidence behavior is unchanged. |
| When are commits made? | After applicable checks pass, commit authorized scoped work with Review, Plan, Changes, Validation, Key learnings, and Remaining work. Preserve unrelated staged and unstaged hunks. |
| What if a review changes nothing? | Keep an honest host record. Do not manufacture an edit or empty commit unless an explicit audit-commit-every-iteration request authorizes the identified no-change audit commit. |
| When is it complete? | The exit condition, current relevant checks, and every other requested condition are satisfied, with two distinct consecutive qualifying trivial/no-change reviews and no unresolved material finding. |

### Influences, decisions, and new learnings

Each verbose iteration record explains what shaped its consequential decisions
and what was learned. Connect the specific behavior, guarantee, limitation, or
argument in an influential technique, system, style, reference, or library to
the resulting choice. Where components interact, explain the ordering, ownership,
state, or failure boundary that made the interaction matter. Record meaningful
adaptations and rejected approaches, evidence, limits, and conditions for
revisiting the choice. A list of technologies or a generic claim that a source
was useful does not preserve that reasoning.

Weave genuinely influential prior commits into that account with their resolved
full IDs, subjects, and the particular lesson used. Follow older references only
when needed for a relevant decision; never inherit their citation lists. Keep
the complete reading inventory in review evidence. Original learnings deserve
the same detail when no prior commit helped, and later corroboration must not be
presented as the original cause of a decision. Preserve the existing commit
sections and no-commit/no-change rules; this adds no runtime state or reference
quota. See the required [decision rationale and learning guidance](references/callback-evidence.md#decision-rationale-and-learning).

The reusable obligations are in [review-policy.md](references/review-policy.md).
[callback-evidence.md](references/callback-evidence.md) explains the new
host-record and handoff boundary. [evidence-capture.md](references/evidence-capture.md)
remains the factual collector guide for explicitly selected legacy runs.

## Preview and installation

Dry run, preview, show how you interpret this, and do not execute show the
proposed scope, history window, one-cycle work, exit rule, continuation rule,
incomplete stops, assumptions, evidence needed, and first action. Preview does
not start a callback run, write loop notes, edit files, execute task checks,
stage, or commit. A later execution request rechecks current context.

SKILL.md is the sole public Improve entrypoint. Its internal runtime is
runtime/until-loop/, whose source card is deliberately named ADAPTER.md so
recursive discovery still finds only Improve. Install or distribute the whole
leaf. A successful installation does not establish that every host can execute
every project check.

This is Improve 0.3.0-rc.2. The bundled default Until Loop runtime is
0.4.0-rc.2. The package has a relocation regression and focused compatibility
checks; those checks do not prove universal model judgment, a completed
multi-host rollout, or a particular repository's review quality.

## Provenance and packaging boundary

The default callback runtime is vendored from
[whichguy/until-loop](https://github.com/whichguy/until-loop) commit
458f40ac35c8254906898890c25a784a6e3eb39c (runtime 0.4.0-rc.2). Its
scripts/until_loop_ephemeral.py is byte-identical to upstream, with SHA-256
6a4131f8a70b56a361556fbc61e924f060ebf1ba5d5f1387a6d6d735e89b4212.

[runtime/until-loop/PROVENANCE.json](runtime/until-loop/PROVENANCE.json)
records the upstream commit, version, source paths, and SHA-256 values for the
new default runtime, retained v1/v2 scripts, and the small package-local legacy
reference adaptations required by the renamed ADAPTER.md layout. The bundled
ADAPTER.md also clarifies owner-bound user updates versus changes to immutable
loop conditions; its provenance entry retains both upstream and bundled hashes
and the adaptation reason. The runtime Python script remains byte-identical.
The old durable
scripts, adapters, and collector remain only for explicit legacy calls; they are
not fallback behavior for a new request.

The source repository's tests, experiment output, validation manifests,
activation reports, working-checkout instructions, .git data, and bytecode are
intentionally excluded. They are not runtime dependencies. The package license
is [MIT](LICENSE); the nested runtime carries its upstream
[MIT license](runtime/until-loop/LICENSE).

## Research and release ownership

[The Improve research decision record in the source repository](https://github.com/whichguy/skill-craft/blob/main/docs/improve-research.md)
documents evaluated GitHub mechanisms, proposed pilot arms, controls, and
promotion criteria. It proposes no behavior change by itself.

The canonical package stays in skill-craft/skills/improve. Its version and
marketplace pin can advance independently through the existing installer,
plugin-view generator, and validation suite. Updating the bundled Until Loop
snapshot requires an explicit provenance update and compatibility checks.

## Maintainer validation

From the source repository, run:

~~~sh
PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH PYTHONDONTWRITEBYTECODE=1 bash test/improve.test.sh
PATH=/Library/Developer/CommandLineTools/usr/bin:$PATH PYTHONDONTWRITEBYTECODE=1 python3 test/improve-plugin.test.py
~~~

The package test relocates the leaf to a path with spaces, verifies the new
ephemeral start/next/done two-review terminal path and state deletion, and keeps
the read-only v2 preview plus collector compatibility checks. It does not run
arbitrary repository changes or prove semantic review quality.
