#!/usr/bin/env bash
# Hermes materialize-copy lifecycle + self-containment (skill-craft).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
install_sh="$root/install.sh"
fixture_sample="$root/test/fixtures/sample-skill"

fail() {
  printf 'hermes-binding.test.sh: FAIL %s\n' "$*" >&2
  exit 1
}

fresh_home() {
  export HOME="$tmpdir/home-$1"
  mkdir -p "$HOME"
}

hermes_dest() {
  printf '%s/.hermes/skills/software-development/%s\n' "$HOME" "$1"
}

hermes_marker() {
  printf '%s/.hermes/skills/software-development/.skill-craft/%s.json\n' "$HOME" "$1"
}

assert_copy_tree() {
  local leaf="$1"
  local source="$2"
  local dest
  dest="$(hermes_dest "$leaf")"
  local marker
  marker="$(hermes_marker "$leaf")"
  [[ -d "$dest" ]] || fail "expected real dir $dest"
  [[ ! -L "$dest" ]] || fail "must not be symlink: $dest"
  [[ -f "$marker" ]] || fail "missing marker $marker"
  grep -q '"mode":"copy"' "$marker" || fail "marker mode: $(cat "$marker")"
  grep -q '"schema":2' "$marker" || fail "marker schema 2: $(cat "$marker")"
  # Dest is normalized (no symlinks); compare via install path is ownership+content for non-link packages
  if find "$source" -type l 2>/dev/null | grep -q .; then
    : # source may contain internal links; dest is dereferenced
  else
    diff -rq "$source" "$dest" >/dev/null || fail "diff -rq failed for $dest"
  fi
  [[ -f "$(dirname "$marker")/receipts.jsonl" ]] || fail "missing receipts.jsonl next to marker"
}

# Build a tiny mutable package under tmpdir.
make_pkg() {
  local dir="$1"
  mkdir -p "$dir/scripts"
  {
    printf '%s\n' '---'
    printf '%s\n' 'name: hermes-bind-fixture'
    printf '%s\n' 'description: fixture'
    printf '%s\n' '---'
    printf '%s\n' ''
    printf '%s\n' '# fixture'
  } >"$dir/SKILL.md"
  {
    printf '%s\n' '#!/bin/sh'
    printf '%s\n' 'echo ok'
  } >"$dir/scripts/run.sh"
  chmod +x "$dir/scripts/run.sh"
}

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-hermes-bind.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

[[ -x "$install_sh" ]] || fail "install.sh not executable"
[[ -f "$fixture_sample/SKILL.md" ]] || fail "missing sample-skill fixture"

# Leaf is basename of --from path (not frontmatter name).
pkg="$tmpdir/hermes-bind-fixture"
make_pkg "$pkg"
pkg_abs="$(cd "$pkg" && pwd -P)"
leaf="hermes-bind-fixture"

# ---------------------------------------------------------------------------
# H1: fresh install → real tree + marker
# ---------------------------------------------------------------------------
fresh_home h1
out1="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H1 failed: $out1"
assert_copy_tree "$leaf" "$pkg_abs"
printf '%s\n' "$out1" | grep -q 'Installed' || fail "H1 should report Installed: $out1"
printf '%s\n' "$out1" | grep -q '(copy)' || fail "H1 should mention (copy): $out1"
# marker outside leaf
diff -rq "$pkg_abs" "$(hermes_dest "$leaf")" >/dev/null || fail "H1 leaf must match source exactly (marker outside)"

# ---------------------------------------------------------------------------
# H2: unchanged re-run
# ---------------------------------------------------------------------------
out2="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H2 failed: $out2"
printf '%s\n' "$out2" | grep -q 'Already installed (up to date)' || fail "H2: $out2"
assert_copy_tree "$leaf" "$pkg_abs"

# ---------------------------------------------------------------------------
# H3: source modified → Updated
# ---------------------------------------------------------------------------
printf 'extra\n' >"$pkg_abs/extra.txt"
out3="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H3 failed: $out3"
printf '%s\n' "$out3" | grep -q 'Updated (Hermes' || fail "H3 should Updated: $out3"
[[ -f "$(hermes_dest "$leaf")/extra.txt" ]] || fail "H3 dest missing extra.txt"
assert_copy_tree "$leaf" "$pkg_abs"

# ---------------------------------------------------------------------------
# H4: source file deleted → removed from dest
# ---------------------------------------------------------------------------
rm -f "$pkg_abs/extra.txt"
out4="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H4 failed: $out4"
printf '%s\n' "$out4" | grep -q 'Updated (Hermes' || fail "H4 should Updated: $out4"
[[ ! -f "$(hermes_dest "$leaf")/extra.txt" ]] || fail "H4 dest still has extra.txt"
assert_copy_tree "$leaf" "$pkg_abs"

# ---------------------------------------------------------------------------
# H5: legacy exact symlink auto-migrates
# ---------------------------------------------------------------------------
fresh_home h5
mkdir -p "$HOME/.hermes/skills/software-development"
ln -s "$pkg_abs" "$(hermes_dest "$leaf")"
out5="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H5 failed: $out5"
printf '%s\n' "$out5" | grep -q 'Migrated to copy' || fail "H5 migrate: $out5"
assert_copy_tree "$leaf" "$pkg_abs"

# ---------------------------------------------------------------------------
# H6: wrong symlink, no --relink → skip
# ---------------------------------------------------------------------------
fresh_home h6
mkdir -p "$HOME/.hermes/skills/software-development"
ln -s "/nonexistent/wrong-h6" "$(hermes_dest "$leaf")"
out6="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H6 failed: $out6"
printf '%s\n' "$out6" | grep -q 'Skipped existing path' || fail "H6 skip: $out6"
[[ -L "$(hermes_dest "$leaf")" ]] || fail "H6 must remain symlink"
got6="$(readlink "$(hermes_dest "$leaf")")"
[[ "$got6" == "/nonexistent/wrong-h6" ]] || fail "H6 target changed: $got6"

# ---------------------------------------------------------------------------
# H7: dangling + --relink → copy
# ---------------------------------------------------------------------------
fresh_home h7
mkdir -p "$HOME/.hermes/skills/software-development"
ln -s "/nonexistent/dangling-h7" "$(hermes_dest "$leaf")"
out7="$("$install_sh" --from "$pkg_abs" --hermes-only --relink 2>&1)" || fail "H7 failed: $out7"
printf '%s\n' "$out7" | grep -q 'Relinked' || fail "H7 Relinked: $out7"
assert_copy_tree "$leaf" "$pkg_abs"

# ---------------------------------------------------------------------------
# H8: foreign real tree
# ---------------------------------------------------------------------------
fresh_home h8
dest8="$(hermes_dest "$leaf")"
mkdir -p "$dest8"
printf 'sentinel\n' >"$dest8/SENTINEL"
set +e
out8="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)"
rc8=$?
set -e
[[ "$rc8" -eq 3 ]] || fail "H8 want exit 3 got $rc8: $out8"
printf '%s\n' "$out8" | grep -q 'Skipped (foreign)' || fail "H8 foreign: $out8"
[[ -f "$dest8/SENTINEL" ]] || fail "H8 sentinel lost"
[[ "$(cat "$dest8/SENTINEL")" == "sentinel" ]] || fail "H8 sentinel content"
[[ ! -f "$(hermes_marker "$leaf")" ]] || fail "H8 must not write marker for foreign"

# ---------------------------------------------------------------------------
# H9: no symlink under dest
# ---------------------------------------------------------------------------
fresh_home h9
"$install_sh" --from "$pkg_abs" --hermes-only >/dev/null
hits9="$(find "$(hermes_dest "$leaf")" -type l 2>/dev/null | head -n 1 || true)"
[[ -z "$hits9" ]] || fail "H9 found symlink under dest: $hits9"

# ---------------------------------------------------------------------------
# H10: absolute symlink in source → refuse, no dest
# ---------------------------------------------------------------------------
fresh_home h10
pkg10="$tmpdir/h10-abs-link"
make_pkg "$pkg10"
ln -s /etc/hosts "$pkg10/leak"
set +e
out10="$("$install_sh" --from "$pkg10" --hermes-only 2>&1)"
rc10=$?
set -e
[[ "$rc10" -ne 0 ]] || fail "H10 should fail (got 0): $out10"
printf '%s\n' "$out10" | grep -qi 'symlink' || fail "H10 should mention symlink: $out10"
[[ ! -e "$(hermes_dest h10-abs-link)" ]] || fail "H10 must not create dest"
if find "$HOME/.hermes" -name '.tmp-*' 2>/dev/null | grep -q .; then
  fail "H10 left staging tmp"
fi

# ---------------------------------------------------------------------------
# H11: escaping relative symlink in source → refuse
# ---------------------------------------------------------------------------
fresh_home h11
pkg11="$tmpdir/h11-rel-link"
make_pkg "$pkg11"
ln -s ../../outside "$pkg11/escape"
set +e
out11="$("$install_sh" --from "$pkg11" --hermes-only 2>&1)"
rc11=$?
set -e
[[ "$rc11" -ne 0 ]] || fail "H11 should fail: $out11"
[[ ! -e "$(hermes_dest h11-rel-link)" ]] || fail "H11 must not create dest"

# ---------------------------------------------------------------------------
# H12: exec bit preserved
# ---------------------------------------------------------------------------
fresh_home h12
"$install_sh" --from "$pkg_abs" --hermes-only >/dev/null
[[ -x "$(hermes_dest "$leaf")/scripts/run.sh" ]] || fail "H12 scripts/run.sh not executable"

# ---------------------------------------------------------------------------
# H13: dry-run mutates nothing
# ---------------------------------------------------------------------------
fresh_home h13
out13="$("$install_sh" --from "$pkg_abs" --hermes-only --dry-run 2>&1)" || fail "H13 dry-run failed: $out13"
printf '%s\n' "$out13" | grep -q 'Would install' || fail "H13 Would install: $out13"
[[ ! -d "$HOME/.hermes" ]] || fail "H13 dry-run must not create ~/.hermes"

# dry-run on drifted managed copy
fresh_home h13b
"$install_sh" --from "$pkg_abs" --hermes-only >/dev/null
printf 'drift\n' >"$pkg_abs/drift.txt"
# capture tree fingerprint
before="$(find "$(hermes_dest "$leaf")" -type f | LC_ALL=C sort | xargs cksum 2>/dev/null || true)"
out13b="$("$install_sh" --from "$pkg_abs" --hermes-only --dry-run 2>&1)" || fail "H13b failed: $out13b"
printf '%s\n' "$out13b" | grep -q 'Would update' || fail "H13b Would update: $out13b"
after="$(find "$(hermes_dest "$leaf")" -type f | LC_ALL=C sort | xargs cksum 2>/dev/null || true)"
[[ "$before" == "$after" ]] || fail "H13b dry-run mutated dest"
rm -f "$pkg_abs/drift.txt"

# ---------------------------------------------------------------------------
# H14: --from sample-skill into Hermes is host-keyed copy
# ---------------------------------------------------------------------------
fresh_home h14
fixture_abs="$(cd "$fixture_sample" && pwd -P)"
out14="$("$install_sh" --from "$fixture_abs" 2>&1)" || fail "H14 failed: $out14"
assert_copy_tree "sample-skill" "$fixture_abs"
[[ -L "$HOME/.claude/skills/sample-skill" ]] || fail "H14 Claude should still be symlink"
[[ -L "$HOME/.grok/skills/sample-skill" ]] || fail "H14 Grok should still be symlink"
[[ -L "$HOME/.codex/skills/sample-skill" ]] || fail "H14 Codex should still be symlink"

# ---------------------------------------------------------------------------
# H15: gitignore hint when ~/.hermes is a git work tree (no write to .gitignore)
# ---------------------------------------------------------------------------
fresh_home h15
mkdir -p "$HOME/.hermes"
git -C "$HOME/.hermes" init -q
printf 'x\n' >"$HOME/.hermes/README"
git -C "$HOME/.hermes" add README
git -C "$HOME/.hermes" -c user.email=t@t -c user.name=t commit -q -m init
# no .gitignore
out15="$("$install_sh" --from "$pkg_abs" --hermes-only 2>&1)" || fail "H15 failed: $out15"
printf '%s\n' "$out15" | grep -q 'gitignore' || fail "H15 should print gitignore hint: $out15"
[[ ! -f "$HOME/.hermes/.gitignore" ]] || fail "H15 must not write .gitignore"

# ---------------------------------------------------------------------------
# H16: package-internal symlink is allowed and dereferenced
# ---------------------------------------------------------------------------
fresh_home h16
pkg16="$tmpdir/pkg-int-link"
make_pkg "$pkg16"
printf 'target-body\n' >"$pkg16/real.txt"
ln -s real.txt "$pkg16/alias.txt"
out16="$("$install_sh" --from "$pkg16" --hermes-only 2>&1)" || fail "H16 failed: $out16"
dest16="$(hermes_dest hermes-bind-fixture)"
# leaf is basename of pkg16 path
dest16="$(hermes_dest pkg-int-link)"
[[ -f "$dest16/alias.txt" ]] || fail "H16 alias missing"
[[ ! -L "$dest16/alias.txt" ]] || fail "H16 alias should be dereferenced file"
[[ "$(cat "$dest16/alias.txt")" == "target-body" ]] || fail "H16 alias content"
hits16="$(find "$dest16" -type l 2>/dev/null | head -n 1 || true)"
[[ -z "$hits16" ]] || fail "H16 residual symlink: $hits16"
# re-run up to date
out16b="$("$install_sh" --from "$pkg16" --hermes-only 2>&1)" || fail "H16b: $out16b"
printf '%s\n' "$out16b" | grep -q 'Already installed (up to date)' || fail "H16b: $out16b"

# ---------------------------------------------------------------------------
# H17: receipts.jsonl appends install + uninstall
# ---------------------------------------------------------------------------
fresh_home h17
"$install_sh" --from "$pkg_abs" --hermes-only >/dev/null
rcpt="$HOME/.hermes/skills/software-development/.skill-craft/receipts.jsonl"
[[ -f "$rcpt" ]] || fail "H17 missing receipts"
grep -q '"action":"install"' "$rcpt" || fail "H17 install action"
grep -q '"outcome":"created"' "$rcpt" || fail "H17 created"
"$install_sh" --uninstall --from "$pkg_abs" --hermes-only >/dev/null
grep -q '"action":"uninstall"' "$rcpt" || fail "H17 uninstall action"
grep -q '"outcome":"removed"' "$rcpt" || fail "H17 removed"


# H18: src==dst refused
fresh_home h18
# Use --from with destination nested under a temp skill home is hard; instead call install with
# HERMES skills dir equal to package source by installing into a path that is the source itself.
# Build a tiny package under HOME and try --copy install with skills_dir parent == source (via --from into hermes using force).
pkg18="$tmpdir/pkg18"
mkdir -p "$pkg18"
printf -- '---\nname: nest-test\ndescription: x\nversion: 0.0.1\nlicense: MIT\nplatforms: [macos]\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n# n\n' >"$pkg18/SKILL.md"
# Point Hermes software-development at a dir that contains the package as the leaf path equal to source:
# destination = $HOME/.hermes/skills/software-development/nest-test
# We cannot easily make source==dest with install.sh public API unless --from and we hack.
# Nest: put source inside destination tree by pre-creating dest as parent of source — not valid for --from.
# Instead: use --copy --claude-only with skills dir under source (containment).
# Simpler unit: run bash function via sourcing is not exported.
# Public path: install_hermes with destination nested under source:
#   source=$tmpdir/srcleaf, create $tmpdir/srcleaf/nested-dest and... no.
# Use install --from where we set HOME so hermes dest is under the package dir:
mkdir -p "$pkg18/skills/software-development"
# Impossible with normal layout. Call install.sh in a subshell with a wrapper:
# Create source at $HOME/.hermes/skills/software-development/self and --from that path with hermes-only —
# then destination is $HOME/.hermes/skills/software-development/self == source.
self="$HOME/.hermes/skills/software-development/self"
mkdir -p "$self"
printf -- '---\nname: self\ndescription: x\nversion: 0.0.1\nlicense: MIT\nplatforms: [macos]\nmetadata:\n  skill_craft:\n    kind: prompt-only\n---\n# s\n' >"$self/SKILL.md"
set +e
out18="$("$install_sh" --from "$self" --hermes-only 2>&1)"
rc18=$?
set -e
[[ "$rc18" -ne 0 ]] || fail "H18 want nonzero for src==dst: $out18"
printf '%s\n' "$out18" | grep -qi 'same path\|nest\|Refused' || fail "H18 message: $out18"

printf 'hermes-binding.test.sh: PASS H1–H18 (copy lifecycle, internal symlink deref, receipts)\n'
