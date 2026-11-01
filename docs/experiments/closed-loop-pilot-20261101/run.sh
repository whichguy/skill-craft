#!/usr/bin/env bash
# Stage 4 pilot of docs/shiploop-e2e-closed-loop-plan-2026-10-30.md: a known-bad candidate must not be promoted.
#
#   run.sh CONTROL_SHA OUTPUT_DIR
#
# CONTROL_SHA   the commit that holds this kit. It is the evaluator checkout and the control build.
# OUTPUT_DIR    a folder that does not exist yet, outside every checkout. Worktrees, builds and the cycle's output go here.
#
# The candidate is the control without the qualified missing-completion hook: the reverse of the source delta between
# 779980629a81ce0e740f7c196e83e000dd582d99 (control of 07734b9f's pair) and 7f25acff8dab239485f262249ec70773ba906aad
# (its candidate), minus the change note a release already consumed. Nothing here edits the repository at $SKILL_CRAFT_REPO
# except adding and removing two detached worktrees; no commit is made and nothing is pushed.
#
# Environment: SKILL_CRAFT_REPO (default ~/src/skill-craft) only supplies git objects; PARALLEL (default 3) is the number
# of subject runs at once; DRY_RUN=1 stops after the two builds are made and shown to differ, before any model call.
# See README.md for what to expect and what to return.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1

control_sha=${1:?usage: run.sh CONTROL_SHA OUTPUT_DIR}
out=${2:?usage: run.sh CONTROL_SHA OUTPUT_DIR}
repo=${SKILL_CRAFT_REPO:-$HOME/src/skill-craft}
kit=docs/experiments/closed-loop-pilot-20261101
hook_before=779980629a81ce0e740f7c196e83e000dd582d99
hook_after=7f25acff8dab239485f262249ec70773ba906aad

if [ -e "$out" ]; then
  echo "run.sh: $out exists; choose a folder that does not" >&2
  exit 2
fi
mkdir -p "$out"

git -C "$repo" fetch -q origin
git -C "$repo" cat-file -e "$control_sha^{commit}" || { echo "run.sh: $control_sha is not a commit of $repo" >&2; exit 2; }
git -C "$repo" worktree add -q --detach "$out/control-tree" "$control_sha"
git -C "$repo" worktree add -q --detach "$out/candidate-tree" "$control_sha"

# The candidate tree: refuse loudly when the reverse does not apply, never half-apply it.
git -C "$out/candidate-tree" diff "$hook_before" "$hook_after" -- . ':!changes' > "$out/hook-delta.patch"
git -C "$out/candidate-tree" apply -R --check "$out/hook-delta.patch"
git -C "$out/candidate-tree" apply -R "$out/hook-delta.patch"
git -C "$out/candidate-tree" diff --stat > "$out/candidate-vs-control.stat"

python3 -B "$out/control-tree/scripts/build-packages.py" "$out/control-build" > /dev/null
python3 -B "$out/candidate-tree/scripts/build-packages.py" "$out/candidate-build" > /dev/null

cp "$out/control-tree/$kit/pilot-ledger.jsonl" "$out/ledger.jsonl"
record=$(python3 -I -c 'import json, sys; print(json.loads(open(sys.argv[1]).readline())["record"])' "$out/ledger.jsonl")

cd "$out/control-tree"
digest='import sys; from pathlib import Path; sys.path.insert(0, "test/shiploop_e2e"); import run; print(run.tree_digest(Path(sys.argv[1])))'
control_digest=$(python3 -B -c "$digest" "$out/control-build/plugins/skill-craft")
candidate_digest=$(python3 -B -c "$digest" "$out/candidate-build/plugins/skill-craft")
echo "control build $control_digest, candidate build $candidate_digest"
if [ "$control_digest" = "$candidate_digest" ]; then
  echo "run.sh: the two builds are identical; there is nothing to compare" >&2
  exit 2
fi
if [ "${DRY_RUN:-}" = 1 ]; then
  echo "dry run: stopping before any model call (worktrees and builds are under $out)"
  exit 0
fi
status=0
python3 -B test/shiploop_e2e/cycle.py --record "$record" --case hello-hook-continuation \
  --tolerance 0.25 --attempts 3 --host codex --model gpt-6.1-terra --effort high --parallel "${PARALLEL:-3}" \
  --skip-reviews \
  --control-plugin "$out/control-build/plugins/skill-craft" \
  --candidate-plugin "$out/candidate-build/plugins/skill-craft" \
  --prediction "$kit/prediction.json" --ledger "$out/ledger.jsonl" --output "$out/cycle" || status=$?

# What to return: small, text, byte-exact. The raw run folders stay where they are.
mkdir -p "$out/results"
cp "$out/ledger.jsonl" "$out/results/ledger.jsonl"
cp "$out/candidate-vs-control.stat" "$out/results/candidate-vs-control.stat"
for name in entry.md cycle-result.json epoch-verdict.json; do
  [ -f "$out/cycle/$name" ] && cp "$out/cycle/$name" "$out/results/$name"
done
python3 -B test/shiploop_e2e/epoch.py --output "$out/cycle/epoch" status > "$out/results/epoch-status.json" 2>&1 || true
echo "cycle.py exit status: $status (0 PROMOTE, 3 DROP, 4 UNDECIDED, other: it did not decide)"
echo "$status" > "$out/results/cycle-exit-status.txt"
exit 0
