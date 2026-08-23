#!/usr/bin/env bash
# Hermetic steer-next wrapper tests (no network).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
next="$root/skills/steer-next/scripts/steer-next"
steer="$root/skills/steer/scripts/steer"
fix="$root/test/fixtures/steer"
export STEER_BACKCHAIN_ROOT="$fix/backchain-leaf"
export STEER_ROOT="$root/skills/steer"

fail() {
  printf 'steer-next.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -f "$root/skills/steer-next/SKILL.md" ]] || fail "missing SKILL.md"
grep -q 'name: steer-next' "$root/skills/steer-next/SKILL.md" || fail "frontmatter name"
chmod +x "$next" "$steer"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/steer-next-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

HEADINGS='## You are here
## Reminder
## Look here
## Next prompt
## When done invoke
## Missing'

DS='result.txt contains exactly one line: ok'
planf="$tmpdir/bound.plan.md"
cat >"$planf" <<'MD'
# Bound
## Review Coverage
x
MD
repo="$tmpdir/repo"
run="$repo/.steer"
mkdir -p "$repo"

python3 "$steer" init --prompt "create result.txt containing exactly one line: ok" \
  --run-dir "$run" --bound-plan "$planf" --repo "$repo" >/dev/null

out="$(python3 "$next" --run-dir "$run")"
printf '%s\n' "$out" | grep -q 'steer-next — reprint the steer packet' || fail "banner: $out"
while IFS= read -r h; do
  printf '%s\n' "$out" | grep -qxF "$h" || fail "missing heading $h"
done <<<"$HEADINGS"

for cmd in update complete-step start-step; do
  set +e
  bad="$(python3 "$next" "$cmd" --run-dir "$run" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 2 ]] || fail "refuse $cmd want 2: $bad"
done

# missing STEER_ROOT in isolated copy
alone="$tmpdir/alone-pkg/steer-next"
mkdir -p "$alone"
cp -R "$root/skills/steer-next/." "$alone/"
export HOME="$tmpdir/empty-home"
unset STEER_ROOT
set +e
out_m="$(python3 "$alone/scripts/steer-next" --run-dir "$run" 2>&1)"
rc_m=$?
set -e
[[ "$rc_m" -eq 2 ]] || fail "missing steer want 2: $out_m"
printf '%s\n' "$out_m" | grep -q 'dep_roots.steer' || fail "missing steer message: $out_m"

# hermetic temp HOME with STEER_ROOT still prints headings
export STEER_ROOT="$root/skills/steer"
out2="$(env HOME="$tmpdir/empty-home-2" STEER_ROOT="$root/skills/steer" \
  python3 "$next" --run-dir "$run")"
printf '%s\n' "$out2" | grep -qxF '## You are here' || fail "temp HOME missing headings"

# implement fixture contains /goal
python3 "$steer" update --run-dir "$run" --to validate-spec >/dev/null
printf '%s\n' "{\"done_sentence\":\"$DS\",\"checkable\":true}" >"$run/spec.json"
printf 'done_sentence: %s\n' "$DS" >"$run/spec.md"
python3 "$steer" update --run-dir "$run" --to plan >/dev/null
mkdir -p "$run/backchain"
cp "$fix/linear.json" "$run/backchain/plan.json"
printf '%s\n' "{\"done_sentence\":\"$DS\"}" >"$run/plan.json"
printf 'done_sentence: %s\n' "$DS" >"$run/plan.md"
python3 "$steer" update --run-dir "$run" --to implement >/dev/null
out3="$(python3 "$next" --run-dir "$run")"
printf '%s\n' "$out3" | grep -q '/goal ' || fail "implement packet missing /goal"

printf 'steer-next.test.sh: PASS\n'
