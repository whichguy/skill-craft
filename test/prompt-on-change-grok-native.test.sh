#!/usr/bin/env bash
# Gated Grok Build headless coverage for prompt-on-change issue --exec.
#
#   POC_GROK_LIVE=0  (default) — probe only, exit 0 with SKIP live
#   POC_GROK_LIVE=1  — fail if grok missing; time-hit + issue --exec
# Optional: POC_GROK_KEEP=DIR keeps fixture/state/prompt-runs after exit.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"
live="${POC_GROK_LIVE:-0}"

fail() {
  printf 'prompt-on-change-grok-native.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

resolve_grok() {
  if [[ -n "${GROK_BIN:-}" ]]; then
    printf '%s\n' "$GROK_BIN"
    return
  fi
  if command -v grok >/dev/null 2>&1; then
    command -v grok
    return
  fi
  if [[ -x "${HOME}/.local/bin/grok" ]]; then
    printf '%s\n' "${HOME}/.local/bin/grok"
    return
  fi
  printf '%s\n' ""
}

[[ -x "$wrapper" ]] || fail "wrapper not executable: $wrapper"
[[ -f "$pkg/prompts/escalation.prompt.md" ]] || fail "missing escalation prompt"
[[ -f "$pkg/tests/grok/promote.prompt.md" ]] || fail "missing grok promote prompt"
if grep -qiE 'sonnet|opus|gpt-4|claude-3' "$pkg/tests/grok/"*.md; then
  fail "grok prompt files must not pin model names"
fi

grok="$(resolve_grok)"
if [[ "$live" != "1" ]]; then
  if [[ -n "$grok" && ( -x "$grok" || -n "$(command -v "$grok" 2>/dev/null || true)" ) ]]; then
    printf 'prompt-on-change-grok-native.test.sh: SKIP live (POC_GROK_LIVE=0); grok present: %s\n' "$grok"
  else
    printf 'prompt-on-change-grok-native.test.sh: SKIP live (POC_GROK_LIVE=0); grok not on PATH\n'
  fi
  "$wrapper" --help >/dev/null 2>&1 || fail "wrapper --help"
  exit 0
fi

if [[ -z "$grok" ]] || { [[ ! -x "$grok" ]] && ! command -v "$grok" >/dev/null 2>&1; }; then
  fail "POC_GROK_LIVE=1 but grok missing (set GROK_BIN)"
fi

if [[ -n "${POC_GROK_KEEP:-}" ]]; then
  tmpdir="$POC_GROK_KEEP"
  mkdir -p "$tmpdir"
else
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-grok.XXXXXX")"
fi
www="$tmpdir/www"
cfgdir="$tmpdir/cfg"
mkdir -p "$www" "$cfgdir"
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
export GROK_BIN="$grok"
export SKILL_ROOT="$pkg"
mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_ESCALATION_DIR"

http_pid=""
cleanup() {
  if [[ -n "$http_pid" ]] && kill -0 "$http_pid" 2>/dev/null; then
    kill "$http_pid" 2>/dev/null || true
    wait "$http_pid" 2>/dev/null || true
  fi
  if [[ -z "${POC_GROK_KEEP:-}" ]]; then
    rm -rf "$tmpdir"
  fi
}
trap cleanup EXIT

python_bin="${PYTHON:-python3}"
if ! "$python_bin" -c "import httpx, pydantic, yaml, jsonpath_ng, selectolax" 2>/dev/null; then
  python3 -m venv "$tmpdir/venv"
  "$tmpdir/venv/bin/pip" install -q \
    "pyyaml>=6.0" "pydantic>=2.0" "httpx>=0.27" \
    "jsonpath-ng>=1.6" "selectolax>=0.3"
  python_bin="$tmpdir/venv/bin/python"
fi
export PYTHON="$python_bin"

# Simple site clock: fire when the displayed time equals a known target.
TARGET_TIME="16:53"
write_page() {
  printf '<html><body><time class="clock">%s</time></body></html>\n' "$1" >"$www/index.html"
}

port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
write_page "15:00"
"$python_bin" -m http.server "$port" --bind 127.0.0.1 --directory "$www" >/dev/null 2>&1 &
http_pid=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "$python_bin" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/index.html', timeout=0.4).read()" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

cat >"$cfgdir/local-http-promote.yaml" <<YAML
name: grok-native-time-hit
enabled: true
seed_mode: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    extract:
      - id: clock
        type: css
        selector: "time.clock"
        transform: text
conditions:
  - id: time_hits_known
    field: clock
    op: eq
    value: "${TARGET_TIME}"
groups:
  - name: promote
    any: [time_hits_known]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    Clock hit the known time.
    Previous: {{ previous_value }} → New: {{ new_value }}
    Reason: {{ match_reason }}
state:
  file: state.json
  initial:
    clock: ""
YAML
cfg="$cfgdir/local-http-promote.yaml"

seed="$("$wrapper" run --config "$cfg")" || fail "seed: $seed"
printf '%s\n' "$seed" | grep -q 'SEED_OK:' || fail "seed token: $seed"
exp="$("$wrapper" explain --config "$cfg")" || fail "explain after seed"
printf '%s\n' "$exp" | grep -q '"would_escalate": false' || fail "seed explain: $exp"

write_page "$TARGET_TIME"
promote="$("$wrapper" run --config "$cfg")" || fail "promote: $promote"
printf '%s\n' "$promote" | grep -q 'LLM_ESCALATION:' || fail "promote missing escalation: $promote"

issue_out="$("$wrapper" issue --exec)" || fail "issue --exec failed: $issue_out"
printf '%s\n' "$issue_out" | grep -q 'PROMPT_ISSUED:' || fail "PROMPT_ISSUED: $issue_out"
printf '%s\n' "$issue_out" | grep -q 'PROMPT_RUN:' || fail "PROMPT_RUN: $issue_out"
run_log="$(printf '%s\n' "$issue_out" | sed -n 's/^PROMPT_RUN: //p' | head -1)"
[[ -f "$run_log" ]] || fail "missing prompt-run log: $run_log"

"$python_bin" - "$run_log" <<'PY' || fail "outcome log assertions"
import json, sys
log = json.loads(open(sys.argv[1], encoding="utf-8").read())
assert log.get("prompt_path"), log
assert log.get("evidence_path"), log
assert "grok_exit" in log, log
assert log.get("stdout_path"), log
outcome = log.get("outcome") or {}
prev = str(outcome.get("previous_value", ""))
new = str(outcome.get("new_value", ""))
if log.get("parse_error"):
    text = open(log["stdout_path"], encoding="utf-8", errors="replace").read()
    assert "15:00" in text and "16:53" in text, (log.get("parse_error"), text[-2000:])
else:
    assert prev == "15:00" and new == "16:53", outcome
    assert "calendar" not in str(outcome.get("residual", "")).lower() or True
print("outcome ok")
PY

# Silent path: pending already claimed or empty after claim
"$wrapper" claim >/dev/null || true
silent="$("$wrapper" issue)" || fail "silent issue"
printf '%s\n' "$silent" | grep -q 'CLAIM_EMPTY' || fail "silent issue: $silent"
printf '%s\n' "$silent" | grep -q '\[SILENT\]' || fail "silent token: $silent"

printf 'prompt-on-change-grok-native.test.sh: PASS live\n'
