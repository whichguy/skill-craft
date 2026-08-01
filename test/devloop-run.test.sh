#!/usr/bin/env bash
# devloop-run preflight + bootstrap (hermetic; no live network).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
run="$root/skills/devloop-run/scripts/devloop-run"

fail() {
  printf 'devloop-run.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$run" ]] || fail "scripts/devloop-run not executable"
[[ -f "$root/skills/devloop-run/SKILL.md" ]] || fail "missing SKILL.md"
[[ -f "$root/skills/devloop-run/references/bootstrap.md" ]] || fail "missing bootstrap.md"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/devloop-run-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

# D1: --help
unset DEVLOOP_HOME HERMES_HOME DEVLOOP_BOOTSTRAP_CMD DEVLOOP_ENGINE_URL DEVLOOP_DATA_HOME || true
export HOME="$tmpdir/empty-home"
mkdir -p "$HOME"
set +e
out1="$("$run" --help 2>&1)"
rc1=$?
set -e
[[ "$rc1" -eq 0 ]] || fail "D1 --help should exit 0 (got $rc1): $out1"

# D1b: no engine + --no-bootstrap → exit 2
set +e
out1b="$("$run" --no-bootstrap "noop" 2>&1)"
rc1b=$?
set -e
[[ "$rc1b" -eq 2 ]] || fail "D1b missing engine want exit 2 got $rc1b: $out1b"
printf '%s\n' "$out1b" | grep -qiE 'not resolved|engine|bootstrap|--setup' || fail "D1b message: $out1b"

# D2: DEVLOOP_HOME fake engine → invokes stub
eng="$tmpdir/fake-engine"
mkdir -p "$eng/scripts"
cat >"$eng/scripts/devloop_cli.py" <<'PY'
import sys
print("STUB_CLI", " ".join(sys.argv[1:]))
sys.exit(0)
PY
export DEVLOOP_HOME="$eng"
out2="$("$run" -- hello --repo /tmp/x 2>&1)" || fail "D2 run failed: $out2"
printf '%s\n' "$out2" | grep -q 'STUB_CLI hello --repo /tmp/x' || fail "D2 stub: $out2"

# D3: invalid DEVLOOP_HOME + --strict + --no-bootstrap → 2
export DEVLOOP_HOME="$tmpdir/not-an-engine"
mkdir -p "$DEVLOOP_HOME"
set +e
out3="$("$run" --strict --no-bootstrap hi 2>&1)"
rc3=$?
set -e
[[ "$rc3" -eq 2 ]] || fail "D3 want 2 got $rc3: $out3"

# D4: frontmatter kind + multi-host honesty
grep -q 'kind: script-backed' "$root/skills/devloop-run/SKILL.md" || fail "D4 kind"
grep -q 'engine: true' "$root/skills/devloop-run/SKILL.md" || fail "D4 engine"
grep -qi 'bootstrap' "$root/skills/devloop-run/SKILL.md" || fail "D4 bootstrap honesty"

# D5: leaf is not bare 'devloop'
[[ -d "$root/skills/devloop-run" ]]
[[ ! -d "$root/skills/devloop" ]] || fail "D5 bare skills/devloop must not exist"

# D6: --probe with DEVLOOP_HOME
export DEVLOOP_HOME="$eng"
out6="$("$run" --probe 2>&1)" || fail "D6 probe: $out6"
printf '%s\n' "$out6" | grep -q 'engine=' || fail "D6 probe output: $out6"

# D7: --strict with broken DEVLOOP_HOME does not use fallbacks
export DEVLOOP_HOME="$tmpdir/not-an-engine"
mkdir -p "$HOME/.hermes/skills/software-development/devloop/scripts"
printf 'print(1)\n' >"$HOME/.hermes/skills/software-development/devloop/scripts/devloop_cli.py"
set +e
out7="$("$run" --strict --no-bootstrap hi 2>&1)"
rc7=$?
set -e
[[ "$rc7" -eq 2 ]] || fail "D7 strict want 2 got $rc7: $out7"

# D8: bootstrap via DEVLOOP_BOOTSTRAP_CMD into host-local (no network)
unset DEVLOOP_HOME HERMES_HOME || true
rm -rf "$HOME/.hermes"
export DEVLOOP_DATA_HOME="$tmpdir/data"
python3 -c "
from pathlib import Path
eng = Path(r'''$eng''')
out = Path(r'''$tmpdir''') / 'bootstrap.sh'
src = eng / 'scripts' / 'devloop_cli.py'
out.write_text(
    '#!/usr/bin/env bash\nset -euo pipefail\n'
    'dest=\"\$1\"\nmkdir -p \"\$dest/scripts\"\n'
    f'cp \"{src}\" \"\$dest/scripts/devloop_cli.py\"\n'
)
out.chmod(0o755)
"
export DEVLOOP_BOOTSTRAP_CMD="$tmpdir/bootstrap.sh"
out8="$("$run" --setup 2>&1)" || fail "D8 setup: $out8"
[[ -f "$DEVLOOP_DATA_HOME/devloop/scripts/devloop_cli.py" ]] || fail "D8 engine file missing: $out8"
[[ -f "$DEVLOOP_DATA_HOME/devloop/.skill-craft-engine.json" ]] || fail "D8 marker missing"
out8p="$("$run" --probe --no-bootstrap 2>&1)" || fail "D8 probe: $out8p"
printf '%s\n' "$out8p" | grep -q 'devloop' || fail "D8 probe path: $out8p"

# D9: second setup does not need bootstrap cmd if already present
unset DEVLOOP_BOOTSTRAP_CMD
out9="$("$run" --setup --no-bootstrap 2>&1)" || fail "D9 re-setup: $out9"

# D10: --no-bootstrap with empty data home and no hermes → 2
export DEVLOOP_DATA_HOME="$tmpdir/empty-data"
unset DEVLOOP_HOME || true
rm -rf "$HOME/.hermes"
set +e
out10="$("$run" --probe --no-bootstrap 2>&1)"
rc10=$?
set -e
[[ "$rc10" -eq 2 ]] || fail "D10 want 2 got $rc10: $out10"

printf 'devloop-run.test.sh: PASS D1–D10\n'
