---
name: improve
description: >-
  Use when a repository candidate needs a deliberate review-and-improvement
  loop: use recent Git history, make warranted changes, run meaningful checks,
  and repeat until two consecutive passes make no changes, or the first pass
  completes with no change. Supports a read-only interpretation preview; not a
  one-off code review.
version: 0.5.0
license: MIT
platforms:
  - linux
  - macos
metadata:
  short-description: Review and improve until two clean passes
  skill_craft:
    kind: script-backed
---

# improve

Use the shared [Improve review policy](references/review-policy.md) to turn
“improve these changes” into a bounded review-and-improvement contract. This
standalone card binds that reusable policy to Until Loop's single-file callback
runtime. It does not create a second state machine or invoke `/goal`.

Pick the route first. A ShipLoop review (the argument `ShipLoop Improve: <handoff path>`)
follows "ShipLoop whole-skill subcall" below and reads [the ShipLoop route](references/shiploop-route.md)
once per context. Any other invocation (`/improve`, an `improve-agent` worker) reads
[the standalone route](references/standalone-route.md) in full before interpreting or executing; it
holds the standalone binding, context-loss continuation, completion summary, preview and execution
handoff, and has you read the shared policy in full.

Improve is an execution-capable coding agent, not an audit-only role. Within the
selected entrypoint's task and authority, use the available tools, MCP
interactions and skills to investigate, produce or revise code, tests, documents
and configuration, and perform authorized deployments or other operations.
Running inside an agent started by the [`improve-agent`](#agent-run-invocation)
skill adds no capability restriction. Carry existing authorization forward and
disclose actual host capability gaps. Parent-only control callbacks remain with
their owner.

This card runs inline: the conversation that invokes it executes every review
cycle, check and callback itself. It never hands the invocation, a review or a
check run to another agent unless an independent review is explicitly requested
(see [Agents and independent review](references/standalone-route.md#standalone-owner-binding)). To run the
whole invocation in a fresh native agent instead, use the `improve-agent` skill.

Use your judgment to find worthwhile improvements, including consequential
issues the initiating context did not anticipate. Suggested fixes are starting
points, not an exhaustive checklist or a ceiling on review depth or change size.
Choose the investigation and implementation needed for the candidate; preserve
the actual scope and accepted requirements. Complete meaningful checks, commit
authorized changed files according to the binding, and continue after material
changes until the selected loop's completion condition is met.

For the standalone entrypoint, this package bundles its Until Loop runtime at
[runtime/until-loop/ADAPTER.md](runtime/until-loop/ADAPTER.md). Resolve symlinks
to this card's physical directory before resolving relative links. Read that
bound card in full and follow its current adapter. The package-relative binding
is authoritative: do not substitute a separately installed runtime, an older
card, or an ambient same-named skill.

## Installed package binding

Start with the absolute path of the **selected, loaded** `SKILL.md` supplied by
the host. If the host exposes a selected skill-root alias, expand that alias
first. Keep that logical `SKILL_ROOT` as the host's selected identity; it is not
the target repository cwd, an author checkout, `PATH`, a same-named skill, or a
guessed cache. Claude Code may render `${CLAUDE_SKILL_DIR}` in card text where
supported, but it is not a portable shell environment variable.

```sh
# Replace this illustrative path with the selected absolute location before running.
SKILL_ROOT="/absolute/directory-containing-the-loaded-SKILL.md"
RUNTIME_SCRIPT="$SKILL_ROOT/runtime/until-loop/scripts/until_loop_ephemeral.py"
```

The exact package-relative script locator for a standalone run is
`runtime/until-loop/scripts/until_loop_ephemeral.py`. Its ordinary start must
use `start --isolated`: upstream 0.9.0 also provides host-session mode and
session/recovery helpers, but Improve keeps its own per-run temporary callback
state. Contract/Receipt parent calls continue to use the adapter's receipt-backed
isolated route. The bound adapter is the only CLI caller: it translates
natural-language intent into its internal contract, starts or resumes the
selected run, and consumes the exact callback it returns. Do not make the user
supply JSON or fixed runtime arguments. A skill-directory or marketplace
installation must keep this entire package tree together; the nested runtime is
an internal dependency, not a second standalone parent.

Standalone runs use that per-run temporary callback state. Do not replace
`RUNTIME_SCRIPT` with an ambient Until Loop installation. If Python, the
bundled file, or a repository prerequisite is missing, report that condition
rather than silently changing runtimes.

## ShipLoop whole-skill subcall

When this skill is invoked with the argument `ShipLoop Improve: <handoff path>`,
read that handoff file with a file-reading tool, not cat (the shell cuts it):
ShipLoop wrote it for one child, and it plays the role of
"the ShipLoop packet" in this section. When it (or a ShipLoop packet) names a
selected actual Improve card and prints a
`ShipLoop standalone Improve binding: <binding-id>` marker, this is a
**standalone whole-skill subcall**. Read [the ShipLoop route](references/shiploop-route.md)
once per context: it applies this card's standalone owner binding and the
Until Loop runtime's loop rules to a ShipLoop child and holds what the handoff leaves out. Preserve the
exact binding marker in the child `context.request`. The ShipLoop packet supplies the bounded
candidate scope, permitted paths, current producer result, relevant work-item
`context`, evidence/reference locators, return route, and authority constraints;
retain those as frozen child-contract constraints rather than inventing an
alternate ShipLoop review protocol.

Treat a parent-provided candidate inventory as scope separately from Git
history. Retain every named included path, including relevant untracked product
or requirements artifacts, when the initial commit is empty or `HEAD` does not
move. Keep explicitly excluded scratch or pre-existing user paths outside that
candidate. When the inventory is large, retain one exact inventory locator
rather than recopying every path into each review record.

ShipLoop starts the child itself when its Improve stage begins: it writes the
opening from the run's state, freezes the child contract (binding line,
workspace, conditions, commit policy and return locators) and starts the bound
runtime with the receipt. Read the printed host receipt and continue the child
from it: for `active` status run its `next_argv` once, then follow the returned
instruction. Do not write the opening or start the runtime yourself. The runtime
writes every child packet to the receipt itself, the terminal packet before it
deletes its state, and ShipLoop imports only a packet written that way. Never
write or edit that receipt by hand.

The child `context.resources` must retain the parent latest-packet receipt
location, the exact parent return instruction or callback locator, and the
printed host receipt path for the child response. These locators make a terminal
child packet sufficient for a fresh host to save its exact response at the
required receipt path and then return through the parent route. Do not infer a
different route from a remembered parent state.

The ShipLoop child follows the standalone binding's ordinary commit policy: after
required checks pass, commit authorized scoped changes in the bound candidate
worktree and retain the commit SHA in its handoff. When the ShipLoop packet
prints, or `parent-return.md` lists, an `improve-commit` command, write the commit message to the file it names
with a file-writing tool and run that command: ShipLoop commits exactly the files
the review changed; do not use a shell heredoc or `git commit` for it. Stage only intended paths;
never include runtime receipts or unrelated inherited staging. An explicit
user- or repository-authorized no-commit override, including a frozen override
from an existing invocation, remains binding. Commit authority does not grant
merge, push, parent callback, or broader scope authority. Improve owns its review iterations and
temporary Until Loop handle; ShipLoop keeps the parent graph action pending and
imports accepted child evidence once. Reopen only relevant parent locators for
cold recovery, and retain concise current decision/revalidation locators in the
child handoff. Do not use an ambient Until Loop runtime for this ShipLoop route.

For an `active` or `blocked` child response, do not call a parent callback.
Follow the child packet or report its incomplete state through the recorded
recovery route. For `stopped`, preserve the exact terminal packet and evidence
and return their locators. Only when a ShipLoop v4 packet explicitly prints its
parent-only stopped-child reconciliation callback may the parent, after
collecting or confirming the worker stopped, use that exact callback. The worker
never executes it; no other stopped child advances the parent. After a successful
`complete` response is at the printed host receipt path (the runtime wrote it
there), the parent may use its exact normal return route.

## Agent-run invocation

This card never dispatches itself. The `improve-agent` skill starts one fresh
native agent and has it run this card there; its card owns that dispatch, the
assignment layout, the worker contract and the parent's verification. A native
assignment marked `execution_role: improve-executor` and
`delegation_owner: parent` is such an agent: follow the worker contract its
assignment carries, composed from the `improve-agent` card, and run this card
inside that agent exactly as a direct inline invocation, in the assignment's
workspace and under its frozen authority. Do not dispatch the invocation again.

