#!/usr/bin/env bash
# Stage 5 of docs/shiploop-e2e-closed-loop-plan-2026-10-30.md: one full qualified cycle, on the machine that holds Codex's login.
#
#   run.sh BASE_SHA OUTPUT_DIR
#
# BASE_SHA      the commit the loop starts from. It is the evaluator checkout, the control build and the loop tip.
# OUTPUT_DIR    a folder that does not exist yet, outside every checkout. The worktree, the loop's output and the results go here.
#
# `iterate.py --qualify` makes its own worktree and branch (auto/shiploop-loop-<hex>) from that checkout. With no record this
# cycle can take (select reads the cycle's cases), it explores seat-reservations on the tip: one run, reviewed and judged, whose
# material findings open and admit records. It then applies one record with an improver, checks the change serves the record,
# registers a promotion/5 epoch (a stated tolerance of 0.25 and 3 attempts per arm, recorded as unmeasured), runs both cases for
# both arms, reviews and judges every attempt, decides, and records the prediction's verdict and a journal entry on the loop
# branch. A PROMOTE keeps the candidate on that branch; anything else keeps it only as refs/shiploop-loop/<loop>/<record>.
# Nothing here pushes, commits to main or edits the repository at $SKILL_CRAFT_REPO beyond adding its own detached worktree.
#
# Environment: SKILL_CRAFT_REPO (default ~/src/skill-craft) only supplies git objects; PARALLEL (default 3) is the number of
# subject runs at once. See README.md for what to expect and what to return.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
# A sealed attempt's receipt binds every run that overlapped it inside the runs root. Unset, that root is the epoch's own folder,
# so only the epoch's attempts are neighbours, and epoch.settle_siblings waits for exactly those; a root shared with other
# sessions' runs would bind runs this cycle cannot wait for.
unset SHIPLOOP_E2E_RUNS_ROOT

base_sha=${1:?usage: run.sh BASE_SHA OUTPUT_DIR}
out=${2:?usage: run.sh BASE_SHA OUTPUT_DIR}
repo=${SKILL_CRAFT_REPO:-$HOME/src/skill-craft}

if [ -e "$out" ]; then
  echo "run.sh: $out exists; choose a folder that does not" >&2
  exit 2
fi
mkdir -p "$out"

git -C "$repo" fetch -q origin
git -C "$repo" cat-file -e "$base_sha^{commit}" || { echo "run.sh: $base_sha is not a commit of $repo" >&2; exit 2; }
git -C "$repo" worktree add -q --detach "$out/tree" "$base_sha"

cd "$out/tree"
status=0
python3 -B test/shiploop_e2e/iterate.py --qualify --case seat-reservations --generality-case csv-report \
  --tolerance 0.25 --attempts 3 --host codex --model gpt-6.1-terra --effort high --iterations 1 \
  --parallel "${PARALLEL:-3}" --output "$out/loop" > "$out/loop-stdout.txt" 2>&1 || status=$?

# What to return: small, text, byte-exact. The raw run folders stay where they are.
mkdir -p "$out/results"
echo "$status" > "$out/results/iterate-exit-status.txt"
cp "$out/loop-stdout.txt" "$out/results/loop-stdout.txt"
[ -f "$out/loop/LOOP.md" ] && cp "$out/loop/LOOP.md" "$out/results/LOOP.md"
for stage in "$out"/loop/cycle-* "$out"/loop/explore-*; do
  [ -d "$stage" ] || continue
  name=$(basename "$stage")
  mkdir -p "$out/results/$name"
  for file in cycle-result.json epoch-verdict.json epoch-registration.json prediction.json purpose-1.json purpose-2.json; do
    [ -f "$stage/$file" ] && cp "$stage/$file" "$out/results/$name/$file"
  done
  [ -f "$stage/run/result.json" ] && cp "$stage/run/result.json" "$out/results/$name/exploration-result.json"
  [ -d "$stage/epoch" ] && python3 -B test/shiploop_e2e/epoch.py --output "$stage/epoch" status > "$out/results/$name/epoch-status.json" 2>&1 || true
done
branch=$(sed -n 's/^  branch: *//p' "$out/loop-stdout.txt" | tail -1)
{
  echo "base: $base_sha"
  echo "loop branch: ${branch:-unknown}"
  [ -n "$branch" ] && git -C "$repo" log --format='%H %an %s' "$base_sha..$branch" 2>/dev/null || true
  echo "kept candidates:"
  git -C "$repo" for-each-ref --format='%(objectname) %(refname)' refs/shiploop-loop/ 2>/dev/null || true
} > "$out/results/branches.txt"
echo "iterate.py exit status: $status; loop branch: ${branch:-unknown}"
exit 0
