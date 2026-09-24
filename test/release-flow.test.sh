#!/usr/bin/env bash
# Release flow: ordinary commits add change notes; only scripts/release.py
# bumps versions and rewrites release output, and check-release-boundary.py
# enforces that split. Runs in a disposable repository built from the current
# working tree (no network, no pushes).
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
fail() { printf 'release-flow.test.sh: FAIL %s\n' "$*" >&2; exit 1; }
tmp="$(mktemp -d "${TMPDIR:-/tmp}/release-flow.XXXXXX")"
trap 'rm -rf "$tmp"' EXIT
repo="$tmp/repo"
mkdir -p "$repo"

(cd "$root" && git ls-files -z --cached --others --exclude-standard -- \
  skills agents bundles catalog changes scripts plugins .grok-plugin .cursor-plugin .claude-plugin .agents \
  README.md LICENSE .gitattributes | xargs -0 tar -cf -) | (cd "$repo" && tar -xf -)
cd "$repo"
export GIT_AUTHOR_NAME=test GIT_AUTHOR_EMAIL=test@example.invalid
export GIT_COMMITTER_NAME=test GIT_COMMITTER_EMAIL=test@example.invalid
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1
git init -q -b main . && git add -A && git commit -qm base
# The working tree may lag its last release; start from a released state.
bash scripts/sync-plugin-views.sh >/dev/null
git add -A && git commit -qm "release: baseline" -m "Skill-Craft-Release: baseline" --allow-empty
base="$(git rev-parse HEAD)"
boundary() { python3 -B scripts/check-release-boundary.py "$@" 2>&1; }

shiploop_old="$(sed -n 's/^version: //p' skills/shiploop/SKILL.md | head -1)"
improve_old="$(sed -n 's/^version: //p' skills/improve/SKILL.md | head -1)"

# 1. A feature commit edits source and adds notes: accepted.
echo "Release-flow fixture line." >> skills/shiploop/SKILL.md
echo "Release-flow fixture line." >> skills/improve/SKILL.md
mkdir -p changes/shiploop changes/improve
printf -- '---\nbump: minor\n---\nShipLoop fixture change.\n' > changes/shiploop/fixture.md
printf -- '---\nbump: patch\n---\nImprove fixture change.\n' > changes/improve/fixture.md
git add -A && git commit -qm "feat: fixture"
boundary --base "$base" >/dev/null || fail "feature commit with notes must pass"

# 2. Hand-editing a version or plugins/ is refused.
sed -i.bak "s/^version: .*/version: 99.0.0/" skills/architect/SKILL.md && rm skills/architect/SKILL.md.bak
echo "stale" >> plugins/architect/README.md
git add -A && git commit -qm "bad: hand bump"
out="$(boundary --base "$base")" && fail "hand-edited release output must fail"
[[ "$out" == *"skills/architect/SKILL.md (version)"* ]] || fail "version edit not named: $out"
[[ "$out" == *"plugins/architect/README.md"* ]] || fail "plugins/ edit not named: $out"
[[ "$out" == *"no changes/architect/*.md note"* ]] || fail "missing note not named: $out"
git reset -q --hard HEAD~1

# 3. A skill change without a note fails unless it opts out.
echo "typo" >> skills/c-plan/SKILL.md
git add -A && git commit -qm "fix: typo"
boundary --base "$base" >/dev/null && fail "skill change without a note must fail"
git commit -q --amend -m "fix: typo" -m "No-Change-Note: typo only"
boundary --base "$base" >/dev/null || fail "No-Change-Note trailer must satisfy the note rule"
git reset -q --hard HEAD~1

# 4. A dry run changes nothing; a release consumes the notes.
python3 -B scripts/release.py --dry-run >/dev/null
[[ -z "$(git status --porcelain)" ]] || fail "dry run changed the checkout"
python3 -B scripts/release.py --date 2000-01-01 >/dev/null || fail "release command failed"
[[ -z "$(git status --porcelain)" ]] || fail "release left uncommitted changes"
[[ -z "$(find changes -mindepth 2 -name '*.md')" ]] || fail "release left change notes behind"
git log -1 --format='%(trailers:key=Skill-Craft-Release,valueonly)' | grep -q "shiploop@" \
  || fail "release commit lacks its trailer"
shiploop_new="$(sed -n 's/^version: //p' skills/shiploop/SKILL.md | head -1)"
improve_new="$(sed -n 's/^version: //p' skills/improve/SKILL.md | head -1)"
[[ "$shiploop_new" != "$shiploop_old" && "$improve_new" != "$improve_old" ]] || fail "versions not bumped"
grep -q "\"version\": \"$shiploop_new\"" plugins/shiploop/.claude-plugin/plugin.json || fail "plugin manifest not regenerated"
grep -q "\"version\": \"$shiploop_new\"" .claude-plugin/marketplace.json || fail "Claude catalog not regenerated"
grep -q "### shiploop $shiploop_new" CHANGELOG.md || fail "changelog missing the release"
cmp -s skills/shiploop/SKILL.md plugins/shiploop/skills/shiploop/SKILL.md || fail "plugin copy not refreshed"
boundary --base "$base" >/dev/null || fail "feature plus release must pass"
python3 -B scripts/check-release-boundary.py --release-sync >/dev/null || fail "release output must match source"

# 5. Nothing pending is a no-op.
python3 -B scripts/release.py | grep -q "no pending notes" || fail "empty release must be a no-op"

printf 'release-flow.test.sh: PASS\n'
