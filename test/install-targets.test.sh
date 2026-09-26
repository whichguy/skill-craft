#!/usr/bin/env bash
# Hermetic install.sh coverage for skill-craft: five hosts × repo skills, flags, skip-if-exists, dry-run, --relink.
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

assert_all_hosts() {
  local leaf="$1"
  local source="$2"
  assert_symlink "$HOME/.claude/skills/$leaf" "$source"
  assert_symlink "$HOME/.grok/skills/$leaf" "$source"
  assert_symlink "$HOME/.codex/skills/$leaf" "$source"
  assert_symlink "$HOME/.cursor/skills/$leaf" "$source"
  assert_symlink "$(opencode_skills_dir)/$leaf" "$source"
}

assert_no_hosts() {
  local leaf="$1"
  assert_absent "$HOME/.claude/skills/$leaf"
  assert_absent "$HOME/.grok/skills/$leaf"
  assert_absent "$HOME/.codex/skills/$leaf"
  assert_absent "$HOME/.cursor/skills/$leaf"
  assert_absent "$(opencode_skills_dir)/$leaf"
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
# I1: Fresh HOME, no flags → the default host only: OpenCode. Claude, Grok, Codex and Cursor now get
# every skill through the skill-craft marketplace plugin, so they stay absent
# without an explicit host flag or --all.
# ---------------------------------------------------------------------------
fresh_home i1
out="$("$install_sh" 2>&1)" || fail "I1 install.sh failed on fresh home: $out"
assert_symlink "$(opencode_skills_dir)/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"
printf '%s\n' "$out" | grep -q 'OpenCode' || fail "I1 stdout missing OpenCode install line"
printf '%s\n' "$out" | grep -q 'Claude Code' && fail "I1 default must not touch Claude Code: $out"
printf '%s\n' "$out" | grep -q 'Grok' && fail "I1 default must not touch Grok: $out"
printf '%s\n' "$out" | grep -q 'Codex' && fail "I1 default must not touch Codex: $out"
printf '%s\n' "$out" | grep -q 'Cursor' && fail "I1 default must not touch Cursor: $out"
# Backchain and Plan Dispatcher are ordinary skills/ leaves; same default scope.
assert_symlink "$(opencode_skills_dir)/backchain" "$root/skills/backchain"
assert_symlink "$(opencode_skills_dir)/plan-dispatcher" "$root/skills/plan-dispatcher"
assert_absent "$HOME/.claude/skills/backchain"
assert_absent "$HOME/.claude/skills/plan-dispatcher"

# ---------------------------------------------------------------------------
# I2: Idempotent re-run of the default (no flags), same HOME as I1 →
# "already installed" for OpenCode (the only symlink host the default touches).
# ---------------------------------------------------------------------------
out2="$("$install_sh" 2>&1)" || fail "I2 install.sh re-run failed: $out2"
printf '%s\n' "$out2" | grep -q 'Already installed' || fail "I2 re-run should report already installed"
assert_symlink "$(opencode_skills_dir)/skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I1b: --all → all hosts × all skills (explicit opt-in; this is what a
# no-flags run used to do before Claude/Grok/Codex/Cursor moved to the
# skill-craft marketplace plugin by default).
# ---------------------------------------------------------------------------
fresh_home i1all
outall="$("$install_sh" --all 2>&1)" || fail "I1b install.sh --all failed: $outall"
assert_all_hosts "skill-interop" "$source_interop"
printf '%s\n' "$outall" | grep -q 'Claude Code' || fail "I1b stdout missing Claude install line"
printf '%s\n' "$outall" | grep -q 'Grok' || fail "I1b stdout missing Grok install line"
printf '%s\n' "$outall" | grep -q 'Codex' || fail "I1b stdout missing Codex install line"
printf '%s\n' "$outall" | grep -q 'Cursor' || fail "I1b stdout missing Cursor install line"
printf '%s\n' "$outall" | grep -q 'OpenCode' || fail "I1b stdout missing OpenCode install line"
assert_all_hosts "backchain" "$root/skills/backchain"
assert_all_hosts "plan-dispatcher" "$root/skills/plan-dispatcher"

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
# I4: --all --skill skill-interop → only skill-interop leaves, all hosts
# ---------------------------------------------------------------------------
fresh_home i4
out4="$("$install_sh" --all --skill skill-interop 2>&1)" || fail "I4 failed: $out4"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I5: --all --skill all → same skill-interop coverage as I4, via --skill all
# ---------------------------------------------------------------------------
fresh_home i5
out5="$("$install_sh" --all --skill all 2>&1)" || fail "I5 failed: $out5"
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

# ---------------------------------------------------------------------------
# I7: --grok-only
# ---------------------------------------------------------------------------
fresh_home i7
out7="$("$install_sh" --grok-only --skill skill-interop 2>&1)" || fail "I7 failed: $out7"
assert_symlink "$HOME/.grok/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"

# ---------------------------------------------------------------------------
# I8: --codex-only
# ---------------------------------------------------------------------------
fresh_home i8
out8="$("$install_sh" --codex-only --skill skill-interop 2>&1)" || fail "I8 failed: $out8"
assert_symlink "$HOME/.codex/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
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
# I14: --agents installs thin agent card for Claude + Grok (--all: agent
# install is gated on the Claude/Grok skill flags, which need an explicit
# host flag or --all now that the default doesn't select those hosts)
# ---------------------------------------------------------------------------
fresh_home i14
agent_src="$root/agents/skill-interop.md"
[[ -f "$agent_src" ]] || fail "I14 missing agents/skill-interop.md"
out14="$("$install_sh" --all --skill skill-interop --agents 2>&1)" || fail "I14 failed: $out14"
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

# ---------------------------------------------------------------------------
# I18: --opencode-only uses XDG_CONFIG_HOME (including spaces) and isolates
# OpenCode from all other host skill and agent directories.
# ---------------------------------------------------------------------------
fresh_home i18
export XDG_CONFIG_HOME="$tmpdir/opencode config i18"
# Agent cards install only for Claude/Grok: asking for them with OpenCode alone
# is a usage error that writes nothing.
set +e
out18a="$("$install_sh" --opencode-only --skill skill-interop --agents 2>&1)"
rc18a=$?
set -e
[[ "$rc18a" -eq 64 ]] || fail "I18 --opencode-only --agents want exit 64 got $rc18a: $out18a"
printf '%s\n' "$out18a" | grep -q -- '--agents needs' || fail "I18 --agents message: $out18a"
assert_absent "$XDG_CONFIG_HOME/opencode/skills/skill-interop"
out18="$("$install_sh" --opencode-only --skill skill-interop 2>&1)" || fail "I18 failed: $out18"
assert_symlink "$XDG_CONFIG_HOME/opencode/skills/skill-interop" "$source_interop"
assert_absent "$HOME/.config/opencode/skills/skill-interop"
assert_absent "$HOME/.claude/skills/skill-interop"
assert_absent "$HOME/.grok/skills/skill-interop"
assert_absent "$HOME/.codex/skills/skill-interop"
assert_absent "$HOME/.cursor/skills/skill-interop"
assert_absent "$XDG_CONFIG_HOME/opencode/agents/skill-interop.md"
assert_absent "$XDG_CONFIG_HOME/opencode/opencode.json"
printf '%s\n' "$out18" | grep -q 'OpenCode' || fail "I18 stdout missing OpenCode install line: $out18"

# ---------------------------------------------------------------------------
# I19: --all explicitly selects every host (Claude/Grok/Codex/Cursor/OpenCode),
# no longer the same as the default (which now only selects OpenCode).
# ---------------------------------------------------------------------------
fresh_home i19
out19="$("$install_sh" --all --skill skill-interop 2>&1)" || fail "I19 failed: $out19"
assert_all_hosts "skill-interop" "$source_interop"

# ---------------------------------------------------------------------------
# I21: --from refuses generated plugin views (exit 64, every action, no
# writes) so --relink cannot repoint a canonical
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
expect_from_refused "I21 leaf plugin view" --from "$root/plugins/skill-craft/skills/skill-interop"
expect_from_refused "I21 view status" --status --from "$root/plugins/skill-craft/skills/skill-interop"
expect_from_refused "I21 view uninstall" --uninstall --from "$root/plugins/skill-craft/skills/skill-interop"
assert_no_hosts "skill-interop"
canonical="$tmpdir/canonical/skills/backchain"
mkdir -p "$canonical" "$HOME/.claude/skills"
printf -- '---\nname: backchain\n---\n' >"$canonical/SKILL.md"
ln -s "$canonical" "$HOME/.claude/skills/backchain"
expect_from_refused "I21 relink from view" --claude-only --relink \
  --from "$root/plugins/skill-craft/skills/backchain"
assert_symlink "$HOME/.claude/skills/backchain" "$canonical"

other="$tmpdir/other-checkout"
mkdir -p "$other/scripts" "$other/plugins/yy/skills/yy" "$other/plugins/yy/.claude-plugin"
printf '#!/usr/bin/env bash\n' >"$other/scripts/sync-plugin-views.sh"
printf '{}\n' >"$other/plugins/yy/.claude-plugin/plugin.json"
printf -- '---\nname: yy\n---\n' >"$other/plugins/yy/skills/yy/SKILL.md"
expect_from_refused "I21 other checkout view" --claude-only --from "$other/plugins/yy/skills/yy"
assert_absent "$HOME/.claude/skills/yy"

# A copy of a generated view outside any checkout (a host plugin cache or a
# git-subdir clone) is recognized by its manifest's repository, not its path:
# --relink must not repoint a canonical link at it, dry run or not.
repo_const="$(sed -n 's/^skill_craft_repository="\(.*\)"$/\1/p' "$install_sh")"
[[ -n "$repo_const" ]] || fail "I21 install.sh must declare skill_craft_repository"
grep -Fq "const REPOSITORY = \"$repo_const\";" "$root/scripts/skill-frontmatter-to-plugin-json.js" \
  || fail "I21 install.sh skill_craft_repository must equal the generator REPOSITORY"
cache_root="$HOME/.claude/plugins/cache/whichguy/skill-craft"
mkdir -p "$cache_root"
cp -R "$root/plugins/skill-craft" "$cache_root/1.0.0"
expect_from_refused "I21 cached view copy relink dry run" --claude-only --relink --dry-run \
  --from "$cache_root/1.0.0/skills/backchain"
expect_from_refused "I21 cached view copy relink" --claude-only --relink \
  --from "$cache_root/1.0.0/skills/backchain"
expect_from_refused "I21 cached leaf view copy" --claude-only \
  --from "$cache_root/1.0.0/skills/skill-interop"
# One host's manifest is enough (a Codex cache need not keep the others).
rm -rf "$cache_root/1.0.0/.claude-plugin" "$cache_root/1.0.0/.cursor-plugin"
expect_from_refused "I21 Codex-only cached copy" --claude-only --relink \
  --from "$cache_root/1.0.0/skills/backchain"
# The repository may be spelled as a .git URL or an npm-style object.
spelled="$tmpdir/spelled-copy"
mkdir -p "$spelled/.cursor-plugin" "$spelled/skills/spelled-leaf"
printf '{"repository":{"type":"git","url":"%s.git/"}}\n' "$repo_const" >"$spelled/.cursor-plugin/plugin.json"
printf -- '---\nname: spelled-leaf\n---\n' >"$spelled/skills/spelled-leaf/SKILL.md"
expect_from_refused "I21 repository spelling" --claude-only --from "$spelled/skills/spelled-leaf"
assert_absent "$HOME/.claude/skills/spelled-leaf"
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
printf '%s\n' "$help_text" | grep -q 'marketplace-only' || fail "--help must state generated plugin views are marketplace-only"

# Invalid flag → exit 64
set +e
"$install_sh" --not-a-flag >/dev/null 2>&1
rc=$?
set -e
[[ "$rc" -eq 64 ]] || fail "invalid flag should exit 64 (got $rc)"

# One spelling per flag: --relink and --skill all. The retired --force and
# --skill both spellings are not synonyms any more.
printf '%s\n' "$help_text" | grep -q -- '--relink' || fail "--help must document --relink"
printf '%s\n' "$help_text" | grep -q -- '--force' && fail "--help must not document --force"
printf '%s\n' "$help_text" | grep -qw 'both' && fail "--help must not document --skill both"
fresh_home flags
set +e
out_force="$("$install_sh" --claude-only --skill skill-interop --force 2>&1)"
rc_force=$?
set -e
[[ "$rc_force" -eq 64 ]] || fail "--force must be an unknown flag (exit 64, got $rc_force): $out_force"
printf '%s\n' "$out_force" | grep -q 'Unknown flag: --force' || fail "--force refusal message: $out_force"
set +e
out_both="$("$install_sh" --claude-only --skill both 2>&1)"
rc_both=$?
set -e
[[ "$rc_both" -eq 1 ]] || fail "--skill both must not select every skill (exit 1, got $rc_both): $out_both"
printf '%s\n' "$out_both" | grep -q 'skills/both/SKILL.md' || fail "--skill both is a plain leaf name: $out_both"
[[ ! -e "$HOME/.claude" ]] || fail "--force/--skill both must not write"

# --agents with --status is a usage error (exit 64), not a printf failure (exit 2).
set +e
out_agents="$("$install_sh" --status --agents 2>&1)"
rc_agents=$?
set -e
[[ "$rc_agents" -eq 64 ]] || fail "--status --agents want exit 64 got $rc_agents: $out_agents"
printf '%s\n' "$out_agents" | grep -q -- '--agents is only valid for install' || fail "--agents message: $out_agents"

printf 'install-targets.test.sh: PASS I1, I1b, I2–I8, I10–I15, I18, I19, I21 (skill-craft install, 5 hosts, default-hosts scope, identity dest, flags, dry-run, skip-if-exists, --relink, --agents, marketplace-only sources)\n'
