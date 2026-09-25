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

tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/skill-craft-install-arb.XXXXXX")"
cleanup() { rm -rf "$tmpdir"; }
trap cleanup EXIT

[[ -f "$fixture_sample/SKILL.md" ]] || fail "missing frozen fixture: $fixture_sample/SKILL.md"

# ---------------------------------------------------------------------------
# E1: --from fixture sample-skill → all 5 symlink hosts get sample-skill symlink
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

# ---------------------------------------------------------------------------
# E6: an OpenCode --copy install ships Ask Agent's real helper. It can prepare
# a worktree from an unrelated cwd without importing the source checkout.
# ---------------------------------------------------------------------------
fresh_home e6
ask_agent_source="$root/skills/ask-agent"
[[ -f "$ask_agent_source/scripts/ask_agent_workspace.py" ]] || fail "E6 missing Ask Agent helper"
out6i="$("$install_sh" --opencode-only --copy --skill ask-agent 2>&1)" || fail "E6 OpenCode copy install: $out6i"
installed_ask_agent="$(opencode_skills_dir)/ask-agent"
installed_helper="$installed_ask_agent/scripts/ask_agent_workspace.py"
[[ -d "$installed_ask_agent" && ! -L "$installed_ask_agent" ]] || fail "E6 expected copied Ask Agent package"
[[ -f "$installed_helper" && ! -L "$installed_helper" ]] || fail "E6 expected copied helper"
case "$installed_helper" in
  "$root"/*) fail "E6 helper unexpectedly resolves into source checkout: $installed_helper" ;;
esac
installed_bytecode_before="$(find "$installed_ask_agent" \( -name __pycache__ -o -name '*.pyc' \) -print | LC_ALL=C sort)"

workspace_source="$tmpdir/e6 helper source repo"
unrelated_cwd="$tmpdir/e6 unrelated invocation cwd"
workspace_store="$tmpdir/e6 workspace store"
mkdir -p "$workspace_source" "$unrelated_cwd"
git init -q "$workspace_source"
git -C "$workspace_source" config user.email "installer-test@example.invalid"
git -C "$workspace_source" config user.name "Installer Test"
printf 'baseline\n' >"$workspace_source/README.md"
git -C "$workspace_source" add README.md
git -C "$workspace_source" commit -qm "baseline"
out6p="$(
  cd "$unrelated_cwd"
  unset PYTHONPATH
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python3 -B "$installed_helper" prepare \
    --source "$workspace_source" --store "$workspace_store" --label "installed copy" --writers-quiescent 2>&1
)" || fail "E6 copied helper prepare: $out6p"
printf '%s\n' "$out6p" | grep -q '"worktree"' || fail "E6 helper did not emit a worktree receipt: $out6p"
prepared_worktree="$(printf '%s\n' "$out6p" | python3 -c 'import json, sys; print(json.load(sys.stdin)["worktree"])')" \
  || fail "E6 helper output was not JSON: $out6p"
prepared_receipt="$(printf '%s\n' "$out6p" | python3 -c 'import json, sys; print(json.load(sys.stdin)["receipt"])')" \
  || fail "E6 helper receipt was not JSON: $out6p"
[[ -d "$prepared_worktree" ]] || fail "E6 prepared worktree missing: $prepared_worktree"
(mkdir -p "$prepared_worktree/reports")
printf '# Installed helper report\n\nReport-only lifecycle check.\n' >"$prepared_worktree/reports/installed-copy.md"
out6r="$(
  cd "$unrelated_cwd"
  unset PYTHONPATH
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python3 -B "$installed_helper" inspect \
    --receipt "$prepared_receipt" --phase returned --artifact reports/installed-copy.md \
    --delivery-mode report-only 2>&1
)" || fail "E6 copied helper report-only inspect: $out6r"
inspection_fingerprint="$(printf '%s\n' "$out6r" | python3 -c 'import json, sys; print(json.load(sys.stdin)["fingerprint"])')" \
  || fail "E6 helper inspection was not JSON: $out6r"
acceptance="$tmpdir/e6 acceptance.json"
printf '{"schema":"ask-agent.acceptance.v1","inspection_fingerprint":"%s","decision":"report-consumed","workers_stopped":true,"completion_reference":"installer test native return","acceptance_reference":"installer test report consumed","artifacts":[{"path":"reports/installed-copy.md","purpose":"installed helper report"}],"discard":[]}\n' \
  "$inspection_fingerprint" >"$acceptance"
out6c="$(
  cd "$unrelated_cwd"
  unset PYTHONPATH
  PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 python3 -B "$installed_helper" close \
    --receipt "$prepared_receipt" --acceptance "$acceptance" 2>&1
)" || fail "E6 copied helper close: $out6c"
close_status="$(printf '%s\n' "$out6c" | python3 -c 'import json, sys; print(json.load(sys.stdin)["status"])')" \
  || fail "E6 helper close output was not JSON: $out6c"
[[ "$close_status" == 'closed' ]] || fail "E6 copied helper did not close: $out6c"
archived_report="$(printf '%s\n' "$out6c" | python3 -c 'import json, sys; print(json.load(sys.stdin)["archived_artifacts"][0]["archive"])')" \
  || fail "E6 helper archive output was not JSON: $out6c"
[[ -f "$archived_report" ]] || fail "E6 archived report missing: $archived_report"
[[ ! -e "$prepared_worktree" ]] || fail "E6 worker worktree remains after close"
[[ -z "$(git -C "$workspace_source" status --porcelain)" ]] || fail "E6 helper changed source checkout"
installed_bytecode_after="$(find "$installed_ask_agent" \( -name __pycache__ -o -name '*.pyc' \) -print | LC_ALL=C sort)"
[[ "$installed_bytecode_before" == "$installed_bytecode_after" ]] || fail "E6 copied package was mutated with Python bytecode"

printf 'install-arbitrary-skill.test.sh: PASS E1–E6 (--from, --skill all, exclusivity, installed Ask Agent copy)\n'
