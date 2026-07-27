#!/usr/bin/env bash
# Hermetic coverage for skills/skill-interop/scripts/scaffold-skill.sh
# Cases S1–S6 per skill-interop Phase 3.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
scaffold="$root/skills/skill-interop/scripts/scaffold-skill.sh"

fail() {
  printf 'scaffold-skill.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

[[ -x "$scaffold" ]] || fail "scaffold script not executable: $scaffold"

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-scaffold.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

out="$tmpdir/skills"

# ---------------------------------------------------------------------------
# S1: scaffold hello-portable → tree exists; name in frontmatter
# ---------------------------------------------------------------------------
"$scaffold" --name hello-portable --out "$out" \
  --description "Use when testing the hello-portable portable skill." \
  --goals "Demo goals for hello-portable." \
  >/dev/null || fail "S1 scaffold failed"

dest="$out/hello-portable"
[[ -f "$dest/SKILL.md" ]] || fail "S1 missing SKILL.md"
[[ -f "$dest/prompts/main.prompt.md" ]] || fail "S1 missing main.prompt.md"
[[ -f "$dest/references/host-matrix.md" ]] || fail "S1 missing host-matrix.md"
grep -q '^name: hello-portable$' "$dest/SKILL.md" || fail "S1 frontmatter name missing"

# ---------------------------------------------------------------------------
# S2: invalid name Hello_World → exit 3
# ---------------------------------------------------------------------------
set +e
"$scaffold" --name Hello_World --out "$out" >/dev/null 2>&1
ec=$?
set -e
[[ "$ec" -eq 3 ]] || fail "S2 expected exit 3 for invalid name, got $ec"

# ---------------------------------------------------------------------------
# S3: dest exists without --force → exit 4
# ---------------------------------------------------------------------------
set +e
"$scaffold" --name hello-portable --out "$out" >/dev/null 2>&1
ec=$?
set -e
[[ "$ec" -eq 4 ]] || fail "S3 expected exit 4 when dest exists, got $ec"

# ---------------------------------------------------------------------------
# S4: SKILL has sections Triggers, Procedure (case-insensitive)
# ---------------------------------------------------------------------------
grep -qi 'Triggers' "$dest/SKILL.md" || fail "S4 missing Triggers section"
grep -qi 'Procedure' "$dest/SKILL.md" || fail "S4 missing Procedure section"

# ---------------------------------------------------------------------------
# S5: main.prompt.md has {{INPUT}} (or similar); no model pins
# ---------------------------------------------------------------------------
prompt="$dest/prompts/main.prompt.md"
grep -qE '\{\{INPUT\}\}|\{\{input\}\}' "$prompt" || fail "S5 prompt missing {{INPUT}}"
if grep -qiE 'sonnet|opus|gpt-' "$prompt"; then
  fail "S5 prompt must not pin model names (sonnet/opus/gpt-)"
fi

# ---------------------------------------------------------------------------
# S6: re-scaffold with --force succeeds
# ---------------------------------------------------------------------------
"$scaffold" --name hello-portable --out "$out" --force \
  --description "Use when re-scaffolded hello-portable." \
  >/dev/null || fail "S6 --force re-scaffold failed"
grep -q '^name: hello-portable$' "$dest/SKILL.md" || fail "S6 name missing after --force"
grep -q 're-scaffolded' "$dest/SKILL.md" || fail "S6 description not updated after --force"

printf 'scaffold-skill.test.sh: PASS S1–S6\n'
exit 0
