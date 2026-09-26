#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [flags]\n' "${0##*/}" >&2
  printf '\n' >&2
  printf 'Install skill package(s) into local skill homes.\n' >&2
  printf 'Claude/Grok/Codex/Cursor/OpenCode: symlink. Hermes: materialized copy (default).\n' >&2
  printf 'Optionally install thin agent cards (Claude + Grok only).\n' >&2
  printf '\n' >&2
  printf 'Flags:\n' >&2
  printf '  --help | -h\n' >&2
  printf '  --claude-only | --grok-only | --codex-only | --hermes-only | --cursor-only | --opencode-only\n' >&2
  printf '  --all                 # all six hosts (Claude, Grok, Codex, Hermes, Cursor, OpenCode)\n' >&2
  printf '  --skill NAME          # all (default) | any skills/<name> with SKILL.md\n' >&2
  printf '  --from DIR            # install only basename(DIR) from that path\n' >&2
  printf '                        # (must contain SKILL.md); exclusive with --skill\n' >&2
  printf '  --agents              # also symlink agents/<leaf>.md for Claude/Grok\n' >&2
  printf '  --relink              # replace wrong/dangling skill or agent symlinks; with\n' >&2
  printf '                        # --copy, also turn an owned symlink into a managed copy\n' >&2
  printf '                        # (never clobbers a real file/directory)\n' >&2
  printf '  --copy                # force copy mode for all hosts (Hermes default)\n' >&2
  printf '  --symlink             # force symlink mode for all hosts (overrides Hermes copy)\n' >&2
  printf '  --status              # report install state (no writes); outcomes per host\n' >&2
  printf '  --uninstall           # remove only owned installs (symlink-owned or managed copy)\n' >&2
  printf '  --dry-run             # print actions only, no writes\n' >&2
  printf '\n' >&2
  printf 'Default (no host flags): OpenCode only, the one host without a skill\n' >&2
  printf '  marketplace. Claude, Grok, Codex and Cursor get every skill from the\n' >&2
  printf '  skill-craft@whichguy marketplace plugin; link them only for development,\n' >&2
  printf '  with an explicit host flag or --all. Hermes needs --hermes-only or --all.\n' >&2
  printf 'Default (no --skill/--from): install every skills/<leaf> with SKILL.md.\n' >&2
  printf 'Default action: install. --status / --uninstall are exclusive with each other.\n' >&2
  printf '\n' >&2
  printf 'Skill destinations (per skill leaf):\n' >&2
  printf '  Claude:  ~/.claude/skills/<dest>  (symlink)\n' >&2
  printf '  Grok:    ~/.grok/skills/<dest>  (symlink)\n' >&2
  printf '  Codex:   ~/.codex/skills/<dest>  (symlink)\n' >&2
  printf '  Cursor:  ~/.cursor/skills/<dest>  (symlink; never ~/.cursor/skills-cursor)\n' >&2
  printf '  OpenCode: ${XDG_CONFIG_HOME:-$HOME/.config}/opencode/skills/<dest>  (symlink)\n' >&2
  printf '  Hermes:  ~/.hermes/skills/software-development/<dest>  (copy)\n' >&2
  printf '           (container bind: /opt/data/skills/software-development/<dest>)\n' >&2
  printf '           Provenance: ~/.hermes/skills/software-development/.skill-craft/<dest>.json\n' >&2
  printf '  dest = leaf. Leaf devloop skips Hermes (engine owns software-development/devloop).\n' >&2
  printf '  Grok slash: skills/devloop/commands/devloop.md → ~/.grok/commands/devloop.md\n' >&2
  printf '\n' >&2
  printf 'Status outcomes: absent | symlink-owned | symlink-wrong | copy-owned |\n' >&2
  printf '  copy-owned-stale | foreign | foreign-file\n' >&2
  printf 'When Claude plugin inventory is available, --status also reports plugin-track\n' >&2
  printf '(the skill-craft plugin carries every skill) and warns on double-install only\n' >&2
  printf 'when that plugin is confirmed enabled.\n' >&2
  printf 'Only the installed_plugins.json version 2 shape {"version": 2, "plugins":\n' >&2
  printf '{id: [records]}} is read; any other shape gets one unsupported-inventory note.\n' >&2
  printf 'Plugin state is confirmed-enabled only for literal JSON enabled:true; otherwise\n' >&2
  printf 'it is cached-state-unknown or disabled.\n' >&2
  printf 'Override inventory path: CLAUDE_INSTALLED_PLUGINS_JSON (default\n' >&2
  printf '~/.claude/plugins/installed_plugins.json). Set empty to skip plugin probe.\n' >&2
  printf '\n' >&2
  printf 'Agent destinations (only with --agents; Claude + Grok):\n' >&2
  printf '  Claude:  ~/.claude/agents/<leaf>.md\n' >&2
  printf '  Grok:    ~/.grok/agents/<leaf>.md\n' >&2
  printf '  Codex/Cursor/OpenCode/Hermes: skipped (no agent install)\n' >&2
  printf '\n' >&2
  printf 'Sources: skills/<name> under this repo, or --from DIR.\n' >&2
  printf 'Generated plugin views (plugins/<name>) are marketplace-only: never installed\n' >&2
  printf 'here, and refused as --from sources (exit 64),\n' >&2
  printf 'as is any copy whose plugin manifest names the skill-craft repository (host caches).\n' >&2
  printf 'Foreign real directories are never overwritten or uninstalled.\n' >&2
  printf 'With --relink, only symlinks are replaced: wrong or dangling ones, and in copy\n' >&2
  printf 'mode an owned symlink install. Switching an existing symlink install to --copy\n' >&2
  printf 'needs --relink; without it the symlink is skipped.\n' >&2
  printf 'Hermes managed copies are refreshed on re-run; foreign trees are skipped.\n' >&2
  printf '\n' >&2
  printf 'Exit codes:\n' >&2
  printf '  0  success (all requested actions completed without refusal)\n' >&2
  printf '  2  needs human / binding incomplete (reserved; engines)\n' >&2
  printf '  3  foreign-refused (install/uninstall hit unowned path)\n' >&2
  printf '  4  absent (uninstall: nothing owned present)\n' >&2
  printf '  8  drift-blocked (reserved for drift-aware uninstall)\n' >&2
  printf '  64 usage / flag error\n' >&2
}

# Safe skill leaf: all (special = every skills/*) OR ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ length 2–64
is_safe_skill_name() {
  local name="$1"
  if [[ "$name" == "all" ]]; then
    return 0
  fi
  local len=${#name}
  if [[ "$len" -lt 2 || "$len" -gt 64 ]]; then
    return 1
  fi
  [[ "$name" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]
}

# Discover skills/<leaf> directories that contain SKILL.md (sorted).
# Use globs — never parse `ls` (color aliases inject ANSI into names).
list_repo_skills() {
  local skills_root="$1"
  local d leaf
  local -a leaves=()
  if [[ ! -d "$skills_root" ]]; then
    return 0
  fi
  shopt -s nullglob
  for d in "$skills_root"/*/; do
    leaf="$(basename "$d")"
    if [[ -f "$skills_root/$leaf/SKILL.md" ]] && is_safe_skill_name "$leaf" && [[ "$leaf" != "all" ]]; then
      leaves+=("$leaf")
    fi
  done
  shopt -u nullglob
  if [[ ${#leaves[@]} -eq 0 ]]; then
    return 0
  fi
  # Sort for stable install order
  printf '%s\n' "${leaves[@]}" | LC_ALL=C sort
}

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
# The repository every generated plugin manifest names. Must equal REPOSITORY
# in scripts/skill-frontmatter-to-plugin-json.js (pinned by
# test/install-targets.test.sh I21).
skill_craft_repository="https://github.com/whichguy/skill-craft"

# Host flags: 0 = unset by user, 1 = selected. When none selected, enable all.
install_claude=0
install_grok=0
install_codex=0
install_hermes=0
install_cursor=0
install_opencode=0
host_flag_set=0

skill_mode="all" # all | named leaf | (unused when --from set)
skill_from=""    # absolute path when --from used
skill_flag_set=0
from_flag_set=0
install_agents=0
dry_run=0
relink=0
# force_mode: "" | copy | symlink — empty means host defaults (Hermes=copy, others=symlink)
force_mode=""
# action: install | status | uninstall
action="install"

# Aggregate process exit (highest code wins). 0=ok 3=foreign-refused 4=absent 8=drift 64=usage
worst_exit=0
note_exit() {
  local c="${1:-0}"
  [[ "$c" =~ ^[0-9]+$ ]] || return 0
  if [[ "$c" -gt "$worst_exit" ]]; then
    worst_exit="$c"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --claude-only)
      install_claude=1
      host_flag_set=1
      shift
      ;;
    --grok-only)
      install_grok=1
      host_flag_set=1
      shift
      ;;
    --codex-only)
      install_codex=1
      host_flag_set=1
      shift
      ;;
    --hermes-only)
      install_hermes=1
      host_flag_set=1
      shift
      ;;
    --cursor-only)
      install_cursor=1
      host_flag_set=1
      shift
      ;;
    --opencode-only)
      install_opencode=1
      host_flag_set=1
      shift
      ;;
    --all)
      install_claude=1
      install_grok=1
      install_codex=1
      install_hermes=1
      install_cursor=1
      install_opencode=1
      host_flag_set=1
      shift
      ;;
    --skill)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --skill\n' >&2
        usage
        exit 64
      fi
      if ! is_safe_skill_name "$2"; then
        printf 'Invalid --skill value: %s (want all or safe leaf 2–64: [a-z0-9][a-z0-9-]*[a-z0-9]?)\n' "$2" >&2
        usage
        exit 64
      fi
      skill_mode="$2"
      skill_flag_set=1
      shift 2
      ;;
    --from)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --from\n' >&2
        usage
        exit 64
      fi
      skill_from="$2"
      from_flag_set=1
      shift 2
      ;;
    --agents)
      install_agents=1
      shift
      ;;
    --relink)
      relink=1
      shift
      ;;
    --copy)
      force_mode="copy"
      shift
      ;;
    --symlink)
      force_mode="symlink"
      shift
      ;;
    --status)
      if [[ "$action" != "install" && "$action" != "status" ]]; then
        printf 'Cannot combine --status with --uninstall\n' >&2
        exit 64
      fi
      action="status"
      shift
      ;;
    --uninstall)
      if [[ "$action" != "install" && "$action" != "uninstall" ]]; then
        printf 'Cannot combine --uninstall with --status\n' >&2
        exit 64
      fi
      action="uninstall"
      shift
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    *)
      printf 'Unknown flag: %s\n' "$1" >&2
      usage
      exit 64
      ;;
  esac
done

if [[ "$skill_flag_set" -eq 1 && "$from_flag_set" -eq 1 ]]; then
  printf 'Cannot combine --skill and --from\n' >&2
  usage
  exit 64
fi

if [[ "$action" != "install" && "$install_agents" -eq 1 ]]; then
  printf '%s\n' '--agents is only valid for install (not --status/--uninstall)' >&2
  exit 64
fi

# Claude, Grok, Codex and Cursor install every skill through the skill-craft
# marketplace plugin, so linking them by default would load each skill twice.
# Hermes copies are written only when selected.
if [[ "$host_flag_set" -eq 0 ]]; then
  install_opencode=1
fi

# Agent cards go only to Claude and Grok; without either host --agents would
# silently install nothing.
if [[ "$install_agents" -eq 1 && "$install_claude" -eq 0 && "$install_grok" -eq 0 ]]; then
  printf '%s\n' '--agents needs --claude-only, --grok-only or --all (agent cards install only for Claude/Grok)' >&2
  exit 64
fi

# OpenCode's documented global skills path uses the XDG config root. Keep this
# as a function so HOME/XDG overrides are resolved at invocation time.
opencode_skills_dir() {
  printf '%s/opencode/skills\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
}

# install_one LABEL SKILLS_DIR LEAF SOURCE_DIR
# Creates SKILLS_DIR/LEAF -> SOURCE_DIR when missing (symlink mode).
# Skip-if-exists: never replace a foreign real path; report already-correct symlink.
# With --relink: replace wrong/dangling symlinks only (never clobber real trees).
install_one() {
  local label="$1"
  local skills_dir="$2"
  local leaf="$3"
  local source_dir="$4"
  local destination="$skills_dir/$leaf"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    printf 'Skill source is missing (%s): %s\n' "$label" "$source_dir/SKILL.md" >&2
    exit 1
  fi

  if [[ -e "$destination" || -L "$destination" ]]; then
    if [[ -L "$destination" && "$(readlink "$destination")" == "$source_dir" ]]; then
      printf 'Already installed (%s): %s\n' "$label" "$destination"
      return 0
    fi
    # Wrong or dangling symlink: only rewrite when --relink is set.
    if [[ -L "$destination" && "$relink" -eq 1 ]]; then
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would relink (%s): %s -> %s\n' "$label" "$destination" "$source_dir"
        return 0
      fi
      rm -f "$destination"
      mkdir -p "$skills_dir"
      ln -s "$source_dir" "$destination"
      append_receipt "$skills_dir" "relink" "$leaf" "symlink" "$source_dir" "relinked"
      printf 'Relinked (%s): %s -> %s\n' "$label" "$destination" "$source_dir"
      return 0
    fi
    # Real file/directory, or wrong symlink without --relink: never clobber.
    printf 'Skipped existing path (not replacing it) (%s): %s\n' "$label" "$destination"
    return 0
  fi

  if [[ "$dry_run" -eq 1 ]]; then
    printf 'Would install (%s): %s -> %s\n' "$label" "$destination" "$source_dir"
    return 0
  fi

  mkdir -p "$skills_dir"
  ln -s "$source_dir" "$destination"
  append_receipt "$skills_dir" "install" "$leaf" "symlink" "$source_dir" "created"
  printf 'Installed (%s): %s -> %s\n' "$label" "$destination" "$source_dir"
}

# Provenance marker path (outside the leaf so diff -rq source dest stays exact).
hermes_marker_path() {
  local skills_dir="$1"
  local leaf="$2"
  printf '%s/.skill-craft/%s.json\n' "$skills_dir" "$leaf"
}

# skill_version from SKILL.md frontmatter (best-effort; empty if missing).
read_skill_version() {
  local source_dir="$1"
  local skill_md="$source_dir/SKILL.md"
  if [[ ! -f "$skill_md" ]]; then
    printf ''
    return 0
  fi
  # First version: line in frontmatter only (before second ---)
  awk '
    BEGIN { in_fm=0 }
    /^---[[:space:]]*$/ {
      if (in_fm==0) { in_fm=1; next }
      if (in_fm==1) exit
    }
    in_fm && /^version:[[:space:]]*/ {
      sub(/^version:[[:space:]]*/, "")
      gsub(/[[:space:]]+$/, "")
      print
      exit
    }
  ' "$skill_md"
}

write_hermes_marker() {
  local marker="$1"
  local leaf="$2"
  local source_dir="$3"
  local skill_version
  skill_version="$(read_skill_version "$source_dir")"
  mkdir -p "$(dirname "$marker")"
  # Schema 2 identity marker — no timestamps (byte-stable for same source).
  # skill_version may be empty string.
  printf '{"schema":2,"leaf":"%s","mode":"copy","source":"%s","skill_version":"%s"}\n' \
    "$leaf" "$source_dir" "$skill_version" >"$marker"
}

# Returns 0 if marker proves managed ownership for this leaf+source; else 1.
# Requires ALL of: schema==2, leaf match, mode=="copy", source realpath match.
# Malformed / wrong-leaf / wrong-mode / wrong-schema / non-canonical source → not owned (foreign).
hermes_marker_is_owned() {
  local marker="$1"
  local leaf="$2"
  local source_dir="$3"
  [[ -f "$marker" ]] || return 1
  python3 - "$marker" "$leaf" "$source_dir" <<'PYMARKER'
import json
import os
import sys

marker_path, want_leaf, want_source = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(marker_path, encoding="utf-8") as f:
        data = json.load(f)
except (OSError, json.JSONDecodeError, UnicodeError):
    sys.exit(1)
if not isinstance(data, dict):
    sys.exit(1)
if data.get("schema") != 2:
    sys.exit(1)
if data.get("leaf") != want_leaf:
    sys.exit(1)
if data.get("mode") != "copy":
    sys.exit(1)
src = data.get("source")
if not isinstance(src, str) or not src.strip():
    sys.exit(1)
try:
    if os.path.realpath(src) != os.path.realpath(want_source):
        sys.exit(1)
except OSError:
    if os.path.normpath(src) != os.path.normpath(want_source):
        sys.exit(1)
sys.exit(0)
PYMARKER
}


# Append-only audit log (timestamps ok here; not used for ownership identity).
append_receipt() {
  local skills_dir="$1"
  local action="$2"   # install|update|relink|uninstall
  local leaf="$3"
  local mode="$4"     # copy|symlink
  local source_dir="$5"
  local outcome="$6"  # created|updated|relinked|removed
  local craft_dir="$skills_dir/.skill-craft"
  local receipt_file="$craft_dir/receipts.jsonl"
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf 'unknown')"
  if [[ "$dry_run" -eq 1 ]]; then
    return 0
  fi
  mkdir -p "$craft_dir"
  # Escape minimal JSON specials in paths
  local esc_source esc_leaf
  esc_source="${source_dir//\\/\\\\}"
  esc_source="${esc_source//\"/\\\"}"
  esc_leaf="${leaf//\\/\\\\}"
  esc_leaf="${esc_leaf//\"/\\\"}"
  printf '{"schema":1,"ts":"%s","action":"%s","leaf":"%s","mode":"%s","source":"%s","outcome":"%s"}\n' \
    "$ts" "$action" "$esc_leaf" "$mode" "$esc_source" "$outcome" >>"$receipt_file"
}

# Validate package symlinks resolve under package root; refuse escaping links.
# Prints offending path on failure to stderr.
validate_package_symlinks() {
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
        "Hermes copy refused (%s): symlink escapes package root:\n  %s\n"
        % (label, bad[0])
    )
    sys.stderr.write(
        "Only package-internal symlinks are allowed; they are dereferenced on copy.\n"
    )
    sys.exit(1)
sys.exit(0)
PY
}

# Copy package into stage, dereferencing internal symlinks (-L).
copy_package_to_stage() {
  local source_dir="$1"
  local stage="$2"
  local label="$3"
  validate_package_symlinks "$source_dir" "$label"
  # -L: follow symlinks (macOS + GNU). Prefer rsync -L when available.
  if command -v rsync >/dev/null 2>&1; then
    mkdir -p "$stage"
    rsync -aL --delete "$source_dir"/ "$stage"/
  else
    rm -rf "$stage"
    # shellcheck disable=SC2086
    cp -R -L "$source_dir" "$stage"
  fi
  rm -rf "$stage/.skill-craft" 2>/dev/null || true
  # After dereference, stage must contain no symlinks.
  local leftover
  leftover="$(find "$stage" -type l 2>/dev/null | head -n 1 || true)"
  if [[ -n "$leftover" ]]; then
    printf 'Hermes copy refused (%s): residual symlink after dereference: %s\n' "$label" "$leftover" >&2
    exit 1
  fi
}


# Refuse copy when source and destination are the same tree or nest either way.
refuse_src_dst_nesting() {
  local source_dir="$1"
  local destination="$2"
  local label="$3"
  local src_r dst_r
  src_r="$(cd "$source_dir" && pwd -P)"
  # destination may not exist yet — resolve parent + basename
  if [[ -e "$destination" || -L "$destination" ]]; then
    dst_r="$(cd "$(dirname "$destination")" && pwd -P)/$(basename "$destination")"
    if [[ -d "$destination" && ! -L "$destination" ]]; then
      dst_r="$(cd "$destination" && pwd -P)"
    fi
  else
    local parent
    parent="$(dirname "$destination")"
    if [[ -d "$parent" ]]; then
      dst_r="$(cd "$parent" && pwd -P)/$(basename "$destination")"
    else
      # Do not create parents (dry-run / absent dest); compare absolute-ish paths
      if [[ "$parent" == /* ]]; then
        dst_r="$destination"
      else
        dst_r="$(pwd -P)/$destination"
      fi
    fi
  fi
  if [[ "$src_r" == "$dst_r" ]]; then
    printf 'Refused (%s): source and destination are the same path\n  source=%s\n  dest=%s\n' \
      "$label" "$src_r" "$dst_r" >&2
    exit 1
  fi
  if [[ "$dst_r" == "$src_r"/* || "$src_r" == "$dst_r"/* ]]; then
    printf 'Refused (%s): source and destination nest (containment)\n  source=%s\n  dest=%s\n' \
      "$label" "$src_r" "$dst_r" >&2
    exit 1
  fi
}

# Atomic materialize: stage under .skill-craft, swap into destination, write marker.
materialize_hermes_copy() {
  local label="$1"
  local skills_dir="$2"
  local leaf="$3"
  local source_dir="$4"
  local destination="$5"
  local marker="$6"
  local verb="$7" # Installed | Updated | Relinked
  local craft_dir="$skills_dir/.skill-craft"
  local stage="$craft_dir/.tmp-${leaf}.$$"
  local old="$craft_dir/.old-${leaf}.$$"
  local receipt_action="install"
  local receipt_outcome="created"

  case "$verb" in
    Updated) receipt_action="update"; receipt_outcome="updated" ;;
    Relinked) receipt_action="relink"; receipt_outcome="relinked" ;;
    Installed|*) receipt_action="install"; receipt_outcome="created" ;;
  esac

  mkdir -p "$craft_dir"
  rm -rf "$stage" "$old"

  # Best-effort cleanup if we die mid-swap (trap path is absolute).
  trap "rm -rf \"$stage\" \"$old\" 2>/dev/null || true" EXIT

  refuse_src_dst_nesting "$source_dir" "$destination" "$label"
  copy_package_to_stage "$source_dir" "$stage" "$label"

  if [[ -e "$destination" || -L "$destination" ]]; then
    mv "$destination" "$old"
  fi
  mv "$stage" "$destination"
  # Order: tree ready → receipt → marker last (ownership only after durable tree)
  append_receipt "$skills_dir" "$receipt_action" "$leaf" "copy" "$source_dir" "$receipt_outcome"
  write_hermes_marker "$marker" "$leaf" "$source_dir"
  rm -rf "$old"

  trap - EXIT

  case "$verb" in
    Installed)
      printf 'Installed (%s): %s (copy)\n' "$label" "$destination"
      ;;
    Updated)
      printf 'Updated (%s): %s\n' "$label" "$destination"
      ;;
    Relinked)
      printf 'Relinked (%s): %s (copy)\n' "$label" "$destination"
      ;;
    *)
      printf 'Installed (%s): %s (copy)\n' "$label" "$destination"
      ;;
  esac

  # Hint only when installing into real ~/.hermes that is a git work tree.
  if [[ "$skills_dir" == "$HOME/.hermes/skills/software-development" ]] \
    && git -C "$HOME/.hermes" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    printf 'Operator cleanup (install never writes ~/.hermes/.gitignore):\n' >&2
    printf '  git -C ~/.hermes rm -r --cached --ignore-unmatch skills/software-development/%s skills/software-development/.skill-craft\n' "$leaf" >&2
    printf '  Then gitignore: skills/software-development/%s/ and skills/software-development/.skill-craft/\n' "$leaf" >&2
  fi
}

# install_hermes_copy LABEL SKILLS_DIR LEAF SOURCE_DIR
# Materialized copy for Hermes (or --copy override). Marker-backed lifecycle.
install_hermes_copy() {
  local label="$1"
  local skills_dir="$2"
  local leaf="$3"
  local source_dir="$4"
  local destination="$skills_dir/$leaf"
  local marker
  marker="$(hermes_marker_path "$skills_dir" "$leaf")"

  if [[ ! -f "$source_dir/SKILL.md" ]]; then
    printf 'Skill source is missing (%s): %s\n' "$label" "$source_dir/SKILL.md" >&2
    exit 1
  fi
  # Always refuse identity/nesting (before foreign skip) so src==dst is not silent foreign.
  refuse_src_dst_nesting "$source_dir" "$destination" "$label"

  # --- Absent ---
  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    if [[ "$dry_run" -eq 1 ]]; then
      printf 'Would install (%s): %s (copy)\n' "$label" "$destination"
      return 0
    fi
    materialize_hermes_copy "$label" "$skills_dir" "$leaf" "$source_dir" "$destination" "$marker" "Installed"
    return 0
  fi

  # --- Any symlink: an owned symlink install, or a wrong/dangling one ---
  # Copy mode replaces a symlink only with --relink (then reports Relinked).
  if [[ -L "$destination" ]]; then
    if [[ "$relink" -eq 1 ]]; then
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would relink (%s): %s (copy)\n' "$label" "$destination"
        return 0
      fi
      materialize_hermes_copy "$label" "$skills_dir" "$leaf" "$source_dir" "$destination" "$marker" "Relinked"
      return 0
    fi
    printf 'Skipped existing path (not replacing it) (%s): %s\n' "$label" "$destination"
    if [[ "$(readlink "$destination")" == "$source_dir" ]]; then
      local rerun="--relink"
      if [[ "$force_mode" == "copy" ]]; then
        rerun="--copy --relink"
      fi
      printf '  owned symlink install; re-run with %s to replace it with a managed copy\n' "$rerun"
    fi
    return 0
  fi

  # --- Real directory ---
  if [[ -d "$destination" ]]; then
    # Managed only when marker proves ownership (schema/leaf/mode/source).
    if hermes_marker_is_owned "$marker" "$leaf" "$source_dir"; then
      # Managed copy: refresh if drifted (compare via normalized/dereferenced source).
      if normalized_trees_match "$source_dir" "$destination" "$label"; then
        printf 'Already installed (up to date) (%s): %s\n' "$label" "$destination"
        return 0
      fi
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would update (%s): %s\n' "$label" "$destination"
        return 0
      fi
      materialize_hermes_copy "$label" "$skills_dir" "$leaf" "$source_dir" "$destination" "$marker" "Updated"
      return 0
    fi
    # Foreign real tree (no marker or marker-invalid) — never touch.
    printf 'Skipped (foreign) (%s): %s\n' "$label" "$destination"
    note_exit 3
    return 0
  fi

  # Real non-directory file — treat as foreign skip.
  printf 'Skipped (foreign) (%s): %s\n' "$label" "$destination"
  note_exit 3
  return 0
}

# install_agent_one LABEL AGENTS_DIR LEAF SOURCE_FILE
# Creates AGENTS_DIR/LEAF.md -> SOURCE_FILE when missing.
# Same skip-if-exists / already-installed / --relink / dry-run semantics as install_one.
install_agent_one() {
  local label="$1"
  local agents_dir="$2"
  local leaf="$3"
  local source_file="$4"
  local destination="$agents_dir/${leaf}.md"

  if [[ ! -f "$source_file" ]]; then
    # No agent card for this leaf — silent skip (not an error).
    return 0
  fi

  if [[ -e "$destination" || -L "$destination" ]]; then
    if [[ -L "$destination" && "$(readlink "$destination")" == "$source_file" ]]; then
      printf 'Already installed (%s): %s\n' "$label" "$destination"
      return 0
    fi
    if [[ -L "$destination" && "$relink" -eq 1 ]]; then
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would relink (%s): %s -> %s\n' "$label" "$destination" "$source_file"
        return 0
      fi
      rm -f "$destination"
      mkdir -p "$agents_dir"
      ln -s "$source_file" "$destination"
      printf 'Relinked (%s): %s -> %s\n' "$label" "$destination" "$source_file"
      return 0
    fi
    printf 'Skipped existing path (not replacing it) (%s): %s\n' "$label" "$destination"
    return 0
  fi

  if [[ "$dry_run" -eq 1 ]]; then
    printf 'Would install (%s): %s -> %s\n' "$label" "$destination" "$source_file"
    return 0
  fi

  mkdir -p "$agents_dir"
  ln -s "$source_file" "$destination"
  printf 'Installed (%s): %s -> %s\n' "$label" "$destination" "$source_file"
}

# Host default: Hermes=copy, all other hosts=symlink. --copy / --symlink overrides all hosts.
host_uses_copy() {
  local host="$1" # claude|grok|codex|hermes|cursor|opencode
  if [[ "$force_mode" == "copy" ]]; then
    return 0
  fi
  if [[ "$force_mode" == "symlink" ]]; then
    return 1
  fi
  [[ "$host" == "hermes" ]]
}

# The destination name on every host is the source leaf.
install_host_skill() {
  local host="$1"
  local label="$2"
  local skills_dir="$3"
  local leaf="$4"
  local source_dir="$5"
  if host_uses_copy "$host"; then
    install_hermes_copy "$label / $leaf" "$skills_dir" "$leaf" "$source_dir"
  else
    install_one "$label / $leaf" "$skills_dir" "$leaf" "$source_dir"
  fi
}

install_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"

  if [[ "$install_claude" -eq 1 ]]; then
    install_host_skill claude "Claude Code" "$HOME/.claude/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    install_host_skill grok "Grok" "$HOME/.grok/skills" "$leaf" "$source_dir"
    if [[ "$leaf" == "devloop" ]]; then
      install_agent_one "Grok command /devloop" "$HOME/.grok/commands" "devloop" \
        "$source_dir/commands/devloop.md"
    fi
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    install_host_skill codex "Codex" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_cursor" -eq 1 ]]; then
    install_host_skill cursor "Cursor" "$HOME/.cursor/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_opencode" -eq 1 ]]; then
    install_host_skill opencode "OpenCode" "$(opencode_skills_dir)" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    # Peer layout under Hermes skillhub. Host ~/.hermes is typically bind-mounted
    # to /opt/data in the hermes container — abs-symlinks to host checkouts break.
    # Default: materialize a managed copy with provenance under .skill-craft/.
    # Leaf "devloop" skips Hermes — the engine owns software-development/devloop.
    if [[ "$leaf" == "devloop" ]]; then
      printf 'Skipped Hermes card install for leaf devloop (engine owns software-development/devloop)\n'
    else
      install_host_skill hermes "Hermes skillhub" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
    fi
  fi
}

install_agent_to_hosts() {
  local leaf="$1"
  local source_file="$repo_dir/agents/${leaf}.md"

  # Agents: Claude + Grok only; skip Codex, Cursor, OpenCode, and Hermes.
  if [[ "$install_claude" -eq 1 ]]; then
    install_agent_one "Claude Code agent / $leaf" "$HOME/.claude/agents" "$leaf" "$source_file"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    install_agent_one "Grok agent / $leaf" "$HOME/.grok/agents" "$leaf" "$source_file"
  fi
}

# Compare source package to installed copy using the same normalize/dereference path.
normalized_trees_match() {
  local source_dir="$1"
  local dest_dir="$2"
  local label="$3"
  local skills_dir
  skills_dir="$(dirname "$dest_dir")"
  local craft_dir="$skills_dir/.skill-craft"
  local tmpcmp="$craft_dir/.cmp-$$"
  mkdir -p "$craft_dir"
  rm -rf "$tmpcmp"
  if ! copy_package_to_stage "$source_dir" "$tmpcmp" "$label" 2>/dev/null; then
    rm -rf "$tmpcmp"
    return 1
  fi
  if diff -rq "$tmpcmp" "$dest_dir" >/dev/null 2>&1; then
    rm -rf "$tmpcmp"
    return 0
  fi
  rm -rf "$tmpcmp"
  return 1
}

# classify_destination SKILLS_DIR LEAF SOURCE_DIR -> prints one outcome token
# Outcomes: absent | symlink-owned | symlink-wrong | copy-owned | copy-owned-stale | foreign | foreign-file
classify_destination() {
  local skills_dir="$1"
  local leaf="$2"
  local source_dir="$3"
  local destination="$skills_dir/$leaf"
  local marker
  marker="$(hermes_marker_path "$skills_dir" "$leaf")"

  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    printf 'absent\n'
    return 0
  fi
  if [[ -L "$destination" ]]; then
    local target
    target="$(readlink "$destination")"
    if [[ "$target" == "$source_dir" ]]; then
      printf 'symlink-owned\n'
    else
      printf 'symlink-wrong\n'
    fi
    return 0
  fi
  if [[ -d "$destination" ]]; then
    # Marker file alone is not ownership — parse schema/leaf/mode/source.
    if hermes_marker_is_owned "$marker" "$leaf" "$source_dir"; then
      if normalized_trees_match "$source_dir" "$destination" "classify/$leaf"; then
        printf 'copy-owned\n'
      else
        printf 'copy-owned-stale\n'
      fi
    else
      # No marker, or marker-invalid (malformed / wrong schema/leaf/mode/source)
      printf 'foreign\n'
    fi
    return 0
  fi
  printf 'foreign-file\n'
}

status_one() {
  local label="$1"
  local skills_dir="$2"
  local leaf="$3"
  local source_dir="$4"
  local destination="$skills_dir/$leaf"
  local state
  state="$(classify_destination "$skills_dir" "$leaf" "$source_dir")"
  printf 'status (%s): %s  state=%s  path=%s\n' "$label" "$leaf" "$state" "$destination"
}

# Claude plugin-track probe for double-install detect (skill-dir + marketplace plugin).
# Reads installed_plugins.json (no claude CLI required). Injectable for tests:
#   CLAUDE_INSTALLED_PLUGINS_JSON=/path/to/file.json  — use that file
#   CLAUDE_INSTALLED_PLUGINS_JSON=                    — skip probe (empty string)
# Unset → default $HOME/.claude/plugins/installed_plugins.json
#
# Only the installed_plugins.json version 2 shape is read:
#   {"version": 2, "plugins": {"<name>@<market>": [<record object>, ...]}}
# The skill-craft plugin bundles every skill, so any skill-craft@* id tracks
# every leaf. Prints one line to stdout when a plugin id matches skill-craft@* :
#   plugin-track: <id>  version=<v>  enabled=<true|false|unknown>  state=<state>
# Returns 0 if a plugin track is present for leaf, 1 when there is no inventory
# or no match, and 2 (with the reason on stdout) for an unreadable file or any
# other shape.
claude_plugin_track_line() {
  local leaf="$1"
  local inv_path
  if [[ -n "${CLAUDE_INSTALLED_PLUGINS_JSON+x}" ]]; then
    inv_path="${CLAUDE_INSTALLED_PLUGINS_JSON}"
    [[ -n "$inv_path" ]] || return 1
  else
    inv_path="${HOME}/.claude/plugins/installed_plugins.json"
  fi
  [[ -f "$inv_path" ]] || return 1

  # python3 always available in this stack; parse inventory without jq.
  local rc=0
  CLAUDE_PLUGIN_INV_PATH="$inv_path" python3 - <<'PY' || rc=$?
import json, os, sys
from pathlib import Path

path = Path(os.environ["CLAUDE_PLUGIN_INV_PATH"])


def unsupported(reason):
    print(
        f"unsupported inventory {path}: {reason}; "
        'want {"version": 2, "plugins": {id: [records]}}; plugin-track skipped'
    )
    sys.exit(2)


try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, ValueError):
    unsupported("not readable JSON")
if not isinstance(data, dict) or data.get("version") != 2:
    unsupported("version is not 2")
plugins = data.get("plugins")
if not isinstance(plugins, dict):
    unsupported("plugins is not an object")
for plugin_id, records in plugins.items():
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        unsupported(f"plugins[{plugin_id!r}] is not a list of record objects")

found = []
ordinal = 0

def consider(plugin_id, record):
    global ordinal
    if "@" not in plugin_id:
        return
    name = plugin_id.split("@", 1)[0]
    if name != "skill-craft":
        return
    version = str(record.get("version") or "")
    enabled_value = record.get("enabled")
    if enabled_value is True:
        enabled = "true"
    elif enabled_value is False:
        enabled = "false"
    else:
        enabled = "unknown"
    found.append((plugin_id, version, enabled, ordinal))
    ordinal += 1

for plugin_id, records in plugins.items():
    # A matching, empty cached record list is still informative, but not enabled.
    for record in records or [{}]:
        consider(plugin_id, record)

if not found:
    sys.exit(1)
# A literal true is the only evidence that a plugin is enabled. Prefer that state
# first, then an unknown cached state, then a literal false; only break ties by
# the preferred marketplace and plugin id.
status_rank = {"true": 0, "unknown": 1, "false": 2}
found.sort(key=lambda t: (
    status_rank[t[2]],
    0 if t[0].endswith("@whichguy") else 1,
    t[0],
    t[3],
))
pid, version, enabled, _ = found[0]
state = {
    "true": "confirmed-enabled",
    "unknown": "cached-state-unknown",
    "false": "disabled",
}[enabled]
ver_s = version if version else "?"
print(f"plugin-track: {pid}  version={ver_s}  enabled={enabled}  state={state}")
sys.exit(0)
PY
  return "$rc"
}

# The unsupported-inventory note prints once per run, not once per leaf.
plugin_inventory_note_shown=0

# After Claude skill-dir status, report plugin-track and warn only for a confirmed
# enabled plugin plus a present skill directory.
status_claude_plugin_overlay() {
  local leaf="$1"
  local skill_state="$2"
  local line rc=0
  line="$(claude_plugin_track_line "$leaf")" || rc=$?
  if [[ "$rc" -eq 2 ]]; then
    if [[ "$plugin_inventory_note_shown" -eq 0 ]]; then
      printf 'note (Claude plugin inventory): %s\n' "$line" >&2
      plugin_inventory_note_shown=1
    fi
    return 0
  fi
  if [[ "$rc" -ne 0 ]]; then
    return 0
  fi
  printf 'status (Claude plugin / %s): %s\n' "$leaf" "$line"
  case "$line" in
    *' state=confirmed-enabled')
      case "$skill_state" in
        absent)
          # A confirmed plugin-only track is fine.
          ;;
        *)
          printf 'warn (Claude / %s): double-install — skill-dir state=%s AND %s\n' \
            "$leaf" "$skill_state" "$line" >&2
          printf '  pick one track: skill-dir (install.sh) OR plugin (plugin install …@market); not both\n' >&2
          ;;
      esac
      ;;
  esac
}

uninstall_one() {
  local label="$1"
  local skills_dir="$2"
  local leaf="$3"
  local source_dir="$4"
  local destination="$skills_dir/$leaf"
  local marker
  marker="$(hermes_marker_path "$skills_dir" "$leaf")"
  local state
  state="$(classify_destination "$skills_dir" "$leaf" "$source_dir")"

  case "$state" in
    absent)
      printf 'Already absent (%s): %s\n' "$label" "$destination"
      note_exit 4
      return 0
      ;;
    symlink-owned)
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would uninstall symlink (%s): %s\n' "$label" "$destination"
        return 0
      fi
      rm -f "$destination"
      append_receipt "$skills_dir" "uninstall" "$leaf" "symlink" "$source_dir" "removed"
      printf 'Uninstalled symlink (%s): %s\n' "$label" "$destination"
      return 0
      ;;
    copy-owned|copy-owned-stale)
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would uninstall copy (%s): %s\n' "$label" "$destination"
        return 0
      fi
      rm -rf "$destination"
      rm -f "$marker"
      append_receipt "$skills_dir" "uninstall" "$leaf" "copy" "$source_dir" "removed"
      printf 'Uninstalled copy (%s): %s\n' "$label" "$destination"
      return 0
      ;;
    foreign|foreign-file|symlink-wrong)
      printf 'Skipped uninstall (not owned) (%s): %s  state=%s\n' "$label" "$destination" "$state"
      note_exit 3
      return 0
      ;;
    *)
      printf 'Skipped uninstall (unknown state) (%s): %s  state=%s\n' "$label" "$destination" "$state" >&2
      note_exit 3
      return 0
      ;;
  esac
}

# status_host_skill LABEL SKILLS_DIR LEAF SOURCE_DIR (dest = leaf)
status_host_skill() {
  status_one "$1 / $3" "$2" "$3" "$4"
}

# uninstall_host_skill LABEL SKILLS_DIR LEAF SOURCE_DIR (dest = leaf)
uninstall_host_skill() {
  uninstall_one "$1 / $3" "$2" "$3" "$4"
}

status_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"
  local claude_state=""
  if [[ "$install_claude" -eq 1 ]]; then
    status_host_skill "Claude Code" "$HOME/.claude/skills" "$leaf" "$source_dir"
    claude_state="$(classify_destination "$HOME/.claude/skills" "$leaf" "$source_dir")"
    status_claude_plugin_overlay "$leaf" "$claude_state"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    status_host_skill "Grok" "$HOME/.grok/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    status_host_skill "Codex" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_cursor" -eq 1 ]]; then
    status_host_skill "Cursor" "$HOME/.cursor/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_opencode" -eq 1 ]]; then
    status_host_skill "OpenCode" "$(opencode_skills_dir)" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    if [[ "$leaf" == "devloop" ]]; then
      printf 'Skipped Hermes card status for leaf devloop (engine owns software-development/devloop)\n'
    else
      status_host_skill "Hermes skillhub" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
    fi
  fi
}

uninstall_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"
  if [[ "$install_claude" -eq 1 ]]; then
    uninstall_host_skill "Claude Code" "$HOME/.claude/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    uninstall_host_skill "Grok" "$HOME/.grok/skills" "$leaf" "$source_dir"
    if [[ "$leaf" == "devloop" ]]; then
      local cmd_src="$source_dir/commands/devloop.md"
      local cmd_dest="$HOME/.grok/commands/devloop.md"
      if [[ -L "$cmd_dest" && "$(readlink "$cmd_dest")" == "$cmd_src" ]]; then
        if [[ "$dry_run" -eq 1 ]]; then
          printf 'Would uninstall symlink (Grok command /devloop): %s\n' "$cmd_dest"
        else
          rm -f "$cmd_dest"
          printf 'Uninstalled symlink (Grok command /devloop): %s\n' "$cmd_dest"
        fi
      fi
    fi
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    uninstall_host_skill "Codex" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_cursor" -eq 1 ]]; then
    uninstall_host_skill "Cursor" "$HOME/.cursor/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_opencode" -eq 1 ]]; then
    uninstall_host_skill "OpenCode" "$(opencode_skills_dir)" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    if [[ "$leaf" == "devloop" ]]; then
      printf 'Skipped Hermes card uninstall for leaf devloop (engine owns software-development/devloop)\n'
    else
      uninstall_host_skill "Hermes skillhub" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
    fi
  fi
}

# True when a package's host manifest (Claude, Codex or Cursor plugin.json)
# names skill-craft's repository: only a generated plugin view does, wherever
# it was copied (a host plugin cache or a git-subdir clone). A manifest that is
# absent or unreadable is not that signature, so a foreign package stays
# installable; canonical upstream sources name their own repository.
package_names_skill_craft_repository() {
  local package="$1"
  [[ -f "$package/.claude-plugin/plugin.json" || -f "$package/.codex-plugin/plugin.json" \
     || -f "$package/.cursor-plugin/plugin.json" ]] || return 1
  python3 - "$package" "$skill_craft_repository" <<'PY'
import json
import sys
from pathlib import Path

package, wanted = Path(sys.argv[1]), sys.argv[2]


def normalized(value):
    if isinstance(value, dict):
        value = value.get("url")
    if not isinstance(value, str):
        return None
    value = value.strip().rstrip("/")
    if value.endswith(".git"):
        value = value[:-4]
    return value.lower()


for host in (".claude-plugin", ".codex-plugin", ".cursor-plugin"):
    try:
        data = json.loads((package / host / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        continue
    if isinstance(data, dict) and normalized(data.get("repository")) == normalized(wanted):
        sys.exit(0)
sys.exit(1)
PY
}

# Generated plugin views (plugins/<name>) duplicate a skills/<leaf> source.
# Refuse them as --from sources for every action: paths in this checkout or
# in any other skill-craft checkout, and any copy whose host manifest names
# skill-craft's repository (host plugin caches, git-subdir clones). So a
# --relink cannot repoint a canonical link at a marketplace copy that still
# carries its generated manifests. Structure and manifests, not skill names,
# decide.
marketplace_only_source_reason() {
  local source="$1"
  case "$source/" in
    "$repo_dir/plugins/"*)
      printf 'generated plugin views are marketplace-only; install skills/<leaf> or the canonical source'
      return 0
      ;;
  esac
  local skills_dir package
  skills_dir="$(dirname "$source")"
  package="$(dirname "$skills_dir")"
  [[ "$(basename "$skills_dir")" == "skills" ]] || return 1
  if [[ "$(basename "$(dirname "$package")")" == "plugins" && -f "$package/.claude-plugin/plugin.json" \
        && -f "$(dirname "$(dirname "$package")")/scripts/sync-plugin-views.sh" ]]; then
    printf 'generated plugin views are marketplace-only; install skills/<leaf> or the canonical source'
    return 0
  fi
  if package_names_skill_craft_repository "$package"; then
    printf 'copies of generated plugin views (host plugin caches) are marketplace-only; install skills/<leaf> or the canonical source'
    return 0
  fi
  return 1
}

# Collect leaves to install as "leaf|source_dir" pairs.
declare -a install_pairs=()

if [[ "$from_flag_set" -eq 1 ]]; then
  # Resolve --from DIR to absolute path; leaf = basename.
  if [[ ! -d "$skill_from" ]]; then
    printf 'Skill source directory not found: %s\n' "$skill_from" >&2
    exit 1
  fi
  skill_from="$(cd "$skill_from" && pwd -P)"
  if refusal="$(marketplace_only_source_reason "$skill_from")"; then
    printf 'Refusing --from %s: %s\n' "$skill_from" "$refusal" >&2
    exit 64
  fi
  leaf="$(basename "$skill_from")"
  if ! is_safe_skill_name "$leaf" || [[ "$leaf" == "all" ]]; then
    printf 'Invalid skill leaf from --from path basename: %s\n' "$leaf" >&2
    exit 64
  fi
  if [[ ! -f "$skill_from/SKILL.md" ]]; then
    printf 'Skill source is missing SKILL.md: %s\n' "$skill_from/SKILL.md" >&2
    exit 1
  fi
  install_pairs+=("${leaf}|${skill_from}")
else
  case "$skill_mode" in
    all)
      while IFS= read -r leaf; do
        [[ -n "$leaf" ]] || continue
        install_pairs+=("${leaf}|${repo_dir}/skills/${leaf}")
      done < <(list_repo_skills "$repo_dir/skills")
      if [[ ${#install_pairs[@]} -eq 0 ]]; then
        printf 'No skills found under %s (need skills/<leaf>/SKILL.md)\n' "$repo_dir/skills" >&2
        exit 1
      fi
      ;;
    *)
      # Named leaf: require skills/NAME/SKILL.md
      source_named="$repo_dir/skills/$skill_mode"
      if [[ ! -f "$source_named/SKILL.md" ]]; then
        printf 'Skill source is missing SKILL.md: %s\n' "$source_named/SKILL.md" >&2
        printf 'Provide skills/%s/SKILL.md or use --from DIR\n' "$skill_mode" >&2
        exit 1
      fi
      install_pairs+=("${skill_mode}|${source_named}")
      ;;
  esac
fi

for pair in "${install_pairs[@]}"; do
  leaf="${pair%%|*}"
  source_dir="${pair#*|}"
  case "$action" in
    status)
      status_skill_to_hosts "$leaf" "$source_dir"
      ;;
    uninstall)
      uninstall_skill_to_hosts "$leaf" "$source_dir"
      ;;
    install|*)
      install_skill_to_hosts "$leaf" "$source_dir"
      if [[ "$install_agents" -eq 1 ]]; then
        install_agent_to_hosts "$leaf"
      fi
      ;;
  esac
done

exit "$worst_exit"
