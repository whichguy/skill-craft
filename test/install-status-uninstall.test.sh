#!/usr/bin/env bash
# --status and --uninstall for owned vs foreign installs.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_sh="$root/install.sh"
source_interop="$root/skills/skill-interop"

fail() {
  printf 'install-status-uninstall.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

fresh_home() {
  export HOME="$tmpdir/home-$1"
  mkdir -p "$HOME"
}

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-status.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

[[ -x "$install_sh" ]] || fail "install.sh not executable"

# S1: status absent
fresh_home s1
out1="$("$install_sh" --status --skill skill-interop --claude-only 2>&1)" || fail "S1: $out1"
printf '%s\n' "$out1" | grep -q 'state=absent' || fail "S1 absent: $out1"

# S2: install then status owned
fresh_home s2
"$install_sh" --skill skill-interop >/dev/null
out2="$("$install_sh" --status --skill skill-interop 2>&1)" || fail "S2: $out2"
printf '%s\n' "$out2" | grep -q 'Claude Code' || fail "S2 missing Claude"
printf '%s\n' "$out2" | grep -q 'state=symlink-owned' || fail "S2 symlink-owned: $out2"
printf '%s\n' "$out2" | grep -q 'state=copy-owned' || fail "S2 copy-owned Hermes: $out2"

# S3: foreign Hermes not uninstalled
fresh_home s3
mkdir -p "$HOME/.hermes/skills/software-development/skill-interop"
printf 'foreign\n' >"$HOME/.hermes/skills/software-development/skill-interop/SKILL.md"
out3="$("$install_sh" --status --skill skill-interop --hermes-only 2>&1)" || fail "S3 status: $out3"
printf '%s\n' "$out3" | grep -q 'state=foreign' || fail "S3 foreign: $out3"
out3u="$("$install_sh" --uninstall --skill skill-interop --hermes-only 2>&1)" || fail "S3 uninstall: $out3u"
printf '%s\n' "$out3u" | grep -q 'Skipped uninstall (not owned)' || fail "S3 skip: $out3u"
[[ -f "$HOME/.hermes/skills/software-development/skill-interop/SKILL.md" ]] || fail "S3 foreign deleted"
[[ "$(cat "$HOME/.hermes/skills/software-development/skill-interop/SKILL.md")" == "foreign" ]] || fail "S3 content"

# S4: uninstall owned symlink + copy
fresh_home s4
"$install_sh" --skill skill-interop >/dev/null
out4="$("$install_sh" --uninstall --skill skill-interop 2>&1)" || fail "S4: $out4"
printf '%s\n' "$out4" | grep -q 'Uninstalled symlink' || fail "S4 symlink: $out4"
printf '%s\n' "$out4" | grep -q 'Uninstalled copy' || fail "S4 copy: $out4"
[[ ! -e "$HOME/.claude/skills/skill-interop" ]] || fail "S4 claude remains"
[[ ! -e "$HOME/.hermes/skills/software-development/skill-interop" ]] || fail "S4 hermes remains"
[[ ! -f "$HOME/.hermes/skills/software-development/.skill-craft/skill-interop.json" ]] || fail "S4 marker remains"

# S5: dry-run uninstall no mutate
fresh_home s5
"$install_sh" --skill skill-interop --claude-only >/dev/null
out5="$("$install_sh" --uninstall --skill skill-interop --claude-only --dry-run 2>&1)" || fail "S5: $out5"
printf '%s\n' "$out5" | grep -q 'Would uninstall symlink' || fail "S5 would: $out5"
[[ -L "$HOME/.claude/skills/skill-interop" ]] || fail "S5 dry-run removed"

# S6: status/uninstall exclusive
set +e
"$install_sh" --status --uninstall --skill skill-interop >/dev/null 2>&1
rc6=$?
set -e
[[ "$rc6" -eq 64 ]] || fail "S6 want exit 64 got $rc6"

# S7: status symlink-wrong (dangling/wrong target) + uninstall refuses to own it
fresh_home s7
mkdir -p "$HOME/.claude/skills"
ln -s "/nonexistent/wrong-target-s7" "$HOME/.claude/skills/skill-interop"
out7="$("$install_sh" --status --skill skill-interop --claude-only 2>&1)" || fail "S7 status: $out7"
printf '%s\n' "$out7" | grep -q 'state=symlink-wrong' || fail "S7 symlink-wrong: $out7"
out7u="$("$install_sh" --uninstall --skill skill-interop --claude-only 2>&1)" || fail "S7 uninstall: $out7u"
printf '%s\n' "$out7u" | grep -q 'Skipped uninstall (not owned)' || fail "S7 skip: $out7u"
[[ -L "$HOME/.claude/skills/skill-interop" ]] || fail "S7 wrong symlink must remain"

# S8: status copy-owned-stale after managed install then dest content drift
fresh_home s8
"$install_sh" --skill skill-interop --hermes-only >/dev/null
printf 'drift-s8\n' >>"$HOME/.hermes/skills/software-development/skill-interop/SKILL.md"
out8="$("$install_sh" --status --skill skill-interop --hermes-only 2>&1)" || fail "S8 status: $out8"
printf '%s\n' "$out8" | grep -q 'state=copy-owned-stale' || fail "S8 stale: $out8"
# uninstall still owns stale managed copy
out8u="$("$install_sh" --uninstall --skill skill-interop --hermes-only 2>&1)" || fail "S8 uninstall: $out8u"
printf '%s\n' "$out8u" | grep -q 'Uninstalled copy' || fail "S8 uninstall owned: $out8u"
[[ ! -e "$HOME/.hermes/skills/software-development/skill-interop" ]] || fail "S8 dest remains"

printf 'install-status-uninstall.test.sh: PASS S1–S8\n'
