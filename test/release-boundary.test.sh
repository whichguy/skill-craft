#!/usr/bin/env bash
# Release boundary guard edge cases: release-commit verification, the pre-guard
# transition, per-commit trailers, agent cards, note deletions, misplaced
# trailers, pending-note validation and a missing base. Each case runs in a
# small disposable repository holding the current guard and release scripts
# and a stub sync check (no network, no pushes).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail() { printf 'release-boundary.test.sh: FAIL %s\n' "$*" >&2; exit 1; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/release-boundary.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1

card() { # <leaf> <version> [body]
  mkdir -p "skills/$1"
  printf -- '---\nname: %s\ndescription: fixture\nversion: %s\n---\n%s\n' "$1" "$2" "${3:-Body.}" > "skills/$1/SKILL.md"
}
guard_scripts() {
  mkdir -p scripts
  cp "$root/scripts/check-release-boundary.py" "$root/scripts/release.py" scripts/
  # Stub release output check: plugins/<leaf>/SKILL.md must copy skills/<leaf>/SKILL.md.
  printf '#!/usr/bin/env bash\nfor s in skills/*/SKILL.md; do l="${s#skills/}"; cmp -s "$s" "plugins/${l%%/SKILL.md}/SKILL.md" || exit 1; done\n' \
    > scripts/sync-plugin-views.sh
}
publish() { for leaf in "$@"; do mkdir -p "plugins/$leaf" && cp "skills/$leaf/SKILL.md" "plugins/$leaf/SKILL.md"; done; }
note() { mkdir -p "changes/$1" && printf -- '%b' "$3" > "changes/$1/$2.md"; }
fixture() { # <name>: a released repository with skills a and b and agent card a
  mkdir -p "$tmp/$1" && cd "$tmp/$1"
  git init -q -b main .
  card a 0.1.0 && card b 0.1.0 && publish a b
  mkdir -p agents && echo "Agent a." > agents/a.md
  [[ "${2:-}" == pre-guard ]] || guard_scripts
  git add -A && git commit -qm base
  base="$(git rev-parse HEAD)"
}
commit() { git add -A && git commit -q "$@"; }
boundary() { python3 -B scripts/check-release-boundary.py "$@" 2>&1; }
passes() { local out; out="$(boundary --base "$base")" || fail "$1 must pass: $out"; }
fails() { # <label> <expected message>
  local out
  out="$(boundary --base "$base")" && fail "$1 must fail"
  [[ "$out" == *"$2"* ]] || fail "$1: expected '$2', got: $out"
}

# A1: a release commit is verified in its own tree, whatever the checkout holds,
# and the temporary worktree is always removed.
fixture a1
echo "Change." >> skills/a/SKILL.md && publish a
commit -m "release: a" -m "Skill-Craft-Release: a@0.1.1"
passes "an in-sync release commit"
echo "Drift." >> skills/a/SKILL.md
commit -m "release: out of sync" -m "Skill-Craft-Release: a@0.1.2"
publish a && commit -m "release: repair" -m "Skill-Craft-Release: a@0.1.3"
fails "an out-of-sync release commit before a repair" "release: out of sync: release commit output does not match its source"
[[ "$(git worktree list | wc -l)" -eq 1 ]] || fail "release verification left a worktree: $(git worktree list)"

# A2: commits whose parents predate the guard are skipped; later ones are not.
fixture a2 pre-guard
git checkout -qb old
echo "Old habit." >> plugins/a/SKILL.md && commit -m "old: hand-edit plugins"
git checkout -q main
guard_scripts && commit -m "build: add the release guard"
base="$(git rev-parse HEAD)"
git merge -q --no-ff old -m "merge old branch"
out="$(boundary --base "$base")" || fail "a pre-guard commit merged after the guard must pass: $out"
[[ "$out" == *"predates the release guard"* ]] || fail "pre-guard skip not reported: $out"
echo "New habit." >> plugins/a/SKILL.md && commit -m "new: hand-edit plugins"
fails "a post-guard hand edit" "new: hand-edit plugins: changes release output"

# A3: No-Change-Note excuses only its own commit.
fixture a3
echo "Edit." >> skills/a/SKILL.md && commit -m "feat: a without a note"
echo "Typo." >> skills/b/SKILL.md && commit -m "fix: b typo" -m "No-Change-Note: typo only"
fails "one commit's opt-out covering another" "skills/a/SKILL.md changed"
out="$(boundary --base "$base")" || true
[[ "$out" != *"skills/b"* ]] || fail "the opted-out commit was reported: $out"

# A4: an agent card is part of its skill.
fixture a4
echo "Agent edit." >> agents/a.md && commit -m "feat: agent a"
fails "an agent card edit without a note" "agents/a.md changed"
note a card '---\nbump: patch\n---\nAgent card change.\n' && commit -m "docs: note for agent a"
passes "an agent card edit with a note"

# A9: a note counts only while it exists; pending notes are the release's to consume.
fixture a9
echo "Edit." >> skills/a/SKILL.md
note a fixture '---\nbump: patch\n---\nFixture.\n' && commit -m "feat: a"
git rm -q changes/a/fixture.md && commit -m "chore: drop the note"
fails "a note added then removed" "no changes/a/*.md note"
fixture a9b
note b pending '---\nbump: patch\n---\nPending.\n' && commit -m "feat: b note"
base="$(git rev-parse HEAD)"
git rm -q changes/b/pending.md && commit -m "chore: drop a pending note"
fails "deleting a note pending at base" "deletes pending change note changes/b/pending.md"

# A6: trailer keys ignore case; a trailer outside the final paragraph is explained.
fixture a6
echo "Typo." >> skills/a/SKILL.md
commit -m "fix: typo" -m "No-Change-Note: typo only" -m "Co-Authored-By: test <test@example.invalid>"
out="$(python3 -B scripts/check-release-boundary.py --base "$base" 2>&1 >/dev/null)" && fail "a misplaced trailer must fail"
[[ "$out" == *"final paragraph"* ]] || fail "misplaced trailer not explained on stderr: $out"
git commit -q --amend -m "fix: typo" -m "no-change-note: typo only
Co-Authored-By: test <test@example.invalid>"
passes "a lowercase No-Change-Note key"

# A8: pending notes must pass the release command's own validation.
fixture a8
echo "Edit." >> skills/a/SKILL.md
note a bad '---\nbump: pach\n---\nFixture.\n' && commit -m "feat: a"
fails "a note the release would refuse" "pending change notes would break the next release: changes/a/bad.md"

# A10: only the front matter's version: is release output, never a body line.
fixture a10
printf -- '---\nname: c\ndescription: fixture\nmetadata:\n  version: 0.1.0\n---\nversion: 1.0.0\n---\nMore.\n' > "$tmp/c.md"
mkdir -p skills/c && cp "$tmp/c.md" skills/c/SKILL.md && publish c
commit -m "release: c" -m "Skill-Craft-Release: c@0.1.0"
sed -i.bak 's/^version: 1.0.0$/version: 2.0.0/' skills/c/SKILL.md && rm skills/c/SKILL.md.bak
commit -m "docs: c body" -m "No-Change-Note: body example only"
out="$(boundary --base "$base")" || true
[[ "$out" != *"skills/c/SKILL.md (version)"* ]] || fail "a body version: line was read as the card version: $out"
sed -i.bak 's/^version: 0.1.0$/version: 0.2.0/' skills/a/SKILL.md && rm skills/a/SKILL.md.bak
commit -m "bad: hand bump" -m "No-Change-Note: fixture"
fails "a front matter version edit" "skills/a/SKILL.md (version)"

# A7: a base missing from the clone is a clear error, not a traceback.
fixture a7
out="$(boundary --base 0123456789abcdef0123456789abcdef01234567)" && fail "a missing base must fail"
[[ "$out" == *"not a commit in this clone"* ]] || fail "missing base not explained: $out"
[[ "$out" != *Traceback* ]] || fail "missing base raised a traceback: $out"

printf 'release-boundary.test.sh: PASS\n'
