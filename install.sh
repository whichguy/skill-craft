#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [flags]\n' "${0##*/}" >&2
  printf '\n' >&2
  printf 'Install skill package(s) into local skill homes.\n' >&2
  printf 'Claude/Grok/Codex: symlink. Hermes: materialized copy (default).\n' >&2
  printf 'Optionally install thin agent cards (Claude + Grok only).\n' >&2
  printf '\n' >&2
  printf 'Flags:\n' >&2
  printf '  --help | -h\n' >&2
  printf '  --claude-only | --grok-only | --codex-only | --hermes-only\n' >&2
  printf '  --all                 # all four hosts (Claude, Grok, Codex, Hermes)\n' >&2
  printf '  --skill NAME          # all (default) | any skills/<name> with SKILL.md\n' >&2
  printf '  --from DIR            # install only basename(DIR) from that path\n' >&2
  printf '                        # (must contain SKILL.md); exclusive with --skill\n' >&2
  printf '  --agents              # also symlink agents/<leaf>.md for Claude/Grok\n' >&2
  printf '  --relink | --force    # replace wrong/dangling skill or agent symlinks\n' >&2
  printf '                        # (never clobbers a real file/directory)\n' >&2
  printf '  --copy                # force copy mode for all hosts (Hermes default)\n' >&2
  printf '  --symlink             # force symlink mode for all hosts (overrides Hermes copy)\n' >&2
  printf '  --status              # report install state (no writes); outcomes per host\n' >&2
  printf '  --uninstall           # remove only owned installs (symlink-owned or managed copy)\n' >&2
  printf '  --dry-run             # print actions only, no writes\n' >&2
  printf '\n' >&2
  printf 'Default (no host flags): install ALL four hosts.\n' >&2
  printf 'Default (no --skill/--from): install every skills/<leaf> with SKILL.md.\n' >&2
  printf 'Default action: install. --status / --uninstall are exclusive with each other.\n' >&2
  printf '\n' >&2
  printf 'Skill destinations (per skill leaf):\n' >&2
  printf '  Claude:  ~/.claude/skills/<leaf>  (symlink)\n' >&2
  printf '  Grok:    ~/.grok/skills/<leaf>  (symlink)\n' >&2
  printf '  Codex:   ~/.codex/skills/<leaf>  (symlink)\n' >&2
  printf '  Hermes:  ~/.hermes/skills/software-development/<leaf>  (copy)\n' >&2
  printf '           (container bind: /opt/data/skills/software-development/<leaf>)\n' >&2
  printf '           Provenance: ~/.hermes/skills/software-development/.skill-craft/<leaf>.json\n' >&2
  printf '\n' >&2
  printf 'Status outcomes: absent | symlink-owned | symlink-wrong | copy-owned |\n' >&2
  printf '  copy-owned-stale | foreign | foreign-file\n' >&2
  printf '\n' >&2
  printf 'Agent destinations (only with --agents; Claude + Grok):\n' >&2
  printf '  Claude:  ~/.claude/agents/<leaf>.md\n' >&2
  printf '  Grok:    ~/.grok/agents/<leaf>.md\n' >&2
  printf '  Codex/Hermes: skipped (no agent install)\n' >&2
  printf '\n' >&2
  printf 'Sources: skills/<name> under this repo, or --from DIR.\n' >&2
  printf 'Foreign real directories are never overwritten or uninstalled.\n' >&2
  printf 'With --relink, only wrong or dangling symlinks are replaced.\n' >&2
  printf 'Hermes managed copies are refreshed on re-run; foreign trees are skipped.\n' >&2
}

# Safe skill leaf: all|both (special = every skills/*) OR ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ length 2–64
is_safe_skill_name() {
  local name="$1"
  if [[ "$name" == "all" || "$name" == "both" ]]; then
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

# Host flags: 0 = unset by user, 1 = selected. When none selected, enable all.
install_claude=0
install_grok=0
install_codex=0
install_hermes=0
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
    --all)
      install_claude=1
      install_grok=1
      install_codex=1
      install_hermes=1
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
    --relink|--force)
      # --relink is primary; --force is a synonym
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
  printf '--agents is only valid for install (not --status/--uninstall)\n' >&2
  exit 64
fi

if [[ "$host_flag_set" -eq 0 ]]; then
  install_claude=1
  install_grok=1
  install_codex=1
  install_hermes=1
fi

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
  printf 'Installed (%s): %s -> %s\n' "$label" "$destination" "$source_dir"
}

# Provenance marker path (outside the leaf so diff -rq source dest stays exact).
hermes_marker_path() {
  local skills_dir="$1"
  local leaf="$2"
  printf '%s/.skill-craft/%s.json\n' "$skills_dir" "$leaf"
}

write_hermes_marker() {
  local marker="$1"
  local leaf="$2"
  local source_dir="$3"
  mkdir -p "$(dirname "$marker")"
  # Stable key order; no timestamps (byte-identical on unchanged reinstall).
  printf '{"schema":1,"leaf":"%s","mode":"copy","source":"%s"}\n' "$leaf" "$source_dir" >"$marker"
}

# Refuse packages with any symlink (self-containment for bind-mounted Hermes).
assert_no_source_symlinks() {
  local source_dir="$1"
  local label="$2"
  local hit
  hit="$(find "$source_dir" -type l 2>/dev/null | head -n 1 || true)"
  if [[ -n "$hit" ]]; then
    printf 'Hermes copy refused (%s): source contains symlink: %s\n' "$label" "$hit" >&2
    printf 'Packages installed as materializations must be self-contained (no symlinks).\n' >&2
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
  local verb="$7" # Installed | Updated | Migrated | Relinked
  local craft_dir="$skills_dir/.skill-craft"
  local stage="$craft_dir/.tmp-${leaf}.$$"
  local old="$craft_dir/.old-${leaf}.$$"

  assert_no_source_symlinks "$source_dir" "$label"

  mkdir -p "$craft_dir"
  rm -rf "$stage" "$old"

  # Best-effort cleanup if we die mid-swap (trap path is absolute).
  trap "rm -rf \"$stage\" \"$old\" 2>/dev/null || true" EXIT

  cp -R "$source_dir" "$stage"
  rm -rf "$stage/.skill-craft" 2>/dev/null || true

  if [[ -e "$destination" || -L "$destination" ]]; then
    mv "$destination" "$old"
  fi
  mv "$stage" "$destination"
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
    Migrated)
      printf 'Migrated to copy (%s): %s\n' "$label" "$destination"
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
    printf 'Hint: add '\''skills/software-development/%s/'\'' to ~/.hermes/.gitignore (skill-craft materializations are local, not synced).\n' "$leaf"
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

  # --- Absent ---
  if [[ ! -e "$destination" && ! -L "$destination" ]]; then
    if [[ "$dry_run" -eq 1 ]]; then
      printf 'Would install (%s): %s (copy)\n' "$label" "$destination"
      return 0
    fi
    materialize_hermes_copy "$label" "$skills_dir" "$leaf" "$source_dir" "$destination" "$marker" "Installed"
    return 0
  fi

  # --- Legacy exact symlink → auto-migrate ---
  if [[ -L "$destination" && "$(readlink "$destination")" == "$source_dir" ]]; then
    if [[ "$dry_run" -eq 1 ]]; then
      printf 'Would migrate to copy (%s): %s\n' "$label" "$destination"
      return 0
    fi
    materialize_hermes_copy "$label" "$skills_dir" "$leaf" "$source_dir" "$destination" "$marker" "Migrated"
    return 0
  fi

  # --- Wrong or dangling symlink ---
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
    return 0
  fi

  # --- Real directory ---
  if [[ -d "$destination" ]]; then
    if [[ -f "$marker" ]]; then
      # Managed copy: refresh if drifted.
      if diff -rq "$source_dir" "$destination" >/dev/null 2>&1; then
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
    # Foreign real tree — never touch.
    printf 'Skipped (foreign) (%s): %s\n' "$label" "$destination"
    return 0
  fi

  # Real non-directory file — treat as foreign skip.
  printf 'Skipped (foreign) (%s): %s\n' "$label" "$destination"
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

# Host default: Hermes=copy, others=symlink. --copy / --symlink overrides all hosts.
host_uses_copy() {
  local host="$1" # claude|grok|codex|hermes
  if [[ "$force_mode" == "copy" ]]; then
    return 0
  fi
  if [[ "$force_mode" == "symlink" ]]; then
    return 1
  fi
  [[ "$host" == "hermes" ]]
}

install_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"

  if [[ "$install_claude" -eq 1 ]]; then
    if host_uses_copy claude; then
      install_hermes_copy "Claude Code / $leaf" "$HOME/.claude/skills" "$leaf" "$source_dir"
    else
      install_one "Claude Code / $leaf" "$HOME/.claude/skills" "$leaf" "$source_dir"
    fi
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    if host_uses_copy grok; then
      install_hermes_copy "Grok / $leaf" "$HOME/.grok/skills" "$leaf" "$source_dir"
    else
      install_one "Grok / $leaf" "$HOME/.grok/skills" "$leaf" "$source_dir"
    fi
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    if host_uses_copy codex; then
      install_hermes_copy "Codex / $leaf" "$HOME/.codex/skills" "$leaf" "$source_dir"
    else
      install_one "Codex / $leaf" "$HOME/.codex/skills" "$leaf" "$source_dir"
    fi
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    # Peer layout under Hermes skillhub. Host ~/.hermes is typically bind-mounted
    # to /opt/data in the hermes container — abs-symlinks to host checkouts break.
    # Default: materialize a managed copy with provenance under .skill-craft/.
    if host_uses_copy hermes; then
      install_hermes_copy "Hermes skillhub / $leaf" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
    else
      install_one "Hermes skillhub / $leaf" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
    fi
  fi
}

install_agent_to_hosts() {
  local leaf="$1"
  local source_file="$repo_dir/agents/${leaf}.md"

  # Agents: Claude + Grok only; skip Codex and Hermes.
  if [[ "$install_claude" -eq 1 ]]; then
    install_agent_one "Claude Code agent / $leaf" "$HOME/.claude/agents" "$leaf" "$source_file"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    install_agent_one "Grok agent / $leaf" "$HOME/.grok/agents" "$leaf" "$source_file"
  fi
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
    if [[ -f "$marker" ]]; then
      if diff -rq "$source_dir" "$destination" >/dev/null 2>&1; then
        printf 'copy-owned\n'
      else
        printf 'copy-owned-stale\n'
      fi
    else
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
      return 0
      ;;
    symlink-owned)
      if [[ "$dry_run" -eq 1 ]]; then
        printf 'Would uninstall symlink (%s): %s\n' "$label" "$destination"
        return 0
      fi
      rm -f "$destination"
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
      printf 'Uninstalled copy (%s): %s\n' "$label" "$destination"
      return 0
      ;;
    foreign|foreign-file|symlink-wrong)
      printf 'Skipped uninstall (not owned) (%s): %s  state=%s\n' "$label" "$destination" "$state"
      return 0
      ;;
    *)
      printf 'Skipped uninstall (unknown state) (%s): %s  state=%s\n' "$label" "$destination" "$state" >&2
      return 0
      ;;
  esac
}

status_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"
  if [[ "$install_claude" -eq 1 ]]; then
    status_one "Claude Code / $leaf" "$HOME/.claude/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    status_one "Grok / $leaf" "$HOME/.grok/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    status_one "Codex / $leaf" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    status_one "Hermes skillhub / $leaf" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
  fi
}

uninstall_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"
  if [[ "$install_claude" -eq 1 ]]; then
    uninstall_one "Claude Code / $leaf" "$HOME/.claude/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    uninstall_one "Grok / $leaf" "$HOME/.grok/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    uninstall_one "Codex / $leaf" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    uninstall_one "Hermes skillhub / $leaf" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
  fi
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
  leaf="$(basename "$skill_from")"
  if ! is_safe_skill_name "$leaf" || [[ "$leaf" == "all" || "$leaf" == "both" ]]; then
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
    all|both)
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
