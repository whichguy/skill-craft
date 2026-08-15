#!/usr/bin/env bash
# Hermetic prompt-on-change tests (no network, no gws, no host harness CLIs).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"

fail() {
  printf 'prompt-on-change.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -f "$pkg/SKILL.md" ]] || fail "missing SKILL.md"
[[ -f "$pkg/prompts/escalation.prompt.md" ]] || fail "missing escalation prompt"
[[ -x "$pkg/scripts/detect_runner.sh" ]] || fail "runner not executable"
[[ -f "$pkg/scripts/detect_engine.py" ]] || fail "missing detect_engine.py"
grep -q 'kind: script-backed' "$pkg/SKILL.md" || fail "frontmatter kind"
grep -q 'name: prompt-on-change' "$pkg/SKILL.md" || fail "frontmatter name"
grep -q 'delta_between' "$pkg/SKILL.md" || fail "card must mention delta_between"
grep -q 'date_between' "$pkg/SKILL.md" || fail "card must mention date_between"
grep -q 'not_matches' "$pkg/SKILL.md" || fail "card must mention not_matches"
grep -q 'LLM_ESCALATION' "$pkg/SKILL.md" || fail "card must document prompt-event contract"
if grep -qiE 'sonnet|opus|gpt-4|claude-3' "$pkg/prompts/escalation.prompt.md" "$pkg/SKILL.md"; then
  fail "prompts must not pin model names"
fi
# Portable defaults: engine/runner must not require /opt/data
if grep -n 'DETECT_DIR:-/opt/data' "$pkg/scripts/detect_runner.sh"; then
  fail "runner default DETECT_DIR still /opt/data"
fi
printf 'LAYER simple: structure+purity OK\n'

example="$pkg/configs/examples/price-range-delta.yaml"
[[ -f "$example" ]] || fail "missing example config"
date_example="$pkg/configs/examples/date-regex-delta.yaml"
[[ -f "$date_example" ]] || fail "missing date-regex example config"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-test.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$tmpdir/health"
export DETECT_ENGINE_ESCALATION_DIR="$tmpdir/escalations"
export DETECT_ENGINE_LOG_FILE="$tmpdir/engine.log"
mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_HEALTH_DIR" "$DETECT_ENGINE_ESCALATION_DIR"

python_bin=python3
if ! python3 -c "import httpx, pydantic, yaml, jsonpath_ng, selectolax, pytest" 2>/dev/null; then
  python3 -m venv "$tmpdir/venv"
  "$tmpdir/venv/bin/pip" install -q \
    "pyyaml>=6.0" "pydantic>=2.0" "httpx>=0.27" \
    "jsonpath-ng>=1.6" "selectolax>=0.3" "pytest>=8.0"
  python_bin="$tmpdir/venv/bin/python"
fi

"$python_bin" "$pkg/scripts/detect_engine.py" --config "$example" --validate \
  || fail "example --validate"
"$python_bin" "$pkg/scripts/detect_engine.py" --config "$date_example" --validate \
  || fail "date-regex example --validate"
printf 'LAYER simple: example validate OK\n'

# Runner self-check against the examples dir (no live fetches)
DETECT_DIR="$pkg/configs/examples" \
  PYTHON="$python_bin" \
  ENGINE="$pkg/scripts/detect_engine.py" \
  LOG_FILE="$tmpdir/runner.log" \
  bash "$pkg/scripts/detect_runner.sh" --self-check \
  || fail "runner --self-check"
printf 'LAYER simple: runner self-check OK\n'

# Engine unit tests via the native runner (pytest collection re-executes
# runner.run() side effects and double-fires backoff tests).
if ! "$python_bin" "$pkg/tests/test_detect_engine.py"; then
  fail "test_detect_engine.py"
fi
printf 'LAYER e2e: engine tests OK\n'

printf 'prompt-on-change.test.sh: PASS\n'
