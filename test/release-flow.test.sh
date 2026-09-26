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
  skills agents catalog changes scripts plugins .grok-plugin .cursor-plugin .claude-plugin .agents \
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
echo "stale" >> plugins/skill-craft/README.md
git add -A && git commit -qm "bad: hand bump"
out="$(boundary --base "$base")" && fail "hand-edited release output must fail"
[[ "$out" == *"skills/architect/SKILL.md (version)"* ]] || fail "version edit not named: $out"
[[ "$out" == *"plugins/skill-craft/README.md"* ]] || fail "plugins/ edit not named: $out"
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
git log -1 --format='%(trailers:key=Skill-Craft-Release,valueonly)' | grep -q "skill-craft@" \
  || fail "release commit trailer lacks the bundle plugin"
shiploop_new="$(sed -n 's/^version: //p' skills/shiploop/SKILL.md | head -1)"
improve_new="$(sed -n 's/^version: //p' skills/improve/SKILL.md | head -1)"
bundle_new="$(python3 -c "import json; print(json.load(open('catalog/skill-craft-plugin.json'))['version'])")"
[[ "$shiploop_new" != "$shiploop_old" && "$improve_new" != "$improve_old" ]] || fail "versions not bumped"
grep -q "^version: $shiploop_new\$" plugins/skill-craft/skills/shiploop/SKILL.md || fail "bundled skill card not regenerated"
grep -q "\"version\": \"$bundle_new\"" plugins/skill-craft/.claude-plugin/plugin.json || fail "bundle plugin manifest not regenerated"
grep -q "\"version\": \"$bundle_new\"" .claude-plugin/marketplace.json || fail "Claude catalog not regenerated"
grep -q "### skill-craft $bundle_new" CHANGELOG.md || fail "changelog missing the bundle release heading"
grep -q "^- Skills: .*shiploop $shiploop_new" CHANGELOG.md || fail "changelog skills summary missing shiploop"
grep -q "### shiploop $shiploop_new" CHANGELOG.md || fail "changelog missing the release"
cmp -s skills/shiploop/SKILL.md plugins/skill-craft/skills/shiploop/SKILL.md || fail "plugin copy not refreshed"
boundary --base "$base" >/dev/null || fail "feature plus release must pass"
bash scripts/sync-plugin-views.sh --check >/dev/null 2>&1 || fail "release output must match source"
release_head="$(git rev-parse HEAD)"

# 5. Nothing pending (no notes, no drift) is a no-op with no commit.
python3 -B scripts/release.py | grep -q "no pending notes" || fail "empty release must be a no-op"
[[ "$(git rev-parse HEAD)" == "$release_head" ]] || fail "no-op release made a commit"

# Invalid notes fail the dry run and change nothing. Each case cleans up after itself.
dry_fails() { # <label> <expected message>
  local out
  out="$(python3 -B scripts/release.py --dry-run 2>&1)" && fail "$1 must fail the dry run"
  [[ "$out" == *"$2"* ]] || fail "$1: expected '$2', got: $out"
  git clean -fdq -- changes skills && git checkout -q -- changes skills
}
note() { mkdir -p "changes/$1" && printf -- '%b' "$3" > "changes/$1/$2.md"; }

# 6. A10: only the front matter's top-level version: counts, never a body line.
mkdir -p skills/zz-meta
printf -- '---\nname: zz-meta\ndescription: fixture\nmetadata:\n  version: 0.1.0\n---\nversion: 1.0.0\n' > skills/zz-meta/SKILL.md
cp skills/zz-meta/SKILL.md "$tmp/zz-meta.card"
note zz-meta fixture '---\nbump: patch\n---\nFixture.\n'
out="$(python3 -B scripts/release.py --dry-run 2>&1)" && fail "a body version: line must not count as the card version"
[[ "$out" == *"has no front matter version"* ]] || fail "body version not refused: $out"
cmp -s skills/zz-meta/SKILL.md "$tmp/zz-meta.card" || fail "failed dry run changed the card"
git clean -fdq -- changes skills

# 7. B2: versions are strict semver.
note c-plan fixture '---\nversion: 01.2.3\n---\nFixture.\n'
dry_fails "a leading-zero version" "version must be semantic"

# 8. B4: no downgrades, no note with both fields, no leaf mixing both kinds.
note architect fixture '---\nversion: 0.0.1\n---\nFixture.\n'
dry_fails "a downgrade" "not above current"
note c-plan fixture '---\nbump: patch\nversion: 9.0.0\n---\nFixture.\n'
dry_fails "a note with bump: and version:" "not both"
note c-plan one '---\nbump: patch\n---\nFixture.\n'
note c-plan two '---\nversion: 9.0.0\n---\nFixture.\n'
dry_fails "mixed bump: and version: notes" "mix bump: and version:"

# 9. B3: a bump from a prerelease finalizes it when it lands on the same line.
python3 -B - <<'PY' || fail "prerelease bumps"
import importlib.util
spec = importlib.util.spec_from_file_location("release", "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
cases = {("0.3.0-rc.1", "minor"): "0.3.0", ("1.0.0-rc.1", "major"): "1.0.0", ("0.3.1-rc.1", "minor"): "0.4.0",
         ("0.3.0-rc.1", "patch"): "0.3.0-rc.2", ("0.3.0-beta", "patch"): "0.3.0"}
for (version, bump), want in cases.items():
    got = release.bumped(version, bump)
    assert got == want, f"bumped({version!r}, {bump!r}) = {got!r}, want {want!r}"
PY

# 10. B6: a released version is never reused, even after the release is reverted.
git revert --no-edit HEAD >/dev/null
git commit -q --amend -m "Revert release" -m "Skill-Craft-Release: revert"
out="$(python3 -B scripts/release.py --dry-run 2>&1)" && fail "reusing a released version must fail"
[[ "$out" == *"already released"* ]] || fail "reuse not named: $out"
git reset -q --hard HEAD~1

# 11. B5: a never-released skill ships at its authored version; a released one cannot.
note shiploop fixture "---\nversion: $shiploop_new\n---\nFixture.\n"
dry_fails "a released skill at its current version" "not above current"
cp -R skills/c-plan skills/zz-new
sed -i.bak -e 's/^name: c-plan$/name: zz-new/' -e 's/^version: .*/version: 0.1.0/' skills/zz-new/SKILL.md
rm skills/zz-new/SKILL.md.bak
note zz-new first '---\nversion: 0.1.0\n---\nFirst release.\n'
git add -A && git commit -qm "feat: zz-new"
python3 -B scripts/release.py --date 2000-01-01 >/dev/null || fail "a new skill must release at its authored version"
[[ -d plugins/skill-craft/skills/zz-new ]] || fail "new skill missing from the bundle after its first release"
git log -1 --format='%(trailers:key=Skill-Craft-Release,valueonly)' | grep -q "zz-new@0.1.0" \
  || fail "new skill did not release at 0.1.0"

# 12. B8: one heading per date; blank body lines stay blank.
note c-plan same-day '---\nbump: patch\n---\nFirst line.\n\nThird line.\n'
git add -A && git commit -qm "fix: c-plan"
python3 -B scripts/release.py --date 2000-01-01 >/dev/null || fail "same-date release failed"
[[ "$(grep -c '^## 2000-01-01$' CHANGELOG.md)" == 1 ]] || fail "same date got a second heading"
grep -q '^### c-plan ' CHANGELOG.md || fail "same-date release missing from the changelog"
! grep -qE '[[:space:]]$' CHANGELOG.md || fail "changelog has trailing whitespace"

# 13. B1: a failed release restores the checkout and keeps the notes.
note c-plan rollback '---\nbump: patch\n---\nFixture.\n'
printf '#!/usr/bin/env bash\nexit 1\n' > scripts/sync-plugin-views.sh
git add -A && git commit -qm "test: broken sync"
before="$(git rev-parse HEAD)"
out="$(python3 -B scripts/release.py 2>&1)" && fail "a release with a failing sync must fail"
[[ "$out" == *"checkout restored to HEAD"* ]] || fail "rollback not reported: $out"
[[ -z "$(git status --porcelain)" ]] || fail "failed release left changes: $(git status --porcelain)"
[[ "$(git rev-parse HEAD)" == "$before" && -f changes/c-plan/rollback.md ]] || fail "failed release lost HEAD or its note"
git reset -q --hard HEAD~1

# 14. A1: a trailer does not exempt a commit whose output differs from its source.
pre_lag="$(git rev-parse HEAD)"
bundle_version="$(python3 -c "import json; print(json.load(open('catalog/skill-craft-plugin.json'))['version'])")"
sed -i.bak "s/\"version\": \"$bundle_version\"/\"version\": \"0.0.1\"/" plugins/skill-craft/.claude-plugin/plugin.json
rm plugins/skill-craft/.claude-plugin/plugin.json.bak
git add -A && git commit -qm "release: fixture lagging output" -m "Skill-Craft-Release: fixture"
lagging="$(git rev-parse HEAD)"
out="$(boundary --base "$pre_lag")" && fail "an out-of-sync release commit must fail the boundary check"
[[ "$out" == *"release commit output does not match its source"* ]] || fail "out-of-sync release not named: $out"

# 15. B7: deleting a skill cuts an output-only release that prunes it from the bundle.
git rm -rq skills/zz-new && git commit -qm "chore: remove zz-new"
python3 -B scripts/release.py --dry-run | grep -q "output drift" || fail "dry run must report output drift"
python3 -B scripts/release.py >/dev/null || fail "output-only release failed"
git log -1 --format='%(trailers:key=Skill-Craft-Release,valueonly)' | grep -Eqx 'skill-craft@[0-9]+\.[0-9]+\.[0-9]+' \
  || fail "output-only release trailer must name only the bundle plugin"
[[ ! -e plugins/skill-craft/skills/zz-new ]] || fail "deleted skill survived the release"
bash scripts/sync-plugin-views.sh --check >/dev/null 2>&1 || fail "output-only release must match source"
[[ -z "$(git status --porcelain)" ]] || fail "output-only release left changes"
grep -q "^### skill-craft " CHANGELOG.md || fail "output-only release missing its bundle heading"
grep -qxF -- "- Release output regenerated; no skill changed." CHANGELOG.md \
  || fail "output-only release missing its no-skill-changed changelog line"
boundary --base "$base" --head "$pre_lag" >/dev/null || fail "releases after the feature commit must pass the boundary check"
boundary --base "$lagging" >/dev/null || fail "releases after the lagging fixture must pass the boundary check: $(boundary --base "$lagging")"

printf 'release-flow.test.sh: PASS\n'
