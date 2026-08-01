#!/usr/bin/env bash
# Arbitrary --skill leaf + --from DIR install coverage (skill-craft).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_sh="$root/install.sh"
source_interop="$root/skills/skill-interop"
fixture_sample="$root/test/fixtures/sample-skill"

fail() {
  printf 'install-arbitrary-skill.test.sh: FAIL %s\n' "$*" >&2
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

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-install-arb.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

[[ -f "$fixture_sample/SKILL.md" ]] || fail "missing frozen fixture: $fixture_sample/SKILL.md"

# ---------------------------------------------------------------------------
# E1: --from fixture sample-skill → all 4 hosts get sample-skill symlink
# ---------------------------------------------------------------------------
fresh_home e1
fixture_abs="$(cd "$fixture_sample" && pwd -P)"
out1="$("$install_sh" --from "$fixture_sample" 2>&1)" || fail "E1 --from failed: $out1"
assert_all_hosts "sample-skill" "$fixture_abs"
assert_no_hosts "skill-interop"
printf '%s\n' "$out1" | grep -q 'sample-skill' || fail "E1 stdout should mention sample-skill"

# ---------------------------------------------------------------------------
# E2: --skill nonexistent → exit non-zero (missing SKILL.md)
# ---------------------------------------------------------------------------
fresh_home e2
set +e
out2="$("$install_sh" --skill nonexistent-skill-xyz 2>&1)"
rc2=$?
set -e
[[ "$rc2" -ne 0 ]] || fail "E2 --skill nonexistent should fail (got exit 0)"
printf '%s\n' "$out2" | grep -qi 'SKILL.md\|missing' || fail "E2 should mention missing SKILL.md: $out2"
assert_no_hosts "nonexistent-skill-xyz"

# ---------------------------------------------------------------------------
# E3: --skill all installs repo skills (skill-interop), not fixture
# ---------------------------------------------------------------------------
fresh_home e3
out3="$("$install_sh" --skill all 2>&1)" || fail "E3 --skill all failed: $out3"
assert_all_hosts "skill-interop" "$source_interop"
assert_no_hosts "sample-skill"

# ---------------------------------------------------------------------------
# E4: --skill and --from together → usage error 64
# ---------------------------------------------------------------------------
fresh_home e4
set +e
"$install_sh" --skill skill-interop --from "$fixture_sample" >/dev/null 2>&1
rc4=$?
set -e
[[ "$rc4" -eq 64 ]] || fail "E4 combined --skill/--from should exit 64 (got $rc4)"

# ---------------------------------------------------------------------------
# E5: --from installs only that leaf (not all repo skills)
# ---------------------------------------------------------------------------
fresh_home e5
fixture_abs="$(cd "$fixture_sample" && pwd -P)"
out5="$("$install_sh" --from "$fixture_abs" --claude-only 2>&1)" || fail "E5 failed: $out5"
assert_symlink "$HOME/.claude/skills/sample-skill" "$fixture_abs"
assert_absent "$HOME/.claude/skills/skill-interop"

printf 'install-arbitrary-skill.test.sh: PASS E1–E5 (--from, --skill all, exclusivity)\n'
