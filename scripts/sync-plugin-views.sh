#!/usr/bin/env bash
# Materialize plugin views from skills/ SoT and from plugin bundles.
# Plugin installs must not depend on a symlink outside the plugin directory,
# so plugins/<name>/skills/<name> must be a real tree (copy). Claude, Codex,
# and Cursor manifests plus the Cursor/Grok marketplace indexes are derived
# from SKILL.md. A bundle (bundles/<plugin>/bundle.json) becomes one plugin
# with several member skills; its vendored bytes are verified against
# PROVENANCE.json (scripts/sync-vendored-bundles.py) before any write.
#
# Usage:
#   ./scripts/sync-plugin-views.sh           # sync all skills/* and bundles/*
#   ./scripts/sync-plugin-views.sh skill-interop   # one leaf or one bundle
#   ./scripts/sync-plugin-views.sh --check   # exit 1 if out of sync (CI)
#
# Copy and --check ignore __pycache__/, *.pyc and .DS_Store at every depth.
# Running a leaf script is not plugin-view drift. Other content diffs still
# fail --check. A leaf or bundle operation first validates every bundle
# declaration against the source skills (collisions fail closed before any
# write, for a named operation too).
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

# Default: enumerate from skills/ and bundles/ sources (not plugins/), so new
# sources are not invisible. A named argument resolves to a leaf or a bundle.
leaves=()
bundles=()
if [[ ${#names[@]} -eq 0 ]]; then
  shopt -s nullglob
  for d in skills/*/; do
    n="$(basename "$d")"
    if [[ -f "skills/$n/SKILL.md" ]]; then
      leaves+=("$n")
    fi
  done
  for d in bundles/*/; do
    n="$(basename "$d")"
    if [[ -f "bundles/$n/bundle.json" ]]; then
      bundles+=("$n")
    fi
  done
  shopt -u nullglob
  # Stable order
  if [[ ${#leaves[@]} -gt 0 ]]; then
    IFS=$'\n' leaves=($(printf '%s\n' "${leaves[@]}" | LC_ALL=C sort))
    unset IFS
  fi
  if [[ ${#bundles[@]} -gt 0 ]]; then
    IFS=$'\n' bundles=($(printf '%s\n' "${bundles[@]}" | LC_ALL=C sort))
    unset IFS
  fi
  # Fail closed before any write: bundles alone are never a distribution.
  if [[ ${#leaves[@]} -eq 0 ]]; then
    printf 'sync-plugin-views: FAIL no source skills; refusing empty distribution\n' >&2
    exit 1
  fi
else
  for n in "${names[@]}"; do
    if [[ -f "bundles/$n/bundle.json" && ! -d "skills/$n" ]]; then
      bundles+=("$n")
    else
      leaves+=("$n")
    fi
  done
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

# Validate every selected bundle before any write (fail closed; no partial
# plugin view): declarations and collisions, then vendored bytes, lint and
# provenance. The member list comes from the validated declaration.
# bash 3.2 compatible (no associative arrays): members are re-read from the
# validated declaration where needed.
bundle_members() {
  node "$derive_js" --bundle "$1" --members | awk -v kind="$2" '$1 == kind { print $2 }'
}
for name in ${bundles[@]+"${bundles[@]}"}; do
  node "$derive_js" --bundle "$name" --members >/dev/null || exit 1
  if ! python3 "$root/scripts/sync-vendored-bundles.py" --check --bundle "$name"; then
    printf 'sync-plugin-views: FAIL bundles/%s is not a verified vendored bundle\n' "$name" >&2
    exit 1
  fi
  while IFS= read -r member; do
    [[ -n "$member" ]] || continue
    validate_skill_package_symlinks "$root/bundles/$name/skills/$member" "$name/$member" || exit 1
  done < <(bundle_members "$name" skill)
done

# Orphan plugin views (plugin without a source SKILL.md or bundle.json) — only
# when syncing the full set. A source directory without either is not valid.
if [[ "$check_only" -eq 1 && "$full_sync" -eq 1 ]]; then
  shopt -s nullglob
  for d in plugins/*/; do
    n="$(basename "$d")"
    if [[ ! -f "skills/$n/SKILL.md" && ! -f "bundles/$n/bundle.json" ]] && plugin_has_packaged_contents "$d"; then
      printf 'sync-plugin-views: FAIL orphan plugins/%s (no skills/%s/SKILL.md or bundles/%s/bundle.json)\n' "$n" "$n" "$n" >&2
      fail=1
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
    continue
  fi

  # Validate SoT symlinks before any write (fail closed; no partial plugin view).
  validate_skill_package_symlinks "$sot" "$name"
  # The generator validates bundle declarations against the leaves before it
  # writes anything, so it runs before any directory is created.
  node "$derive_js" "$name" --write
  mkdir -p "$view/skills" "$view/agents" "$view/.claude-plugin" "$view/.codex-plugin"
  cp "$source_license" "$package_license"
  # Remove symlink or stale tree, then copy with package-internal symlink dereference
  # (escape refuse also inside copy_skill_package_deref).
  copy_skill_package_deref "$sot" "$dest_skill" "$name"
  if [[ -f "$agent_sot" ]]; then
    rm -f "$dest_agent"
    cp "$agent_sot" "$dest_agent"
  fi
  printf 'sync-plugin-views: synced plugins/%s from skills/%s\n' "$name" "$name"
done

# Bundle views: one plugin, several member skills and agent cards. The view's
# top-level entries, skills/* and agents/* are exactly the declared set.
for name in ${bundles[@]+"${bundles[@]}"}; do
  src="$root/bundles/$name"
  view="$root/plugins/$name"
  members=()
  agents=()
  while IFS= read -r item; do [[ -n "$item" ]] && members+=("$item"); done < <(bundle_members "$name" skill)
  while IFS= read -r item; do [[ -n "$item" ]] && agents+=("$item"); done < <(bundle_members "$name" agent)
  expected_top=".claude-plugin .codex-plugin .cursor-plugin LICENSE README.md skills"
  expected_agents=""
  if [[ ${#agents[@]} -gt 0 ]]; then
    expected_top="$expected_top agents"
    expected_agents="$(printf '%s.md\n' "${agents[@]}" | LC_ALL=C sort)"
  fi
  expected_top="$(printf '%s\n' $expected_top | LC_ALL=C sort)"
  expected_members="$(printf '%s\n' "${members[@]}" | LC_ALL=C sort)"

  if [[ "$check_only" -eq 1 ]]; then
    if [[ ! -d "$view" || -L "$view" ]]; then
      printf 'sync-plugin-views: FAIL missing plugins/%s (bundles/%s)\n' "$name" "$name" >&2
      fail=1
      continue
    fi
    if find "$view" -type l 2>/dev/null | grep -q .; then
      printf 'sync-plugin-views: FAIL plugins/%s contains symlinks\n' "$name" >&2
      fail=1
      continue
    fi
    if [[ "$(view_entries "$view")" != "$expected_top" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s top-level entries are not exactly: %s\n' "$name" "$(printf '%s ' $expected_top)" >&2
      fail=1
    fi
    if [[ "$(view_entries "$view/skills")" != "$expected_members" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s/skills is not exactly the declared members: %s\n' "$name" "${members[*]}" >&2
      fail=1
    fi
    if [[ "$(view_entries "$view/agents")" != "$expected_agents" ]]; then
      printf 'sync-plugin-views: FAIL plugins/%s/agents is not exactly the declared agent cards\n' "$name" >&2
      fail=1
    fi
    if [[ ! -f "$view/LICENSE" ]] || ! cmp -s "$source_license" "$view/LICENSE"; then
      printf 'sync-plugin-views: FAIL plugins/%s/LICENSE differs from source root LICENSE\n' "$name" >&2
      fail=1
    fi
    if ! node "$derive_js" --bundle "$name" --check; then
      fail=1
    fi
    for member in "${members[@]}"; do
      if [[ ! -d "$view/skills/$member" ]] || \
         ! skill_package_matches_view "$src/skills/$member" "$view/skills/$member" "$name/$member"; then
        printf 'sync-plugin-views: FAIL plugins/%s/skills/%s out of sync with bundles/%s/skills/%s\n' "$name" "$member" "$name" "$member" >&2
        fail=1
      fi
    done
    for agent in ${agents[@]+"${agents[@]}"}; do
      if [[ ! -f "$view/agents/$agent.md" ]] || ! cmp -s "$src/agents/$agent.md" "$view/agents/$agent.md"; then
        printf 'sync-plugin-views: FAIL agent card plugins/%s/agents/%s.md out of sync\n' "$name" "$agent" >&2
        fail=1
      fi
    done
    continue
  fi

  if [[ -L "$view" ]]; then
    rm -f "$view"
  fi
  mkdir -p "$view/skills" "$view/.claude-plugin" "$view/.codex-plugin"
  # Remove anything the declaration does not produce (stale members, agents,
  # or top-level files); the view is entirely generated.
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    if ! printf '%s\n' "$expected_top" | grep -Fxq -- "$entry"; then
      rm -rf "${view:?}/$entry"
    fi
  done < <(view_entries "$view")
  while IFS= read -r entry; do
    [[ -n "$entry" ]] || continue
    if ! printf '%s\n' "$expected_members" | grep -Fxq -- "$entry"; then
      rm -rf "${view:?}/skills/$entry"
    fi
  done < <(view_entries "$view/skills")
  node "$derive_js" --bundle "$name" --write
  cp "$source_license" "$view/LICENSE"
  for member in "${members[@]}"; do
    copy_skill_package_deref "$src/skills/$member" "$view/skills/$member" "$name/$member"
  done
  if [[ ${#agents[@]} -gt 0 ]]; then
    mkdir -p "$view/agents"
    while IFS= read -r entry; do
      [[ -n "$entry" ]] || continue
      if ! printf '%s\n' "$expected_agents" | grep -Fxq -- "$entry"; then
        rm -rf "${view:?}/agents/$entry"
      fi
    done < <(view_entries "$view/agents")
    for agent in "${agents[@]}"; do
      rm -f "$view/agents/$agent.md"
      cp "$src/agents/$agent.md" "$view/agents/$agent.md"
    done
  fi
  printf 'sync-plugin-views: synced plugins/%s from bundles/%s\n' "$name" "$name"
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
