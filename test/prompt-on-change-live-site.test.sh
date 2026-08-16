#!/usr/bin/env bash
# Live public-site scrape: poll https://time.is/Los_Angeles until #clock
# hits a known next-minute value, then issue the escalation prompt.
#
#   POC_LIVE_SITE=0  (default) — no network; exit 0 with SKIP
#   POC_LIVE_SITE=1  — fetch the real page; fail if extract/promote fails
#   POC_GROK_LIVE=1  — also run --exec (Grok headless) on the issued prompt
#   POC_GROK_KEEP=DIR — keep state / issued prompts / scorecard
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"
live_site="${POC_LIVE_SITE:-0}"
live_grok="${POC_GROK_LIVE:-0}"
site_url="${POC_LIVE_SITE_URL:-https://time.is/Los_Angeles}"

fail() {
  printf 'prompt-on-change-live-site.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$wrapper" ]] || fail "wrapper not executable"

if [[ "$live_site" != "1" ]]; then
  printf 'prompt-on-change-live-site.test.sh: SKIP live site (POC_LIVE_SITE=0)\n'
  "$wrapper" --help >/dev/null 2>&1 || fail "wrapper --help"
  exit 0
fi

if [[ -n "${POC_GROK_KEEP:-}" ]]; then
  tmpdir="$POC_GROK_KEEP"
  mkdir -p "$tmpdir"
else
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-live-site.XXXXXX")"
fi
cfgdir="$tmpdir/cfg"
rm -rf "$tmpdir/state" "$tmpdir/cfg"
mkdir -p "$cfgdir"
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
export SKILL_ROOT="$pkg"
mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_ESCALATION_DIR"

cleanup() {
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

write_config() {
  local target="$1"
  cat >"$cfgdir/live-site.yaml" <<YAML
name: live-site-time-hit
enabled: true
seed_mode: true
sources:
  - id: page
    url: "${site_url}"
    headers:
      User-Agent: "prompt-on-change-e2e/1.0"
      Accept: "text/html,application/xhtml+xml"
    extract:
      - id: clock
        type: css
        selector: "#clock"
        transform: text
      - id: clockdate
        type: css
        selector: "#dd"
        transform: text
conditions:
  - id: time_hits_known
    field: clock
    op: matches
    value: "${target}"
groups:
  - name: promote
    any: [time_hits_known]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    Public site clock hit the known time.
    URL: ${site_url}
    Previous: {{ previous_value }} → New: {{ new_value }}
    Date: {{ clockdate }}
    Reason: {{ match_reason }}
    Do not fetch the page. Use only this evidence.
state:
  file: state.json
  initial:
    clock: ""
    clockdate: ""
YAML
}

# Peek the live #clock so the known value is the next minute on that page.
peek="$("$python_bin" - "$site_url" <<'PY'
import re, sys
import httpx
from selectolax.parser import HTMLParser

url = sys.argv[1]
resp = httpx.get(
    url,
    headers={
        "User-Agent": "prompt-on-change-e2e/1.0",
        "Accept": "text/html,application/xhtml+xml",
    },
    follow_redirects=True,
    timeout=20.0,
)
resp.raise_for_status()
tree = HTMLParser(resp.text)
clock_node = tree.css_first("#clock")
date_node = tree.css_first("#dd")
if clock_node is None:
    raise SystemExit("peek: #clock missing from " + url)
clock = clock_node.text(strip=True)
date = date_node.text(strip=True) if date_node is not None else ""
m = re.match(r"(?P<h>\d{1,2}):(?P<min>\d{2}):(?P<sec>\d{2})(?P<ampm>AM|PM)?", clock)
if not m:
    raise SystemExit("peek: unparseable clock %r" % clock)
hour = int(m.group("h"))
minute = int(m.group("min"))
ampm = m.group("ampm") or ""
minute += 1
if minute >= 60:
    minute = 0
    hour += 1
    if hour == 12 and ampm:
        ampm = "PM" if ampm == "AM" else "AM"
    elif hour > 12:
        hour = 1
target = "%02d:%02d" % (hour, minute)
print(clock)
print(date)
print(target)
print("^%s:" % target)
PY
)" || fail "peek ${site_url}"

seed_clock="$(printf '%s\n' "$peek" | sed -n '1p')"
seed_date="$(printf '%s\n' "$peek" | sed -n '2p')"
target_hm="$(printf '%s\n' "$peek" | sed -n '3p')"
target_re="$(printf '%s\n' "$peek" | sed -n '4p')"
[[ -n "$seed_clock" && -n "$target_hm" && -n "$target_re" ]] || fail "peek fields: $peek"
printf 'live site %s peek clock=%s date=%s target=%s\n' "$site_url" "$seed_clock" "$seed_date" "$target_hm"

write_config "$target_re"
cfg="$cfgdir/live-site.yaml"
"$wrapper" validate --config "$cfg" >/dev/null || fail "validate"

run_once() {
  local -a args=(run --config "$cfg")
  if [[ "$live_grok" == "1" ]]; then
    args+=(--exec)
  fi
  set +e
  out="$("$wrapper" "${args[@]}" 2>"$tmpdir/run.err")"
  rc=$?
  set -e
  printf '%s\n' "$out"
  return "$rc"
}

seed_out="$(run_once)" || fail "seed rc out=[$seed_out] err=$(cat "$tmpdir/run.err")"
printf '%s\n' "$seed_out" | grep -q '^SEED_OK:' || fail "seed token: [$seed_out] err=$(cat "$tmpdir/run.err")"
printf 'seed: %s\n' "$seed_out"

score="$tmpdir/scorecard.jsonl"
: >"$score"
hit=""
polls=0
max_polls="${POC_LIVE_SITE_MAX_POLLS:-16}"
sleep_s="${POC_LIVE_SITE_SLEEP:-8}"

while [[ "$polls" -lt "$max_polls" ]]; do
  polls=$((polls + 1))
  sleep "$sleep_s"
  set +e
  out="$(run_once)"
  rc=$?
  set -e
  class="other"
  if [[ "$rc" -eq 0 && -z "$out" ]]; then
    class="silent"
  elif printf '%s\n' "$out" | grep -q '^SEED_OK:'; then
    class="seed"
  elif printf '%s\n' "$out" | grep -q '^LLM_ESCALATION:'; then
    class="escalate"
    hit="$out"
  fi
  clock_now=""
  if [[ -f "$cfgdir/state.json" ]]; then
    clock_now="$("$python_bin" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("clock",""))' "$cfgdir/state.json")"
  fi
  printf 'poll %s clock=%s want=escalate-or-silent got=%s rc=%s\n' "$polls" "$clock_now" "$class" "$rc"
  printf '%s\n' "$out" | sed 's/^/  | /'
  "$python_bin" -c '
import json,sys
print(json.dumps({
  "poll": int(sys.argv[1]),
  "clock": sys.argv[2],
  "got": sys.argv[3],
  "rc": int(sys.argv[4]),
}))
' "$polls" "$clock_now" "$class" "$rc" >>"$score"
  if [[ "$rc" -ne 0 ]]; then
    fail "poll $polls rc=$rc out=[$out] err=$(cat "$tmpdir/run.err")"
  fi
  if [[ "$class" == "escalate" ]]; then
    break
  fi
  if [[ "$class" != "silent" ]]; then
    fail "poll $polls unexpected class=$class out=[$out]"
  fi
done

[[ -n "$hit" ]] || fail "time $target_hm never appeared on ${site_url} after ${polls} polls"

printf '%s\n' "$hit" | grep -q '^PROMPT_ISSUED:' || fail "match must issue a prompt: $hit"
ev="$(printf '%s\n' "$hit" | sed -n 's/^LLM_ESCALATION: //p' | head -1)"
if [[ ! -f "$ev" ]]; then
  # issue / issue --exec claims the file into processed/.
  ev="$(dirname "$ev")/processed/$(basename "$ev")"
fi
[[ -f "$ev" ]] || fail "missing evidence: $ev"
"$python_bin" - "$ev" "$target_hm" "$site_url" <<'PY' || fail "evidence from live site"
import json, sys
ev = json.loads(open(sys.argv[1], encoding="utf-8").read())
target, url = sys.argv[2], sys.argv[3]
new = str(ev.get("new_value") or "")
assert new.startswith(target + ":"), (new, target, ev)
blob = json.dumps(ev)
assert "time.is" in blob or url in blob, ev
print("evidence ok new_value=%s" % new)
PY

if [[ "$live_grok" == "1" ]]; then
  printf '%s\n' "$hit" | grep -q '^PROMPT_RUN:' || fail "match must exec the prompt: $hit"
  run_log="$(printf '%s\n' "$hit" | sed -n 's/^PROMPT_RUN: //p' | head -1)"
  "$python_bin" - "$run_log" "$target_hm" <<'PY' || fail "grok outcome"
import json, sys
log = json.loads(open(sys.argv[1], encoding="utf-8").read())
target = sys.argv[2]
assert log.get("grok_exit") == 0, log
out = log.get("outcome") or {}
if log.get("parse_error"):
    text = open(log["stdout_path"], encoding="utf-8", errors="replace").read()
    assert target in text, (log.get("parse_error"), text[-1500:])
else:
    assert target in str(out.get("new_value")), out
print("grok outcome ok")
PY
else
  "$wrapper" claim >/dev/null || fail "claim after issued prompt"
fi

printf 'prompt-on-change-live-site.test.sh: PASS (%s polls, target=%s, site=%s)\n' \
  "$polls" "$target_hm" "$site_url"
