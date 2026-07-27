#!/usr/bin/env bash
set -euo pipefail

usage() {
  printf 'Usage: %s [flags]\n' "${0##*/}" >&2
  printf '\n' >&2
  printf 'Install skill package(s) via symlink(s) into local skill homes.\n' >&2
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
  printf '  --dry-run             # print actions only, no writes\n' >&2
  printf '\n' >&2
  printf 'Default (no host flags): install ALL four hosts.\n' >&2
  printf 'Default (no --skill/--from): install every skills/<leaf> with SKILL.md.\n' >&2
  printf '\n' >&2
  printf 'Skill destinations (per skill leaf):\n' >&2
  printf '  Claude:  ~/.claude/skills/<leaf>\n' >&2
  printf '  Grok:    ~/.grok/skills/<leaf>\n' >&2
  printf '  Codex:   ~/.codex/skills/<leaf>\n' >&2
  printf '  Hermes:  ~/.hermes/skills/software-development/<leaf>\n' >&2
  printf '           (container bind: /opt/data/skills/software-development/<leaf>)\n' >&2
  printf '\n' >&2
  printf 'Agent destinations (only with --agents; Claude + Grok):\n' >&2
  printf '  Claude:  ~/.claude/agents/<leaf>.md\n' >&2
  printf '  Grok:    ~/.grok/agents/<leaf>.md\n' >&2
  printf '  Codex/Hermes: skipped (no agent install)\n' >&2
  printf '\n' >&2
  printf 'Sources: skills/<name> under this repo, or --from DIR.\n' >&2
  printf 'Real file/directory destinations are never overwritten (even with --relink).\n' >&2
  printf 'With --relink, only wrong or dangling symlinks are replaced.\n' >&2
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

if [[ "$host_flag_set" -eq 0 ]]; then
  install_claude=1
  install_grok=1
  install_codex=1
  install_hermes=1
fi

# install_one LABEL SKILLS_DIR LEAF SOURCE_DIR
# Creates SKILLS_DIR/LEAF -> SOURCE_DIR when missing.
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

install_skill_to_hosts() {
  local leaf="$1"
  local source_dir="$2"

  if [[ "$install_claude" -eq 1 ]]; then
    install_one "Claude Code / $leaf" "$HOME/.claude/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_grok" -eq 1 ]]; then
    install_one "Grok / $leaf" "$HOME/.grok/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_codex" -eq 1 ]]; then
    install_one "Codex / $leaf" "$HOME/.codex/skills" "$leaf" "$source_dir"
  fi
  if [[ "$install_hermes" -eq 1 ]]; then
    # Peer layout for software-development skills under Hermes skillhub / user-local hub.
    # Host path ~/.hermes is typically bind-mounted to /opt/data in the hermes container.
    install_one "Hermes skillhub / $leaf" "$HOME/.hermes/skills/software-development" "$leaf" "$source_dir"
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
  install_skill_to_hosts "$leaf" "$source_dir"
  if [[ "$install_agents" -eq 1 ]]; then
    install_agent_to_hosts "$leaf"
  fi
done
