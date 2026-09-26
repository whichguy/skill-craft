#!/usr/bin/env bash
# The one plugins/skill-craft bundle must be a real tree (not symlinks)
# matching skills/ SoT. The generator's CLI and sync-plugin-views.sh take no
# per-leaf argument any more: every check and sync operates on the whole
# bundle.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

# The cases below intentionally corrupt views and source fixtures. Re-run the
# same test in a disposable copy when invoked from a real checkout so no
# compatibility test can alter a collaborator's active tree.
if [[ "${SKILL_CRAFT_SYNC_FIXTURE:-}" != "1" ]]; then
  fixture_tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-sync-test.XXXXXX")"
  fixture_root="$fixture_tmp/repo"
  cleanup_fixture() { rm -rf "$fixture_tmp"; }
  trap cleanup_fixture EXIT
  mkdir -p "$fixture_root"
  (cd "$root" && tar \
    --exclude='.git' \
    --exclude='.claude/worktrees' \
    --exclude='.ruff_cache' \
    --exclude='node_modules' \
    --exclude='.results' \
    --exclude='results' \
    --exclude='tasks' \
    --exclude='dist' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -cf - .) | (cd "$fixture_root" && tar -xf -)
  set +e
  SKILL_CRAFT_SYNC_FIXTURE=1 bash "$fixture_root/test/sync-plugin-views.test.sh"
  fixture_rc=$?
  set -e
  exit "$fixture_rc"
fi

cd "$root"

PLUGIN="skill-craft"
BASE="plugins/$PLUGIN"

fail() {
  printf 'sync-plugin-views.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x scripts/sync-plugin-views.sh ]] || fail "scripts/sync-plugin-views.sh not executable"
# plugins/ is release output; rebuild this fixture's views from source first.
bash scripts/sync-plugin-views.sh >/dev/null || fail "baseline sync"

# An unknown argument (a leaf name) is refused; every skill ships in the one
# bundle, so there is no per-leaf sync any more.
set +e
out_leafarg="$(bash scripts/sync-plugin-views.sh --check shiploop 2>&1)"
rc_leafarg=$?
set -e
[[ "$rc_leafarg" -eq 64 ]] || fail "a leaf argument should be refused with exit 64: rc=$rc_leafarg out=$out_leafarg"
printf '%s\n' "$out_leafarg" | grep -Fq 'unknown argument shiploop' || fail "leaf-argument refusal message missing: $out_leafarg"

# Bytecode anywhere under a bundled skill is not plugin-view drift (.gitignore
# already ignores it).
pyc_pin="skills/shiploop/scripts/__pycache__"
cleanup_pyc_pin() { rm -rf "$pyc_pin"; }
trap cleanup_pyc_pin EXIT
mkdir -p "$pyc_pin"
printf 'x' >"$pyc_pin/pin.pyc"
set +e
out_pyc="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_pyc=$?
set -e
cleanup_pyc_pin
trap - EXIT
[[ "$rc_pyc" -eq 0 ]] || fail "__pycache__ should not fail --check: $out_pyc"

# Check mode must pass after regenerating
bash scripts/sync-plugin-views.sh --check || fail "plugin view out of sync or still symlinked"

# No symlinks under the bundle's skills or agents
if find "$BASE" -type l 2>/dev/null | grep -q .; then
  fail "symlinks under $BASE (Claude git-subdir cannot follow them): $(find "$BASE" -type l | tr '\n' ' ')"
fi

# skill-interop SKILL.md present in the bundle
[[ -f "$BASE/skills/skill-interop/SKILL.md" ]] || fail "missing materialised SKILL.md"
[[ -f "$BASE/agents/skill-interop.md" ]] || fail "missing materialised agent card"
[[ -f "$BASE/.claude-plugin/plugin.json" ]] || fail "missing plugin.json"

# plugin.json is derived from every bundled SKILL.md (version/description/license)
node scripts/skill-frontmatter-to-plugin-json.js --package --check \
  || fail "bundle plugin.json not derived from frontmatter"

# Default enumeration is skills/ — every skill leaf must be materialized into
# the bundle after sync, under the one set of package-root artifacts.
[[ -f LICENSE ]] || fail "source root LICENSE missing"
[[ -f "$BASE/LICENSE" ]] || fail "missing package-root LICENSE"
cmp -s LICENSE "$BASE/LICENSE" || fail "package-root LICENSE drift"
[[ -s "$BASE/README.md" ]] || fail "missing package-root README"
[[ -f "$BASE/.codex-plugin/plugin.json" ]] || fail "missing Codex manifest"
for d in skills/*/; do
  n="$(basename "$d")"
  [[ -f "skills/$n/SKILL.md" ]] || continue
  [[ -f "$BASE/skills/$n/SKILL.md" ]] || fail "missing materialized skill for skills/$n"
done

# --check fails on a stray plugins/<name> directory other than the one bundle
orphan="plugins/_zz-orphan-sync-test_"
mkdir -p "$orphan/.claude-plugin"
printf '%s\n' '{"name":"_zz-orphan-sync-test_","version":"0.0.0","description":"orphan"}' \
  >"$orphan/.claude-plugin/plugin.json"
set +e
out_orphan="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_orphan=$?
set -e
rm -rf "$orphan"
[[ "$rc_orphan" -ne 0 ]] || fail "stray plugin directory should fail --check: $out_orphan"
printf '%s\n' "$out_orphan" | grep -q 'is not generated' || fail "stray plugin message missing: $out_orphan"
# suite still clean after cleanup
bash scripts/sync-plugin-views.sh --check || fail "check failed after stray-plugin cleanup"

# --check fails when plugin.json drifts from SKILL.md frontmatter
pj="$BASE/.claude-plugin/plugin.json"
cp "$pj" "$pj.bak-sync-test"
python3 - <<PY
import json
p = "$pj"
d = json.load(open(p))
d["version"] = "9.9.9-drift"
json.dump(d, open(p, "w"), indent=2)
open(p, "a").write("\n")
PY
set +e
out_drift="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_drift=$?
set -e
mv "$pj.bak-sync-test" "$pj"
[[ "$rc_drift" -ne 0 ]] || fail "drifted plugin.json should fail --check: $out_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after drift restore"

# Package-root distribution artifacts are generated as part of the same
# contract. A changed license must fail closed rather than silently
# publishing a package whose root no longer carries the source license.
license_path="$BASE/LICENSE"
cp "$license_path" "$license_path.bak-sync-test"
printf 'license drift fixture\n' >"$license_path"
set +e
out_license_drift="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_license_drift=$?
set -e
mv "$license_path.bak-sync-test" "$license_path"
[[ "$rc_license_drift" -ne 0 ]] || fail "drifted package LICENSE should fail --check: $out_license_drift"
printf '%s\n' "$out_license_drift" | grep -Fq 'LICENSE' \
  || fail "package LICENSE drift message missing: $out_license_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after license drift restore"

readme_path="$BASE/README.md"
cp "$readme_path" "$readme_path.bak-sync-test"
printf '# stale package README\n' >"$readme_path"
set +e
out_readme_drift="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_readme_drift=$?
set -e
mv "$readme_path.bak-sync-test" "$readme_path"
[[ "$rc_readme_drift" -ne 0 ]] || fail "drifted package README should fail --check: $out_readme_drift"
printf '%s\n' "$out_readme_drift" | grep -Fq 'README' \
  || fail "package README drift message missing: $out_readme_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after README drift restore"

# base checks ok; continue to SA8 sample-leaf cases

pass_sync() { printf '  ok %s\n' "$*"; }

# --- Internal symlink deref + escape refuse (SA8 sample leaf) ---
sample="_zz-sync-symlink-sample_"
cleanup_sample() {
  rm -rf "skills/$sample" "$BASE/skills/$sample"
}
trap 'cleanup_sample' EXIT

cleanup_sample
mkdir -p "skills/$sample/nested"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
printf 'target-body\n' >"skills/$sample/nested/real.txt"
ln -s "nested/real.txt" "skills/$sample/alias.txt"

# Internal link: sync succeeds and dereferences
bash scripts/sync-plugin-views.sh || fail "internal symlink sync failed"
[[ -f "$BASE/skills/$sample/alias.txt" ]] || fail "alias missing in view"
[[ ! -L "$BASE/skills/$sample/alias.txt" ]] || fail "alias still symlink in view"
[[ "$(cat "$BASE/skills/$sample/alias.txt")" == "target-body" ]] || fail "alias content"
[[ -f "$BASE/.codex-plugin/plugin.json" ]] || fail "bundle Codex manifest missing"
[[ -s "$BASE/README.md" ]] || fail "bundle package README missing"
cmp -s LICENSE "$BASE/LICENSE" || fail "bundle package LICENSE mismatch"
# residual no symlinks under the new skill's materialized tree
if find "$BASE/skills/$sample" -type l 2>/dev/null | grep -q .; then
  fail "residual symlink in plugin view after internal deref"
fi
pass_sync "internal symlink dereferenced"

# .DS_Store below the skill root is noise in the source and in the view: it
# never fails --check and a sync never copies it.
printf 'finder' >"skills/$sample/nested/.DS_Store"
printf 'finder' >"$BASE/skills/$sample/nested/.DS_Store"
bash scripts/sync-plugin-views.sh --check >/dev/null \
  || fail "nested .DS_Store must not fail --check"
bash scripts/sync-plugin-views.sh >/dev/null || fail "sync with nested .DS_Store"
[[ -z "$(find "$BASE/skills/$sample" -name .DS_Store)" ]] || fail "sync copied .DS_Store into the view"
rm -f "skills/$sample/nested/.DS_Store"
pass_sync "nested .DS_Store ignored"

# Escaping symlink: refuse, no partial plugin view materialization of the escape
cleanup_sample
mkdir -p "skills/$sample"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
ln -s "/etc/passwd" "skills/$sample/escape.txt"
rm -rf "$BASE/skills/$sample"
set +e
out_esc="$(bash scripts/sync-plugin-views.sh 2>&1)"
rc_esc=$?
set -e
[[ "$rc_esc" -ne 0 ]] || fail "escape symlink should fail sync: $out_esc"
printf '%s\n' "$out_esc" | grep -qi 'escape\|escapes' || fail "escape message missing: $out_esc"
# no partial write of the skill tree with the escape file as symlink
if [[ -e "$BASE/skills/$sample/escape.txt" ]]; then
  fail "partial write left escape in plugin view"
fi
cleanup_sample
# Restore trap only cleanup
trap - EXIT
cleanup_sample
bash scripts/sync-plugin-views.sh >/dev/null || fail "restore sync after escape refusal"


# --- B1 dest-symlink tripwire (must not follow/delete through symlinked dest entry) ---
sample_b1="_zz-sync-dest-symlink_"
cleanup_b1() { rm -rf "skills/$sample_b1" "$BASE/skills/$sample_b1" "$root/.tmp-b1-home"; }
trap 'cleanup_sample; cleanup_b1' EXIT
cleanup_b1
mkdir -p "skills/$sample_b1"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample_b1" >"skills/$sample_b1/SKILL.md"
printf 'safe-body\n' >"skills/$sample_b1/body.txt"
# Pre-create the bundle's skill tree with a symlinked path pointing outside (home fixture)
mkdir -p "$BASE/skills/$sample_b1" "$root/.tmp-b1-home"
printf 'DO-NOT-DELETE\n' >"$root/.tmp-b1-home/protected.txt"
# place symlink as child of dest skill tree
ln -s "$root/.tmp-b1-home" "$BASE/skills/$sample_b1/outside-link"
# log rsync implementation
if command -v rsync >/dev/null 2>&1; then
  rsync --version 2>&1 | head -1 || true
fi
# Sync must succeed (overwrite tree via rm -rf dest then copy) OR fail closed — either way protected must remain
set +e
out_b1="$(bash scripts/sync-plugin-views.sh 2>&1)"
rc_b1=$?
set -e
[[ -f "$root/.tmp-b1-home/protected.txt" ]] || fail "B1 protected target deleted via symlink (rc=$rc_b1 out=$out_b1)"
[[ "$(cat "$root/.tmp-b1-home/protected.txt")" == "DO-NOT-DELETE" ]] || fail "B1 protected content changed"
# After successful sync, outside-link should not remain as a live escape into home
if [[ "$rc_b1" -eq 0 ]]; then
  if [[ -L "$BASE/skills/$sample_b1/outside-link" ]]; then
    fail "B1 residual outside-link symlink after sync"
  fi
fi
pass_sync "dest-symlink tripwire (protected intact; rsync logged)"
cleanup_b1

# --- Exact bundle view: the view holds only what generation produces ---
expect_fail() {
  local label="$1" needle="$2"
  shift 2
  local out rc
  set +e
  out="$("$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -ne 0 ]] || fail "$label should fail: $out"
  printf '%s\n' "$out" | grep -Fq -- "$needle" || fail "$label did not report '$needle': $out"
}

# Backchain and Plan Dispatcher are both bundled skills in the one plugin.
[[ -d "$BASE/skills/backchain" ]] || fail "$BASE/skills/backchain missing"
[[ -d "$BASE/skills/plan-dispatcher" ]] || fail "$BASE/skills/plan-dispatcher missing"
[[ "$(ls "$BASE/agents")" == $'backchain.md\nshiploop.md\nskill-interop.md' ]] \
  || fail "$BASE/agents is not exactly the three carded skills"

mkdir -p "$BASE/skills/stale-skill"
printf 'stale\n' > "$BASE/skills/stale-skill/SKILL.md"
expect_fail "stale skill in the bundle view" "$BASE/skills/stale-skill is not generated from skills/" \
  bash scripts/sync-plugin-views.sh --check
printf 'stale\n' > "$BASE/agents/stale.md"
expect_fail "stale agent card in the bundle view" "$BASE/agents/stale.md is not generated" \
  bash scripts/sync-plugin-views.sh --check
printf 'stray\n' > "$BASE/notes.md"
expect_fail "stray top-level entry in the bundle view" "$BASE/notes.md is not generated" \
  bash scripts/sync-plugin-views.sh --check
bash scripts/sync-plugin-views.sh >/dev/null || fail "sync over stale bundle entries"
[[ ! -e "$BASE/skills/stale-skill" && ! -e "$BASE/agents/stale.md" \
   && ! -e "$BASE/notes.md" ]] || fail "sync must remove stale bundle entries"
[[ -f "$BASE/agents/skill-interop.md" ]] || fail "sync removed a generated agent card"

# Local noise is not a stale entry.
printf 'finder' > "$BASE/.DS_Store"
printf 'finder' > "$BASE/skills/.DS_Store"
bash scripts/sync-plugin-views.sh --check >/dev/null || fail ".DS_Store must not fail the exact-view check"
rm -f "$BASE/.DS_Store" "$BASE/skills/.DS_Store"
bash scripts/sync-plugin-views.sh --check >/dev/null || fail "check after exact-view repairs"
pass_sync "the bundle view is exact; stale entries reported and removed"

# Host hooks: generated only from skills/<leaf>/host-hooks.json across the
# whole bundle, merged into one file per host, each command running its own
# skill's script through that host's root variable.
hooks_json() { python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), sort_keys=True))' "$1"; }
[[ "$(ls "$BASE/hooks")" == $'codex.json\ncursor.json\nhooks.json' ]] \
  || fail "$BASE/hooks is not exactly the three generated host files"
[[ "$(hooks_json "$BASE/hooks/hooks.json")" == '{"hooks": {"PostToolUse": [{"hooks": [{"command": "${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-status-hook", "timeout": 10, "type": "command"}, {"command": "${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-keepalive-observe", "timeout": 30, "type": "command"}], "matcher": "Bash"}], "Stop": [{"hooks": [{"command": "${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-keepalive-stop", "timeout": 30, "type": "command"}]}]}}' ]] \
  || fail "Claude/Grok hook file content"
[[ "$(hooks_json "$BASE/hooks/codex.json")" == '{"hooks": {"PostToolUse": [{"hooks": [{"command": "$PLUGIN_ROOT/skills/shiploop/scripts/shiploop-status-hook", "timeout": 10, "type": "command"}, {"command": "$PLUGIN_ROOT/skills/shiploop/scripts/shiploop-keepalive-observe", "timeout": 30, "type": "command"}], "matcher": "Bash"}], "Stop": [{"hooks": [{"command": "$PLUGIN_ROOT/skills/shiploop/scripts/shiploop-keepalive-stop", "timeout": 30, "type": "command"}]}]}}' ]] \
  || fail "Codex hook file content"
[[ "$(hooks_json "$BASE/hooks/cursor.json")" == '{"hooks": {"afterShellExecution": [{"command": "${CURSOR_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-status-hook", "timeout": 10}, {"command": "${CURSOR_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-keepalive-observe", "timeout": 30}], "stop": [{"command": "${CURSOR_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-keepalive-stop", "loop_limit": 50, "timeout": 30}]}, "version": 1}' ]] \
  || fail "Cursor hook file content"
grep -q '"hooks": "./hooks/codex.json"' "$BASE/.codex-plugin/plugin.json" || fail "Codex manifest hooks field"
grep -q '"hooks": "./hooks/cursor.json"' "$BASE/.cursor-plugin/plugin.json" || fail "Cursor manifest hooks field"
! grep -q '"hooks"' "$BASE/.claude-plugin/plugin.json" || fail "Claude manifest must use the default hooks path"
python3 scripts/check-marketplace-packages.py "$BASE" >/dev/null || fail "package check of generated hooks"

# When no skill declares hooks, the bundle may not carry hooks/ at all.
mv skills/shiploop/host-hooks.json skills/shiploop/host-hooks.json.bak-sync-test
mkdir -p "$BASE/hooks" && printf '{}\n' > "$BASE/hooks/hooks.json"
expect_fail "hooks/ with no declaring skill" "$BASE/hooks is not generated" \
  bash scripts/sync-plugin-views.sh --check
bash scripts/sync-plugin-views.sh >/dev/null || fail "sync over undeclared hooks/"
[[ ! -e "$BASE/hooks" ]] || fail "sync must remove undeclared hooks/"
mv skills/shiploop/host-hooks.json.bak-sync-test skills/shiploop/host-hooks.json
bash scripts/sync-plugin-views.sh >/dev/null || fail "restore shiploop's hooks declaration"

# check-marketplace-packages.py rejects a hook file that declares no commands.
cp "$BASE/hooks/hooks.json" "$BASE/hooks/hooks.json.bak-sync-test"
printf '{}\n' > "$BASE/hooks/hooks.json"
expect_fail "package check of an empty hook file" "declares no hook commands" \
  python3 scripts/check-marketplace-packages.py "$BASE"
mv "$BASE/hooks/hooks.json.bak-sync-test" "$BASE/hooks/hooks.json"

# Edited or extra hook files are drift; a command outside scripts/ is refused.
printf 'extra\n' > "$BASE/hooks/extra.json"
expect_fail "extra hook file" "hooks/ holds" bash scripts/sync-plugin-views.sh --check
rm "$BASE/hooks/extra.json"
sed -i.bak 's|/scripts/shiploop-status-hook|/scripts/../SKILL.md|' "$BASE/hooks/codex.json" && rm "$BASE/hooks/codex.json.bak"
expect_fail "edited hook file" "hooks/codex.json out of sync" bash scripts/sync-plugin-views.sh --check
expect_fail "package check of a command outside scripts/" "command must run an executable" \
  python3 scripts/check-marketplace-packages.py "$BASE"
bash scripts/sync-plugin-views.sh >/dev/null || fail "sync over edited hooks"

# The declaration itself is validated before anything is generated.
decl=skills/shiploop/host-hooks.json
cp "$decl" "$decl.orig"
sed 's|scripts/shiploop-status-hook|../SKILL.md|' "$decl.orig" > "$decl"
expect_fail "declaration outside scripts/" "script must be scripts/<file>" bash scripts/sync-plugin-views.sh --check
sed 's|scripts/shiploop-status-hook|scripts/shiploop_status_hook.py|' "$decl.orig" > "$decl"
expect_fail "non-executable declared script" "must be an executable regular file" bash scripts/sync-plugin-views.sh --check
sed 's|"grok"|"opencode"|' "$decl.orig" > "$decl"
expect_fail "unknown host" "hosts must be distinct values" bash scripts/sync-plugin-views.sh --check
mv "$decl.orig" "$decl"
bash scripts/sync-plugin-views.sh --check >/dev/null || fail "check after restoring the declaration"
pass_sync "host hooks are generated per host from host-hooks.json and nowhere else"

printf 'sync-plugin-views.test.sh: PASS (incl. internal deref + escape refuse + B1 + exact views + host hooks)\n'
exit 0
