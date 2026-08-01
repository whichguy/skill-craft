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

# Without setup/deps, control should fail closed with exit 2 (or help path)
set +e
out="$("$cli" status 2>&1)"
rc=$?
set -e
# Either missing deps (2) or missing LENNOX_IP after deps (1/SystemExit) — both fail-closed
if [[ "$rc" -eq 0 ]]; then
  fail "status without LENNOX_IP must not succeed"
fi
pass "status fails closed without config (rc=$rc)"

# Python module syntax without writing __pycache__ into skills/
python3 -c 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())' "$py" || fail "python parse"
rm -rf "$(dirname "$py")/__pycache__"
pass "python syntax"

# Plugin view presence after sync (advisory if not synced yet)
if [[ -f "$root/plugins/lennox-s40/.claude-plugin/plugin.json" ]]; then
  grep -q '"name": "lennox-s40"' "$root/plugins/lennox-s40/.claude-plugin/plugin.json" || fail "plugin.json name"
  pass "plugin view present"
else
  printf '  skip plugin view (run scripts/sync-plugin-views.sh)\n'
fi

printf 'lennox-s40.test.sh: PASS\n'
