#!/usr/bin/env bash
# Hermetic lifecycle: local HTTP fixture + wrapper run/explain/issue/claim/status.
# No Grok, no example.com. Honors PYTHON / POC_STATE_DIR when the parent exports them.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
pkg="$root/skills/prompt-on-change"
wrapper="$pkg/scripts/prompt-on-change"

fail() {
  printf 'prompt-on-change-lifecycle.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$wrapper" ]] || fail "wrapper not executable"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/poc-life.XXXXXX")"
www="$tmpdir/www"
cfgdir="$tmpdir/cfg"
mkdir -p "$www" "$cfgdir/state"
# Always isolate monitor state (do not inherit a dirty POC_STATE_DIR).
export POC_STATE_DIR="$tmpdir/state"
export DETECT_ENGINE_HEALTH_DIR="$POC_STATE_DIR"
export DETECT_ENGINE_ESCALATION_DIR="$POC_STATE_DIR/escalations"
export DETECT_ENGINE_LOG_FILE="$POC_STATE_DIR/engine.log"
mkdir -p "$POC_STATE_DIR" "$DETECT_ENGINE_ESCALATION_DIR"

http_pid=""
post_pid=""
cleanup() {
  if [[ -n "$http_pid" ]] && kill -0 "$http_pid" 2>/dev/null; then
    kill "$http_pid" 2>/dev/null || true
    wait "$http_pid" 2>/dev/null || true
  fi
  if [[ -n "${post_pid:-}" ]] && kill -0 "$post_pid" 2>/dev/null; then
    kill "$post_pid" 2>/dev/null || true
    wait "$post_pid" 2>/dev/null || true
  fi
  rm -rf "$tmpdir"
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

write_page() {
  printf '<html><body><span class="price">%s</span></body></html>\n' "$1" >"$www/index.html"
}

port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
write_page 100
"$python_bin" -m http.server "$port" --bind 127.0.0.1 --directory "$www" >/dev/null 2>&1 &
http_pid=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "$python_bin" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:${port}/index.html', timeout=0.4).read()" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

cat >"$cfgdir/local-http-promote.yaml" <<YAML
name: local-http-promote
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
conditions:
  - id: price_changed
    field: price
    op: changed
  - id: price_in_sale
    field: price
    op: between
    min: 10
    max: 50
groups:
  - name: promote
    any: [price_changed, price_in_sale]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    {{ config_name }} fired {{ condition_id }}.
    Previous: {{ previous_value }} → New: {{ new_value }}
state:
  file: state.json
  initial:
    price: ""
YAML

cfg="$cfgdir/local-http-promote.yaml"
"$wrapper" validate --config "$cfg" >/dev/null || fail "fixture validate"

explain_json() {
  "$wrapper" explain --config "$cfg"
}

# 1. Fresh explain is seed (no last_checked yet)
pre="$(explain_json)" || fail "explain before seed: $pre"
printf '%s\n' "$pre" | grep -q '"seed": true' || fail "pre-seed explain seed true: $pre"
printf '%s\n' "$pre" | grep -q '"would_escalate": false' || fail "pre-seed would_escalate false: $pre"

# 2. Seed run
seed_out="$("$wrapper" run --config "$cfg")" || fail "seed run failed: $seed_out"
printf '%s\n' "$seed_out" | grep -q 'SEED_OK: local-http-promote' || fail "seed token: $seed_out"
printf '%s\n' "$seed_out" | grep -q 'LLM_ESCALATION:' && fail "seed must not escalate: $seed_out"

# 3. After seed, same HTML: not seed, no escalate
after_seed="$(explain_json)" || fail "explain after seed"
printf '%s\n' "$after_seed" | grep -q '"seed": false' || fail "after seed explain seed false: $after_seed"
printf '%s\n' "$after_seed" | grep -q '"would_escalate": false' || fail "after seed would_escalate: $after_seed"

# 4. No-change run: empty stdout
nochange="$("$wrapper" run --config "$cfg")" || fail "no-change run"
printf '%s\n' "$nochange" | grep -q 'LLM_ESCALATION:' && fail "no-change escalated: $nochange"
printf '%s\n' "$nochange" | grep -q 'SEED_OK:' && fail "no-change reprinted seed: $nochange"
[[ -z "${nochange}" ]] || fail "no-change stdout must be empty: [$nochange]"

# 5. Rewrite then explain (read-only) should want to escalate
write_page 40
promotable="$(explain_json)" || fail "explain after rewrite"
printf '%s\n' "$promotable" | grep -q '"would_escalate": true' || fail "rewrite explain would_escalate: $promotable"

# 5b. --dry-run must not write evidence, issue, or advance fire_once
dry="$("$wrapper" run --config "$cfg" --dry-run")" || fail "dry-run: $dry"
printf '%s\n' "$dry" | grep -q 'LLM_ESCALATION:' && fail "dry-run must not escalate: $dry"
printf '%s\n' "$dry" | grep -q 'PROMPT_ISSUED:' && fail "dry-run must not issue: $dry"
still_promotable="$(explain_json)" || fail "explain after dry-run"
printf '%s\n' "$still_promotable" | grep -q '"would_escalate": true' \
  || fail "dry-run must leave would_escalate true: $still_promotable"

# 6. Promote run
promote="$("$wrapper" run --config "$cfg")" || fail "promote run: $promote"
printf '%s\n' "$promote" | grep -q 'LLM_ESCALATION:' || fail "promote missing LLM_ESCALATION: $promote"
esc_path="$(printf '%s\n' "$promote" | sed -n 's/^LLM_ESCALATION: //p' | head -1)"
[[ -f "$esc_path" ]] || fail "evidence missing: $esc_path"
"$python_bin" -c '
import json,sys
d=json.loads(open(sys.argv[1],encoding="utf-8").read())
assert str(d.get("previous_value")) == "100", d
assert str(d.get("new_value")) == "40", d
assert "http" in d, d
' "$esc_path" || fail "evidence prev/new/http"

# 7. Issue without exec
issue_out="$("$wrapper" issue)" || fail "issue pending"
printf '%s\n' "$issue_out" | grep -q 'PROMPT_ISSUED:' || fail "issue token: $issue_out"
issued="$(printf '%s\n' "$issue_out" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
[[ -f "$issued" ]] || fail "issued prompt missing"
grep -q 'escalation handler' "$issued" || fail "issued prompt missing escalation text"
grep -q '"previous_value"' "$issued" || fail "issued prompt missing spliced evidence"

# 8. Claim then empty claim
claim_out="$("$wrapper" claim)" || fail "claim"
printf '%s\n' "$claim_out" | grep -q 'CLAIMED:' || fail "claim token: $claim_out"
claim2="$("$wrapper" claim)" || fail "second claim"
printf '%s\n' "$claim2" | grep -q 'CLAIM_EMPTY' || fail "second claim empty: $claim2"
printf '%s\n' "$claim2" | grep -q '\[SILENT\]' || fail "second claim silent: $claim2"

# 9. Replay from processed
replay="$("$wrapper" issue --last)" || fail "issue --last"
printf '%s\n' "$replay" | grep -q 'PROMPT_ISSUED:' || fail "replay token: $replay"
replay_path="$(printf '%s\n' "$replay" | sed -n 's/^PROMPT_ISSUED: //p' | head -1)"
grep -q 'already in processed' "$replay_path" || fail "replay should mark processed mode"

# 10. Fire-once: same new price, no new escalation
fire="$("$wrapper" run --config "$cfg")" || fail "fire-once run"
printf '%s\n' "$fire" | grep -q 'LLM_ESCALATION:' && fail "fire-once re-escalated: $fire"
fired="$(explain_json)" || fail "explain fire-once"
printf '%s\n' "$fired" | grep -q '"gated_by": "fire_once"' || fail "explain fire_once: $fired"
printf '%s\n' "$fired" | grep -q '"would_escalate": false' || fail "fire-once would_escalate: $fired"

# 11. Status
st="$("$wrapper" status)" || fail "status"
printf '%s\n' "$st" | grep -q 'pending: 0' || fail "status pending: $st"
printf '%s\n' "$st" | grep -E -q 'processed: [1-9]' || fail "status processed: $st"
printf '%s\n' "$st" | grep -q 'CLAIM_EMPTY' || fail "status empty pending: $st"

# Empty issue
empty_issue="$("$wrapper" issue)" || fail "issue empty pending"
printf '%s\n' "$empty_issue" | grep -q 'CLAIM_EMPTY' || fail "empty issue: $empty_issue"

# --- usage / bootstrap / validate rejects ---
set +e
"$wrapper" >/dev/null 2>"$tmpdir/usage.err"
usage_rc=$?
"$wrapper" not-a-command >/dev/null 2>"$tmpdir/unk.err"
unk_rc=$?
"$wrapper" run >/dev/null 2>"$tmpdir/noconfig.err"
noconfig_rc=$?
set -e
[[ "$usage_rc" -eq 64 ]] || fail "no-args exit 64 got $usage_rc"
[[ "$unk_rc" -eq 64 ]] || fail "unknown cmd exit 64 got $unk_rc"
grep -qi 'unknown command' "$tmpdir/unk.err" || fail "unknown cmd message"
[[ "$noconfig_rc" -eq 64 ]] || fail "run without --config exit 64 got $noconfig_rc"

set +e
POC_STATE_DIR="$pkg" "$wrapper" bootstrap >/dev/null 2>"$tmpdir/boot.err"
boot_rc=$?
set -e
[[ "$boot_rc" -ne 0 ]] || fail "bootstrap inside skill must refuse"
grep -qi 'refuse venv' "$tmpdir/boot.err" || fail "bootstrap refuse: $(cat "$tmpdir/boot.err")"

write_bad_cfg() {
  local name="$1"
  cat >"$cfgdir/${name}.yaml"
}

write_bad_cfg get-form <<YAML
name: get-form
enabled: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    method: GET
    form: {q: x}
    extract:
      - id: price
        type: css
        selector: ".price"
        transform: text
conditions:
  - {id: c, field: price, op: changed}
groups:
  - {name: g, any: [c]}
state:
  file: state-get-form.json
  initial: {price: ""}
YAML
write_bad_cfg head-body <<YAML
name: head-body
enabled: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    method: HEAD
    body: "x"
    headers: {Content-Type: text/plain}
    extract:
      - {id: st, type: header, name: status_code}
conditions:
  - {id: c, field: st, op: changed}
groups:
  - {name: g, any: [c]}
state:
  file: state-head-body.json
  initial: {st: ""}
YAML
write_bad_cfg put-method <<YAML
name: put-method
enabled: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    method: PUT
    extract:
      - id: price
        type: css
        selector: ".price"
        transform: text
conditions:
  - {id: c, field: price, op: changed}
groups:
  - {name: g, any: [c]}
state:
  file: state-put.json
  initial: {price: ""}
YAML
write_bad_cfg form-json <<YAML
name: form-json
enabled: true
sources:
  - id: page
    url: "http://127.0.0.1:${port}/index.html"
    method: POST
    form: {q: a}
    json: {q: b}
    extract:
      - id: price
        type: css
        selector: ".price"
        transform: text
conditions:
  - {id: c, field: price, op: changed}
groups:
  - {name: g, any: [c]}
state:
  file: state-form-json.json
  initial: {price: ""}
YAML
for bad in get-form head-body put-method form-json; do
  set +e
  "$wrapper" validate --config "$cfgdir/${bad}.yaml" >/dev/null 2>"$tmpdir/${bad}.err"
  bad_rc=$?
  set -e
  [[ "$bad_rc" -ne 0 ]] || fail "validate must reject ${bad}"
done

# --- --no-issue then later issue; CLAIM_SKIP ---
cat >"$cfgdir/local-no-issue.yaml" <<YAML
name: local-no-issue
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
conditions:
  - id: price_changed
    field: price
    op: changed
groups:
  - name: promote
    any: [price_changed]
llm_escalation:
  trigger_groups: [promote]
  fire_once: false
  prompt: |
    {{ config_name }} {{ condition_id }}
state:
  file: state-no-issue.json
  initial:
    price: ""
YAML
write_page 100
"$wrapper" run --config "$cfgdir/local-no-issue.yaml" >/dev/null || fail "no-issue seed"
write_page 41
no_issue="$("$wrapper" run --config "$cfgdir/local-no-issue.yaml" --no-issue")" \
  || fail "no-issue run: $no_issue"
printf '%s\n' "$no_issue" | grep -q 'LLM_ESCALATION:' || fail "no-issue missing escalation: $no_issue"
printf '%s\n' "$no_issue" | grep -q 'PROMPT_ISSUED:' && fail "no-issue must not issue: $no_issue"
later_issue="$("$wrapper" issue)" || fail "issue after --no-issue"
printf '%s\n' "$later_issue" | grep -q 'PROMPT_ISSUED:' || fail "later issue: $later_issue"

skip_name="claim-skip-probe.json"
printf '%s\n' '{"config_name":"local-no-issue","condition_id":"price_changed","escalation_type":"condition_matched"}' \
  >"$DETECT_ENGINE_ESCALATION_DIR/$skip_name"
mkdir -p "$DETECT_ENGINE_ESCALATION_DIR/processed"
chmod a-w "$DETECT_ENGINE_ESCALATION_DIR/processed"
set +e
skip_out="$("$wrapper" claim)"
skip_rc=$?
set -e
chmod u+w "$DETECT_ENGINE_ESCALATION_DIR/processed"
[[ "$skip_rc" -eq 0 ]] || fail "CLAIM_SKIP claim rc: $skip_rc $skip_out"
printf '%s\n' "$skip_out" | grep -q 'CLAIM_SKIP:' || fail "CLAIM_SKIP token: $skip_out"
rm -f "$DETECT_ENGINE_ESCALATION_DIR/$skip_name"

# --- POST form through the wrapper ---
post_port="$("$python_bin" -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
printf '<html><body><span class="headline">old</span></body></html>\n' >"$www/post.html"
"$python_bin" - "$post_port" "$www/post.html" <<'PY' &
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

port = int(sys.argv[1])
page = Path(sys.argv[2])

class H(BaseHTTPRequestHandler):
    def do_POST(self):
        body = page.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *args):
        return

HTTPServer(("127.0.0.1", port), H).serve_forever()
PY
post_pid=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if "$python_bin" -c "import httpx; r=httpx.post('http://127.0.0.1:${post_port}/search', data={'q':'x'}, timeout=0.4); r.raise_for_status()" 2>/dev/null; then
    break
  fi
  sleep 0.1
done
cat >"$cfgdir/local-post-form.yaml" <<YAML
name: local-post-form
enabled: true
seed_mode: true
sources:
  - id: search
    url: "http://127.0.0.1:${post_port}/search"
    method: POST
    form:
      q: widget
    extract:
      - id: headline
        type: css
        selector: ".headline"
        transform: text
conditions:
  - id: headline_changed
    field: headline
    op: changed
groups:
  - name: promote
    any: [headline_changed]
llm_escalation:
  trigger_groups: [promote]
  fire_once: true
  prompt: |
    {{ config_name }} {{ condition_id }}
state:
  file: state-post.json
  initial:
    headline: ""
YAML
"$wrapper" validate --config "$cfgdir/local-post-form.yaml" >/dev/null || fail "post validate"
post_seed="$("$wrapper" run --config "$cfgdir/local-post-form.yaml")" || fail "post seed: $post_seed"
printf '%s\n' "$post_seed" | grep -q 'SEED_OK:' || fail "post seed token: $post_seed"
printf '<html><body><span class="headline">new</span></body></html>\n' >"$www/post.html"
post_hit="$("$wrapper" run --config "$cfgdir/local-post-form.yaml" --no-issue")" \
  || fail "post promote: $post_hit"
printf '%s\n' "$post_hit" | grep -q 'LLM_ESCALATION:' || fail "post missing escalation: $post_hit"
kill "$post_pid" 2>/dev/null || true
wait "$post_pid" 2>/dev/null || true

printf 'prompt-on-change-lifecycle.test.sh: PASS\n'
