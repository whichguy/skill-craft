#!/usr/bin/env bash
# Materialize the one skill-craft plugin view from skills/ SoT.
# Every skills/<leaf> ships in plugins/skill-craft/skills/<leaf>, so hosts
# namespace it as skill-craft:<leaf>. Plugin installs must not depend on a
# symlink outside the plugin directory, so each skill is a real tree (copy).
# The Claude, Codex and Cursor manifests, hooks, README and all four marketplace
# indexes are derived from SKILL.md and catalog/skill-craft-plugin.json.
# plugins/ and the catalogs are release output: they are committed only through
# scripts/release.py, never by hand.
#
# Usage:
#   ./scripts/sync-plugin-views.sh           # sync every skills/* into plugins/skill-craft
#   ./scripts/sync-plugin-views.sh --check   # exit 1 if out of sync (gates release commits)
#
# A sync removes any other plugins/<name> directory and any entry of the view
# that generation does not produce; --check reports them.
# Copy and --check ignore __pycache__/, *.pyc and .DS_Store at every depth.
# Running a skill script is not plugin-view drift. Other content diffs still
# fail --check.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
cd "$root"
derive_js="$root/scripts/skill-frontmatter-to-plugin-json.js"
source_license="$root/LICENSE"
[[ -f "$derive_js" ]] || { printf 'sync-plugin-views: missing %s\n' "$derive_js" >&2; exit 1; }
[[ -f "$source_license" ]] || { printf 'sync-plugin-views: missing source root LICENSE\n' >&2; exit 1; }

plugin="skill-craft"
check_only=0
for arg in "$@"; do
  case "$arg" in
    --check) check_only=1 ;;
    -h|--help)
      sed -n '2,19p' "$0"
      exit 0
      ;;
    *)
      printf 'sync-plugin-views: unknown argument %s (every skill ships in one plugin; no per-skill sync)\n' "$arg" >&2
      exit 64
      ;;
  esac
done

# Enumerate from skills/ sources (not plugins/), so new sources are not invisible.
leaves=()
shopt -s nullglob
for d in skills/*/; do
  n="$(basename "$d")"
  if [[ -f "skills/$n/SKILL.md" ]]; then
    leaves+=("$n")
  fi
done
shopt -u nullglob
if [[ ${#leaves[@]} -gt 0 ]]; then
  IFS=$'\n' leaves=($(printf '%s\n' "${leaves[@]}" | LC_ALL=C sort))
  unset IFS
fi
# Fail closed before any write.
if [[ ${#leaves[@]} -eq 0 ]]; then
  printf 'sync-plugin-views: FAIL no source skills; refusing empty distribution\n' >&2
  exit 1
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


# Top-level entries of a directory, ignoring local noise.
view_entries() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  find "$dir" -mindepth 1 -maxdepth 1 ! -name '.DS_Store' ! -name '__pycache__' ! -name '*.pyc' \
    -exec basename {} \; | LC_ALL=C sort
}

# Entries of the view that generation does not produce (for example a skill or
# agent card that left the package), as paths relative to the view.
stale_view_entries() {
  local view="$1" entry
  local top=".claude-plugin .codex-plugin .cursor-plugin LICENSE README.md skills"
  if [[ ${#agent_leaves[@]} -gt 0 ]]; then top="$top agents"; fi
  # hooks/ is generated only from skills/<leaf>/host-hooks.json.
  if [[ "$has_hooks" -eq 1 ]]; then top="$top hooks"; fi
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case " $top " in *" $entry "*) ;; *) printf '%s\n' "$entry" ;; esac
  done < <(view_entries "$view")
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case " ${leaves[*]} " in *" $entry "*) ;; *) printf 'skills/%s\n' "$entry" ;; esac
  done < <(view_entries "$view/skills")
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    case " ${agent_leaves[*]-} " in *" ${entry%.md} "*) [[ "$entry" == *.md ]] && continue ;; esac
    printf 'agents/%s\n' "$entry"
  done < <(view_entries "$view/agents")
  return 0
}

view="$root/plugins/$plugin"
agent_leaves=()
has_hooks=0
for name in "${leaves[@]}"; do
  [[ -f "$root/agents/${name}.md" ]] && agent_leaves+=("$name")
  [[ -f "$root/skills/$name/host-hooks.json" ]] && has_hooks=1
done

# Any other plugins/<name> is not generated (for example a per-skill package
# from before every skill moved into skill-craft).
while IFS= read -r entry; do
  [[ -n "$entry" && "$entry" != "$plugin" ]] || continue
  if [[ "$check_only" -eq 1 ]]; then
    printf 'sync-plugin-views: FAIL plugins/%s is not generated (only plugins/%s is)\n' "$entry" "$plugin" >&2
    fail=1
  else
    rm -rf "$root/plugins/${entry:?}"
    printf 'sync-plugin-views: removed plugins/%s\n' "$entry"
  fi
done < <(view_entries "$root/plugins")

if [[ "$check_only" -eq 1 ]]; then
  if [[ ! -f "$view/LICENSE" ]]; then
    printf 'sync-plugin-views: FAIL missing plugins/%s/LICENSE\n' "$plugin" >&2
    fail=1
  elif ! cmp -s "$source_license" "$view/LICENSE"; then
    printf 'sync-plugin-views: FAIL plugins/%s/LICENSE differs from source root LICENSE\n' "$plugin" >&2
    fail=1
  fi
  if ! node "$derive_js" --package --check; then
    fail=1
  fi
  for name in "${leaves[@]}"; do
    dest_skill="$view/skills/$name"
    if [[ -L "$dest_skill" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills/%s is a symlink (must be real tree)\n' "$plugin" "$name" >&2
      fail=1
    elif [[ ! -d "$dest_skill" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/skills/%s\n' "$plugin" "$name" >&2
      fail=1
    elif ! skill_package_matches_view "$root/skills/$name" "$dest_skill" "$name"; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills/%s out of sync with skills/%s\n' "$plugin" "$name" "$name" >&2
      fail=1
    fi
  done
  for name in ${agent_leaves[@]+"${agent_leaves[@]}"}; do
    dest_agent="$view/agents/${name}.md"
    if [[ -L "$dest_agent" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s/agents/%s.md is a symlink\n' "$plugin" "$name" >&2
      fail=1
    elif [[ ! -f "$dest_agent" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s/agents/%s.md\n' "$plugin" "$name" >&2
      fail=1
    elif ! cmp -s "$root/agents/${name}.md" "$dest_agent"; then
      printf 'sync-plugin-views: FAIL agent card out of sync for %s\n' "$name" >&2
      fail=1
    fi
  done
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    printf 'sync-plugin-views: FAIL plugins/%s/%s is not generated from skills/\n' "$plugin" "$entry" >&2
    fail=1
  done < <(stale_view_entries "$view")
  if ! node "$derive_js" --marketplaces --check; then
    fail=1
  fi
  if [[ "$fail" -ne 0 ]]; then
    printf 'sync-plugin-views: CHECK FAILED (run ./scripts/sync-plugin-views.sh)\n' >&2
    exit 1
  fi
  printf 'sync-plugin-views: CHECK OK\n'
  exit 0
fi

# Validate every source before any write (fail closed; no partial plugin view).
for name in "${leaves[@]}"; do
  validate_skill_package_symlinks "$root/skills/$name" "$name"
done
node "$derive_js" --package --write
mkdir -p "$view/skills"
cp "$source_license" "$view/LICENSE"
for name in "${leaves[@]}"; do
  # Remove a symlink or stale tree, then copy with package-internal symlink
  # dereference (escape refuse also inside copy_skill_package_deref).
  copy_skill_package_deref "$root/skills/$name" "$view/skills/$name" "$name"
done
while IFS= read -r entry; do
  if [[ -n "$entry" ]]; then rm -rf "${view:?}/$entry"; fi
done < <(stale_view_entries "$view")
if [[ ${#agent_leaves[@]} -gt 0 ]]; then
  # Only skills with a card get one; Git does not keep empty directories.
  mkdir -p "$view/agents"
  for name in "${agent_leaves[@]}"; do
    rm -f "$view/agents/${name}.md"
    cp "$root/agents/${name}.md" "$view/agents/${name}.md"
  done
fi
printf 'sync-plugin-views: synced plugins/%s from %d skills\n' "$plugin" "${#leaves[@]}"
node "$derive_js" --marketplaces --write
