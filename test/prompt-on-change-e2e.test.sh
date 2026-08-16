#!/usr/bin/env bash
# End-to-end verification + success report for prompt-on-change delivery.
#
#   POC_E2E=0  (default) — offline local multi-poll / multi-condition only
#   POC_E2E=1  — also real Grok --to (local fixture + time.is all-group)
#   POC_GROK_LIVE=1 / POC_LIVE_SITE=1 — same live cases (E2E=1 implies both)
#   POC_E2E_CASES=offline,local-to,external-multi — subset
#   POC_GROK_KEEP=DIR — keep state + SUCCESS.md / scorecard.json
#
# Default suite never hits the public web or a live TUI. Live cases use a
# throwaway grok:<uuid> and --assume-idle on resume only.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"
want_e2e="${POC_E2E:-0}"
if [[ "$want_e2e" == "1" ]]; then
  live_grok=1
  live_site=1
else
  live_grok="${POC_GROK_LIVE:-0}"
  live_site="${POC_LIVE_SITE:-0}"
fi
site_url="${POC_LIVE_SITE_URL:-https://time.is/Los_Angeles}"
cases_csv="${POC_E2E_CASES:-}"

fail() {
  printf 'prompt-on-change-e2e.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

want_case() {
  local name="$1"
  if [[ -z "$cases_csv" ]]; then
    return 0
  fi
  case ",$cases_csv," in
    *",$name,"*) return 0 ;;
    *) return 1 ;;
  esac
}

resolve_grok() {
  if [[ -n "${GROK_BIN:-}" && -x "${GROK_BIN}" ]]; then
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

[[ -x "$wrapper" ]] || fail "wrapper not executable"
[[ -f "$pkg/prompts/event.prompt.md" ]] || fail "missing event.prompt.md"
[[ -f "$pkg/references/e2e-success.md" ]] || fail "missing references/e2e-success.md"

if [[ -n "${POC_GROK_KEEP:-}" ]]; then
  tmpdir="$POC_GROK_KEEP"
  mkdir -p "$tmpdir"
else
  tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-e2e.XXXXXX")"
fi
rm -rf "$tmpdir/state" "$tmpdir/cfg" "$tmpdir/www" "$tmpdir/report"
  mkdir -p "$tmpdir/cfg/state" "$tmpdir/www" "$tmpdir/report"
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
export SKILL_ROOT="$pkg"
export POC_GROK_MAX_TURNS="${POC_GROK_MAX_TURNS:-12}"
mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_ESCALATION_DIR"

http_pid=""
cleanup() {
  if [[ -n "${http_pid:-}" ]] && kill -0 "$http_pid" 2>/dev/null; then
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

score="$tmpdir/report/scorecard.jsonl"
: >"$score"

record() {
  local row="$1"
  printf '%s\n' "$row" >>"$score"
  "$python_bin" -c 'import json,sys; r=json.loads(sys.argv[1]); print("score: %s status=%s %s" % (r.get("case"), r.get("status"), r.get("detail","")))' "$row"
}

count_token() {
  local token="$1" text="$2"
  printf '%s\n' "$text" | grep -c "^${token}:" || true
}

first_token() {
  local token="$1" text="$2"
  printf '%s\n' "$text" | sed -n "s/^${token}: //p" | head -1
}

resolve_evidence() {
  local p="$1"
  if [[ -f "$p" ]]; then
    printf '%s\n' "$p"
    return
  fi
  local alt
  alt="$(dirname "$p")/processed/$(basename "$p")"
  if [[ -f "$alt" ]]; then
    printf '%s\n' "$alt"
    return
  fi
  fail "evidence missing: $p"
}

start_local_http() {
  printf '<html><body><span class="price">100</span><span class="status">ok</span></body></html>\n' \
    >"$tmpdir/www/index.html"
  port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
  "$python_bin" -m http.server "$port" --bind 127.0.0.1 --directory "$tmpdir/www" >/dev/null 2>&1 &
  http_pid=$!
  local i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if "$python_bin" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/index.html', timeout=0.4).read()" 2>/dev/null; then
      return
    fi
    sleep 0.1
  done
  fail "local http fixture did not start"
}

write_local_config() {
  local name="$1"
  cat >"$tmpdir/cfg/${name}.yaml" <<YAML
name: ${name}
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
    Previous: {{ previous_value }} → New: {{ new_value }}
    Do not fetch the page.
state:
  file: "state/${name}.json"
  initial:
    price: ""
    status: ""
YAML
}

reset_monitor_state() {
  rm -rf "$POC_STATE_DIR"
  mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_ESCALATION_DIR"
}

# --- offline: multiple silent polls, then two conditions in one issue ---
case_offline() {
  want_case offline || return 0
  start_local_http
  write_local_config e2e-offline-multi
  local cfg="$tmpdir/cfg/e2e-offline-multi.yaml"
  reset_monitor_state
  local seed silent promote esc_n issue_n issued
  seed="$("$wrapper" run --config "$cfg")" || fail "offline seed: $seed"
  printf '%s\n' "$seed" | grep -q '^SEED_OK:' || fail "offline seed token: $seed"
  silent="$("$wrapper" run --config "$cfg")" || fail "offline silent"
  [[ -z "$silent" ]] || fail "offline no-change must be empty: [$silent]"
  printf '<html><body><span class="price">40</span><span class="status">sale</span></body></html>\n' \
    >"$tmpdir/www/index.html"
  promote="$("$wrapper" run --config "$cfg")" || fail "offline promote: $promote"
  esc_n="$(count_token LLM_ESCALATION "$promote")"
  issue_n="$(count_token PROMPT_ISSUED "$promote")"
  [[ "$esc_n" -eq 2 ]] || fail "offline expected 2 LLM_ESCALATION got $esc_n: $promote"
  [[ "$issue_n" -eq 1 ]] || fail "offline expected 1 PROMPT_ISSUED got $issue_n: $promote"
  issued="$(first_token PROMPT_ISSUED "$promote")"
  grep -q 'price_changed' "$issued" || fail "offline issued missing price_changed"
  grep -q 'status_changed' "$issued" || fail "offline issued missing status_changed"
  printf '%s\n' "$promote" | grep -q '^PROMPT_RUN:' && fail "offline must not exec Grok"
  record '{"case":"offline-local-multi","status":"PASS","site":"127.0.0.1","silent_polls":1,"escalations":2,"issues":1,"conditions":["price_changed","status_changed"],"prompt_run":false,"prompt_resume":false,"detail":"seed + silent + two-condition any → one issue"}'
}

# --- live local --to: same fixture, real Grok new + resume ---
case_local_to() {
  want_case local-to || return 0
  if [[ "$live_grok" != "1" ]]; then
    record '{"case":"live-local-to","status":"SKIP","detail":"POC_E2E=0 / POC_GROK_LIVE=0"}'
    return 0
  fi
  local grok
  grok="$(resolve_grok)"
  [[ -n "$grok" ]] || fail "POC_E2E/POC_GROK_LIVE=1 but grok missing"
  unset GROK_BIN
  export GROK_BIN="$grok"
  if [[ -z "${http_pid:-}" ]] || ! kill -0 "$http_pid" 2>/dev/null; then
    start_local_http
  fi
  printf '<html><body><span class="price">100</span><span class="status">ok</span></body></html>\n' \
    >"$tmpdir/www/index.html"
  write_local_config e2e-local-to
  local cfg="$tmpdir/cfg/e2e-local-to.yaml"
  reset_monitor_state
  local sid seed promote esc_n issue_n issued ev1 ev2 resume resume_issued
  sid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  seed="$("$wrapper" run --config "$cfg")" || fail "local-to seed: $seed"
  printf '%s\n' "$seed" | grep -q '^SEED_OK:' || fail "local-to seed token"
  silent="$("$wrapper" run --config "$cfg")" || fail "local-to silent"
  [[ -z "$silent" ]] || fail "local-to no-change must be empty"
  printf '<html><body><span class="price">40</span><span class="status">sale</span></body></html>\n' \
    >"$tmpdir/www/index.html"
  promote="$("$wrapper" run --config "$cfg" --to "grok:$sid")" || fail "local-to promote: $promote"
  esc_n="$(count_token LLM_ESCALATION "$promote")"
  issue_n="$(count_token PROMPT_ISSUED "$promote")"
  [[ "$esc_n" -eq 2 ]] || fail "local-to expected 2 LLM_ESCALATION got $esc_n"
  [[ "$issue_n" -eq 1 ]] || fail "local-to expected 1 PROMPT_ISSUED"
  printf '%s\n' "$promote" | grep -q '^PROMPT_RUN:' || fail "local-to missing PROMPT_RUN"
  issued="$(first_token PROMPT_ISSUED "$promote")"
  grep -q 'price_changed' "$issued" || fail "local-to issued missing price"
  grep -q 'status_changed' "$issued" || fail "local-to issued missing status"
  ev1="$(resolve_evidence "$(printf '%s\n' "$promote" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '1p')")"
  ev2="$(resolve_evidence "$(printf '%s\n' "$promote" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '2p')")"
  resume="$("$wrapper" issue --exec --to "grok:$sid" --assume-idle --evidence "$ev1" --evidence "$ev2")" \
    || fail "local-to resume: $resume"
  printf '%s\n' "$resume" | grep -q '^PROMPT_RESUME:' || fail "local-to missing PROMPT_RESUME"
  resume_issued="$(first_token PROMPT_ISSUED "$resume")"
  grep -q 'async event' "$resume_issued" || fail "local-to resume should use event.prompt.md"
  record "{\"case\":\"live-local-to\",\"status\":\"PASS\",\"site\":\"127.0.0.1\",\"session\":\"$sid\",\"silent_polls\":1,\"escalations\":2,\"issues\":1,\"conditions\":[\"price_changed\",\"status_changed\"],\"prompt_run\":true,\"prompt_resume\":true,\"detail\":\"real Grok --to new + resume\"}"
}

peek_time_is() {
  "$python_bin" - "$site_url" <<'PY'
import re, sys
import httpx
from selectolax.parser import HTMLParser
url = sys.argv[1]
resp = httpx.get(
    url,
    headers={"User-Agent": "prompt-on-change-e2e/1.0", "Accept": "text/html"},
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
}

# --- live external: time.is, all-group of four, silent polls, --to ---
case_external_multi() {
  want_case external-multi || return 0
  if [[ "$live_grok" != "1" || "$live_site" != "1" ]]; then
    record '{"case":"live-external-multi","status":"SKIP","detail":"needs POC_E2E=1 or POC_GROK_LIVE=1 and POC_LIVE_SITE=1"}'
    return 0
  fi
  local grok
  grok="$(resolve_grok)"
  [[ -n "$grok" ]] || fail "live external-multi needs grok"
  unset GROK_BIN
  export GROK_BIN="$grok"
  local peek seed_clock seed_date target_hm target_re sid cfg
  peek="$(peek_time_is)" || fail "peek $site_url"
  seed_clock="$(printf '%s\n' "$peek" | sed -n '1p')"
  seed_date="$(printf '%s\n' "$peek" | sed -n '2p')"
  target_hm="$(printf '%s\n' "$peek" | sed -n '3p')"
  target_re="$(printf '%s\n' "$peek" | sed -n '4p')"
  [[ -n "$target_re" ]] || fail "peek fields: $peek"
  printf 'e2e peek %s clock=%s date=%s target=%s\n' "$site_url" "$seed_clock" "$seed_date" "$target_hm"
  reset_monitor_state
  cat >"$tmpdir/cfg/e2e-external-multi.yaml" <<YAML
name: e2e-external-multi
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
    value: "${target_re}"
  - id: clock_moved
    field: clock
    op: changed
  - id: page_ok
    field: http.page.status
    op: eq
    value: 200
  - id: has_date
    field: clockdate
    op: exists
groups:
  - name: promote
    all:
      - time_hits_known
      - clock_moved
      - page_ok
      - has_date
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    Public site multi-condition all-group.
    URL: ${site_url}
    Condition: {{ condition_id }}
    Previous: {{ previous_value }} → New: {{ new_value }}
    Do not fetch the page. Use only this evidence.
state:
  file: state/e2e-external-multi.json
  initial:
    clock: ""
    clockdate: ""
YAML
  cfg="$tmpdir/cfg/e2e-external-multi.yaml"
  "$wrapper" validate --config "$cfg" >/dev/null || fail "external-multi validate"
  sid="$(uuidgen | tr '[:upper:]' '[:lower:]')"
  local seed out rc class hit polls silent_n esc_n issue_n issued ev1 ev2 ev3 ev4 resume
  seed="$("$wrapper" run --config "$cfg")" || fail "external-multi seed: $seed"
  printf '%s\n' "$seed" | grep -q '^SEED_OK:' || fail "external-multi seed token"
  hit=""
  silent_n=0
  polls=0
  local max_polls="${POC_LIVE_SITE_MAX_POLLS:-16}"
  local sleep_s="${POC_LIVE_SITE_SLEEP:-8}"
  while [[ "$polls" -lt "$max_polls" ]]; do
    polls=$((polls + 1))
    sleep "$sleep_s"
    set +e
    out="$("$wrapper" run --config "$cfg" --to "grok:$sid" 2>"$tmpdir/run.err")"
    rc=$?
    set -e
    class="other"
    if [[ "$rc" -eq 0 && -z "$out" ]]; then
      class="silent"
      silent_n=$((silent_n + 1))
    elif printf '%s\n' "$out" | grep -q '^LLM_ESCALATION:'; then
      class="escalate"
      hit="$out"
    fi
    printf 'external-multi poll %s got=%s rc=%s\n' "$polls" "$class" "$rc"
    if [[ "$rc" -ne 0 ]]; then
      fail "external-multi poll $polls rc=$rc out=[$out] err=$(cat "$tmpdir/run.err")"
    fi
    if [[ "$class" == "escalate" ]]; then
      break
    fi
    if [[ "$class" != "silent" ]]; then
      fail "external-multi poll $polls unexpected class=$class out=[$out]"
    fi
  done
  [[ -n "$hit" ]] || fail "time $target_hm never appeared on $site_url after $polls polls"
  esc_n="$(count_token LLM_ESCALATION "$hit")"
  issue_n="$(count_token PROMPT_ISSUED "$hit")"
  [[ "$esc_n" -eq 4 ]] || fail "external-multi expected 4 LLM_ESCALATION got $esc_n: $hit"
  [[ "$issue_n" -eq 1 ]] || fail "external-multi expected 1 PROMPT_ISSUED got $issue_n"
  printf '%s\n' "$hit" | grep -q '^PROMPT_RUN:' || fail "external-multi missing PROMPT_RUN"
  issued="$(first_token PROMPT_ISSUED "$hit")"
  local cid
  for cid in time_hits_known clock_moved page_ok has_date; do
    grep -q "$cid" "$issued" || fail "external-multi issued missing $cid"
  done
  ev1="$(resolve_evidence "$(printf '%s\n' "$hit" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '1p')")"
  ev2="$(resolve_evidence "$(printf '%s\n' "$hit" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '2p')")"
  ev3="$(resolve_evidence "$(printf '%s\n' "$hit" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '3p')")"
  ev4="$(resolve_evidence "$(printf '%s\n' "$hit" | sed -n 's/^LLM_ESCALATION: //p' | sed -n '4p')")"
  resume="$("$wrapper" issue --exec --to "grok:$sid" --assume-idle \
    --evidence "$ev1" --evidence "$ev2" --evidence "$ev3" --evidence "$ev4")" \
    || fail "external-multi resume: $resume"
  printf '%s\n' "$resume" | grep -q '^PROMPT_RESUME:' || fail "external-multi missing PROMPT_RESUME"
  record "{\"case\":\"live-external-multi\",\"status\":\"PASS\",\"site\":\"$site_url\",\"session\":\"$sid\",\"target\":\"$target_hm\",\"silent_polls\":$silent_n,\"escalations\":4,\"issues\":1,\"conditions\":[\"time_hits_known\",\"clock_moved\",\"page_ok\",\"has_date\"],\"prompt_run\":true,\"prompt_resume\":true,\"detail\":\"real GET + all-group + Grok --to\"}"
}

write_success_doc() {
  "$python_bin" - "$score" "$tmpdir/report/SUCCESS.md" "$tmpdir/report/scorecard.json" <<'PY'
import json, pathlib, sys
from datetime import datetime, timezone
src, md_path, json_path = sys.argv[1:4]
rows = []
for line in pathlib.Path(src).read_text(encoding="utf-8").splitlines():
    if line.strip():
        rows.append(json.loads(line))
failed = [r for r in rows if r.get("status") == "FAIL"]
passed = [r for r in rows if r.get("status") == "PASS"]
skipped = [r for r in rows if r.get("status") == "SKIP"]
doc = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "passed": len(passed),
    "skipped": len(skipped),
    "failed": len(failed),
    "cases": rows,
}
pathlib.Path(json_path).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
lines = [
    "# prompt-on-change e2e success",
    "",
    "Generated: **%s**" % doc["generated_at"],
    "",
    "| Case | Status | Escalations | Issues | Silent polls | Grok | Detail |",
    "|---|---|---:|---:|---:|---|---|",
]
for r in rows:
    grok = []
    if r.get("prompt_run"):
        grok.append("RUN")
    if r.get("prompt_resume"):
        grok.append("RESUME")
    lines.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (
        r.get("case", ""),
        r.get("status", ""),
        r.get("escalations", "—"),
        r.get("issues", "—"),
        r.get("silent_polls", "—"),
        "+".join(grok) or "—",
        r.get("detail", ""),
    ))
lines += [
    "",
    "## Contract",
    "",
    "- A no-change poll is exit 0 and empty stdout.",
    "- A match prints one `LLM_ESCALATION:` per matched condition, then **one** `PROMPT_ISSUED:`.",
    "- `--to grok:<uuid>` adds exactly one of `PROMPT_RUN:` (new) or `PROMPT_RESUME:` (existing idle).",
    "- `matches[]` / issued prompt include this poll only (no cross-config leak).",
    "",
    "See `references/e2e-success.md` for how to re-run live cases.",
    "",
]
pathlib.Path(md_path).write_text("\n".join(lines), encoding="utf-8")
print(pathlib.Path(md_path).read_text(encoding="utf-8"))
if failed:
    raise SystemExit("scorecard has FAIL rows")
PY
}

case_offline
case_local_to
case_external_multi
write_success_doc

if [[ -n "${POC_GROK_KEEP:-}" ]]; then
  printf 'prompt-on-change-e2e.test.sh: report %s\n' "$tmpdir/report/SUCCESS.md"
fi
printf 'prompt-on-change-e2e.test.sh: PASS\n'
