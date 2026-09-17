# Worktree baseline and return experiments

Date: 2026-09-16. These were disposable real-Git experiments, not a full hosted
ShipLoop run or a claim that a production branch was integrated. Normal host Git
was blocked by the local Xcode license, so the preinstalled fallback Git was
placed first on PATH. No installation, source-index rewrite, stash, source
commit or push was performed in the real skill-craft checkout.

## Questions and observations

| Experiment | Observed result | Design implication |
| --- | --- | --- |
| Start a worktree from HEAD with staged/unstaged source edits and an untracked input | Worktree contained committed `base`, not source's `unstaged`; untracked input absent | Capture the working baseline explicitly; branch identity alone is insufficient |
| Reconstruct cached and working changes through an alternate index and isolated checkout | Reconstructed staged/unstaged contents; original index hash and status unchanged | Do not stash/reset or consume the original index to set up isolation |
| Apply a baseline-relative patch with plain `git apply` | Working changes applied, index hash unchanged; new path remained unindexed | Dirty return can preserve original staging, but must honestly be called working-tree return, not merge |
| Commit then delete a transient artifact before fast-forwarding | Artifact absent at tip but both add/delete commits remained reachable | Review/filter commit history too; a clean final file listing is not enough |
| Helper implementer's alternate-index snapshot with selected untracked input | Isolated baseline contained the combined tracked working contents and selected input; original status/index unchanged | Include untracked inputs deliberately; do not copy ignored credentials/caches |
| Clean source and clean committed isolated candidate | `git merge --ff-only` succeeded | Retain true merge for clean-start cases instead of forcing all returns through patch application |

The first investigator retained its disposable fixture at
`/tmp/shiploop-worktree-audit.JsXXqO`; the helper implementer's proof was at
`/tmp/shiploop-workspace-proof.SYRArE`. These temporary locations are diagnostic
provenance, not persistent dependencies or consumer artifacts.

## Decision

Adopt an explicit isolated start in the skill's normal Git workflow and a small
workspace adapter, keeping the existing SDLC graph and Improve campaign model.
Reject auto-stashing the source, fast-forwarding a private dirty snapshot,
blindly copying all untracked files, or assuming `.gitignore` removes tracked
artifacts/history. Keep existing saved protocols unchanged.

Current branch plus tracked staged/unstaged contents are captured in isolation.
The final path review is candidate-bound; return checks original source state.
Clean starts may fast-forward only a safe committed candidate. Dirty starts
return only the new delta and preserve the source index. Handoff is gated on the
actual return receipt for the new workspace mode. This does not authorize a
push, deployment, or automatic cleanup.

## Verification boundary

The initial experiments covered ordinary file behavior, not every Git feature.
The automated companion `test/shiploop-workspace.test.py` supplies executable
regressions and documents unsupported cases through fail-closed expectations.
Repository text and path classifications remain host judgment. Neither these
tests nor a synthetic navigator walk prove that an LLM performed the review,
that remote environment isolation exists, or that a hosted app was updated.
