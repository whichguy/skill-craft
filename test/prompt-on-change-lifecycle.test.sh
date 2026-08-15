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
cleanup() {
  if [[ -n "$http_pid" ]] && kill -0 "$http_pid" 2>/dev/null; then
    kill "$http_pid" 2>/dev/null || true
    wait "$http_pid" 2>/dev/null || true
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

printf 'prompt-on-change-lifecycle.test.sh: PASS\n'
