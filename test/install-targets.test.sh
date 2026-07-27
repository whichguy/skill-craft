#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_sh="$root/install.sh"
source_interop="$root/skills/skill-interop"
fail() { printf 'install-targets.test.sh: FAIL %s\n' "$*" >&2; exit 1; }
assert_symlink() {
  local path="$1" expected="$2"
  [[ -L "$path" ]] || fail "expected symlink $path"
  local got; got="$(readlink "$path")"
  [[ "$got" == "$expected" ]] || fail "symlink $path -> $got want $expected"
}
tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-install.XXXXXX")"
trap 'rm -rf "$tmpdir"' EXIT
export HOME="$tmpdir/home"
mkdir -p "$HOME"
out="$("$install_sh" --skill skill-interop 2>&1)" || fail "install failed: $out"
assert_symlink "$HOME/.claude/skills/skill-interop" "$source_interop"
assert_symlink "$HOME/.grok/skills/skill-interop" "$source_interop"
assert_symlink "$HOME/.codex/skills/skill-interop" "$source_interop"
assert_symlink "$HOME/.hermes/skills/software-development/skill-interop" "$source_interop"
# relink dangling
rm -f "$HOME/.claude/skills/skill-interop"
ln -s /nonexistent/dangling "$HOME/.claude/skills/skill-interop"
"$install_sh" --claude-only --skill skill-interop --relink >/dev/null
assert_symlink "$HOME/.claude/skills/skill-interop" "$source_interop"
printf 'install-targets.test.sh: PASS\n'
