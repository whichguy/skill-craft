#!/usr/bin/env bash
# Hermetic install.sh coverage for skill-craft: four hosts × repo skills, flags, skip-if-exists, dry-run, --relink.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_sh="$root/install.sh"
source_interop="$root/skills/skill-interop"

fail() {
  printf 'install-targets.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

assert_symlink() {
  local path="$1"
  local expected="$2"
  [[ -L "$path" ]] || fail "expected symlink at $path"
  local got
  got="$(readlink "$path")"
  [[ "$got" == "$expected" ]] || fail "symlink $path -> $got (want $expected)"
}

assert_absent() {
  local path="$1"
  [[ ! -e "$path" && ! -L "$path" ]] || fail "expected absent: $path"
}

assert_hermes_copy() {
  local leaf="$1"
  local source="$2"
  local dest="$HOME/.hermes/skills/software-development/$leaf"
  local marker="$HOME/.hermes/skills/software-development/.skill-craft/$leaf.json"
  [[ -d "$dest" ]] || fail "expected Hermes real directory at $dest"
  [[ ! -L "$dest" ]] || fail "Hermes dest must not be a symlink: $dest"
  [[ -f "$dest/SKILL.md" ]] || fail "Hermes copy missing SKILL.md at $dest"
  [[ -f "$marker" ]] || fail "Hermes provenance marker missing: $marker"
  grep -q '"mode":"copy"' "$marker" || fail "marker missing mode=copy: $marker"
  diff -rq "$source" "$dest" >/dev/null || fail "Hermes copy differs from source: $dest"
}

assert_all_hosts() {
  local leaf="$1"
  local source="$2"
  assert_symlink "$HOME/.claude/skills/$leaf" "$source"
  assert_symlink "$HOME/.grok/skills/$leaf" "$source"
  assert_symlink "$HOME/.codex/skills/$leaf" "$source"
  assert_hermes_copy "$leaf" "$source"
}

assert_no_hosts() {
  local leaf="$1"
  assert_absent "$HOME/.claude/skills/$leaf"
  assert_absent "$HOME/.grok/skills/$leaf"
  assert_absent "$HOME/.codex/skills/$leaf"
  assert_absent "$HOME/.hermes/skills/software-development/$leaf"
}

fresh_home() {
  export HOME="$tmpdir/home-$1"
  mkdir -p "$HOME"
}

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-install.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

[[ -x "$install_sh" ]] || fail "install.sh not executable: $install_sh"
[[ -f "$source_interop/SKILL.md" ]] || fail "missing skills/skill-interop/SKILL.md"

# ---------------------------------------------------------------------------
# I1: Fresh HOME, no flags → all hosts × all skills (at least skill-interop)
# ---------------------------------------------------------------------------
fresh_home i1
out="$("$install_sh" 2>&1)" || fail "I1 install.sh failed on fresh home: $out"
assert_all_hosts "skill-interop" "$source_interop"
printf '%s\n' "$out" | grep -q 'Claude Code' || fail "I1 stdout missing Claude install line"
printf '%s\n' "$out" | grep -q 'Grok' || fail "I1 stdout missing Grok install line"
printf '%s\n' "$out" | grep -q 'Codex' || fail "I1 stdout missing Codex install line"
printf '%s\n' "$out" | grep -q 'Hermes' || fail "I1 stdout missing Hermes install line"
# Must NOT install product leaves that are not in this monorepo
assert_no_hosts "backchain"

# ---------------------------------------------------------------------------
# I2: Idempotent re-run → "already installed"
# ---------------------------------------------------------------------------
out2="$("$install_sh" 2>&1)" || fail "I2 install.sh re-run failed: $out2"
printf '%s\n' "$out2" | grep -q 'Already installed' || fail "I2 re-run should report already installed"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I3: Foreign tree at dest → skipped, foreign SKILL.md preserved
# ---------------------------------------------------------------------------
fresh_home i3
mkdir -p "$HOME/.claude/skills/skill-interop"
printf 'foreign\n' >"$HOME/.claude/skills/skill-interop/SKILL.md"
out3="$("$install_sh" --claude-only --skill skill-interop 2>&1)" || fail "I3 over foreign failed: $out3"
printf '%s\n' "$out3" | grep -q 'Skipped existing path' || fail "I3 foreign path should be skipped"
[[ -f "$HOME/.claude/skills/skill-interop/SKILL.md" ]] || fail "I3 foreign tree must remain"
got_foreign="$(cat "$HOME/.claude/skills/skill-interop/SKILL.md")"
[[ "$got_foreign" == "foreign" ]] || fail "I3 foreign SKILL.md content changed"

# ---------------------------------------------------------------------------
# I4: --skill skill-interop → only skill-interop leaves
# ---------------------------------------------------------------------------
fresh_home i4
out4="$("$install_sh" --skill skill-interop 2>&1)" || fail "I4 failed: $out4"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I5: --skill all → same as default for current monorepo
# ---------------------------------------------------------------------------
fresh_home i5
out5="$("$install_sh" --skill all 2>&1)" || fail "I5 failed: $out5"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I6: --claude-only → only ~/.claude/skills/*
# ---------------------------------------------------------------------------
fresh_home i6
out6="$("$install_sh" --claude-only --skill skill-interop 2>&1)" || fail "I6 failed: $out6"
assert_symlink "$HOME/.claude/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I7: --grok-only
# ---------------------------------------------------------------------------
fresh_home i7
out7="$("$install_sh" --grok-only --skill skill-interop 2>&1)" || fail "I7 failed: $out7"
assert_symlink "$HOME/.grok/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I8: --codex-only
# ---------------------------------------------------------------------------
fresh_home i8
out8="$("$install_sh" --codex-only --skill skill-interop 2>&1)" || fail "I8 failed: $out8"
assert_symlink "$HOME/.codex/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I9: --hermes-only → materialized copy (not symlink)
# ---------------------------------------------------------------------------
fresh_home i9
out9="$("$install_sh" --hermes-only --skill skill-interop 2>&1)" || fail "I9 failed: $out9"
assert_hermes_copy "skill-interop" "$source_interop"
printf '%s\n' "$out9" | grep -q '(copy)' || fail "I9 should report copy install: $out9"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"

# ---------------------------------------------------------------------------
# I10: --dry-run creates no files
# ---------------------------------------------------------------------------
fresh_home i10
out10="$("$install_sh" --dry-run --skill skill-interop 2>&1)" || fail "I10 dry-run failed: $out10"
printf '%s\n' "$out10" | grep -q 'Would install' || fail "I10 dry-run should print Would install"
assert_no_hosts "skill-interop"
[[ ! -d "$HOME/.claude" ]] || fail "I10 dry-run must not create ~/.claude"
[[ ! -d "$HOME/.grok" ]] || fail "I10 dry-run must not create ~/.grok"
[[ ! -d "$HOME/.codex" ]] || fail "I10 dry-run must not create ~/.codex"
[[ ! -d "$HOME/.hermes" ]] || fail "I10 dry-run must not create ~/.hermes"

# ---------------------------------------------------------------------------
# I11: dangling symlink without --relink → skipped
# ---------------------------------------------------------------------------
fresh_home i11
mkdir -p "$HOME/.claude/skills"
ln -s "/nonexistent/dangling-target-i11" "$HOME/.claude/skills/skill-interop"
out11="$("$install_sh" --claude-only --skill skill-interop 2>&1)" || fail "I11 failed: $out11"
printf '%s\n' "$out11" | grep -q 'Skipped existing path' || fail "I11 dangling without --relink should be skipped: $out11"
got11="$(readlink "$HOME/.claude/skills/skill-interop")"
[[ "$got11" == "/nonexistent/dangling-target-i11" ]] || fail "I11 dangling target must remain without --relink (got $got11)"

# ---------------------------------------------------------------------------
# I12: dangling + --relink → fixed
# ---------------------------------------------------------------------------
fresh_home i12
mkdir -p "$HOME/.claude/skills"
ln -s "/nonexistent/dangling-target-i12" "$HOME/.claude/skills/skill-interop"
out12="$("$install_sh" --claude-only --skill skill-interop --relink 2>&1)" || fail "I12 failed: $out12"
printf '%s\n' "$out12" | grep -q 'Relinked' || fail "I12 should report Relinked: $out12"
assert_symlink "$HOME/.claude/skills/skill-interop" "$source_interop"
rm -f "$HOME/.claude/skills/skill-interop"
ln -s "/nonexistent/other" "$HOME/.claude/skills/skill-interop"
out12d="$("$install_sh" --claude-only --skill skill-interop --relink --dry-run 2>&1)" || fail "I12 dry-run failed: $out12d"
printf '%s\n' "$out12d" | grep -q 'Would relink' || fail "I12 dry-run should print Would relink: $out12d"
got12d="$(readlink "$HOME/.claude/skills/skill-interop")"
[[ "$got12d" == "/nonexistent/other" ]] || fail "I12 dry-run must not rewrite symlink"

# ---------------------------------------------------------------------------
# I13: foreign real directory + --relink → still skipped
# ---------------------------------------------------------------------------
fresh_home i13
mkdir -p "$HOME/.claude/skills/skill-interop"
printf 'foreign-relink\n' >"$HOME/.claude/skills/skill-interop/SKILL.md"
out13="$("$install_sh" --claude-only --skill skill-interop --relink 2>&1)" || fail "I13 failed: $out13"
printf '%s\n' "$out13" | grep -q 'Skipped existing path' || fail "I13 foreign real dir must still be skipped: $out13"
[[ -d "$HOME/.claude/skills/skill-interop" ]] || fail "I13 foreign dir must remain a directory"
[[ ! -L "$HOME/.claude/skills/skill-interop" ]] || fail "I13 must not convert foreign dir to symlink"
got13="$(cat "$HOME/.claude/skills/skill-interop/SKILL.md")"
[[ "$got13" == "foreign-relink" ]] || fail "I13 foreign SKILL.md content changed"

# ---------------------------------------------------------------------------
# I14: --agents installs thin agent card for Claude + Grok
# ---------------------------------------------------------------------------
fresh_home i14
agent_src="$root/agents/skill-interop.md"
[[ -f "$agent_src" ]] || fail "I14 missing agents/skill-interop.md"
out14="$("$install_sh" --skill skill-interop --agents 2>&1)" || fail "I14 failed: $out14"
assert_symlink "$HOME/.claude/agents/skill-interop.md" "$agent_src"
assert_symlink "$HOME/.grok/agents/skill-interop.md" "$agent_src"
assert_absent "$HOME/.codex/agents/skill-interop.md"

# --help exits 0
"$install_sh" --help >/dev/null

# Invalid flag → exit 64
set +e
"$install_sh" --not-a-flag >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "invalid flag should exit 64 (got $rc)"

printf 'install-targets.test.sh: PASS I1–I14 (skill-craft install, 4 hosts, flags, dry-run, skip-if-exists, --relink, --agents)\n'
