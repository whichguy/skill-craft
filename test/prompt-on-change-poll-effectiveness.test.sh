#!/usr/bin/env bash
# Repeated-poll effectiveness: advance a page clock, assert silence vs one
# promotion when time hits a known value, fire_once hold, then re-hit.
#
#   POC_GROK_LIVE=0  (default) — engine/wrapper only
#   POC_GROK_LIVE=1  — issue --exec on the first escalation
#   POC_GROK_KEEP=DIR — keep fixture + scorecard
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"
live="${POC_GROK_LIVE:-0}"
target="${POC_POLL_TARGET:-16:53}"

fail() {
  printf 'prompt-on-change-poll-effectiveness.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$wrapper" ]] || fail "wrapper not executable"

if [[ -n "${POC_GROK_KEEP:-}" ]]; then
  tmpdir="$POC_GROK_KEEP"
  mkdir -p "$tmpdir"
else
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-poll.XXXXXX")"
fi
www="$tmpdir/www"
cfgdir="$tmpdir/cfg"
# KEEP may point at a prior run; always start with a clean monitor tree.
rm -rf "$tmpdir/state" "$tmpdir/cfg"
mkdir -p "$www" "$cfgdir"
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
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

write_clock() {
  printf '<html><body><time class="clock">%s</time></body></html>\n' "$1" >"$www/index.html"
}

port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
write_clock "15:50"
"$python_bin" -m http.server "$port" --bind 127.0.0.1 --directory "$www" >/dev/null 2>&1 &
http_pid=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "$python_bin" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/index.html', timeout=0.4).read()" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

cat >"$cfgdir/poll.yaml" <<YAML
name: poll-effectiveness-time-hit
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
    value: "${target}"
groups:
  - name: promote
    any: [time_hits_known]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
state:
  file: state.json
  initial:
    clock: ""
YAML
cfg="$cfgdir/poll.yaml"
"$wrapper" validate --config "$cfg" >/dev/null || fail "validate"

# Sequence: seed, two misses, first hit, hold at target, leave target, re-hit.
clocks=(15:50 15:51 15:52 "$target" "$target" 16:54 "$target")
expect=(seed silent silent escalate silent silent escalate)

score="$tmpdir/scorecard.jsonl"
: >"$score"
escalations=0
unexpected=0
i=0
for clock in "${clocks[@]}"; do
  want="${expect[$i]}"
  i=$((i + 1))
  write_clock "$clock"
  run_args=(run --config "$cfg")
  if [[ "$live" == "1" ]]; then
    run_args+=(--exec)
  fi
  set +e
  out="$("$wrapper" "${run_args[@]}" 2>"$tmpdir/run.err")"
  rc=$?
  set -e
  class="other"
  if [[ "$rc" -eq 0 && -z "$out" ]]; then
    class="silent"
  elif printf '%s\n' "$out" | grep -q '^SEED_OK:'; then
    class="seed"
  elif printf '%s\n' "$out" | grep -q '^LLM_ESCALATION:'; then
    class="escalate"
    escalations=$((escalations + 1))
  fi
  if [[ "$class" != "$want" ]]; then
    unexpected=$((unexpected + 1))
  fi
  printf 'poll %s clock=%s want=%s got=%s rc=%s\n' "$i" "$clock" "$want" "$class" "$rc"
  printf '%s\n' "$out" | sed 's/^/  | /'
  "$python_bin" -c '
import json,sys
print(json.dumps({
  "poll": int(sys.argv[1]),
  "clock": sys.argv[2],
  "want": sys.argv[3],
  "got": sys.argv[4],
  "rc": int(sys.argv[5]),
  "ok": sys.argv[3] == sys.argv[4],
}))
' "$i" "$clock" "$want" "$class" "$rc" >>"$score"
  if [[ "$class" != "$want" ]]; then
    fail "poll $i clock=$clock want=$want got=$class out=[$out] err=$(cat "$tmpdir/run.err")"
  fi

  if [[ "$class" == "escalate" ]]; then
    printf '%s\n' "$out" | grep -q '^PROMPT_ISSUED:' || fail "match must issue a prompt: $out"
    if [[ "$live" == "1" ]]; then
      printf '%s\n' "$out" | grep -q '^PROMPT_RUN:' || fail "match must exec the prompt: $out"
      run_log="$(printf '%s\n' "$out" | sed -n 's/^PROMPT_RUN: //p' | head -1)"
      "$python_bin" - "$run_log" "$target" <<'PY' || fail "grok outcome"
import json,sys
log=json.loads(open(sys.argv[1],encoding="utf-8").read())
target=sys.argv[2]
assert log.get("grok_exit")==0, log
out=log.get("outcome") or {}
if log.get("parse_error"):
    text=open(log["stdout_path"],encoding="utf-8",errors="replace").read()
    assert target in text, (log.get("parse_error"), text[-1500:])
else:
    assert str(out.get("new_value"))==target, out
print("grok outcome ok")
PY
    else
      "$wrapper" claim >/dev/null || fail "claim after issued prompt"
    fi
  fi
done

pending="$("$wrapper" status)"
printf '%s\n' "$pending"

"$python_bin" - "$score" "$escalations" <<'PY'
import json,sys
rows=[json.loads(l) for l in open(sys.argv[1],encoding="utf-8") if l.strip()]
esc=int(sys.argv[2])
ok=sum(1 for r in rows if r["ok"])
print(f"scorecard: {ok}/{len(rows)} polls correct, escalations={esc}")
assert ok==len(rows), rows
assert esc==2, esc
PY

printf 'prompt-on-change-poll-effectiveness.test.sh: PASS (%s polls, 2 promotions)\n' "${#clocks[@]}"
