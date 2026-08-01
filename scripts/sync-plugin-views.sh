#!/usr/bin/env bash
# Materialize Claude plugin views from skills/ SoT.
# Claude git-subdir installs do not resolve relative symlinks outside the
# subdir, so plugins/<name>/skills/<name> must be a real tree (copy).
# plugin.json name/version/description/license are derived from SKILL.md.
#
# Usage:
#   ./scripts/sync-plugin-views.sh           # sync all skills/* with SKILL.md
#   ./scripts/sync-plugin-views.sh skill-interop
#   ./scripts/sync-plugin-views.sh --check   # exit 1 if out of sync (CI)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
derive_js="$root/scripts/skill-frontmatter-to-plugin-json.js"

check_only=0
names=()
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *) names+=("$arg") ;;
  esac
done

# Default: enumerate from skills/ SoT (not plugins/), so new skills are not invisible.
if [[ ${#names[@]} -eq 0 ]]; then
  shopt -s nullglob
  for d in skills/*/; do
    n="$(basename "$d")"
    if [[ -f "skills/$n/SKILL.md" ]]; then
      names+=("$n")
    fi
  done
  shopt -u nullglob
  # Stable order
  if [[ ${#names[@]} -gt 0 ]]; then
    IFS=$'\n' names=($(printf '%s\n' "${names[@]}" | LC_ALL=C sort))
    unset IFS
  fi
fi

if [[ ${#names[@]} -eq 0 ]]; then
  printf 'sync-plugin-views: no skills to sync\n' >&2
  exit 0
fi

fail=0

# Orphan plugin views (plugin without skills/ leaf) — only when syncing the full set.
if [[ "$check_only" -eq 1 && $# -eq 1 && "$1" == "--check" ]]; then
  shopt -s nullglob
  for d in plugins/*/; do
    n="$(basename "$d")"
    if [[ ! -d "skills/$n" ]]; then
      printf 'sync-plugin-views: FAIL orphan plugins/%s (no skills/%s)\n' "$n" "$n" >&2
      fail=1
    fi
  done
  shopt -u nullglob
fi

for name in "${names[@]}"; do
  sot="$root/skills/$name"
  view="$root/plugins/$name"
  dest_skill="$view/skills/$name"
  dest_agent="$view/agents/${name}.md"
  agent_sot="$root/agents/${name}.md"
  plugin_json="$view/.claude-plugin/plugin.json"

  [[ -d "$sot" ]] || { printf 'sync-plugin-views: missing SoT skills/%s\n' "$name" >&2; exit 1; }
  [[ -f "$sot/SKILL.md" ]] || { printf 'sync-plugin-views: missing skills/%s/SKILL.md\n' "$name" >&2; exit 1; }

  if [[ "$check_only" -eq 1 ]]; then
    if [[ ! -f "$plugin_json" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/.claude-plugin/plugin.json\n' "$name" >&2
      fail=1
      continue
    fi
    if ! node "$derive_js" "$name" --check; then
      fail=1
    fi
    if [[ -L "$dest_skill" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills/%s is a symlink (must be real tree)\n' "$name" "$name" >&2
      fail=1
      continue
    fi
    if [[ ! -d "$dest_skill" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/skills/%s\n' "$name" "$name" >&2
      fail=1
      continue
    fi
    if ! diff -rq "$sot" "$dest_skill" >/dev/null 2>&1; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills/%s out of sync with skills/%s\n' "$name" "$name" "$name" >&2
      diff -rq "$sot" "$dest_skill" 2>&1 | head -20 >&2 || true
      fail=1
    fi
    if [[ -f "$agent_sot" ]]; then
      if [[ -L "$dest_agent" ]]; then
        printf 'sync-plugin-views: FAIL plugins/%s/agents/%s.md is a symlink\n' "$name" "$name" >&2
        fail=1
      elif [[ ! -f "$dest_agent" ]]; then
        printf 'sync-plugin-views: FAIL missing plugins/%s/agents/%s.md\n' "$name" "$name" >&2
        fail=1
      elif ! cmp -s "$agent_sot" "$dest_agent"; then
        printf 'sync-plugin-views: FAIL agent card out of sync for %s\n' "$name" >&2
        fail=1
      fi
    fi
    continue
  fi

  mkdir -p "$view/skills" "$view/agents" "$view/.claude-plugin"
  node "$derive_js" "$name" --write
  # Remove symlink or stale tree, then copy
  rm -rf "$dest_skill"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a "$sot/" "$dest_skill/"
  else
    mkdir -p "$dest_skill"
    cp -R "$sot"/. "$dest_skill"/
  fi
  if [[ -f "$agent_sot" ]]; then
    rm -f "$dest_agent"
    cp "$agent_sot" "$dest_agent"
  fi
  printf 'sync-plugin-views: synced plugins/%s from skills/%s\n' "$name" "$name"
done

if [[ "$check_only" -eq 1 ]]; then
  if [[ "$fail" -ne 0 ]]; then
    printf 'sync-plugin-views: CHECK FAILED (run ./scripts/sync-plugin-views.sh)\n' >&2
    exit 1
  fi
  printf 'sync-plugin-views: CHECK OK\n'
fi
