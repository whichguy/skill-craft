#!/usr/bin/env bash
# Hermetic coverage for skills/skill-interop/scripts/marketplace-run.sh (Phase B).
# Cases M1–M8: stub CLIs only — no real marketplace network calls.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
mp="$root/skills/skill-interop/scripts/marketplace-run.sh"

fail() {
  printf 'marketplace-run.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$mp" ]] || fail "marketplace-run.sh not executable: $mp"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-marketplace.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

stub_bin="$tmpdir/bin"
mkdir -p "$stub_bin"
export STUB_LOG="$tmpdir/stub.log"
: >"$STUB_LOG"

# ---------------------------------------------------------------------------
# Stubs: log argv; emit fixture stdout by subcommand
# ---------------------------------------------------------------------------
write_stub() {
  local name="$1"
  cat >"$stub_bin/$name" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
# Log full argv for assertions
{
  printf '%s' "$(basename "$0")"
  for a in "$@"; do printf ' %s' "$a"; done
  printf '\n'
} >>"${STUB_LOG:?}"

host="$(basename "$0")"
# subcommand dispatch: plugin ...
if [[ "${1:-}" != "plugin" ]]; then
  printf '%s: unexpected top-level %s\n' "$host" "${1:-}" >&2
  exit 99
fi
shift
sub="${1:-}"
shift || true

case "$sub" in
  marketplace)
    action="${1:-}"
    shift || true
    case "$action" in
      list)
        case "$host" in
          claude)
            # Honor --json when the facade prefers it (else human list).
            if [[ "${1:-}" == "--json" ]] || [[ "$*" == *"--json"* ]]; then
              cat <<'EOF'
{
  "marketplaces": [
    {"name": "claude-plugins-official", "source": "GitHub (anthropics/claude-plugins-official)"},
    {"name": "fixture-mp-claude", "source": "GitHub (example/fixture-mp-claude)"}
  ]
}
EOF
            else
              cat <<'EOF'
Configured marketplaces:

  ❯ claude-plugins-official
    Source: GitHub (anthropics/claude-plugins-official)

  ❯ fixture-mp-claude
    Source: GitHub (example/fixture-mp-claude)
EOF
            fi
            ;;
          codex)
            cat <<'EOF'
MARKETPLACE             ROOT
openai-bundled          /tmp/fixture/openai-bundled
fixture-mp-codex        /tmp/fixture/fixture-mp-codex
EOF
            ;;
          grok)
            cat <<'EOF'
  xAI Official: https://github.com/xai-org/plugin-marketplace.git
  fixture-mp-grok: https://github.com/example/fixture-mp-grok.git
EOF
            ;;
        esac
        exit 0
        ;;
      add|update|upgrade|remove)
        printf 'stub: marketplace %s ok\n' "$action"
        exit 0
        ;;
      *)
        printf 'stub: unknown marketplace action %s\n' "$action" >&2
        exit 2
        ;;
    esac
    ;;
  list)
    case "$host" in
      claude)
        if [[ "${1:-}" == "--json" ]] || [[ "$*" == *"--json"* ]]; then
          cat <<'EOF'
{
  "installed": [
    {
      "pluginId": "code-review@claude-plugins-official",
      "name": "code-review",
      "marketplaceName": "claude-plugins-official",
      "version": "1.0.0",
      "installed": true,
      "enabled": true
    },
    {
      "pluginId": "fixture-plug@fixture-mp-claude",
      "name": "fixture-plug",
      "marketplaceName": "fixture-mp-claude",
      "version": "0.1.0",
      "installed": true,
      "enabled": true
    }
  ]
}
EOF
        else
          cat <<'EOF'
Installed plugins:

  ❯ code-review@claude-plugins-official
    Version: 1.0.0
    Scope: user
    Status: ✔ enabled

  ❯ fixture-plug@fixture-mp-claude
    Version: 0.1.0
    Scope: user
    Status: ✔ enabled
EOF
        fi
        ;;
      codex)
        # honor --json
        cat <<'EOF'
{
  "installed": [
    {
      "pluginId": "documents@openai-primary-runtime",
      "name": "documents",
      "marketplaceName": "openai-primary-runtime",
      "version": "1.2.3",
      "installed": true,
      "enabled": true
    },
    {
      "pluginId": "fixture-plug@fixture-mp-codex",
      "name": "fixture-plug",
      "marketplaceName": "fixture-mp-codex",
      "version": "0.0.1",
      "installed": true,
      "enabled": true
    }
  ],
  "available": []
}
EOF
        ;;
      grok)
        if [[ "${1:-}" == "--json" ]] || [[ "$*" == *"--json"* ]]; then
          cat <<'EOF'
{"installed":[{"name":"fixture-plug","id":"fixture-plug","marketplace":"fixture-mp-grok","version":"9.9.9","enabled":true}]}
EOF
        else
          cat <<'EOF'
fixture-plug@fixture-mp-grok
EOF
        fi
        ;;
    esac
    exit 0
    ;;
  install|add)
    # real install path (not dry-run)
    printf 'stub: installed %s\n' "${1:-}"
    exit 0
    ;;
  uninstall|remove|update)
    printf 'stub: %s ok\n' "$sub"
    exit 0
    ;;
  *)
    printf 'stub: unknown plugin sub %s\n' "$sub" >&2
    exit 2
    ;;
esac
STUB
  chmod +x "$stub_bin/$name"
}

write_stub claude
write_stub codex
write_stub grok

export PATH="$stub_bin:$PATH"
# Clear env overrides so stubs win via PATH (unless a case sets them)
unset CLAUDE_BIN CODEX_BIN GROK_BIN || true

run_mp() {
  bash "$mp" "$@"
}

# ---------------------------------------------------------------------------
# M1: all stubs → hosts --json shows three available
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
out="$(run_mp hosts --json)" || fail "M1 hosts failed: $out"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
hosts=d.get("hosts") or d
if isinstance(hosts, dict):
    hosts=list(hosts.values())
by={h["host"]:h for h in hosts}
for name in ("claude","grok","codex"):
    assert name in by, name
    assert by[name]["status"]=="available", (name, by[name])
print("M1 ok")
' || fail "M1 JSON shape: $out"

# ---------------------------------------------------------------------------
# M2: PATH without codex stub → codex unavailable, others available
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
# Put only claude+grok on PATH; point CODEX_BIN at missing path
m2_bin="$tmpdir/bin-m2"
mkdir -p "$m2_bin"
cp "$stub_bin/claude" "$stub_bin/grok" "$m2_bin/"
out="$(
  PATH="$m2_bin:/usr/bin:/bin" \
  CLAUDE_BIN="$m2_bin/claude" \
  GROK_BIN="$m2_bin/grok" \
  CODEX_BIN="$tmpdir/missing-codex" \
  bash "$mp" hosts --json
)" || fail "M2 hosts failed: $out"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
by={h["host"]:h for h in d["hosts"]}
assert by["claude"]["status"]=="available"
assert by["grok"]["status"]=="available"
assert by["codex"]["status"]=="unavailable", by["codex"]
print("M2 ok")
' || fail "M2: $out"

# ---------------------------------------------------------------------------
# M3: marketplaces list --json → at least one entry per available host
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
export PATH="$stub_bin:$PATH"
unset CLAUDE_BIN CODEX_BIN GROK_BIN || true
out="$(run_mp marketplaces list --json)" || fail "M3 failed: $out"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
items=d.get("marketplaces") or []
hosts=set()
for it in items:
    if it.get("name"):
        hosts.add(it["host"])
for h in ("claude","grok","codex"):
    assert h in hosts, (h, items)
print("M3 ok")
' || fail "M3: $out"

# ---------------------------------------------------------------------------
# M4: plugins list --json → normalized plugins from stubs
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
out="$(run_mp plugins list --json)" || fail "M4 failed: $out"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
items=d.get("plugins") or []
assert items, "empty plugins"
for p in items:
    assert p.get("kind")=="plugin", p
    assert p.get("host") in ("claude","grok","codex"), p
    assert p.get("id") or p.get("name"), p
# expect at least one claude + one codex plugin from fixtures
hosts=set(p["host"] for p in items)
assert "claude" in hosts and "codex" in hosts, hosts
print("M4 ok")
' || fail "M4: $out"

# ---------------------------------------------------------------------------
# M5: --host claude → stub log has only claude (no grok/codex)
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
out="$(run_mp plugins list --json --host claude)" || fail "M5 failed: $out"
if grep -E '^(grok|codex) ' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M5 stub log has non-claude lines: $(cat "$STUB_LOG")"
fi
grep -q '^claude ' "$STUB_LOG" || fail "M5 expected claude invocations in log"
echo "$out" | python3 -c '
import json,sys
d=json.load(sys.stdin)
for p in d.get("plugins") or []:
    assert p["host"]=="claude", p
print("M5 ok")
' || fail "M5: $out"

# ---------------------------------------------------------------------------
# M6: plugins install dry-run → would-run; stub NOT called for install
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
out="$(run_mp plugins install x@y --dry-run --host claude 2>&1)" || fail "M6 failed: $out"
printf '%s\n' "$out" | grep -qi 'would-run' || fail "M6 missing would-run: $out"
if grep -E 'plugin install|plugin add' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M6 dry-run must not invoke install on stub: $(cat "$STUB_LOG")"
fi
# stub log should be empty (no call at all preferred)
if [[ -s "$STUB_LOG" ]]; then
  # allow only non-install noise; fail if install/add present (already checked)
  :
fi
printf 'M6 ok\n'

# ---------------------------------------------------------------------------
# M7: plugins install code-review@… --host claude (not dry-run) → stub log
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
out="$(run_mp plugins install code-review@claude-plugins-official --host claude 2>&1)" || fail "M7 failed: $out"
grep -q 'claude plugin install code-review@claude-plugins-official' "$STUB_LOG" \
  || fail "M7 stub log missing install line: $(cat "$STUB_LOG")"
printf 'M7 ok\n'

# ---------------------------------------------------------------------------
# M8: plugins install bare-name --host codex → non-zero
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
set +e
out="$(run_mp plugins install bare-name --host codex 2>&1)"
ec=$?
set -e
[[ "$ec" -ne 0 ]] || fail "M8 expected non-zero for codex bare name, got 0: $out"
printf '%s\n' "$out" | grep -qiE 'name@marketplace|@' \
  || fail "M8 should mention name@marketplace requirement: $out"
# should not have called codex plugin add
if grep -E 'codex plugin add' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M8 must not call codex plugin add for bare name: $(cat "$STUB_LOG")"
fi
printf 'M8 ok\n'

# ---------------------------------------------------------------------------
# M9: plugins install Claude-style id --host grok → exit 4; no grok install call
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
set +e
out="$(run_mp plugins install code-review@claude-plugins-official --host grok 2>&1)"
ec=$?
set -e
[[ "$ec" -eq 4 ]] || fail "M9 expected exit 4 for grok Claude-style id, got $ec: $out"
printf '%s\n' "$out" | grep -qiE 'git URL|GitHub|local path|git ref' \
  || fail "M9 should explain Grok accepts git/path only: $out"
if grep -E 'grok plugin install code-review@' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M9 stub log must NOT contain grok plugin install code-review@…: $(cat "$STUB_LOG")"
fi
if grep -E 'plugin install' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M9 must not invoke install at all: $(cat "$STUB_LOG")"
fi
printf 'M9 ok\n'

# ---------------------------------------------------------------------------
# M10: dry-run Claude-style id --host grok → also no install call (precondition)
# ---------------------------------------------------------------------------
: >"$STUB_LOG"
set +e
out="$(run_mp plugins install code-review@claude-plugins-official --host grok --dry-run 2>&1)"
ec=$?
set -e
[[ "$ec" -eq 4 ]] || fail "M10 expected exit 4 on dry-run precondition, got $ec: $out"
if grep -E 'plugin install|would-run' "$STUB_LOG" >/dev/null 2>&1; then
  fail "M10 dry-run must not call install: $(cat "$STUB_LOG")"
fi
# would-run should not appear either (rejected before CLI)
if printf '%s\n' "$out" | grep -qi 'would-run'; then
  fail "M10 dry-run should not print would-run for rejected id: $out"
fi
printf 'M10 ok\n'

# ---------------------------------------------------------------------------
# M11: marketplace-run from relocated tree finds install.sh via walk-up
# ---------------------------------------------------------------------------
reloc="$tmpdir/reloc-root"
mkdir -p "$reloc/skills/skill-interop/scripts"
printf '#!/usr/bin/env bash\necho "dummy-install $*"\n' >"$reloc/install.sh"
chmod +x "$reloc/install.sh"
cp "$mp" "$reloc/skills/skill-interop/scripts/marketplace-run.sh"
chmod +x "$reloc/skills/skill-interop/scripts/marketplace-run.sh"
# Global flag parse only knows marketplace-run flags; pass skill args after -- if needed.
# Walk-up is exercised by install-local resolving reloc/install.sh (no MARKETPLACE_INSTALL_SH).
out="$(bash "$reloc/skills/skill-interop/scripts/marketplace-run.sh" install-local --dry-run 2>&1)" \
  || fail "M11 install-local dry-run from relocated tree failed: $out"
# macOS may resolve /var → /private/var; match on leaf path under reloc-root.
printf '%s\n' "$out" | grep -qE 'reloc-root/install\.sh' \
  || fail "M11 should resolve install.sh under relocated root: $out"
printf '%s\n' "$out" | grep -qi 'would-run' || fail "M11 missing would-run: $out"
# Must not still point at the real skill-craft repo install.sh
if printf '%s\n' "$out" | grep -qF "$root/install.sh"; then
  fail "M11 walk-up must not use repo root install.sh: $out"
fi
# Allowed git-style install for grok still works (not Claude-style)
: >"$STUB_LOG"
out="$(run_mp plugins install example/fixture-plugin --host grok 2>&1)" \
  || fail "M11b grok git shorthand install failed: $out"
grep -q 'grok plugin install example/fixture-plugin' "$STUB_LOG" \
  || fail "M11b expected grok install of user/repo: $(cat "$STUB_LOG")"
printf 'M11 ok\n'

printf 'marketplace-run.test.sh: PASS M1–M11\n'
exit 0
