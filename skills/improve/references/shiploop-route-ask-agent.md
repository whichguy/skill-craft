# Improve: the ShipLoop ask-agent route

Read this file only when the handoff's `Route:` line is `ask-agent`, beside [the core](shiploop-route.md), which holds the rules of every pass (the worker's too). It is the text that stood in every ask-agent handoff before it moved to the route (efficiency plan U18); "the receipt" is `CHILD/packet.json`. For recovery and the stopped child read [the recovery file](shiploop-route-recovery.md) too.

## Ask-agent route (`Route: ask-agent`)

Keep the invoking parent alive and follow Improve's selected context ownership.

Chain precedence ends at producer completion, even when the historical chain
binding remains. The fresh-context boundary belongs to the whole Improve
executor invocation, not the invoking parent and not individual review iterations.
Prefer the selected fresh native executor route; the parent retains collection,
verification and the exact parent-only continuation. Do not clear, replace or
wrap the live parent to satisfy the executor's freshness requirement. A generic
parent reset or manual handoff is not that fresh executor boundary.
Recover an existing child from its receipt and ownership record; collect or
confirm its owner stopped before any replacement. Once fresh for this invocation,
do not clear again or delegate the whole invocation again. If the selected route
is unavailable, use same-context execution only when its ownership policy allows
it and separate context was not explicitly required; otherwise keep this action
pending and report the missing capability. Retain the exact Recovery command
and child receipt locators for interruption recovery.

Parent assignment preparation: ShipLoop's opening (opening.md beside the receipt) holds the stage result, scope, authority and environment; put it first in the worker prompt and add this conversation's learnings, decisions and unresolved concerns (the navigator cannot supply conversation-only learnings). Then say 'Run /improve' with the selected card, the concrete run binding and this started child's receipt. Do not forward this entire parent packet or repeat the skill's execution instructions.

For a genuinely new invocation, after ShipLoop has started the child, run the host-selected improve-agent card for this bound child: it starts one fresh native worker that continues the already-started loop from the receipt's next_argv, with exclusive write ownership in the exact Child workspace, through the host-selected Ask Agent's ask-agent/consumer-owned-workspace/v1 route; never use Ask Agent's default extra-worktree route for this bound child. Read the context-ownership reference before launch or recovery (the handoff's `Improve context ownership:` line names it).

Workspace route: consumer-owned; delivery mode: in-place. Native assignment: execution_role: improve-executor; delegation_owner: parent. Freeze the exact candidate scope, selected packages, explicit user/repository authority including any no-commit override, evidence paths and parent continuation before dispatch. Existing invocations keep their recorded owner and frozen authority; unknown ownership blocks replacement.

ShipLoop's opening cannot hold this conversation's approvals, declines and pending decisions: state them, with action/target, conditions and authorization source, in the dispatch prompt, so the worker applies an approval without asking again and treats a decline as binding. Forward later user decisions through the native channel and record receipt/effect in host-owner.md and the worker handoff; keep launch context immutable and continue the same child.

Parent-only return: the worker continues the child from the receipt and writes its review files, then returns their locators without executing ShipLoop callbacks other than improve-pass and improve-commit, or workspace return. The parent collects and verifies the result before executing the exact return route in the handoff. Worker completion alone never advances this action.

Binding inputs: before dispatch, verify the selected cards, runtime and referenced inputs exist and match this candidate and action. Keep workspace, scope, authority and return ownership explicit. The child packet receipt and review files are output destinations for a new child, not pre-start inputs; a resumed child requires its saved receipt. A missing input leaves dispatch pending; never substitute an ambient skill or another workspace.
