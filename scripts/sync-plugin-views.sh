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

# Validate package-internal symlinks only; refuse escapes (matches install.sh Hermes path).
validate_skill_package_symlinks() {
  local source_dir="$1"
  local label="$2"
  python3 - "$source_dir" "$label" <<'PY'
import os, sys
root = os.path.realpath(sys.argv[1])
label = sys.argv[2]
bad = []
for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
    for name in dirnames + filenames:
        path = os.path.join(dirpath, name)
        if not os.path.islink(path):
            continue
        target = os.path.realpath(path)
        if target != root and not target.startswith(root + os.sep):
            bad.append("%s -> %s" % (path, target))
if bad:
    sys.stderr.write(
        "sync-plugin-views: FAIL (%s): symlink escapes package root:\n  %s\n"
        % (label, bad[0])
    )
    sys.exit(1)
sys.exit(0)
PY
}

# Materialize SoT into dest, dereferencing internal symlinks; refuse residual links.
copy_skill_package_deref() {
  local sot="$1"
  local dest="$2"
  local label="$3"
  validate_skill_package_symlinks "$sot" "$label"
  rm -rf "$dest"
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "$dest"
    rsync -aL "$sot"/ "$dest"/
  else
    mkdir -p "$(dirname "$dest")"
    # shellcheck disable=SC2086
    cp -R -L "$sot" "$dest"
  fi
  local leftover
  leftover="$(find "$dest" -type l 2>/dev/null | head -n 1 || true)"
  if [[ -n "$leftover" ]]; then
    printf 'sync-plugin-views: FAIL (%s): residual symlink after dereference: %s\n' "$label" "$leftover" >&2
    exit 1
  fi
}

# Compare SoT to dest after normalizing SoT via dereference (internal symlinks OK in SoT).
skill_package_matches_view() {
  local sot="$1"
  local dest="$2"
  local label="$3"
  local tmp
  tmp="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-sync-cmp.XXXXXX")"
  if ! validate_skill_package_symlinks "$sot" "$label"; then
    rm -rf "$tmp"
    return 1
  fi
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "$tmp/norm"
    rsync -aL "$sot"/ "$tmp/norm"/
  else
    cp -R -L "$sot" "$tmp/norm"
  fi
  if find "$dest" -type l 2>/dev/null | grep -q .; then
    printf 'sync-plugin-views: FAIL (%s): plugin view still contains symlinks\n' "$label" >&2
    rm -rf "$tmp"
    return 1
  fi
  if diff -rq "$tmp/norm" "$dest" >/dev/null 2>&1; then
    rm -rf "$tmp"
    return 0
  fi
  rm -rf "$tmp"
  return 1
}


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
    if ! skill_package_matches_view "$sot" "$dest_skill" "$name"; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills/%s out of sync with skills/%s\n' "$name" "$name" "$name" >&2
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

  # Validate SoT symlinks before any write (fail closed; no partial plugin view).
  validate_skill_package_symlinks "$sot" "$name"
  mkdir -p "$view/skills" "$view/agents" "$view/.claude-plugin"
  node "$derive_js" "$name" --write
  # Remove symlink or stale tree, then copy with package-internal symlink dereference
  # (escape refuse also inside copy_skill_package_deref).
  copy_skill_package_deref "$sot" "$dest_skill" "$name"
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
