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

printf 'sync-plugin-views.test.sh: PASS\n'
exit 0
