#!/bin/zsh
# Build the pinned R2 harness checkout for E-EFF1: a git worktree at BASE (default: the skill-craft 2.9.0 release commit) with the
# experiment's harness changes applied on top as UNCOMMITTED changes. Nothing in the canonical checkout's working tree is read
# for writing, moved, stashed or reset: every input is a copy kept in this folder (tracked-changes.patch, files/).
#   zsh make_r2_harness.sh [BASE]        # prints the worktree path
# Why a worktree: the canonical checkout moves under the experiment (another session rebased it onto origin/main on 2026-10-24
# and 13 more harness commits are due), the harness imports ShipLoop's modules from its own checkout, and the marketplace gate
# refuses unpublished local commits, so the experiment's changes must stay uncommitted on a published base.
set -euo pipefail
REPO=/Users/dadleet/src/skill-craft
HERE=${0:A:h}
BASE=${1:-31933a73}                       # skill-craft 2.9.0 / ShipLoop 1.9.0
git -C $REPO merge-base --is-ancestor $BASE origin/main   # the gate wants a published base
RAND=$(openssl rand -hex 3)
WT=$REPO/.claude/worktrees/eeff1-r2-$RAND
git -C $REPO worktree add -q -b rehearse/eeff1-r2-$RAND $WT $BASE
git -C $WT apply --3way $HERE/tracked-changes.patch            # 7 tracked files; --3way merges where the base moved
cp $HERE/files/effort.py $WT/test/shiploop_e2e/effort.py
mkdir -p $WT/skills/rubric-eval/suites $WT/docs/experiments/shiploop-effort-by-stage-20261024
cp -R $HERE/files/shiploop-run $WT/skills/rubric-eval/suites/shiploop-run
cp $HERE/files/run_totals.py $WT/docs/experiments/shiploop-effort-by-stage-20261024/run_totals.py   # test/shiploop-e2e-slice.test.py imports it
echo $WT
