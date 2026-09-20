# Ask Agent native workspace routing

Status: implementation, core checks and bounded experiments completed. Per-host
qualification limits are recorded in `ask-agent-routing-results-2026-09-20.md`.
This plan extends the 0.5.1 delivery contract; it does not replace prior evidence.

## Outcome and boundaries

Ask Agent owns faithful Git workspace preparation and result preservation. The
current host owns fresh asynchronous workers and delivery back to the initiating
conversation. A parent supplies the task and calls the packaged helper; it must
not recreate worktree setup. Keep native task transport, workspace binding,
contribution delivery and cleanup as separate responsibilities.

Preserve the staged/unstaged/untracked snapshot contract, patch/commits/report-only
delivery modes, conservative close, native permissions, and existing user work.
User clarification: assume the calling branch/worktree may be dirty on every
invocation, including a second-generation helper worktree. Automatically replay
the staged Git patch into the new index, then the unstaged patch into its working
files. The caller must not commit, stash, clean up, or manually provide a patch.
Do not add a scheduler, model subprocess launcher, global hooks, credentials,
services, or silent synchronous fallback. Test-only external host invocations are
confined to disposable fixtures and retained experiment artifacts.

## Research decisions

| Candidate | Benefit | Cost / boundary | Initial decision |
| --- | --- | --- | --- |
| Native worker cwd argument | Exact startup directory and native task lifecycle | Only available on some tool schemas | Adopt where exposed; Grok Build has prior live proof |
| Explicit per-operation directory | Portable with current tools | Does not bind startup instructions or sandbox roots | Adopt with machine-derived context checks |
| Claude EnterWorktree on an existing helper workspace | Potential native binding without a creation adapter | Child availability and permissions must be observed | Experiment before adoption |
| Claude scoped WorktreeCreate hook | Native isolation can use helper-owned snapshot | Hook scope, concurrency, receipt discovery and early cleanup need proof | Pilot only if simpler native entry is inadequate |
| Codex App Server, Cursor ACP/SDK, OpenCode server | Explicit session directory, events, cancellation APIs | New client owns lifecycle and callback bridge to this conversation | Defer runtime adoption; document separately from native subagents |
| More prose claiming cwd or universal commits-only delivery | Low implementation effort | Does not establish actual execution directory; loses dirty-snapshot semantics | Reject |

Primary references checked on 2026-09-20: [Claude worktrees](https://code.claude.com/docs/en/worktrees),
[Claude hooks](https://code.claude.com/docs/en/hooks#worktreecreate),
[Grok Build subagents](https://docs.x.ai/build/features/subagents),
[Cursor subagents](https://cursor.com/docs/subagents),
[Cursor ACP](https://cursor.com/docs/cli/acp),
[Cursor SDK](https://cursor.com/docs/sdk/typescript),
[Codex App Server](https://developers.openai.com/codex/app-server),
[OpenCode server](https://opencode.ai/docs/server/), and the
[OpenCode 1.18.31 task implementation](https://raw.githubusercontent.com/anomalyco/opencode/v1.18.31/packages/opencode/src/tool/task.ts).
The locally generated Codex 0.155.1 ThreadStartParams schema has a cwd field;
that client API is not the current native spawn-agent schema.

## Implementation sequence

1. Run the existing core baseline before edits and retain its exact outcome.
2. Add a read-only `check-context` helper operation deriving real cwd and Git root
   from its process and binding them to the receipt. Test wrong roots, nested
   repositories, misleading environment values, and valid changed workspaces.
3. Split test verdicts into native launch, continuation, return, workspace
   binding, caller preservation, delivery/acceptance, and retention/cleanup.
   Preserve the existing strict overall gate and immutable old results.
4. Run minimal Claude experiments to choose between native existing-worktree
   entry, explicit operation directories, and a scoped creation hook. Verify
   actual tools and directories, not only final worker claims. Then test the
   selected route with dirty inputs and the current packaged skill.
5. Reorganize the skill around a short common lifecycle and separately loaded
   host recipes. Keep one delivery clause and one helper CLI. Record exact
   supported surfaces, native startup binding versus operation binding, and
   notification versus join evidence without treating model names as harnesses.
6. Run focused regression tests, current-package live checks where behavior
   changed, independent review, core aggregate, and generated-package parity.
   Include a two-generation dirty-worktree test so preparation from an existing
   helper worktree cannot accidentally fall back to the repository's main root.

## Acceptance

- The selected Claude route has evidence for actual helper-root operations,
  independent parent work, native return, caller preservation and retained work.
- Host-specific recipes use observed schemas and disclose qualification gaps.
- Wrong-directory and missing-callback evidence fail the appropriate layer;
  neither can be hidden by successful file delivery or process exit.
- Required report bytes survive cleanup. Failed/unsupported experiments remain
  recorded and cannot be converted into passes.
- Changes remain local; no publication or global host configuration is implied.

Evidence root: `/Users/dadleet/Documents/Codex/experiments/ask-agent-routing-20260920T141216Z/`.
