#!/usr/bin/env bash
# scaffold-skill.sh — create a prompt-only portable skill package from templates.
#
# Exit codes:
#   0  ok
#   2  usage / missing required args
#   3  name invalid (^ [a-z0-9]([a-z0-9-]*[a-z0-9])?$ , length 2-64)
#   4  dest exists without --force
#   5  template dir missing or incomplete
set -euo pipefail

usage() {
  printf 'Usage: %s --name NAME --out DIR [--description TEXT] [--force] [--goals TEXT]\n' "${0##*/}" >&2
  printf '\n' >&2
  printf 'Creates DIR/NAME/{SKILL.md,prompts/main.prompt.md,references/host-matrix.md}\n' >&2
  printf 'from templates under skills/skill-interop/references/create-template/\n' >&2
  printf '\n' >&2
  printf 'Exit codes: 0 ok · 2 usage · 3 name invalid · 4 dest exists · 5 template missing\n' >&2
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
template_dir="$(cd "$script_dir/../references/create-template" && pwd -P)"

name=""
out_dir=""
description=""
goals=""
force=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --name)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --name\n' >&2
        usage
        exit 2
      fi
      name="$2"
      shift 2
      ;;
    --out)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --out\n' >&2
        usage
        exit 2
      fi
      out_dir="$2"
      shift 2
      ;;
    --description)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --description\n' >&2
        usage
        exit 2
      fi
      description="$2"
      shift 2
      ;;
    --goals)
      if [[ $# -lt 2 ]]; then
        printf 'Missing value for --goals\n' >&2
        usage
        exit 2
      fi
      goals="$2"
      shift 2
      ;;
    --force)
      force=1
      shift
      ;;
    *)
      printf 'Unknown flag: %s\n' "$1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$name" || -z "$out_dir" ]]; then
  printf 'Required: --name and --out\n' >&2
  usage
  exit 2
fi

# Name: lowercase alnum + hyphens, 2-64 chars, no leading/trailing hyphen
if ! printf '%s' "$name" | python3 -c '
import re, sys
n = sys.stdin.read()
ok = bool(re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?", n)) and 2 <= len(n) <= 64
sys.exit(0 if ok else 1)
'; then
  printf 'Invalid name %q (want ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$, length 2-64)\n' "$name" >&2
  exit 3
fi

if [[ -z "$description" ]]; then
  description="Use when running the {{NAME}} portable skill workflow across hosts."
fi

if [[ -z "$goals" ]]; then
  goals="Portable prompt-only workflow for {{NAME}} across Grok, Claude Code, Codex, and Hermes."
fi

for req in \
  "$template_dir/SKILL.md.tmpl" \
  "$template_dir/prompts/main.prompt.md.tmpl" \
  "$template_dir/references/host-matrix.md.tmpl"
do
  if [[ ! -f "$req" ]]; then
    printf 'Template missing: %s\n' "$req" >&2
    exit 5
  fi
done

dest="$out_dir/$name"

if [[ -e "$dest" || -L "$dest" ]]; then
  if [[ "$force" -ne 1 ]]; then
    printf 'Destination exists (pass --force to overwrite): %s\n' "$dest" >&2
    exit 4
  fi
  rm -rf "$dest"
fi

mkdir -p "$dest/prompts" "$dest/references"

# Safe {{TOKEN}} substitution via python3 (stdlib only).
# Per-file token sets so documented placeholders (e.g. {{INPUT}} / {{GOALS}} in
# SKILL procedure prose) stay literal until the operator fills them at runtime.
# {{NAME}} is always expanded last so defaults like "… the {{NAME}} portable …"
# inside DESCRIPTION resolve correctly.
render() {
  local src="$1"
  local dst="$2"
  shift 2
  NAME="$name" DESCRIPTION="$description" GOALS_SUMMARY="$goals" GOALS="$goals" \
    python3 - "$src" "$dst" "$@" <<'PY'
import os, sys

src, dst = sys.argv[1], sys.argv[2]
token_names = sys.argv[3:]
env_map = {
    "NAME": "NAME",
    "DESCRIPTION": "DESCRIPTION",
    "GOALS_SUMMARY": "GOALS_SUMMARY",
    "GOALS": "GOALS",
}
text = open(src, encoding="utf-8").read()
# Non-NAME tokens first (longest first for safety).
others = sorted(
    (t for t in token_names if t != "NAME"),
    key=len,
    reverse=True,
)
for t in others:
    env_key = env_map.get(t)
    if env_key is None:
        raise SystemExit(f"unknown token {t}")
    text = text.replace("{{" + t + "}}", os.environ[env_key])
# Expand NAME last (listed or residual inside substituted values).
if "NAME" in token_names or "{{NAME}}" in text:
    text = text.replace("{{NAME}}", os.environ["NAME"])
open(dst, "w", encoding="utf-8").write(text)
PY
}

render "$template_dir/SKILL.md.tmpl" "$dest/SKILL.md" \
  NAME DESCRIPTION GOALS_SUMMARY
render "$template_dir/prompts/main.prompt.md.tmpl" "$dest/prompts/main.prompt.md" \
  NAME GOALS
render "$template_dir/references/host-matrix.md.tmpl" "$dest/references/host-matrix.md" \
  NAME

printf 'Scaffolded %s\n' "$dest"
printf '  SKILL.md\n'
printf '  prompts/main.prompt.md\n'
printf '  references/host-matrix.md\n'
exit 0
