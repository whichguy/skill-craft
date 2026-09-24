# Change notes

Every change to a skill adds one note here instead of editing its version:

```text
changes/<leaf>/<short-slug>.md
```

```markdown
---
bump: patch
---
One or more lines telling people who install the skill what changed.
```

`bump` is `patch`, `minor` or `major`. To set an exact version instead, write
`version: 1.2.3` (strict semver). A note sets one or the other, never both, and
all pending notes for one skill use the same kind. An edit to the skill's
`agents/<leaf>.md` card needs a note too.

The new version must be above the current one and never already released:
`scripts/release.py` refuses a `<leaf>@<version>` that appears in any earlier
`Skill-Craft-Release` trailer. A new skill's first note uses
`version: <the version already in its SKILL.md>`; that is allowed only while
`plugins/<leaf>` does not yet exist at HEAD.

Prereleases: a `patch` bump stays on the rc line (`0.3.0-rc.1` becomes
`0.3.0-rc.2`). A `minor` or `major` bump that lands on the rc's own line
finalizes it (`0.3.0-rc.1` minor becomes `0.3.0`; `1.0.0-rc.1` major becomes
`1.0.0`); `version: X.Y.Z` also promotes an rc. A non-numeric prerelease such as
`0.3.0-beta` graduates on a `patch` bump (`0.3.0`).

Two branches never edit the same note, so notes do not conflict.
`scripts/release.py` turns pending notes into one release commit: it bumps
versions, writes `CHANGELOG.md`, deletes the notes, and regenerates
`plugins/`, the host catalogs and the README inventory. Only `release.py`
deletes a note that is already pending on the base branch.

CI (`scripts/check-release-boundary.py`) rejects ordinary commits that edit
versions or release output, skill changes without a note, and pending notes
that `release.py` would refuse. A change nobody needs to receive as an update
(for example a typo fix) can instead carry a `No-Change-Note: <reason>` commit
trailer; it excuses only the commit that carries it.

## Trailers and merging

Git reads trailers only from the last paragraph of a message, so keep
`No-Change-Note:` in the same final block as any `Co-Authored-By:` line, with
no blank line between them. Keys are case-insensitive. When the key is in the
message but git does not read it as a trailer, the guard's failure says so.

Land pull requests with a merge commit or a rebase/fast-forward, never a
squash. A squash folds every message into one, which moves trailers out of the
final paragraph, so the push check fails on `main`.

## Rolling back

Never revert a release commit. Revert the source commit and add a note; the
next release ships the rollback at a new version. If a release commit was
already reverted, the card sits below the last released version, so the note
must set an explicit `version:` above that release.

## Branches started before release output

The guard skips a commit when none of its parents contains
`scripts/check-release-boundary.py` (it prints `skip <sha> (predates the
release guard)`). That exemption is temporary. Commits made on top of the
guard, including every commit of a rebased branch, follow the note rules. To
move an older branch onto the new workflow:

1. `git rebase origin/main` (or merge it), resolving conflicts. Known conflicts:
   `test/test-groups.test.py`, `.github/workflows/ci.yml`,
   `docs/skill-release-checklist.md`, `test/shiploop-full-runtime.test.py`.
2. `git reset --soft origin/main` to collapse the branch into one staged change.
3. Restore release output from `origin/main`:
   `git restore --source=origin/main --staged --worktree -- plugins .claude-plugin .agents/plugins .grok-plugin .cursor-plugin`.
4. By hand, put each `version:` line in `skills/*/SKILL.md` and the README
   inventory block back to their `origin/main` values.
5. Add a `changes/<leaf>/<slug>.md` note for every skill the branch changed.
6. Commit, then run
   `python3 scripts/check-release-boundary.py --base origin/main`.
