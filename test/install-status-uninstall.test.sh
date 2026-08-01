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
set +e
out3u="$("$install_sh" --uninstall --skill skill-interop --hermes-only 2>&1)"
rc3u=$?
set -e
[[ "$rc3u" -eq 3 ]] || fail "S3 uninstall want exit 3 got $rc3u: $out3u"
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
set +e
out7u="$("$install_sh" --uninstall --skill skill-interop --claude-only 2>&1)"
rc7u=$?
set -e
[[ "$rc7u" -eq 3 ]] || fail "S7 uninstall want exit 3 got $rc7u: $out7u"
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

printf 'install-status-uninstall.test.sh: PASS S1–S8 (continued)\n'

# --- S9–S13: marker-invalid foreign (byte-identical under install/status/uninstall) ---
# Shared setup: foreign tree + invalid marker for hermes skill-interop leaf.

marker_invalid_case() {
  local case_id="$1"
  local marker_body="$2"
  local expect_snip="$3"
  fresh_home "mi-$case_id"
  local dest="$HOME/.hermes/skills/software-development/skill-interop"
  local mdir="$HOME/.hermes/skills/software-development/.skill-craft"
  mkdir -p "$dest" "$mdir"
  printf 'foreign-body-%s\n' "$case_id" >"$dest/SKILL.md"
  printf 'keep-me\n' >"$dest/extra-$case_id.txt"
  printf '%s\n' "$marker_body" >"$mdir/skill-interop.json"
  local before after
  before="$(find "$dest" -type f -print0 | sort -z | xargs -0 shasum 2>/dev/null | shasum | awk '{print $1}')"
  # also fingerprint marker
  local mbefore mafter
  mbefore="$(shasum "$mdir/skill-interop.json" | awk '{print $1}')"

  out_st="$("$install_sh" --status --skill skill-interop --hermes-only 2>&1)" || fail "S$case_id status: $out_st"
  printf '%s\n' "$out_st" | grep -q 'state=foreign' || fail "S$case_id status foreign: $out_st"

  set +e
  out_in="$("$install_sh" --skill skill-interop --hermes-only 2>&1)"
  rc_in=$?
  set -e
  [[ "$rc_in" -eq 3 ]] || fail "S$case_id install want exit 3 got $rc_in: $out_in"
  printf '%s\n' "$out_in" | grep -qi 'foreign\|Skipped' || fail "S$case_id install skip: $out_in"

  set +e
  out_un="$("$install_sh" --uninstall --skill skill-interop --hermes-only 2>&1)"
  rc_un=$?
  set -e
  [[ "$rc_un" -eq 3 ]] || fail "S$case_id uninstall want exit 3 got $rc_un: $out_un"
  printf '%s\n' "$out_un" | grep -q 'Skipped uninstall (not owned)' || fail "S$case_id uninstall skip: $out_un"

  [[ -f "$dest/SKILL.md" ]] || fail "S$case_id dest deleted"
  [[ "$(cat "$dest/SKILL.md")" == "foreign-body-$case_id" ]] || fail "S$case_id content changed"
  [[ -f "$dest/extra-$case_id.txt" ]] || fail "S$case_id extra deleted"
  after="$(find "$dest" -type f -print0 | sort -z | xargs -0 shasum 2>/dev/null | shasum | awk '{print $1}')"
  [[ "$before" == "$after" ]] || fail "S$case_id dest not byte-identical"
  mafter="$(shasum "$mdir/skill-interop.json" | awk '{print $1}')"
  [[ "$mbefore" == "$mafter" ]] || fail "S$case_id marker mutated"
  pass "S$case_id $expect_snip"
}

pass() { printf '  ok %s\n' "$*"; }

# S9: malformed JSON marker
marker_invalid_case 9 'not-json{' 'malformed JSON'

# S10: schema != 2
marker_invalid_case 10 '{"schema":1,"leaf":"skill-interop","mode":"copy","source":"'"$source_interop"'","skill_version":""}' 'schema!=2'

# S11: wrong leaf
marker_invalid_case 11 '{"schema":2,"leaf":"other-skill","mode":"copy","source":"'"$source_interop"'","skill_version":""}' 'wrong leaf'

# S12: mode != copy
marker_invalid_case 12 '{"schema":2,"leaf":"skill-interop","mode":"symlink","source":"'"$source_interop"'","skill_version":""}' 'mode!=copy'

# S13: non-canonical / wrong source path
marker_invalid_case 13 '{"schema":2,"leaf":"skill-interop","mode":"copy","source":"/nonexistent/wrong/source/path","skill_version":""}' 'wrong source'

# S14: uninstall when absent → exit 4
fresh_home s14
set +e
out14="$("$install_sh" --uninstall --skill skill-interop --claude-only 2>&1)"
rc14=$?
set -e
[[ "$rc14" -eq 4 ]] || fail "S14 want exit 4 got $rc14: $out14"
printf '%s\n' "$out14" | grep -q 'Already absent' || fail "S14 message: $out14"
pass "S14 absent uninstall exit 4"

printf 'install-status-uninstall.test.sh: PASS S1–S14\n'
