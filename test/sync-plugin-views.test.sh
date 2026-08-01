#!/usr/bin/env bash
# Plugin views must be real trees (not symlinks) matching skills/ SoT.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

fail() {
  printf 'sync-plugin-views.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x scripts/sync-plugin-views.sh ]] || fail "scripts/sync-plugin-views.sh not executable"

# Check mode must pass against committed materialization
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
for d in skills/*/; do
  n="$(basename "$d")"
  [[ -f "skills/$n/SKILL.md" ]] || continue
  [[ -f "plugins/$n/.claude-plugin/plugin.json" ]] || fail "missing plugin view for skills/$n"
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
# residual no symlinks under this plugin view
if find "plugins/$sample" -type l 2>/dev/null | grep -q .; then
  fail "residual symlink in plugin view after internal deref"
fi
pass_sync "internal symlink dereferenced"

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

printf 'sync-plugin-views.test.sh: PASS (incl. internal deref + escape refuse)\n'
exit 0
