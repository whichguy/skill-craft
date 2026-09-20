# Ask Agent U18 worktree interface handoff

This records the user's subsequent correction to the
[accepted task charters](ask-agent-backchain-coordination-2026-09-18.md).
The accepted charter bytes and earlier acknowledgments remain unchanged.
The user now requires each Ask Agent worker to operate in a separate Git
worktree derived from the caller's current checkout, including staged and
unstaged changes, with parent-owned integration and removal. A separate
temporary result directory is not the requested design.

## Candidate and ownership

Ask Agent U18, version 0.4.0, is frozen at:
`/Users/dadleet/Documents/Codex/experiments/ask-agent-worktree-20260918T230504Z/frozen-U18/ask-agent`.

- `SKILL.md` SHA-256: `a1c08aa2a966b51103793e8432a0ad184f31fcdb088ec3c4186c812571f52bb5`.
- `references/git-integration.md` SHA-256: `557880e53a0e69a2a8ce599f368bedeacf42d95158ebc6593e03c7e35908c9e7`.

Ask Agent owns this generic prompt contract and native-host qualification.
Backchain continues to own concrete dispatcher worktree allocation, durable
attempt/inbox/ledger state, serialized integration and consumer qualification.
No new dispatcher, runtime script or model subprocess launcher was added.

## Interface changes

- Assignments and relevant policy go directly in the native launch prompt.
  Existing input files may be referenced; no generated context-file transport
  is required. Host logging/persistence remains host behavior.
- Start from the actual caller checkout and HEAD, even if already a linked
  worktree. Transfer staged and unstaged layers and non-ignored untracked inputs;
  preserve the source checkout/index and verify a consistent snapshot. Do not
  substitute primary/default branch or HEAD-only state.
- A caller-prepared worktree can be reused when exclusively assigned to this
  invocation and its equivalent baseline is verified. Otherwise prepare a new
  worktree before native dispatch. Fresh retries/nested tasks receive distinct
  worktrees; same-attempt collection/delivery retry retains its existing one.
- Keep inherited dirty state distinguishable from the worker-only contribution.
  A private baseline commit, if used, is not itself a contribution to merge.
- Multiple returned files live in the worker worktree, with a compact index.
  The native receipt identifies observed cwd, worktree root, baseline,
  contribution, results and recommended parent merge/remove/retain action.
- Worker leaves the worktree intact. Parent integrates and validates code before
  removal, or finishes consuming report-only results. Preserve required outputs
  and recovery references outside the worktree before removing it through Git.
  Durable dispatcher inbox/ledger/history must survive cleanup. Completion,
  accepted output, integrated code and removed worktree remain separate facts.

## Evidence and requested consumer action

Before native W1 launch, leaf package checks, generated marketplace checks,
real-Git mechanics and independent source review passed. Mechanics covered two
worktrees copied from a dirty linked feature checkout, dual staged/unstaged
layers, addition/deletion, binary/mode/symlink/untracked inputs, pricing-only
integration, source preservation, durable result retention and owned worktree
removal. This is not native-agent evidence.

Candidate/provenance and mechanics receipts are under
`/Users/dadleet/Documents/Codex/experiments/ask-agent-worktree-20260918T230504Z/operator/`.
Native W1 attempts now establish the exercised core lifecycle for Claude
Sonnet, Grok, Codex Luna/xhigh and OpenCode/Grok, with retained failures and
observation limits. See the
[candidate-specific results](../test/experiments/portable_delegation/usability/WORKTREE-RESULTS.md).
Claude's global SessionEnd hook added a source artifact, and compact lifecycle
reminders were omitted. OpenCode's completed attempt invented resume IDs and
misreported their rejection. Codex, Claude and OpenCode show task commands in
assigned worker worktrees while child startup cwd metadata inherits the caller.
Grok's corrected attempt launched from the actual dirty linked caller. Earlier
U16/U17 runs do not qualify U18; invalid/interrupted W1 attempts remain separate.

Test-only fixture/preflight/public-evidence/completion guards passed 20 offline
tests and a read-only check against actual OpenCode parent/child public records.
They add no Ask Agent runtime script or dispatcher and do not repair
participant mistakes or turn partial native qualification into an all-pass claim.

Backchain should review compatibility with its selected package and current
workspace helpers, retain the new interface as a pending consumer obligation,
and own any rebind/consumer smoke. Do not relabel the prior U16 consumer pilot
as U18-tested. This notice does not claim merge, install, push or publication.

## Consumer response

Backchain reviewed this notice and reports that its current chain route supplies
exclusive external sibling worktrees and retains durable dispatcher reports and
history, but requires a clean initiating target. Direct binding from a dirty
caller is therefore an outstanding U18 consumer gap. It also retained explicit
obligations for worker-contained output/index and merge/remove/retain receipts.
Its completed U16 pilot stays frozen; no U18 rebind or consumer qualification was
claimed. These are counterpart-reported compatibility findings, not a consumer
test rerun by the Ask Agent task.
