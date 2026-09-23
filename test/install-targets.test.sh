#!/usr/bin/env bash
# Hermetic install.sh coverage for skill-craft: six hosts × repo skills, flags, skip-if-exists, dry-run, --relink.
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

opencode_skills_dir() {
  printf '%s/opencode/skills\n' "${XDG_CONFIG_HOME:-$HOME/.config}"
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
  assert_symlink "$HOME/.cursor/skills/$leaf" "$source"
  assert_symlink "$(opencode_skills_dir)/$leaf" "$source"
  assert_hermes_copy "$leaf" "$source"
}

assert_no_hosts() {
  local leaf="$1"
  assert_absent "$HOME/.claude/skills/$leaf"
  assert_absent "$HOME/.grok/skills/$leaf"
  assert_absent "$HOME/.codex/skills/$leaf"
  assert_absent "$HOME/.cursor/skills/$leaf"
  assert_absent "$(opencode_skills_dir)/$leaf"
  assert_absent "$HOME/.hermes/skills/software-development/$leaf"
}

fresh_home() {
  export HOME="$tmpdir/home-$1"
  unset XDG_CONFIG_HOME
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
printf '%s\n' "$out" | grep -q 'Cursor' || fail "I1 stdout missing Cursor install line"
printf '%s\n' "$out" | grep -q 'OpenCode' || fail "I1 stdout missing OpenCode install line"
# Must NOT install product leaves that are not in this monorepo, including
# vendored plugin-bundle members (bundles/backchain is marketplace-only).
assert_no_hosts "backchain"
assert_no_hosts "plan-dispatcher"

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
assert_absent "$HOME/.cursor/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I7: --grok-only
# ---------------------------------------------------------------------------
fresh_home i7
out7="$("$install_sh" --grok-only --skill skill-interop 2>&1)" || fail "I7 failed: $out7"
assert_symlink "$HOME/.grok/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I8: --codex-only
# ---------------------------------------------------------------------------
fresh_home i8
out8="$("$install_sh" --codex-only --skill skill-interop 2>&1)" || fail "I8 failed: $out8"
assert_symlink "$HOME/.codex/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"
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
assert_absent "$HOME/.cursor/skills/skill-interop"

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
[[ ! -d "$HOME/.cursor" ]] || fail "I10 dry-run must not create ~/.cursor"
[[ ! -d "$HOME/.config" ]] || fail "I10 dry-run must not create ~/.config"
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
assert_absent "$(opencode_skills_dir)/../agents/skill-interop.md"

# ---------------------------------------------------------------------------
# I15: --cursor-only
# ---------------------------------------------------------------------------
fresh_home i15
out15="$("$install_sh" --cursor-only --skill skill-interop 2>&1)" || fail "I15 failed: $out15"
assert_symlink "$HOME/.cursor/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"

# ---------------------------------------------------------------------------
# I16: --skill devloop is identity install on Claude/Grok/Codex/Cursor/OpenCode.
# Hermes card install is skipped (engine owns software-development/devloop).
# ---------------------------------------------------------------------------
source_devloop="$root/skills/devloop"
[[ -f "$source_devloop/SKILL.md" ]] || fail "I16 missing skills/devloop/SKILL.md"
fresh_home i16
out16="$("$install_sh" --skill devloop 2>&1)" || fail "I16 install failed: $out16"
assert_symlink "$HOME/.claude/skills/devloop" "$source_devloop"
assert_symlink "$HOME/.grok/skills/devloop" "$source_devloop"
assert_symlink "$HOME/.codex/skills/devloop" "$source_devloop"
assert_symlink "$HOME/.cursor/skills/devloop" "$source_devloop"
assert_symlink "$(opencode_skills_dir)/devloop" "$source_devloop"
assert_absent "$HOME/.hermes/skills/software-development/devloop"
assert_absent "$HOME/.hermes/skills/software-development/devloop-run"
assert_absent "$HOME/.claude/skills/devloop-run"
assert_absent "$HOME/.grok/skills/devloop-run"
assert_absent "$HOME/.codex/skills/devloop-run"
assert_absent "$HOME/.cursor/skills/devloop-run"
assert_absent "$(opencode_skills_dir)/devloop-run"
printf '%s\n' "$out16" | grep -qi 'Skipped Hermes card install' \
  || fail "I16 should skip Hermes card: $out16"
assert_symlink "$HOME/.grok/commands/devloop.md" "$source_devloop/commands/devloop.md"
assert_absent "$HOME/.claude/commands/devloop.md"

# ---------------------------------------------------------------------------
# I17: leftover owned symlink at old dest …/devloop-run is removed
# ---------------------------------------------------------------------------
fresh_home i17
mkdir -p "$HOME/.grok/skills"
ln -s "$source_devloop" "$HOME/.grok/skills/devloop-run"
out17="$("$install_sh" --grok-only --skill devloop 2>&1)" || fail "I17 failed: $out17"
assert_symlink "$HOME/.grok/skills/devloop" "$source_devloop"
assert_absent "$HOME/.grok/skills/devloop-run"
printf '%s\n' "$out17" | grep -q 'Removed leftover dest' || fail "I17 should report leftover removal: $out17"

# ---------------------------------------------------------------------------
# I18: --opencode-only uses XDG_CONFIG_HOME (including spaces) and isolates
# OpenCode from all other host skill and agent directories.
# ---------------------------------------------------------------------------
fresh_home i18
export XDG_CONFIG_HOME="$tmpdir/opencode config i18"
out18="$("$install_sh" --opencode-only --skill skill-interop --agents 2>&1)" || fail "I18 failed: $out18"
assert_symlink "$XDG_CONFIG_HOME/opencode/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.config/opencode/skills/skill-interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"
assert_absent "$HOME/.hermes/skills/software-development/skill-interop"
assert_absent "$XDG_CONFIG_HOME/opencode/agents/skill-interop.md"
assert_absent "$XDG_CONFIG_HOME/opencode/opencode.json"
printf '%s\n' "$out18" | grep -q 'OpenCode' || fail "I18 stdout missing OpenCode install line: $out18"

# ---------------------------------------------------------------------------
# I19: --all explicitly selects the same six host targets as the default.
# ---------------------------------------------------------------------------
fresh_home i19
out19="$("$install_sh" --all --skill skill-interop 2>&1)" || fail "I19 failed: $out19"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I20: vendored plugin bundles are never installed: not by default, not as
# agents, and not by name (bundles/ is invisible to skills/ enumeration).
# ---------------------------------------------------------------------------
[[ -f "$root/bundles/backchain/bundle.json" ]] || fail "I20 expects the vendored backchain bundle"
fresh_home i20
out20="$("$install_sh" --agents 2>&1)" || fail "I20 default --agents install failed: $out20"
assert_no_hosts "backchain"
assert_no_hosts "plan-dispatcher"
assert_absent "$HOME/.claude/agents/backchain.md"
assert_absent "$HOME/.grok/agents/backchain.md"
for member in backchain plan-dispatcher; do
  set +e
  out20n="$("$install_sh" --skill "$member" 2>&1)"
  rc20n=$?
  set -e
  [[ "$rc20n" -eq 1 ]] || fail "I20 --skill $member should exit 1 (got $rc20n): $out20n"
  printf '%s\n' "$out20n" | grep -q 'missing SKILL.md' || fail "I20 --skill $member message: $out20n"
done

# ---------------------------------------------------------------------------
# I21: --from refuses vendored bundle members and generated plugin views
# (exit 64, every action, no writes) so --relink cannot repoint a canonical
# link at a marketplace copy; the guard is structural, so it also covers
# another skill-craft checkout, and it reads the manifest repository, so it
# covers copies in host plugin caches.
# ---------------------------------------------------------------------------
expect_from_refused() {
  local label="$1"
  shift
  local out rc
  set +e
  out="$("$install_sh" "$@" 2>&1)"
  rc=$?
  set -e
  [[ "$rc" -eq 64 ]] || fail "$label should exit 64 (got $rc): $out"
  printf '%s\n' "$out" | grep -q 'marketplace-only' || fail "$label refusal message: $out"
}
fresh_home i21
expect_from_refused "I21 bundle member" --from "$root/bundles/backchain/skills/backchain"
expect_from_refused "I21 bundle view member" --from "$root/plugins/backchain/skills/plan-dispatcher"
expect_from_refused "I21 leaf plugin view" --from "$root/plugins/skill-interop/skills/skill-interop"
expect_from_refused "I21 bundle status" --status --from "$root/bundles/backchain/skills/backchain"
expect_from_refused "I21 bundle uninstall" --uninstall --from "$root/bundles/backchain/skills/backchain"
assert_no_hosts "backchain"
assert_no_hosts "plan-dispatcher"
assert_no_hosts "skill-interop"
[[ ! -d "$HOME/.hermes" ]] || fail "I21 refusal must not create a Hermes copy"
canonical="$tmpdir/canonical/skills/backchain"
mkdir -p "$canonical" "$HOME/.claude/skills"
printf -- '---\nname: backchain\n---\n' >"$canonical/SKILL.md"
ln -s "$canonical" "$HOME/.claude/skills/backchain"
expect_from_refused "I21 relink over canonical link" --claude-only --relink \
  --from "$root/bundles/backchain/skills/backchain"
expect_from_refused "I21 relink from view" --claude-only --relink \
  --from "$root/plugins/backchain/skills/backchain"
assert_symlink "$HOME/.claude/skills/backchain" "$canonical"

other="$tmpdir/other-checkout"
mkdir -p "$other/bundles/zz/skills/zz" "$other/scripts" "$other/plugins/yy/skills/yy" "$other/plugins/yy/.claude-plugin"
printf '{}\n' >"$other/bundles/zz/bundle.json"
printf -- '---\nname: zz\n---\n' >"$other/bundles/zz/skills/zz/SKILL.md"
printf '#!/usr/bin/env bash\n' >"$other/scripts/sync-plugin-views.sh"
printf '{}\n' >"$other/plugins/yy/.claude-plugin/plugin.json"
printf -- '---\nname: yy\n---\n' >"$other/plugins/yy/skills/yy/SKILL.md"
expect_from_refused "I21 other checkout bundle" --claude-only --from "$other/bundles/zz/skills/zz"
expect_from_refused "I21 other checkout view" --claude-only --from "$other/plugins/yy/skills/yy"
assert_absent "$HOME/.claude/skills/zz"
assert_absent "$HOME/.claude/skills/yy"

# A copy of a generated view outside any checkout (a host plugin cache or a
# git-subdir clone) is recognized by its manifest's repository, not its path:
# --relink must not repoint a canonical link at it, dry run or not.
repo_const="$(sed -n 's/^skill_craft_repository="\(.*\)"$/\1/p' "$install_sh")"
[[ -n "$repo_const" ]] || fail "I21 install.sh must declare skill_craft_repository"
grep -Fq "const REPOSITORY = \"$repo_const\";" "$root/scripts/skill-frontmatter-to-plugin-json.js" \
  || fail "I21 install.sh skill_craft_repository must equal the generator REPOSITORY"
cache_root="$HOME/.claude/plugins/cache/skill-craft-market"
mkdir -p "$cache_root/backchain" "$cache_root/skill-interop"
cp -R "$root/plugins/backchain" "$cache_root/backchain/0.3.7"
cp -R "$root/plugins/skill-interop" "$cache_root/skill-interop/0.2.3"
canonical_pd="$tmpdir/canonical/skills/plan-dispatcher"
mkdir -p "$canonical_pd"
printf -- '---\nname: plan-dispatcher\n---\n' >"$canonical_pd/SKILL.md"
ln -s "$canonical_pd" "$HOME/.claude/skills/plan-dispatcher"
expect_from_refused "I21 cached bundle copy relink dry run" --claude-only --relink --dry-run \
  --from "$cache_root/backchain/0.3.7/skills/plan-dispatcher"
expect_from_refused "I21 cached bundle copy relink" --claude-only --relink \
  --from "$cache_root/backchain/0.3.7/skills/plan-dispatcher"
expect_from_refused "I21 cached leaf view copy" --claude-only \
  --from "$cache_root/skill-interop/0.2.3/skills/skill-interop"
# One host's manifest is enough (a Codex cache need not keep the others).
rm -rf "$cache_root/backchain/0.3.7/.claude-plugin" "$cache_root/backchain/0.3.7/.cursor-plugin"
expect_from_refused "I21 Codex-only cached copy" --claude-only --relink \
  --from "$cache_root/backchain/0.3.7/skills/backchain"
# The repository may be spelled as a .git URL or an npm-style object.
spelled="$tmpdir/spelled-copy"
mkdir -p "$spelled/.cursor-plugin" "$spelled/skills/spelled-leaf"
printf '{"repository":{"type":"git","url":"%s.git/"}}\n' "$repo_const" >"$spelled/.cursor-plugin/plugin.json"
printf -- '---\nname: spelled-leaf\n---\n' >"$spelled/skills/spelled-leaf/SKILL.md"
expect_from_refused "I21 repository spelling" --claude-only --from "$spelled/skills/spelled-leaf"
assert_absent "$HOME/.claude/skills/spelled-leaf"
assert_symlink "$HOME/.claude/skills/plan-dispatcher" "$canonical_pd"
assert_symlink "$HOME/.claude/skills/backchain" "$canonical"
assert_absent "$HOME/.claude/skills/skill-interop"

# A plugin repository that is not a generated view stays installable (for
# example a canonical source whose root carries its own .claude-plugin).
external="$tmpdir/plugin-source-repo"
mkdir -p "$external/.claude-plugin" "$external/skills/external-leaf"
printf '{}\n' >"$external/.claude-plugin/plugin.json"
printf -- '---\nname: external-leaf\n---\n' >"$external/skills/external-leaf/SKILL.md"
external="$(cd "$external" && pwd -P)"
out21e="$("$install_sh" --claude-only --from "$external/skills/external-leaf" 2>&1)" \
  || fail "I21 canonical plugin-repository source must install: $out21e"
assert_symlink "$HOME/.claude/skills/external-leaf" "$external/skills/external-leaf"
# The canonical upstream names its own repository, so it stays installable.
upstream="$tmpdir/plan-orchestrator"
mkdir -p "$upstream/.claude-plugin" "$upstream/skills/upstream-leaf"
printf '{"name":"backchain","repository":"https://github.com/whichguy/plan-orchestrator"}\n' \
  >"$upstream/.claude-plugin/plugin.json"
printf -- '---\nname: upstream-leaf\n---\n' >"$upstream/skills/upstream-leaf/SKILL.md"
upstream="$(cd "$upstream" && pwd -P)"
out21u="$("$install_sh" --claude-only --from "$upstream/skills/upstream-leaf" 2>&1)" \
  || fail "I21 canonical upstream source must install: $out21u"
assert_symlink "$HOME/.claude/skills/upstream-leaf" "$upstream/skills/upstream-leaf"

# --help exits 0 and names the marketplace-only sources
help_text="$("$install_sh" --help 2>&1)"
printf '%s\n' "$help_text" | grep -q 'marketplace-only' || fail "--help must state bundles are marketplace-only"

# Invalid flag → exit 64
set +e
"$install_sh" --not-a-flag >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "invalid flag should exit 64 (got $rc)"

printf 'install-targets.test.sh: PASS I1–I21 (skill-craft install, 6 hosts, identity dest, flags, dry-run, skip-if-exists, --relink, --agents, marketplace-only sources)\n'
