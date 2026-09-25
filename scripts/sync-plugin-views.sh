#!/usr/bin/env bash
# Materialize plugin views from skills/ SoT.
# Plugin installs must not depend on a symlink outside the plugin directory,
# so plugins/<name>/skills/<name> must be a real tree (copy). Claude, Codex,
# and Cursor manifests plus the Cursor/Grok marketplace indexes are derived
# from SKILL.md. plugins/ and the catalogs are release output: they are
# committed only through scripts/release.py, never by hand.
#
# Usage:
#   ./scripts/sync-plugin-views.sh           # sync all skills/*
#   ./scripts/sync-plugin-views.sh skill-interop   # one leaf
#   ./scripts/sync-plugin-views.sh --check   # exit 1 if out of sync (gates release commits)
#
# A full sync removes orphan plugins/<name> packages (no skills/<name>/SKILL.md);
# a full --check reports them. A view holds exactly the generated entries: a
# sync removes anything else and --check reports it.
# Copy and --check ignore __pycache__/, *.pyc and .DS_Store at every depth.
# Running a leaf script is not plugin-view drift. Other content diffs still
# fail --check.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
derive_js="$root/scripts/skill-frontmatter-to-plugin-json.js"
source_license="$root/LICENSE"
[[ -f "$derive_js" ]] || { printf 'sync-plugin-views: missing %s\n' "$derive_js" >&2; exit 1; }
[[ -f "$source_license" ]] || { printf 'sync-plugin-views: missing source root LICENSE\n' >&2; exit 1; }

check_only=0
names=()
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    -h|--help)
      sed -n '2,19p' "$0"
      exit 0
      ;;
    *) names+=("$arg") ;;
  esac
done

# Root marketplace indexes are generated only for a full sync/check. A leaf
# operation is deliberately self-contained so fixture and repair workflows do
# not need to materialize every marketplace entry.
full_sync=0
if [[ ${#names[@]} -eq 0 ]]; then
  full_sync=1
fi

# Default: enumerate from skills/ sources (not plugins/), so new sources are
# not invisible.
leaves=()
if [[ ${#names[@]} -eq 0 ]]; then
  shopt -s nullglob
  for d in skills/*/; do
    n="$(basename "$d")"
    if [[ -f "skills/$n/SKILL.md" ]]; then
      leaves+=("$n")
    fi
  done
  shopt -u nullglob
  # Stable order
  if [[ ${#leaves[@]} -gt 0 ]]; then
    IFS=$'\n' leaves=($(printf '%s\n' "${leaves[@]}" | LC_ALL=C sort))
    unset IFS
  fi
  # Fail closed before any write.
  if [[ ${#leaves[@]} -eq 0 ]]; then
    printf 'sync-plugin-views: FAIL no source skills; refusing empty distribution\n' >&2
    exit 1
  fi
else
  leaves=("${names[@]}")
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
    rsync -aL --exclude '__pycache__/' --exclude '*.pyc' --exclude '.DS_Store' "$sot"/ "$dest"/
  else
    mkdir -p "$(dirname "$dest")"
    # shellcheck disable=SC2086
    cp -R -L "$sot" "$dest"
    find "$dest" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$dest" \( -name '*.pyc' -o -name '.DS_Store' \) -delete 2>/dev/null || true
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
    rsync -aL --exclude '__pycache__/' --exclude '*.pyc' --exclude '.DS_Store' "$sot"/ "$tmp/norm"/
  else
    cp -R -L "$sot" "$tmp/norm"
    find "$tmp/norm" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$tmp/norm" \( -name '*.pyc' -o -name '.DS_Store' \) -delete 2>/dev/null || true
  fi
  if find "$dest" -type l 2>/dev/null | grep -q .; then
    printf 'sync-plugin-views: FAIL (%s): plugin view still contains symlinks\n' "$label" >&2
    rm -rf "$tmp"
    return 1
  fi
  if diff -rq -x __pycache__ -x '*.pyc' -x .DS_Store "$tmp/norm" "$dest" >/dev/null 2>&1; then
    rm -rf "$tmp"
    return 0
  fi
  rm -rf "$tmp"
  return 1
}


# A plugin with package contents but no source SKILL.md is an orphan. Empty,
# ignored directory remnants are harmless and should not make a valid checkout
# fail its full sync check.
plugin_has_packaged_contents() {
  local plugin_dir="$1"
  find "$plugin_dir" -mindepth 1 \
    \( -type d -name __pycache__ -prune \) -o \
    \( -type f ! -name '*.pyc' ! -name '.DS_Store' -print -quit \) -o \
    \( -type l -print -quit \) 2>/dev/null | grep -q .
}

# Top-level entries of a plugin view, ignoring local noise.
view_entries() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  find "$dir" -mindepth 1 -maxdepth 1 ! -name '.DS_Store' ! -name '__pycache__' ! -name '*.pyc' \
    -exec basename {} \; | LC_ALL=C sort
}

# Entries of plugins/<name> that its generation does not produce (for example
# a skill or agent card that left the package), as paths relative to the view.
stale_view_entries() {
  local view="$1" name="$2" has_agent="$3" has_hooks="$4" entry
  local top=".claude-plugin .codex-plugin .cursor-plugin LICENSE README.md skills"
  if [[ "$has_agent" -eq 1 ]]; then top="$top agents"; fi
  # hooks/ is generated only from skills/<name>/host-hooks.json.
  if [[ "$has_hooks" -eq 1 ]]; then top="$top hooks"; fi
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case " $top " in *" $entry "*) ;; *) printf '%s\n' "$entry" ;; esac
  done < <(view_entries "$view")
  while IFS= read -r entry; do
    if [[ -n "$entry" && "$entry" != "$name" ]]; then printf 'skills/%s\n' "$entry"; fi
  done < <(view_entries "$view/skills")
  if [[ "$has_agent" -eq 1 ]]; then
    while IFS= read -r entry; do
      if [[ -n "$entry" && "$entry" != "$name.md" ]]; then printf 'agents/%s\n' "$entry"; fi
    done < <(view_entries "$view/agents")
  fi
  return 0
}

# Orphan plugin views (plugin without a source SKILL.md) — only when syncing
# the full set.
# --check reports them; a full sync removes them (a deleted skill's package).
if [[ "$full_sync" -eq 1 ]]; then
  shopt -s nullglob
  for d in plugins/*/; do
    n="$(basename "$d")"
    if [[ ! -f "skills/$n/SKILL.md" ]] && plugin_has_packaged_contents "$d"; then
      if [[ "$check_only" -eq 1 ]]; then
        printf 'sync-plugin-views: FAIL orphan plugins/%s (no skills/%s/SKILL.md)\n' "$n" "$n" >&2
        fail=1
      else
        rm -rf "plugins/${n:?}"
        printf 'sync-plugin-views: removed orphan plugins/%s\n' "$n"
      fi
    fi
  done
  shopt -u nullglob
fi

for name in ${leaves[@]+"${leaves[@]}"}; do
  sot="$root/skills/$name"
  view="$root/plugins/$name"
  dest_skill="$view/skills/$name"
  dest_agent="$view/agents/${name}.md"
  agent_sot="$root/agents/${name}.md"
  plugin_json="$view/.claude-plugin/plugin.json"
  codex_plugin_json="$view/.codex-plugin/plugin.json"
  package_license="$view/LICENSE"

  [[ -d "$sot" ]] || { printf 'sync-plugin-views: missing SoT skills/%s\n' "$name" >&2; exit 1; }
  [[ -f "$sot/SKILL.md" ]] || { printf 'sync-plugin-views: missing skills/%s/SKILL.md\n' "$name" >&2; exit 1; }
  has_agent=0
  if [[ -f "$agent_sot" ]]; then has_agent=1; fi
  has_hooks=0
  if [[ -f "$sot/host-hooks.json" ]]; then has_hooks=1; fi

  if [[ "$check_only" -eq 1 ]]; then
    if [[ ! -f "$plugin_json" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/.claude-plugin/plugin.json\n' "$name" >&2
      fail=1
      continue
    fi
    if [[ ! -f "$codex_plugin_json" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/.codex-plugin/plugin.json\n' "$name" >&2
      fail=1
      continue
    fi
    if [[ ! -f "$package_license" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/LICENSE\n' "$name" >&2
      fail=1
      continue
    fi
    if ! cmp -s "$source_license" "$package_license"; then
      printf 'sync-plugin-views: FAIL plugins/%s/LICENSE differs from source root LICENSE\n' "$name" >&2
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
    while IFS= read -r entry; do
      [[ -n "$entry" ]] || continue
      printf 'sync-plugin-views: FAIL plugins/%s/%s is not generated from skills/%s\n' "$name" "$entry" "$name" >&2
      fail=1
    done < <(stale_view_entries "$view" "$name" "$has_agent" "$has_hooks")
    continue
  fi

  # Validate SoT symlinks before any write (fail closed; no partial plugin view).
  validate_skill_package_symlinks "$sot" "$name"
  node "$derive_js" "$name" --write
  mkdir -p "$view/skills" "$view/.claude-plugin" "$view/.codex-plugin"
  cp "$source_license" "$package_license"
  # Remove symlink or stale tree, then copy with package-internal symlink dereference
  # (escape refuse also inside copy_skill_package_deref).
  copy_skill_package_deref "$sot" "$dest_skill" "$name"
  while IFS= read -r entry; do
    if [[ -n "$entry" ]]; then rm -rf "${view:?}/$entry"; fi
  done < <(stale_view_entries "$view" "$name" "$has_agent" "$has_hooks")
  if [[ -f "$agent_sot" ]]; then
    # Only a skill with a card gets agents/; Git does not keep empty directories.
    mkdir -p "$view/agents"
    rm -f "$dest_agent"
    cp "$agent_sot" "$dest_agent"
  fi
  printf 'sync-plugin-views: synced plugins/%s from skills/%s\n' "$name" "$name"
done

# A full operation owns the marketplace catalog; a leaf operation intentionally
# does not, so it remains usable for isolated fixtures and single-plugin repair.
if [[ "$full_sync" -eq 1 ]]; then
  if [[ "$check_only" -eq 1 ]]; then
    if ! node "$derive_js" --marketplaces --check; then
      fail=1
    fi
  else
    node "$derive_js" --marketplaces --write
  fi
fi

if [[ "$check_only" -eq 1 ]]; then
  if [[ "$fail" -ne 0 ]]; then
    printf 'sync-plugin-views: CHECK FAILED (run ./scripts/sync-plugin-views.sh)\n' >&2
    exit 1
  fi
  printf 'sync-plugin-views: CHECK OK\n'
fi
