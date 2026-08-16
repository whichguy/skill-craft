#!/usr/bin/env bash
# Hermetic --to grok:<uuid> delivery: fake GROK_BIN, no network, no live TUI.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"
helper="$pkg/scripts/poc_delivery.py"

fail() {
  printf 'prompt-on-change-delivery.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$wrapper" ]] || fail "wrapper not executable"
[[ -f "$helper" ]] || fail "missing poc_delivery.py"
[[ -f "$pkg/prompts/event.prompt.md" ]] || fail "missing event.prompt.md"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-deliv.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
export GROK_HOME="$tmpdir/grok"
export POC_GROK_KEEP=
unset POC_ASSUME_IDLE
mkdir -p "$POC_STATE_DIR/issued" "$DETECT_ENGINE_ESCALATION_DIR" \
  "$GROK_HOME/sessions" "$tmpdir/bin"

python_bin="${PYTHON:-python3}"
if ! "$python_bin" -c "import httpx, pydantic, yaml, jsonpath_ng, selectolax" 2>/dev/null; then
  python3 -m venv "$tmpdir/venv"
  "$tmpdir/venv/bin/pip" install -q \
    "pyyaml>=6.0" "pydantic>=2.0" "httpx>=0.27" \
    "jsonpath-ng>=1.6" "selectolax>=0.3"
  python_bin="$tmpdir/venv/bin/python"
fi
export PYTHON="$python_bin"

sid="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
other="bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"

write_evidence() {
  local path="$1" name="$2" cond="$3" etype="${4:-condition_matched}"
  mkdir -p "$(dirname "$path")"
  cat >"$path" <<JSON
{
  "config_name": "$name",
  "condition_id": "$cond",
  "escalation_type": "$etype",
  "previous_value": "100",
  "new_value": "40",
  "changed_fields": ["price"],
  "match_reason": "changed"
}
JSON
}

fake_grok="$tmpdir/bin/fake-grok"
cat >"$fake_grok" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$@" >"${GROK_ARGV_FILE:?}"
if [[ -n "${GROK_SLEEP:-}" ]]; then
  sleep "$GROK_SLEEP"
fi
printf '%s\n' '```json outcome'
printf '%s\n' '{"silent": false, "claimed": [], "condition_id": "price_changed"}'
printf '%s\n' '```'
exit 0
SH
chmod +x "$fake_grok"
export GROK_BIN="$fake_grok"
export GROK_ARGV_FILE="$tmpdir/grok.argv"

# --- parse-to ---
"$python_bin" "$helper" parse-to --to "grok:$sid" | grep -q '"host": "grok"' \
  || fail "parse-to grok"
if "$python_bin" "$helper" parse-to --to "claude:$sid" >/dev/null 2>"$tmpdir/unknown.err"; then
  fail "unknown host must fail"
fi
grep -qi 'unknown host' "$tmpdir/unknown.err" || fail "unknown host message: $(cat "$tmpdir/unknown.err")"

# --- new session: --session-id, dontAsk, no yolo, sandbox ---
ev1="$DETECT_ENGINE_ESCALATION_DIR/example-http-promote_price_changed_1.json"
write_evidence "$ev1" "example-http-promote" "price_changed"
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$sid" --evidence "$ev1")" || fail "new session issue: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_ISSUED:' || fail "new must issue: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_RUN:' || fail "new must PROMPT_RUN: $out"
printf '%s\n' "$out" | grep -q 'PROMPT_RESUME:' && fail "new must not resume: $out"
grep -q -- "--session-id $sid" "$GROK_ARGV_FILE" || fail "new argv session-id: $(cat "$GROK_ARGV_FILE")"
grep -q -- "--permission-mode dontAsk" "$GROK_ARGV_FILE" || fail "new argv dontAsk"
grep -q -- "--sandbox read-only" "$GROK_ARGV_FILE" || fail "new argv sandbox"
grep -q -- "--no-memory" "$GROK_ARGV_FILE" || fail "new argv no-memory"
if grep -q -- "--yolo" "$GROK_ARGV_FILE"; then fail "new must not yolo"; fi
if grep -q -- "bypassPermissions" "$GROK_ARGV_FILE"; then fail "new must not bypass"; fi
issued="$(printf '%s\n' "$out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q "$sid" <<<"$issued" || fail "issued name should include uuid: $issued"
grep -q 'escalation handler' "$issued" || fail "new session uses escalation prompt"
grep -q '"condition_id": "price_changed"' "$issued" || fail "matches in issued prompt"

# --- resume: local dir exists, idle ---
enc="$(python3 -c 'from urllib.parse import quote; print(quote("/tmp/poc-session-cwd", safe=""))')"
sess_dir="$GROK_HOME/sessions/$enc/$sid"
mkdir -p "$sess_dir"
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$sid" --evidence "$ev1")" || fail "resume issue: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_RESUME:' || fail "resume token: $out"
grep -q -- "--resume $sid" "$GROK_ARGV_FILE" || fail "resume argv: $(cat "$GROK_ARGV_FILE")"
if grep -q -- "--session-id" "$GROK_ARGV_FILE"; then fail "resume must not session-id"; fi
if grep -q -- "--sandbox" "$GROK_ARGV_FILE"; then fail "resume must not set sandbox"; fi
issued="$(printf '%s\n' "$out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q 'async event' "$issued" || fail "resume uses event prompt: $issued"
grep -q -- "--cwd /tmp/poc-session-cwd" "$GROK_ARGV_FILE" || fail "resume cwd from glob: $(cat "$GROK_ARGV_FILE")"

# --- refuse: fresh live pid ---
cat >"$GROK_HOME/active_sessions.json" <<JSON
[{"session_id": "$sid", "pid": $$, "cwd": "/tmp/poc-session-cwd", "opened_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}]
JSON
: >"$GROK_ARGV_FILE"
set +e
refuse_out="$("$wrapper" issue --exec --to "grok:$sid" --evidence "$ev1" 2>"$tmpdir/refuse.err")"
refuse_rc=$?
set -e
[[ "$refuse_rc" -ne 0 ]] || fail "live must refuse"
printf '%s\n' "$refuse_out" | grep -q '^PROMPT_ISSUED:' || fail "refuse still issues: $refuse_out"
printf '%s\n' "$refuse_out" | grep -q 'PROMPT_RUN:\|PROMPT_RESUME:' && fail "refuse must not exec: $refuse_out"
grep -qi 'delivery refuse' "$tmpdir/refuse.err" || fail "refuse message: $(cat "$tmpdir/refuse.err")"
grep -q 'issue --exec --to' "$tmpdir/refuse.err" || fail "refuse replay: $(cat "$tmpdir/refuse.err")"
[[ ! -s "$GROK_ARGV_FILE" ]] || fail "refuse must not invoke grok"

# --- --assume-idle overrides uncertain/live ---
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$sid" --assume-idle --evidence "$ev1")" \
  || fail "assume-idle: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_RESUME:' || fail "assume-idle resume: $out"
grep -q -- "--resume $sid" "$GROK_ARGV_FILE" || fail "assume-idle argv"

# --- stale+alive without override still refuses ---
old="2000-01-01T00:00:00Z"
cat >"$GROK_HOME/active_sessions.json" <<JSON
[{"session_id": "$sid", "pid": $$, "cwd": "/tmp/poc-session-cwd", "opened_at": "$old"}]
JSON
: >"$GROK_ARGV_FILE"
set +e
"$wrapper" issue --exec --to "grok:$sid" --evidence "$ev1" >/dev/null 2>"$tmpdir/stale.err"
stale_rc=$?
set -e
[[ "$stale_rc" -ne 0 ]] || fail "stale+alive must refuse without --assume-idle"
grep -qi 'refuse' "$tmpdir/stale.err" || fail "stale refuse: $(cat "$tmpdir/stale.err")"

# --- --force-new: new uuid, session-id, not resume ---
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$sid" --force-new --evidence "$ev1")" \
  || fail "force-new: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_RUN:' || fail "force-new RUN: $out"
if grep -q -- "--resume" "$GROK_ARGV_FILE"; then fail "force-new must not resume"; fi
grep -q -- "--session-id" "$GROK_ARGV_FILE" || fail "force-new session-id"
if grep -q -- "--session-id $sid" "$GROK_ARGV_FILE"; then
  fail "force-new must generate a new uuid: $(cat "$GROK_ARGV_FILE")"
fi
issued="$(printf '%s\n' "$out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q 'escalation handler' "$issued" || fail "force-new uses escalation prompt"

# --- unknown host on wrapper ---
set +e
"$wrapper" issue --exec --to "claude:$sid" --evidence "$ev1" >/dev/null 2>"$tmpdir/host.err"
host_rc=$?
set -e
[[ "$host_rc" -ne 0 ]] || fail "wrapper unknown host must fail"
grep -qi 'unknown host' "$tmpdir/host.err" || fail "wrapper host err: $(cat "$tmpdir/host.err")"

# --- this-poll two condition_matched → one issue containing both ---
rm -f "$GROK_HOME/active_sessions.json"
rm -rf "$GROK_HOME/sessions/$enc/$other"
ev2="$DETECT_ENGINE_ESCALATION_DIR/example-http-promote_status_changed_2.json"
write_evidence "$ev2" "example-http-promote" "status_changed"
leak="$DETECT_ENGINE_ESCALATION_DIR/other-config_leaked_9.json"
write_evidence "$leak" "other-config" "leaked"
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$other" --evidence "$ev1" --evidence "$ev2" --evidence "$leak")" \
  || fail "two-match issue: $out"
printf '%s\n' "$out" | grep -c '^PROMPT_ISSUED:' | grep -qx 1 \
  || fail "exactly one issue: $out"
issued="$(printf '%s\n' "$out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q 'price_changed' "$issued" || fail "issue missing first match"
grep -q 'status_changed' "$issued" || fail "issue missing second match"
grep -q 'other-config' "$issued" && fail "cross-config leak into --to prompt"

# --- fetch_failure only: no --to delivery ---
ff="$DETECT_ENGINE_ESCALATION_DIR/example-http-promote_fetch_1.json"
write_evidence "$ff" "example-http-promote" "search" "fetch_failure"
: >"$GROK_ARGV_FILE"
out="$("$wrapper" issue --exec --to "grok:$other" --evidence "$ff")" || fail "fetch-only: $out"
printf '%s\n' "$out" | grep -q '^PROMPT_ISSUED:' || fail "fetch-only still issues"
printf '%s\n' "$out" | grep -q '^PROMPT_RUN:' || fail "fetch-only falls back to legacy exec"
grep -q -- "--yolo" "$GROK_ARGV_FILE" || fail "fetch-only legacy yolo"

# --- --to without --evidence fails (no newest_file) ---
set +e
"$wrapper" issue --exec --to "grok:$sid" >/dev/null 2>"$tmpdir/noev.err"
noev_rc=$?
set -e
[[ "$noev_rc" -ne 0 ]] || fail "--to without --evidence must fail"
grep -qi 'evidence' "$tmpdir/noev.err" || fail "no-evidence message"

# --- flock: second deliver waits ---
mkdir -p "$GROK_HOME/sessions/$enc/$sid"
rm -f "$GROK_HOME/active_sessions.json"
lock="$POC_STATE_DIR/locks/grok-${sid}.lock"
mkdir -p "$POC_STATE_DIR/locks"
python3 - "$lock" "$wrapper" "$ev1" "grok:$sid" "$tmpdir/flock.out" "$tmpdir/flock.err" <<'PY' &
import fcntl, os, subprocess, sys, time
lock, wrapper, ev, spec, out_path, err_path = sys.argv[1:7]
with open(lock, "a", encoding="utf-8") as handle:
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    time.sleep(1.2)
PY
holder=$!
sleep 0.15
start_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
GROK_SLEEP=0 "$wrapper" issue --exec --to "grok:$sid" --evidence "$ev1" \
  >"$tmpdir/flock.out" 2>"$tmpdir/flock.err" || fail "flock waiter failed: $(cat "$tmpdir/flock.err")"
end_ms="$(python3 -c 'import time; print(int(time.time()*1000))')"
wait "$holder" || true
elapsed=$((end_ms - start_ms))
[[ "$elapsed" -ge 800 ]] || fail "second run should wait on flock (${elapsed}ms)"
grep -q '^PROMPT_RESUME:\|^PROMPT_RUN:' "$tmpdir/flock.out" || fail "flock waiter tokens: $(cat "$tmpdir/flock.out")"

# --- run --to binds this poll (local HTTP, two conditions) ---
www="$tmpdir/www"
cfgdir="$tmpdir/cfg"
mkdir -p "$www" "$cfgdir/state"
printf '<html><body><span class="price">100</span><span class="status">ok</span></body></html>\n' >"$www/index.html"
port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
"$python_bin" -m http.server "$port" --bind 127.0.0.1 --directory "$www" >/dev/null 2>&1 &
http_pid=$!
cleanup_http() {
  if kill -0 "$http_pid" 2>/dev/null; then
    kill "$http_pid" 2>/dev/null || true
    wait "$http_pid" 2>/dev/null || true
  fi
  cleanup
}
trap cleanup_http EXIT
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "$python_bin" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/index.html', timeout=0.4).read()" 2>/dev/null; then
    break
  fi
  sleep 0.1
done
cat >"$cfgdir/two-any.yaml" <<YAML
name: two-any
enabled: true
seed_mode: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    extract:
      - id: price
        type: css
        selector: ".price"
        transform: text
      - id: status
        type: css
        selector: ".status"
        transform: text
conditions:
  - id: price_changed
    field: price
    op: changed
  - id: status_changed
    field: status
    op: changed
groups:
  - name: promote
    any: [price_changed, status_changed]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    {{ config_name }} {{ condition_id }}
state:
  file: state.json
  initial:
    price: ""
    status: ""
YAML
run_sid="cccccccc-dddd-4eee-8fff-000000000001"
"$wrapper" run --config "$cfgdir/two-any.yaml" >/dev/null || fail "seed two-any"
printf '<html><body><span class="price">40</span><span class="status">sale</span></body></html>\n' >"$www/index.html"
# leftover from another config must not leak
write_evidence "$DETECT_ENGINE_ESCALATION_DIR/other-config_leaked_run.json" "other-config" "leaked"
: >"$GROK_ARGV_FILE"
run_out="$("$wrapper" run --config "$cfgdir/two-any.yaml" --to "grok:$run_sid")" \
  || fail "run --to: $run_out"
printf '%s\n' "$run_out" | grep -c '^LLM_ESCALATION:' | grep -qx 2 \
  || fail "two escalations this poll: $run_out"
printf '%s\n' "$run_out" | grep -c '^PROMPT_ISSUED:' | grep -qx 1 \
  || fail "one issue this poll: $run_out"
printf '%s\n' "$run_out" | grep -q '^PROMPT_RUN:' || fail "run --to exec: $run_out"
issued="$(printf '%s\n' "$run_out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q 'price_changed' "$issued" || fail "run issue missing price"
grep -q 'status_changed' "$issued" || fail "run issue missing status"
grep -q 'other-config' "$issued" && fail "run --to leaked other-config"
grep -q -- "--session-id $run_sid" "$GROK_ARGV_FILE" || fail "run --to new session-id"

# --- engine rc!=0 must not --to (broken config) ---
# covered by wrapper: non-zero engine return before issue. Smoke: missing file.
set +e
"$wrapper" run --config "$tmpdir/missing.yaml" --to "grok:$sid" >/dev/null 2>"$tmpdir/rc.err"
bad_rc=$?
set -e
[[ "$bad_rc" -ne 0 ]] || fail "missing config must fail"

printf 'prompt-on-change-delivery.test.sh: PASS\n'
