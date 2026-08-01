#!/usr/bin/env bash
# devloop-run preflight: refuse without engine; exec when DEVLOOP_HOME set.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
run="$root/skills/devloop-run/scripts/devloop-run"

fail() {
  printf 'devloop-run.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$run" ]] || fail "scripts/devloop-run not executable"
[[ -f "$root/skills/devloop-run/SKILL.md" ]] || fail "missing SKILL.md"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/devloop-run-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

# D1: no engine → exit 2
unset DEVLOOP_HOME HERMES_HOME || true
export HOME="$tmpdir/empty-home"
mkdir -p "$HOME"
set +e
out1="$("$run" --help 2>&1)"
rc1=$?
set -e
[[ "$rc1" -eq 0 ]] || fail "D1 --help should exit 0 (got $rc1): $out1"

set +e
out1b="$("$run" "noop" 2>&1)"
rc1b=$?
set -e
[[ "$rc1b" -eq 2 ]] || fail "D1 missing engine want exit 2 got $rc1b: $out1b"
printf '%s\n' "$out1b" | grep -qi 'not resolved\|engine' || fail "D1 message: $out1b"

# D2: DEVLOOP_HOME fake engine → invokes python with --help style via stub
eng="$tmpdir/fake-engine"
mkdir -p "$eng/scripts"
# Stub CLI that records argv and exits 0
cat >"$eng/scripts/devloop_cli.py" <<'PY'
import sys
print("STUB_CLI", " ".join(sys.argv[1:]))
sys.exit(0)
PY
export DEVLOOP_HOME="$eng"
out2="$("$run" -- hello --repo /tmp/x 2>&1)" || fail "D2 run failed: $out2"
printf '%s\n' "$out2" | grep -q 'STUB_CLI hello --repo /tmp/x' || fail "D2 stub: $out2"

# D3: invalid DEVLOOP_HOME → exit 2
export DEVLOOP_HOME="$tmpdir/not-an-engine"
mkdir -p "$DEVLOOP_HOME"
set +e
out3="$("$run" hi 2>&1)"
rc3=$?
set -e
[[ "$rc3" -eq 2 ]] || fail "D3 want 2 got $rc3: $out3"

# D4: frontmatter kind + engine honesty
grep -q 'kind: script-backed' "$root/skills/devloop-run/SKILL.md" || fail "D4 kind"
grep -q 'engine: true' "$root/skills/devloop-run/SKILL.md" || fail "D4 engine"
grep -qi 'discovery' "$root/skills/devloop-run/SKILL.md" || fail "D4 discovery honesty"

# D5: leaf is not bare 'devloop' (collision avoidance)
[[ "$(basename "$(dirname "$root/skills/devloop-run")")" == "skills" ]]
[[ -d "$root/skills/devloop-run" ]]
[[ ! -d "$root/skills/devloop" ]] || fail "D5 bare skills/devloop must not exist"

printf 'devloop-run.test.sh: PASS D1–D5\n'
