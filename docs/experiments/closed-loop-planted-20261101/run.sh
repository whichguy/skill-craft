#!/usr/bin/env bash
# Stage 5b of docs/shiploop-e2e-closed-loop-plan-2026-10-30.md: a full qualified cycle on a PLANTED fault, on the machine that
# holds Codex's login. An instrument test: it gives the loop a real, mechanical defect to find, so the improver, the purpose check
# and a whole epoch with reviews run live on a record without anyone's product decision.
#
#   run.sh BASE_SHA OUTPUT_DIR
#
# BASE_SHA      a commit that holds this kit (it is read from there). The checkout the loop starts from is that commit plus ONE
#               local commit made here that backs out the qualified missing-completion hook.
# OUTPUT_DIR    a folder that does not exist yet, outside every checkout. The worktree, the loop's output and the results go here.
#
# The fault is the reverse of the source and test delta between 779980629a81ce0e740f7c196e83e000dd582d99 (the control of 07734b9f's
# pair) and 7f25acff8dab239485f262249ec70773ba906aad (its candidate), minus the change note a release already consumed: the same
# reverse the stage 4 pilot and the stage 4b restore pilot use. It is committed in the throwaway worktree only. Nothing here pushes,
# and the loop branch that results has that commit as an ancestor, so it must NEVER be merged: land its journal entry, ledger rows and
# evidence by copying them, not by merging the branch.
#
# Then `iterate.py --qualify` explores hello-hook-continuation on that checkout (one run, reviewed and judged); a clear defect there
# should open and admit a record; an improver applies it in one commit with a prediction; the purpose check passes or rejects it; a
# promotion/5 epoch registers the tip against the candidate on hello-hook-continuation (the exposing case) and csv-report (kept unseen
# by the improver), a stated tolerance of 0.25 and 3 attempts per arm recorded as unmeasured, every attempt reviewed and judged (each
# incomplete review is assessed again, up to three times); it decides and records the prediction's verdict and a journal entry.
#
# Environment: SKILL_CRAFT_REPO (default ~/src/skill-craft) only supplies git objects; PARALLEL (default 3) is the number of subject
# runs at once (hello-hook-continuation and csv-report declare no fixed port); EFFORT (default xhigh) is the subject's reasoning effort
# (the owner asked on 2026-11-01 for Codex with Terra 6.1 at Extra High); DRY_RUN=1 stops after the planted commit is made and its
# diffstat printed, before any model call. See README.md for what to expect and what to return.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
# A sealed attempt's receipt binds every run that overlapped it inside the runs root. Unset, that root is the epoch's own folder,
# so only the epoch's attempts are neighbours, and epoch.settle_siblings waits for exactly those.
unset SHIPLOOP_E2E_RUNS_ROOT

base_sha=${1:?usage: run.sh BASE_SHA OUTPUT_DIR}
out=${2:?usage: run.sh BASE_SHA OUTPUT_DIR}
repo=${SKILL_CRAFT_REPO:-$HOME/src/skill-craft}
effort=${EFFORT:-xhigh}
hook_before=779980629a81ce0e740f7c196e83e000dd582d99
hook_after=7f25acff8dab239485f262249ec70773ba906aad

if [ -e "$out" ]; then
  echo "run.sh: $out exists; choose a folder that does not" >&2
  exit 2
fi
mkdir -p "$out"

git -C "$repo" fetch -q origin
git -C "$repo" cat-file -e "$base_sha^{commit}" || { echo "run.sh: $base_sha is not a commit of $repo" >&2; exit 2; }
git -C "$repo" worktree add -q --detach "$out/tree" "$base_sha"

# The planted fault: refuse loudly when the reverse does not apply, never half-apply it; then one local commit.
git -C "$out/tree" diff "$hook_before" "$hook_after" -- . ':!changes' > "$out/hook-delta.patch"
git -C "$out/tree" apply -R --check "$out/hook-delta.patch"
git -C "$out/tree" apply -R "$out/hook-delta.patch"
git -C "$out/tree" diff --stat > "$out/planted-fault.stat"
git -C "$out/tree" add -A skills test
git -C "$out/tree" -c user.name="skill-craft planted-fault kit" -c user.email="planted-fault@example.invalid" commit -q -F - <<MSG
revert(shiploop): back out the same-action continuation ($hook_after)

An instrument test, not a change to propose. This commit exists only in the throwaway checkout made by
docs/experiments/closed-loop-planted-20261101/run.sh, so that a qualified cycle has a real, mechanical defect to find. It reverses the
source and test delta of that commit (git diff $hook_before $hook_after, minus changes/). Nothing pushes it and it is never merged.
MSG
planted_sha=$(git -C "$out/tree" rev-parse HEAD)
echo "planted commit $planted_sha on $base_sha"
cat "$out/planted-fault.stat"
if [ "${DRY_RUN:-}" = 1 ]; then
  echo "dry run: stopping before any model call (the worktree is under $out)"
  exit 0
fi

cd "$out/tree"
status=0
python3 -B test/shiploop_e2e/iterate.py --qualify --case hello-hook-continuation --generality-case csv-report \
  --tolerance 0.25 --attempts 3 --host codex --model gpt-6.1-terra --effort "$effort" --iterations 1 \
  --parallel "${PARALLEL:-3}" --output "$out/loop" > "$out/loop-stdout.txt" 2>&1 || status=$?

# What to return: text, byte-exact. The raw run folders stay where they are.
mkdir -p "$out/results"
echo "$status" > "$out/results/iterate-exit-status.txt"
cp "$out/loop-stdout.txt" "$out/results/loop-stdout.txt"
cp "$out/planted-fault.stat" "$out/results/planted-fault.stat"
echo "$planted_sha" > "$out/results/planted-commit.txt"
[ -f "$out/loop/LOOP.md" ] && cp "$out/loop/LOOP.md" "$out/results/LOOP.md"
for stage in "$out"/loop/cycle-* "$out"/loop/explore-*; do
  [ -d "$stage" ] || continue
  name=$(basename "$stage")
  mkdir -p "$out/results/$name"
  ls -l "$stage" > "$out/results/$name/listing.txt" 2>&1 || true
  for file in cycle-result.json epoch-verdict.json epoch-registration.json prediction.json purpose-1.json purpose-2.json; do
    [ -f "$stage/$file" ] && cp "$stage/$file" "$out/results/$name/$file"
  done
  [ -f "$stage/run/result.json" ] && cp "$stage/run/result.json" "$out/results/$name/exploration-result.json"
  if [ -d "$stage/epoch" ]; then
    python3 -B test/shiploop_e2e/epoch.py --output "$stage/epoch" status > "$out/results/$name/epoch-status.json" 2>&1 || true
    [ -f "$stage/epoch/events.jsonl" ] && cp "$stage/epoch/events.jsonl" "$out/results/$name/epoch-events.jsonl"
    if [ -d "$stage/epoch/receipts" ]; then
      mkdir -p "$out/results/$name/receipts"
      cp "$stage"/epoch/receipts/*.json "$out/results/$name/receipts/" 2>/dev/null || true
    fi
  fi
done
branch=$(sed -n 's/^  branch: *//p' "$out/loop-stdout.txt" | tail -1)
{
  echo "base: $base_sha"
  echo "planted commit: $planted_sha"
  echo "loop branch: ${branch:-unknown}"
  [ -n "$branch" ] && git -C "$repo" log --format='%H %an %s' "$planted_sha..$branch" 2>/dev/null || true
  echo "kept candidates:"
  git -C "$repo" for-each-ref --format='%(objectname) %(refname)' refs/shiploop-loop/ 2>/dev/null || true
} > "$out/results/branches.txt"
echo "iterate.py exit status: $status; loop branch: ${branch:-unknown}"
exit 0
