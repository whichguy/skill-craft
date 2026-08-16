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
[[ -f "$pkg/prompts/author.prompt.md" ]] || fail "missing author prompt"
[[ -f "$pkg/prompts/schedule.prompt.md" ]] || fail "missing schedule prompt"
[[ -f "$pkg/prompts/escalation.prompt.md" ]] || fail "missing escalation prompt"
[[ -f "$pkg/prompts/event.prompt.md" ]] || fail "missing event prompt"
[[ -f "$pkg/references/e2e-success.md" ]] || fail "missing e2e-success reference"
[[ -x "$root/test/prompt-on-change-e2e.test.sh" ]] || fail "e2e suite not executable"
[[ -x "$pkg/scripts/detect_runner.sh" ]] || fail "runner not executable"
[[ -x "$pkg/scripts/prompt-on-change" ]] || fail "wrapper not executable"
[[ -f "$pkg/scripts/detect_engine.py" ]] || fail "missing detect_engine.py"
[[ -f "$root/agents/prompt-on-change.md" ]] || fail "missing agents/prompt-on-change.md"
grep -q 'prompt-on-change' "$root/agents/prompt-on-change.md" || fail "agent card must point at the skill"
grep -q 'kind: script-backed' "$pkg/SKILL.md" || fail "frontmatter kind"
grep -q 'name: prompt-on-change' "$pkg/SKILL.md" || fail "frontmatter name"
grep -q 'version: 2.2.0' "$pkg/SKILL.md" || fail "card version must be 2.2.0"
grep -q 'status' "$pkg/SKILL.md" || fail "card must document status"
grep -q 'explain' "$pkg/SKILL.md" || fail "card must document explain"
grep -q 'PROMPT_ISSUED' "$pkg/SKILL.md" || fail "card must document PROMPT_ISSUED"
grep -q 'SEED_OK' "$pkg/SKILL.md" || fail "card must document SEED_OK"
grep -q 'delta_between' "$pkg/SKILL.md" || fail "card must mention delta_between"
grep -q 'date_between' "$pkg/SKILL.md" || fail "card must mention date_between"
grep -q 'not_matches' "$pkg/SKILL.md" || fail "card must mention not_matches"
grep -q 'http.' "$pkg/SKILL.md" || fail "card must mention http. envelope fields"
grep -q 'delta.http' "$pkg/SKILL.md" || fail "card must mention delta.http"
grep -q 'LLM_ESCALATION' "$pkg/SKILL.md" || fail "card must document prompt-event contract"
# Native router: author prompt is the procedure before the engine CLI.
author_line="$(grep -n 'author.prompt.md' "$pkg/SKILL.md" | head -1 | cut -d: -f1)"
cli_line="$(grep -n 'scripts/prompt-on-change' "$pkg/SKILL.md" | head -1 | cut -d: -f1)"
[[ -n "$author_line" && -n "$cli_line" ]] || fail "SKILL procedure must name author.prompt.md and wrapper CLI"
[[ "$author_line" -lt "$cli_line" ]] || fail "SKILL must name author.prompt.md before the engine CLI"
grep -q 'json outcome' "$pkg/prompts/escalation.prompt.md" || fail "escalation prompt must define outcome fence"
if grep -qiE 'sonnet|opus|gpt-4|claude-3' \
  "$pkg/prompts/author.prompt.md" \
  "$pkg/prompts/schedule.prompt.md" \
  "$pkg/prompts/escalation.prompt.md" \
  "$pkg/prompts/event.prompt.md" \
  "$pkg/SKILL.md"; then
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
http_example="$pkg/configs/examples/http-change-events.yaml"
[[ -f "$http_example" ]] || fail "missing http-change-events example config"
post_example="$pkg/configs/examples/http-post-form.yaml"
[[ -f "$post_example" ]] || fail "missing http-post-form example config"
multi_post_example="$pkg/configs/examples/multi-post-any-all.yaml"
[[ -f "$multi_post_example" ]] || fail "missing multi-post-any-all example config"

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
"$python_bin" "$pkg/scripts/detect_engine.py" --config "$http_example" --validate \
  || fail "http-change-events example --validate"
"$python_bin" "$pkg/scripts/detect_engine.py" --config "$post_example" --validate \
  || fail "http-post-form example --validate"
"$python_bin" "$pkg/scripts/detect_engine.py" --config "$multi_post_example" --validate \
  || fail "multi-post-any-all example --validate"
printf 'LAYER simple: example validate OK\n'

wrapper="$pkg/scripts/prompt-on-change"
claim_out="$(PYTHON="$python_bin" "$wrapper" claim)" || fail "wrapper claim on empty dir"
printf '%s\n' "$claim_out" | grep -q 'CLAIM_EMPTY' || fail "empty claim must print CLAIM_EMPTY (not silent success): $claim_out"
printf '%s\n' "$claim_out" | grep -q '\[SILENT\]' || fail "empty claim must print [SILENT]: $claim_out"
self_out="$(PYTHON="$python_bin" "$wrapper" self-check)" || fail "wrapper self-check failed: $self_out"
printf '%s\n' "$self_out" | grep -q 'example validate: ok' || fail "self-check missing validate ok: $self_out"
printf 'LAYER simple: wrapper claim/self-check OK\n'

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

# Lifecycle fixture (local HTTP, wrapper verbs). Reuses PYTHON + POC_* dirs.
export PYTHON="$python_bin"
bash "$root/test/prompt-on-change-lifecycle.test.sh" \
  || fail "lifecycle tests"
printf 'LAYER e2e: lifecycle OK\n'

bash "$root/test/prompt-on-change-delivery.test.sh" \
  || fail "delivery tests"
printf 'LAYER e2e: delivery OK\n'

POC_GROK_LIVE=0 POC_GROK_KEEP= bash "$root/test/prompt-on-change-poll-effectiveness.test.sh" \
  || fail "poll effectiveness"
printf 'LAYER e2e: poll effectiveness OK\n'

# Probe only — never inherit a live Grok run into the hermetic suite.
POC_GROK_LIVE=0 bash "$root/test/prompt-on-change-grok-native.test.sh" \
  || fail "grok-native probe"
printf 'LAYER simple: grok-native probe OK\n'

# Probe only — never inherit a public-site scrape into the hermetic suite.
POC_LIVE_SITE=0 bash "$root/test/prompt-on-change-live-site.test.sh" \
  || fail "live-site probe"
printf 'LAYER simple: live-site probe OK\n'

# Offline e2e card (local HTTP multi-condition). Live Grok/site stay skipped.
POC_E2E=0 POC_GROK_LIVE=0 POC_LIVE_SITE=0 bash "$root/test/prompt-on-change-e2e.test.sh" \
  || fail "e2e offline"
printf 'LAYER e2e: e2e offline OK\n'

printf 'prompt-on-change.test.sh: PASS\n'
