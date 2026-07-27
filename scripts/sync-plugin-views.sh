#!/usr/bin/env bash
# Materialize Claude plugin views from skills/ SoT.
# Claude git-subdir installs do not resolve relative symlinks outside the
# subdir, so plugins/<name>/skills/<name> must be a real tree (copy).
#
# Usage:
#   ./scripts/sync-plugin-views.sh           # sync all plugins/* that have SoT
#   ./scripts/sync-plugin-views.sh skill-interop
#   ./scripts/sync-plugin-views.sh --check   # exit 1 if out of sync (CI)
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"

check_only=0
names=()
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *) names+=("$arg") ;;
  esac
done

if [[ ${#names[@]} -eq 0 ]]; then
  shopt -s nullglob
  for d in plugins/*/; do
    n="$(basename "$d")"
    [[ -d "skills/$n" ]] && names+=("$n")
  done
  shopt -u nullglob
fi

if [[ ${#names[@]} -eq 0 ]]; then
  printf 'sync-plugin-views: no plugin views to sync\n' >&2
  exit 0
fi

fail=0
for name in "${names[@]}"; do
  sot="$root/skills/$name"
  view="$root/plugins/$name"
  dest_skill="$view/skills/$name"
  dest_agent="$view/agents/${name}.md"
  agent_sot="$root/agents/${name}.md"

  [[ -d "$sot" ]] || { printf 'sync-plugin-views: missing SoT skills/%s\n' "$name" >&2; exit 1; }
  [[ -f "$view/.claude-plugin/plugin.json" ]] || {
    printf 'sync-plugin-views: missing plugins/%s/.claude-plugin/plugin.json\n' "$name" >&2
    exit 1
  }

  if [[ "$check_only" -eq 1 ]]; then
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

  mkdir -p "$view/skills" "$view/agents"
  # Remove symlink or stale tree, then copy
  rm -rf "$dest_skill"
  rsync -a "$sot/" "$dest_skill/"
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
