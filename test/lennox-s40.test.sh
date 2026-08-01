#!/usr/bin/env bash
# Hermetic checks for skills/lennox-s40 (no live thermostat required).
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
skill="$root/skills/lennox-s40"
cli="$skill/scripts/lennox-s40"
py="$skill/scripts/lennox_s40.py"

fail() { printf 'lennox-s40.test.sh: FAIL %s\n' "$*" >&2; exit 1; }
pass() { printf '  ok %s\n' "$*"; }

[[ -f "$skill/SKILL.md" ]] || fail "missing SKILL.md"
[[ -x "$cli" || -f "$cli" ]] || fail "missing scripts/lennox-s40"
[[ -f "$py" ]] || fail "missing lennox_s40.py"
[[ -f "$skill/requirements.txt" ]] || fail "missing requirements.txt"
[[ -f "$skill/references/host-matrix.md" ]] || fail "missing host-matrix"
[[ -f "$skill/references/setup.md" ]] || fail "missing setup.md"

grep -q '^name: lennox-s40$' "$skill/SKILL.md" || fail "frontmatter name"
grep -q 'kind: script-backed' "$skill/SKILL.md" || fail "kind script-backed"
grep -q 'lennoxs30api' "$skill/requirements.txt" || fail "requirements package"
# No personal LAN defaults baked into SoT
if grep -ERq '192\.168\.1\.148|BT23M53278|Sagewood' "$skill"; then
  fail "personal home identifiers must not ship in skill SoT"
fi
pass "package shape + no personal identifiers"

chmod +x "$cli" 2>/dev/null || true
"$cli" --help >/dev/null || fail "--help"
pass "cli --help"

# Config helpers work without thermostat (isolated path — never touch real home config)
tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT
export LENNOX_CONFIG="$tmpdir/config.json"
unset LENNOX_IP LENNOX_APP_ID || true

cfg_path="$("$cli" config path)"
[[ "$cfg_path" == "$LENNOX_CONFIG" ]] || fail "config path want $LENNOX_CONFIG got $cfg_path"
pass "config path ($cfg_path)"

# config show with empty / missing file is non-fatal
show_out="$("$cli" config show 2>&1)" || fail "config show empty: $show_out"
pass "config show (empty)"

# Seed a fake running config and verify show/clear hermetically
printf '%s\n' '{"version":1,"ip":"203.0.113.50","host":"Lennox-S40-TEST.local"}' >"$LENNOX_CONFIG"
chmod 600 "$LENNOX_CONFIG"
show_out="$("$cli" config show 2>&1)" || fail "config show seeded: $show_out"
printf '%s\n' "$show_out" | grep -q '203.0.113.50' || fail "config show missing ip: $show_out"
pass "config show (seeded)"

"$cli" config clear >/dev/null 2>&1 || fail "config clear"
[[ ! -e "$LENNOX_CONFIG" ]] || fail "config clear left file"
pass "config clear"

# SKILL.md documents running config (contract honesty)
grep -q 'config show' "$skill/SKILL.md" || fail "SKILL.md missing config CLI"
grep -q 'rediscover\|config' "$skill/SKILL.md" || fail "SKILL.md missing resolve/config narrative"
pass "SKILL.md config contract"

# No address + --no-rediscover must not mDNS/LAN-scan (hermetic; live unit may exist)
set +e
out="$(
  env -u LENNOX_IP -u LENNOX_APP_ID \
    LENNOX_CONFIG="$tmpdir/nope.json" \
    LENNOX_NO_LAN_SCAN=1 \
    "$cli" --no-rediscover status 2>&1
)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  fail "status without address + --no-rediscover must not succeed (out=$out)"
fi
printf '%s\n' "$out" | grep -qi 'No thermostat address' || fail "expected no-address message: $out"
pass "status fails closed without address (rc=$rc)"

# Unreachable explicit IP + no rediscover must fail closed (hermetic; no live unit)
set +e
out="$(
  env -u LENNOX_IP -u LENNOX_APP_ID \
    LENNOX_CONFIG="$tmpdir/nope.json" \
    LENNOX_NO_LAN_SCAN=1 \
    "$cli" --ip 203.0.113.1 --no-rediscover --no-lan-scan status 2>&1
)"
rc=$?
set -e
if [[ "$rc" -eq 0 ]]; then
  fail "status with dead --ip --no-rediscover must not succeed (out=$out)"
fi
pass "status fails closed on dead IP without rediscover (rc=$rc)"

# Python module syntax without writing __pycache__ into skills/
python3 -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' "$py" || fail "python parse"
rm -rf "$(dirname "$py")/__pycache__"
pass "python syntax"

# Plugin view must track SoT (packaging contract)
plugin_py="$root/plugins/lennox-s40/skills/lennox-s40/scripts/lennox_s40.py"
if [[ -f "$root/plugins/lennox-s40/.claude-plugin/plugin.json" ]]; then
  grep -q '"name": "lennox-s40"' "$root/plugins/lennox-s40/.claude-plugin/plugin.json" || fail "plugin.json name"
  [[ -f "$plugin_py" ]] || fail "plugin missing lennox_s40.py"
  cmp -s "$py" "$plugin_py" || fail "plugin lennox_s40.py drifted from skills SoT (run sync-plugin-views.sh)"
  pass "plugin view present + SoT match"
else
  fail "plugin view missing (run scripts/sync-plugin-views.sh)"
fi

printf 'lennox-s40.test.sh: PASS\n'
