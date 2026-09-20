# U18 worktree handoff results

U18 is version 0.4.0. It supersedes the standalone temporary-report approach:
each native worker uses a separate Git worktree copied from the caller's actual
current checkout, including its staged and unstaged state. Multiple result files
live in that worktree. The parent owns integration and eventual removal.

## Frozen candidate and case

Campaign root:
`/Users/dadleet/Documents/Codex/experiments/ask-agent-worktree-20260918T230504Z`.

- Main SHA-256: `a1c08aa2a966b51103793e8432a0ad184f31fcdb088ec3c4186c812571f52bb5`.
- Git reference SHA-256: `557880e53a0e69a2a8ce599f368bedeacf42d95158ebc6593e03c7e35908c9e7`.
- Fixture: [W1 protocol](worktree-handoff/README.md); exact copied inputs and
  manifests are in `frozen-W1/` and `operator/PLAN-U18-W1.json` at the campaign root.

Earlier U15–U17 evidence remains attached to its frozen versions. No earlier
native run or Backchain consumer run is relabeled as U18 qualification.

## Checks completed before native launch

The source/generated package baseline passed before editing. U18 then passed
independent source review, leaf plugin parity/metadata checks and generated
marketplace checks. Only Ask Agent's catalog version changed; unrelated generated
entries were checked against their prior state.

The real-Git mechanics experiment passed in disposable repositories. It created
two workers from a linked feature worktree ahead of primary main, carried both
staged and unstaged layers (including both on one file), and preserved staged
addition/deletion, unstaged deletion, binary content, executable mode, symlink
and untracked input. Worker-only pricing integration preserved the caller's
index and unrelated content. Both owned worker worktrees were removed through
Git after required multi-file results were archived to a durable inbox.
Fixture branches were retained and enumerated. See the
[mechanics receipt](</Users/dadleet/Documents/Codex/experiments/ask-agent-worktree-20260918T230504Z/operator/MECHANICS.json>).
This proves the exercised Git operations, not native worker behavior.

## Native W1

Seven attempts were operated across Claude Sonnet, native Grok, Codex
Luna/xhigh and OpenCode/Grok. The model parents prepared their own worker
worktrees and used native agents. Operator errors remain separate from agent
behavior defects; reruns retain their own identities and evidence.

| Native attempt | Observed result | Retained qualification boundary |
| --- | --- | --- |
| Claude W1, Sonnet | Fresh workers, natural overlap, useful parent continuation, automatic returns, pricing-only integration, four archived reports and both worktrees removed. Original index/sentinels preserved. | Strict source cleanliness failed: an enabled global SessionEnd hook created an extra `tasks/` file. Child startup cwd inherited caller, although task commands used assigned worktrees. Compact worker and parent receipts omitted explicit lifecycle/owner reminders. |
| Codex W1, Luna/xhigh | Fresh native workers, overlap, useful continuation, timed wait/status, pricing-only integration, nine archived files and both worktrees removed. Original index/sentinels preserved. | Child startup cwd inherited caller; task commands used assigned worktrees. Encrypted child launch packets and full tool parity remain unobserved. Two tool-router rejections recovered. |
| Grok W1, grok-4.6 | Native workers, overlap/returns, dirty snapshot, pricing-only integration and archive/removal worked from an explicitly supplied source path. | Operator launched parent outside Git. This attempt does not qualify selection from the parent's current checkout. |
| Grok W1b, grok-4.6 | Corrected parent cwd is the dirty linked caller. Two fresh native workers in distinct worktrees returned; parent archived five files, integrated only pricing, preserved original dirty sentinels and removed both worktrees. | Corrected launch is a separate attempt; W1's directory error remains recorded. |
| OpenCode W1, grok-4.6 | Core Git operations occurred. | INVALID: operator diagnostic export contaminated the participant context. No qualification credit. |
| OpenCode W1b, grok-4.6 | Fresh native launches omitted resume IDs; overlap and worker returns observed. | INCOMPLETE: operator stopped parent before final integration/removal. Worktrees retained for recovery. |
| OpenCode W1c, grok-4.6 | Root waited for the actual final result. Native overlap/returns, useful continuation, five archived reports, pricing-only integration, sentinel/index preservation and both worktree removals passed. | Fresh-launch conformance failed: three invented UUID resume IDs were rejected, then invented `ses_` IDs were accepted. Parent final incorrectly suggested an omitted ID was rejected. Child startup directory inherited caller; command-scoped worker isolation observed. |

These observations establish the exercised core lifecycle in all four lanes,
with the stated defects; they do not establish uniform instruction compliance.
Each attempt's `RESULTS.json` / `RESULTS.md` is under its host/case directory at
the campaign root. W1c's public projection, terminal/filesystem gate and guarded
discovery cleanup receipt are retained under `opencode/W1c/operator/`.
Claude's hook attribution is retained under `claude/W1/operator/`.

## Harness improvements from these attempts

The test-only [operator guard](worktree-handoff/operator/verify-w1.py) and
[hermetic regression suite](../../../ask-agent-worktree-harness.test.py) address
repeatable fixture preparation, launch cwd/input checks, public-only diagnostic
projection and completion validation. They do not launch models, delegate work,
stop healthy runs, repair agent mistakes or remove worktrees. Native parent
launch and worker behavior remain the harness/skill's responsibility.

These guards were added after the frozen W1 campaign. Existing attempts were not
silently rerun through changed inputs. Their native qualification defects remain
visible; no passing apparatus test converts them into passing agent behavior.

The final apparatus suite passes 20 offline tests, and aggregate registration
passes its 14 tests. A read-only check against the completed OpenCode W1c parent
and both children projected 61/26/21 public records, verified their native
parent relationships, and retained five Task calls including three rejected
calls. No raw export was made. The adapter receipt is
`opencode/W1c/operator/HARNESS-ADAPTER-CHECK.json` at the campaign root.
These checks validate collection and deterministic guards, not a new model run.

Normal W1 covers textual dirty inputs and two tasks. Binary/symlink/mode checks
are mechanical evidence only. Non-Git handling, dirty submodules, concurrent
source writers, fresh task retries and nested worktree inheritance remain
outside this native case unless separately exercised. One run is not a general
reliability guarantee or proof of identical host capabilities.

Backchain's consumer compatibility and selected-package qualification are
separate responsibilities. The exact interface notice is in
[the U18 coordination handoff](../../../../docs/ask-agent-worktree-handoff-2026-09-18.md).
