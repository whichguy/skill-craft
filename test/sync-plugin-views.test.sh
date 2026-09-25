#!/usr/bin/env bash
# Plugin views must be real trees (not symlinks) matching skills/ SoT.
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

fail() {
  printf 'sync-plugin-views.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x scripts/sync-plugin-views.sh ]] || fail "scripts/sync-plugin-views.sh not executable"
# plugins/ is release output; rebuild this fixture's views from source first.
bash scripts/sync-plugin-views.sh >/dev/null || fail "baseline sync"

# Leaf-only bytecode is not plugin-view drift (.gitignore already ignores it).
pyc_pin="skills/shiploop/scripts/__pycache__"
cleanup_pyc_pin() { rm -rf "$pyc_pin"; }
trap cleanup_pyc_pin EXIT
mkdir -p "$pyc_pin"
printf 'x' >"$pyc_pin/pin.pyc"
set +e
out_pyc="$(bash scripts/sync-plugin-views.sh --check shiploop 2>&1)"
rc_pyc=$?
set -e
cleanup_pyc_pin
trap - EXIT
[[ "$rc_pyc" -eq 0 ]] || fail "leaf-only __pycache__ should not fail --check: $out_pyc"

# Check mode must pass after regenerating
bash scripts/sync-plugin-views.sh --check || fail "plugin views out of sync or still symlinked"

# No symlinks under any plugins/*/skills or plugins/*/agents
if find plugins -type l 2>/dev/null | grep -q .; then
  fail "symlinks under plugins/ (Claude git-subdir cannot follow them): $(find plugins -type l | tr '\n' ' ')"
fi

# skill-interop SKILL.md present in plugin view
[[ -f plugins/skill-interop/skills/skill-interop/SKILL.md ]] || fail "missing materialised SKILL.md"
[[ -f plugins/skill-interop/agents/skill-interop.md ]] || fail "missing materialised agent card"
[[ -f plugins/skill-interop/.claude-plugin/plugin.json ]] || fail "missing plugin.json"

# plugin.json is derived from SKILL.md SoT (version/description/license)
node scripts/skill-frontmatter-to-plugin-json.js skill-interop --check \
  || fail "skill-interop plugin.json not derived from frontmatter"
node scripts/skill-frontmatter-to-plugin-json.js c-plan --check \
  || fail "c-plan plugin.json not derived from frontmatter"

# Default enumeration is skills/ — every skill leaf must have a plugin view after sync
[[ -f LICENSE ]] || fail "source root LICENSE missing"
for d in skills/*/; do
  n="$(basename "$d")"
  [[ -f "skills/$n/SKILL.md" ]] || continue
  [[ -f "plugins/$n/.claude-plugin/plugin.json" ]] || fail "missing plugin view for skills/$n"
  [[ -f "plugins/$n/.codex-plugin/plugin.json" ]] || fail "missing Codex manifest for skills/$n"
  [[ -f "plugins/$n/LICENSE" ]] || fail "missing package-root LICENSE for skills/$n"
  cmp -s LICENSE "plugins/$n/LICENSE" \
    || fail "package-root LICENSE drift for skills/$n"
  [[ -s "plugins/$n/README.md" ]] || fail "missing package-root README for skills/$n"
done

# --check fails on orphan plugins/<leaf> with no skills/<leaf>
orphan="plugins/_zz-orphan-sync-test_"
mkdir -p "$orphan/.claude-plugin"
printf '%s\n' '{"name":"_zz-orphan-sync-test_","version":"0.0.0","description":"orphan"}' \
  >"$orphan/.claude-plugin/plugin.json"
set +e
out_orphan="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_orphan=$?
set -e
rm -rf "$orphan"
[[ "$rc_orphan" -ne 0 ]] || fail "orphan plugin view should fail --check: $out_orphan"
printf '%s\n' "$out_orphan" | grep -qi 'orphan' || fail "orphan message missing: $out_orphan"
# suite still clean after cleanup
bash scripts/sync-plugin-views.sh --check || fail "check failed after orphan cleanup"

# --check fails when plugin.json drifts from SKILL.md frontmatter
pj="plugins/c-plan/.claude-plugin/plugin.json"
cp "$pj" "$pj.bak-sync-test"
python3 - <<'PY'
import json
p="plugins/c-plan/.claude-plugin/plugin.json"
d=json.load(open(p))
d["version"]="9.9.9-drift"
json.dump(d, open(p,"w"), indent=2)
open(p,"a").write("\n")
PY
set +e
out_drift="$(bash scripts/sync-plugin-views.sh --check 2>&1)"
rc_drift=$?
set -e
mv "$pj.bak-sync-test" "$pj"
[[ "$rc_drift" -ne 0 ]] || fail "drifted plugin.json should fail --check: $out_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after drift restore"

# Package-root distribution artifacts are generated as part of the same leaf
# contract. A changed license must fail closed rather than silently publishing
# a package whose subdirectory no longer carries the source license.
license_path="plugins/c-plan/LICENSE"
cp "$license_path" "$license_path.bak-sync-test"
printf 'license drift fixture\n' >"$license_path"
set +e
out_license_drift="$(bash scripts/sync-plugin-views.sh --check c-plan 2>&1)"
rc_license_drift=$?
set -e
mv "$license_path.bak-sync-test" "$license_path"
[[ "$rc_license_drift" -ne 0 ]] || fail "drifted package LICENSE should fail --check: $out_license_drift"
printf '%s\n' "$out_license_drift" | grep -Fq 'LICENSE' \
  || fail "package LICENSE drift message missing: $out_license_drift"
bash scripts/sync-plugin-views.sh --check || fail "check failed after license drift restore"

readme_path="plugins/c-plan/README.md"
cp "$readme_path" "$readme_path.bak-sync-test"
printf '# stale package README\n' >"$readme_path"
set +e
out_readme_drift="$(bash scripts/sync-plugin-views.sh --check c-plan 2>&1)"
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
  rm -rf "skills/$sample" "plugins/$sample"
}
trap 'cleanup_sample' EXIT

cleanup_sample
mkdir -p "skills/$sample/nested"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
printf 'target-body\n' >"skills/$sample/nested/real.txt"
ln -s "nested/real.txt" "skills/$sample/alias.txt"

# Internal link: sync succeeds and dereferences
bash scripts/sync-plugin-views.sh "$sample" || fail "internal symlink sync failed"
[[ -f "plugins/$sample/skills/$sample/alias.txt" ]] || fail "alias missing in view"
[[ ! -L "plugins/$sample/skills/$sample/alias.txt" ]] || fail "alias still symlink in view"
[[ "$(cat "plugins/$sample/skills/$sample/alias.txt")" == "target-body" ]] || fail "alias content"
[[ -f "plugins/$sample/.codex-plugin/plugin.json" ]] || fail "sample Codex manifest missing"
[[ -s "plugins/$sample/README.md" ]] || fail "sample package README missing"
cmp -s LICENSE "plugins/$sample/LICENSE" || fail "sample package LICENSE mismatch"
# residual no symlinks under this plugin view
if find "plugins/$sample" -type l 2>/dev/null | grep -q .; then
  fail "residual symlink in plugin view after internal deref"
fi
pass_sync "internal symlink dereferenced"

# .DS_Store below the skill root is noise in the source and in the view: it
# never fails --check and a sync never copies it.
printf 'finder' >"skills/$sample/nested/.DS_Store"
printf 'finder' >"plugins/$sample/skills/$sample/nested/.DS_Store"
bash scripts/sync-plugin-views.sh --check "$sample" >/dev/null \
  || fail "nested .DS_Store must not fail a leaf --check"
bash scripts/sync-plugin-views.sh "$sample" >/dev/null || fail "leaf sync with nested .DS_Store"
[[ -z "$(find "plugins/$sample" -name .DS_Store)" ]] || fail "leaf sync copied .DS_Store into the view"
rm -f "skills/$sample/nested/.DS_Store"
pass_sync "nested .DS_Store ignored for a leaf"

# Escaping symlink: refuse, no partial plugin view materialization of the escape
cleanup_sample
mkdir -p "skills/$sample"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample" >"skills/$sample/SKILL.md"
ln -s "/etc/passwd" "skills/$sample/escape.txt"
# Capture pre-existing plugins path state
rm -rf "plugins/$sample"
set +e
out_esc="$(bash scripts/sync-plugin-views.sh "$sample" 2>&1)"
rc_esc=$?
set -e
[[ "$rc_esc" -ne 0 ]] || fail "escape symlink should fail sync: $out_esc"
printf '%s\n' "$out_esc" | grep -qi 'escape\|escapes' || fail "escape message missing: $out_esc"
# no partial write of the skill tree with the escape file as symlink
if [[ -e "plugins/$sample/skills/$sample/escape.txt" ]]; then
  fail "partial write left escape in plugin view"
fi
cleanup_sample
# Restore trap only cleanup
trap - EXIT
cleanup_sample


# --- B1 dest-symlink tripwire (must not follow/delete through symlinked dest entry) ---
sample_b1="_zz-sync-dest-symlink_"
cleanup_b1() { rm -rf "skills/$sample_b1" "plugins/$sample_b1" "$root/.tmp-b1-home"; }
trap 'cleanup_sample; cleanup_b1' EXIT
cleanup_b1
mkdir -p "skills/$sample_b1"
printf -- '---\nname: %s\ndescription: sample\nversion: 0.0.1\nlicense: MIT\nplatforms:\n  - macos\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# sample\n' "$sample_b1" >"skills/$sample_b1/SKILL.md"
printf 'safe-body\n' >"skills/$sample_b1/body.txt"
# Pre-create plugin view with a symlinked path pointing outside (home fixture)
mkdir -p "plugins/$sample_b1/skills/$sample_b1" "$root/.tmp-b1-home"
printf 'DO-NOT-DELETE\n' >"$root/.tmp-b1-home/protected.txt"
# place symlink as child of dest skill tree
ln -s "$root/.tmp-b1-home" "plugins/$sample_b1/skills/$sample_b1/outside-link"
# log rsync implementation
if command -v rsync >/dev/null 2>&1; then
  rsync --version 2>&1 | head -1 || true
fi
# Sync must succeed (overwrite tree via rm -rf dest then copy) OR fail closed — either way protected must remain
set +e
out_b1="$(bash scripts/sync-plugin-views.sh "$sample_b1" 2>&1)"
rc_b1=$?
set -e
[[ -f "$root/.tmp-b1-home/protected.txt" ]] || fail "B1 protected target deleted via symlink (rc=$rc_b1 out=$out_b1)"
[[ "$(cat "$root/.tmp-b1-home/protected.txt")" == "DO-NOT-DELETE" ]] || fail "B1 protected content changed"
# After successful sync, outside-link should not remain as a live escape into home
if [[ "$rc_b1" -eq 0 ]]; then
  if [[ -L "plugins/$sample_b1/skills/$sample_b1/outside-link" ]]; then
    fail "B1 residual outside-link symlink after sync"
  fi
fi
pass_sync "dest-symlink tripwire (protected intact; rsync logged)"
cleanup_b1

# --- Exact leaf views: a view holds only what its skills/<leaf> generates ---
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

# Backchain and Plan Dispatcher are separate leaf plugins. The baseline sync
# removed the plan-dispatcher skill that an older backchain view carried.
[[ "$(ls plugins/backchain/skills)" == "backchain" ]] || fail "plugins/backchain/skills is not exactly backchain"
[[ "$(ls plugins/backchain/agents)" == "backchain.md" ]] || fail "plugins/backchain/agents is not exactly backchain.md"
[[ "$(ls plugins/plan-dispatcher/skills)" == "plan-dispatcher" ]] \
  || fail "plugins/plan-dispatcher/skills is not exactly plan-dispatcher"
[[ ! -e plugins/plan-dispatcher/agents ]] || fail "plugins/plan-dispatcher has no agent card"

mkdir -p plugins/skill-interop/skills/stale-skill
printf 'stale\n' > plugins/skill-interop/skills/stale-skill/SKILL.md
expect_fail "stale skill in a leaf view" "plugins/skill-interop/skills/stale-skill is not generated from skills/skill-interop" \
  bash scripts/sync-plugin-views.sh --check skill-interop
printf 'stale\n' > plugins/skill-interop/agents/stale.md
expect_fail "stale agent card in a leaf view" "plugins/skill-interop/agents/stale.md is not generated" \
  bash scripts/sync-plugin-views.sh --check skill-interop
printf 'stray\n' > plugins/skill-interop/notes.md
expect_fail "stray top-level entry in a leaf view" "plugins/skill-interop/notes.md is not generated" \
  bash scripts/sync-plugin-views.sh --check skill-interop
bash scripts/sync-plugin-views.sh skill-interop >/dev/null || fail "sync over stale leaf entries"
[[ ! -e plugins/skill-interop/skills/stale-skill && ! -e plugins/skill-interop/agents/stale.md \
   && ! -e plugins/skill-interop/notes.md ]] || fail "sync must remove stale leaf entries"
[[ -f plugins/skill-interop/agents/skill-interop.md ]] || fail "sync removed the generated agent card"

# A leaf without an agent card has no agents/ in its view.
mkdir -p plugins/c-plan/agents
printf 'stale\n' > plugins/c-plan/agents/c-plan.md
expect_fail "agents/ in a leaf view without a card" "plugins/c-plan/agents is not generated" \
  bash scripts/sync-plugin-views.sh --check c-plan
bash scripts/sync-plugin-views.sh c-plan >/dev/null || fail "sync over stale agents/"
[[ ! -e plugins/c-plan/agents ]] || fail "sync must remove agents/ from a leaf without a card"

# Local noise is not a stale entry.
printf 'finder' > plugins/c-plan/.DS_Store
printf 'finder' > plugins/c-plan/skills/.DS_Store
bash scripts/sync-plugin-views.sh --check c-plan >/dev/null || fail ".DS_Store must not fail the exact-view check"
rm -f plugins/c-plan/.DS_Store plugins/c-plan/skills/.DS_Store
bash scripts/sync-plugin-views.sh --check >/dev/null || fail "check after exact-view repairs"
pass_sync "leaf views are exact; stale entries reported and removed"

# Host hooks: generated only from skills/<leaf>/host-hooks.json, one file per
# host, each running the skill's own script through that host's root variable.
hooks_json() { python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1])), sort_keys=True))' "$1"; }
[[ "$(ls plugins/shiploop/hooks)" == $'codex.json\ncursor.json\nhooks.json' ]] \
  || fail "plugins/shiploop/hooks is not exactly the three generated host files"
[[ "$(hooks_json plugins/shiploop/hooks/hooks.json)" == '{"hooks": {"PostToolUse": [{"hooks": [{"command": "\"${CLAUDE_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-status-hook\"", "timeout": 10, "type": "command"}], "matcher": "Bash"}]}}' ]] \
  || fail "Claude/Grok hook file content"
[[ "$(hooks_json plugins/shiploop/hooks/codex.json)" == '{"hooks": {"PostToolUse": [{"hooks": [{"command": "\"$PLUGIN_ROOT/skills/shiploop/scripts/shiploop-status-hook\"", "timeout": 10, "type": "command"}], "matcher": "Bash"}]}}' ]] \
  || fail "Codex hook file content"
[[ "$(hooks_json plugins/shiploop/hooks/cursor.json)" == '{"hooks": {"afterShellExecution": [{"command": "\"${CURSOR_PLUGIN_ROOT}/skills/shiploop/scripts/shiploop-status-hook\"", "timeout": 10}]}, "version": 1}' ]] \
  || fail "Cursor hook file content"
grep -q '"hooks": "./hooks/codex.json"' plugins/shiploop/.codex-plugin/plugin.json || fail "Codex manifest hooks field"
grep -q '"hooks": "./hooks/cursor.json"' plugins/shiploop/.cursor-plugin/plugin.json || fail "Cursor manifest hooks field"
! grep -q '"hooks"' plugins/shiploop/.claude-plugin/plugin.json || fail "Claude manifest must use the default hooks path"
! grep -q '"hooks"' plugins/c-plan/.codex-plugin/plugin.json || fail "a leaf without host-hooks.json declares hooks"
python3 scripts/check-marketplace-packages.py plugins/shiploop >/dev/null || fail "package check of generated hooks"

# A leaf without a declaration may not carry hooks/.
mkdir -p plugins/c-plan/hooks && printf '{}\n' > plugins/c-plan/hooks/hooks.json
expect_fail "hooks/ without host-hooks.json" "plugins/c-plan/hooks is not generated" \
  bash scripts/sync-plugin-views.sh --check c-plan
expect_fail "package check of undeclared hooks" "declares no hook commands" \
  python3 scripts/check-marketplace-packages.py plugins/c-plan
bash scripts/sync-plugin-views.sh c-plan >/dev/null || fail "sync over undeclared hooks/"
[[ ! -e plugins/c-plan/hooks ]] || fail "sync must remove undeclared hooks/"

# Edited or extra hook files are drift; a command outside scripts/ is refused.
printf 'extra\n' > plugins/shiploop/hooks/extra.json
expect_fail "extra hook file" "hooks/ holds" bash scripts/sync-plugin-views.sh --check shiploop
rm plugins/shiploop/hooks/extra.json
sed -i.bak 's|/scripts/shiploop-status-hook|/scripts/../SKILL.md|' plugins/shiploop/hooks/codex.json && rm plugins/shiploop/hooks/codex.json.bak
expect_fail "edited hook file" "hooks/codex.json out of sync" bash scripts/sync-plugin-views.sh --check shiploop
expect_fail "package check of a command outside scripts/" "command must run an executable" \
  python3 scripts/check-marketplace-packages.py plugins/shiploop
bash scripts/sync-plugin-views.sh shiploop >/dev/null || fail "sync over edited hooks"

# The declaration itself is validated before anything is generated.
decl=skills/shiploop/host-hooks.json
cp "$decl" "$decl.orig"
sed 's|scripts/shiploop-status-hook|../SKILL.md|' "$decl.orig" > "$decl"
expect_fail "declaration outside scripts/" "script must be scripts/<file>" bash scripts/sync-plugin-views.sh --check shiploop
sed 's|scripts/shiploop-status-hook|scripts/shiploop_status_hook.py|' "$decl.orig" > "$decl"
expect_fail "non-executable declared script" "must be an executable regular file" bash scripts/sync-plugin-views.sh --check shiploop
sed 's|"grok"|"opencode"|' "$decl.orig" > "$decl"
expect_fail "unknown host" "hosts must be distinct values" bash scripts/sync-plugin-views.sh --check shiploop
mv "$decl.orig" "$decl"
bash scripts/sync-plugin-views.sh --check shiploop >/dev/null || fail "check after restoring the declaration"
pass_sync "host hooks are generated per host from host-hooks.json and nowhere else"

printf 'sync-plugin-views.test.sh: PASS (incl. internal deref + escape refuse + B1 + exact views + host hooks)\n'
exit 0
