#!/usr/bin/env bash
# Phase 5 mechanical hygiene for skill-interop package.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
si="$root/skills/skill-interop"

fail() {
  printf 'skill-interop-hygiene.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

# skill-interop has prompts/review-skill.prompt.md
[[ -f "$si/prompts/review-skill.prompt.md" ]] || fail "missing prompts/review-skill.prompt.md"

# create-template files exist
[[ -f "$si/references/create-template/SKILL.md.tmpl" ]] || fail "missing create-template SKILL.md.tmpl"
[[ -f "$si/references/create-template/prompts/main.prompt.md.tmpl" ]] || fail "missing create-template main.prompt.md.tmpl"
[[ -f "$si/references/create-template/references/host-matrix.md.tmpl" ]] || fail "missing create-template host-matrix.md.tmpl"

# scaffold-skill.sh is executable
scaffold="$si/scripts/scaffold-skill.sh"
[[ -f "$scaffold" ]] || fail "missing scaffold-skill.sh"
[[ -x "$scaffold" ]] || fail "scaffold-skill.sh not executable"

# anti-patterns.md lists host-only / divergent / silent fallback
ap="$si/references/anti-patterns.md"
[[ -f "$ap" ]] || fail "missing anti-patterns.md"
grep -qi 'host-only' "$ap" || fail "anti-patterns.md missing host-only"
grep -qi 'divergent' "$ap" || fail "anti-patterns.md missing divergent"
grep -qiE 'silent fallback|Silent fallback' "$ap" || fail "anti-patterns.md missing silent fallback"

# host-paths.md mentions all five hosts
hp="$si/references/host-paths.md"
[[ -f "$hp" ]] || fail "missing host-paths.md"
grep -q '\.claude' "$hp" || fail "host-paths.md missing .claude"
grep -q '\.grok' "$hp" || fail "host-paths.md missing .grok"
grep -q '\.codex' "$hp" || fail "host-paths.md missing .codex"
grep -q '\.cursor' "$hp" || fail "host-paths.md missing .cursor"
grep -q '\.hermes' "$hp" || fail "host-paths.md missing .hermes"

# No model pin strings in create-template prompts
if grep -qiE 'sonnet|opus|gpt-' "$si/references/create-template/prompts/"*.tmpl 2>/dev/null; then
  fail "create-template prompts must not pin model names (sonnet|opus|gpt-)"
fi
if grep -qiE 'sonnet|opus|gpt-' "$si/references/create-template/SKILL.md.tmpl" 2>/dev/null; then
  fail "create-template SKILL.md.tmpl must not pin model names"
fi

# Default DevLoop package must be skills/devloop (Hermes engine leaf is foreign)
if [[ ! -d "$root/skills/devloop" ]]; then
  fail "package must be skills/devloop"
fi
if [[ -d "$root/skills/devloop-run" ]]; then
  fail "leftover skills/devloop-run (package is skills/devloop)"
fi
grep -q 'skills/devloop' "$root/docs/ARCHITECTURE.md" || fail "ARCHITECTURE should mention skills/devloop"

printf 'skill-interop-hygiene.test.sh: PASS (prompts, templates, scaffold, anti-patterns, host-paths, no pins)\n'
exit 0
