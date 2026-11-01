#!/usr/bin/env bash
# Stage 4b of docs/shiploop-e2e-closed-loop-plan-2026-10-30.md: a build that restores a verified fix must be promoted, with
# every attempt reviewed and judged. The mirror of the stage 4 pilot (docs/experiments/closed-loop-pilot-20261101).
#
#   run.sh BASE_SHA OUTPUT_DIR
#
# BASE_SHA      the commit that holds this kit. It is the evaluator checkout and the CANDIDATE build.
# OUTPUT_DIR    a folder that does not exist yet, outside every checkout. Worktrees, builds and the cycle's output go here.
#
# The control is the candidate without the qualified missing-completion hook: the reverse of the source delta between
# 779980629a81ce0e740f7c196e83e000dd582d99 (control of 07734b9f's pair) and 7f25acff8dab239485f262249ec70773ba906aad
# (its candidate), minus the change note a release already consumed. The candidate is BASE itself, which has the hook, so it
# restores what the control lacks. Nothing here edits the repository at $SKILL_CRAFT_REPO except adding and removing two
# detached worktrees; no commit is made and nothing is pushed.
#
# Unlike the stage 4 pilot this does not skip the reviews: every sealed attempt is reviewed and judged by the roles'
# defaults (Codex gpt-6-astra at xhigh), one after another under the epoch lock.
#
# Environment: SKILL_CRAFT_REPO (default ~/src/skill-craft) only supplies git objects; PARALLEL (default 3) is the number
# of subject runs at once; EFFORT (default xhigh) is the subject's reasoning effort, Codex with Terra 6.1 at Extra High as the
# owner asked on 2026-11-01; DRY_RUN=1 stops after the two builds are made and shown to differ, before any model call.
# See README.md for what to expect and what to return.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
# A sealed attempt's receipt binds every run that overlapped it inside the runs root. Unset, that root is the epoch's own folder,
# so only the epoch's attempts are neighbours, and epoch.settle_siblings waits for exactly those.
unset SHIPLOOP_E2E_RUNS_ROOT

base_sha=${1:?usage: run.sh BASE_SHA OUTPUT_DIR}
out=${2:?usage: run.sh BASE_SHA OUTPUT_DIR}
repo=${SKILL_CRAFT_REPO:-$HOME/src/skill-craft}
kit=docs/experiments/closed-loop-restore-20261101
hook_before=779980629a81ce0e740f7c196e83e000dd582d99
hook_after=7f25acff8dab239485f262249ec70773ba906aad
effort=${EFFORT:-xhigh}

if [ -e "$out" ]; then
  echo "run.sh: $out exists; choose a folder that does not" >&2
  exit 2
fi
mkdir -p "$out"

git -C "$repo" fetch -q origin
git -C "$repo" cat-file -e "$base_sha^{commit}" || { echo "run.sh: $base_sha is not a commit of $repo" >&2; exit 2; }
git -C "$repo" worktree add -q --detach "$out/control-tree" "$base_sha"
git -C "$repo" worktree add -q --detach "$out/candidate-tree" "$base_sha"

# The control tree: refuse loudly when the reverse does not apply, never half-apply it.
git -C "$out/control-tree" diff "$hook_before" "$hook_after" -- . ':!changes' > "$out/hook-delta.patch"
git -C "$out/control-tree" apply -R --check "$out/hook-delta.patch"
git -C "$out/control-tree" apply -R "$out/hook-delta.patch"
git -C "$out/control-tree" diff --stat > "$out/control-vs-candidate.stat"

python3 -B "$out/control-tree/scripts/build-packages.py" "$out/control-build" > /dev/null
python3 -B "$out/candidate-tree/scripts/build-packages.py" "$out/candidate-build" > /dev/null

cp "$out/candidate-tree/$kit/restore-ledger.jsonl" "$out/ledger.jsonl"
record=$(python3 -I -c 'import json, sys; print(json.loads(open(sys.argv[1]).readline())["record"])' "$out/ledger.jsonl")

cd "$out/candidate-tree"
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
  --tolerance 0.25 --attempts 3 --host codex --model gpt-6.1-terra --effort "$effort" --parallel "${PARALLEL:-3}" \
  --control-plugin "$out/control-build/plugins/skill-craft" \
  --candidate-plugin "$out/candidate-build/plugins/skill-craft" \
  --prediction "$kit/prediction.json" --ledger "$out/ledger.jsonl" --output "$out/cycle" || status=$?

# What to return: text, byte-exact. The raw run folders stay where they are.
mkdir -p "$out/results"
cp "$out/ledger.jsonl" "$out/results/ledger.jsonl"
cp "$out/control-vs-candidate.stat" "$out/results/control-vs-candidate.stat"
for name in entry.md cycle-result.json epoch-verdict.json; do
  [ -f "$out/cycle/$name" ] && cp "$out/cycle/$name" "$out/results/$name"
done
[ -f "$out/cycle/epoch/events.jsonl" ] && cp "$out/cycle/epoch/events.jsonl" "$out/results/epoch-events.jsonl"
if [ -d "$out/cycle/epoch/receipts" ]; then
  mkdir -p "$out/results/receipts"
  cp "$out"/cycle/epoch/receipts/*.json "$out/results/receipts/" 2>/dev/null || true
fi
python3 -B test/shiploop_e2e/epoch.py --output "$out/cycle/epoch" status > "$out/results/epoch-status.json" 2>&1 || true
echo "cycle.py exit status: $status (0 PROMOTE, 3 DROP, 4 UNDECIDED, other: it did not decide)"
echo "$status" > "$out/results/cycle-exit-status.txt"
exit 0
