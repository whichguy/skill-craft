# Skill release checklist

Source and release output are separate. Feature work edits source under
`skills/`, `agents/`, `bundles/` and `catalog/` and adds a change note. Only a
release commit changes versions, `plugins/`, the four host catalogs, the README
inventory and `CHANGELOG.md`.

## Every change

1. Edit the skill. Do **not** edit its `version:` or anything under `plugins/`.
2. Add `changes/<leaf>/<slug>.md` with `bump: patch|minor|major` and a line or
   two for people who install it ([format](../changes/README.md)). An
   `agents/<leaf>.md` card edit needs one too. A change nobody needs to
   receive as an update may instead carry a `No-Change-Note: <reason>` commit
   trailer; it excuses only the commit that carries it. Put trailers in the
   message's final paragraph, together with `Co-Authored-By:` and no blank
   line between them.
3. Test against a build from source: package tests do this themselves through
   `test/package_build.py`; `python3 scripts/build-packages.py <new-dir>` builds
   the same output by hand. Start with `bash test/run-all.sh --group smoke`
   and the affected suites; the full aggregate (`bash test/run-all.sh`) is for
   concrete cross-subsystem risk. Record the tested SHA and tree.
4. CI's `release-boundary` job runs `scripts/check-release-boundary.py --base`
   over the pushed range. It rejects ordinary commits that edit release output,
   skip a note, or delete a note that was pending before the range (only
   `release.py` consumes notes), and pending notes that `release.py` would
   refuse. It checks each release commit out in a temporary worktree and
   requires its output to match its own source.
5. **Land** the pull request with a merge commit or a rebase/fast-forward,
   never a squash. A squash folds the messages into one, which moves
   trailers out of the final paragraph (and can fold a release commit into
   ordinary work), so the push check then fails on `main`.

## Release

1. **Fresh canonical checkout.** Apply the local checkout policy: clean `main`,
   `git fetch origin`, `git merge --ff-only origin/main`.
2. **Preview:** `python3 scripts/release.py --dry-run` lists each skill's old
   and new version.
3. **Cut:** `python3 scripts/release.py`. It bumps versions, writes
   `CHANGELOG.md`, deletes the consumed notes, regenerates `plugins/`, the
   catalogs and the README inventory, checks them, and makes one commit with a
   `Skill-Craft-Release:` trailer. It never pushes. A failed release restores
   the checkout to HEAD and keeps the notes: fix the problem and rerun. Never
   commit release output by hand.
4. **Qualify** the release commit at the tier the notes call for. The opt-in
   `marketplace-claude`, `marketplace-grok`, `marketplace-codex`, and
   `marketplace-codex-ask-agent` targets of `test/run-integration.sh` exercise
   real host CLIs in disposable profiles. Record host versions; anything not
   run stays explicitly unverified.
5. **Publish** with [guarded publication](#guarded-publication). Users refresh
   with `claude plugin marketplace update skill-craft-market`,
   `codex plugin marketplace upgrade skill-craft-market`, or the Grok and
   Cursor equivalents in [distribution.md](distribution.md). Skill-directory
   users (`./install.sh`) track the checkout and need no release.

A change with a note always ships at a new version; a source change carrying
`No-Change-Note` ships with the next release at its unchanged version and
reaches only fresh installs. With no pending notes, `release.py` still cuts an
output-only release (trailer `Skill-Craft-Release: output-only`) when release
output no longer matches source, for example after a skill is deleted or
`LICENSE` or `catalog/` changes; `--dry-run` reports it as output drift.

### Rolling back

Never revert a release commit. Revert the source commit instead and add a
note; the next release ships the rollback at a new version. If a release
commit was already reverted, its card sits below the last released version, so
the note must set an explicit `version:` above that release: `release.py`
refuses any `<leaf>@<version>` that already appears in a `Skill-Craft-Release`
trailer.

## External plugins

Lennox S40, Until Loop and Workflow are published from their own repositories
and listed in `catalog/external-plugins.json` with a full 40-character `sha`.
Advance a pin only after verifying that commit. Edit
`catalog/external-plugins.json` in an ordinary commit (no note); the next
`release.py` run publishes it, as an output-only release when no notes are
pending. Never re-add
`skills/<same-name>/` for an external plugin (`test/dual-body-guard.test.sh`).

## Vendored bundle refresh

Backchain's development source (`whichguy/plan-orchestrator`) stays private. skill-craft publishes a hash-verified copy
of its `skills/backchain`, `skills/plan-dispatcher` and `agents/backchain.md`
as `bundles/backchain/`, generated into `plugins/backchain/`. CI proves only
that the bundle matches its own `PROVENANCE.json` and passes the publication
lint; it cannot see the private upstream. Refresh it deliberately:

1. **Upstream release first.** The upstream commit must be published on its
   `origin/main`, and the upstream `.claude-plugin/plugin.json` version must
   increase whenever any vendored byte changes (hosts use it as the update
   signal). The refresh refuses otherwise (exit 4). Its description must equal
   `bundles/backchain/bundle.json`; change bundle.json only in a reviewed edit.
2. **Fresh canonical checkout.** Apply the local checkout policy: clean `main`,
   `git fetch origin`, `git merge --ff-only origin/main`.
3. **Dry run and review.** `python3 scripts/sync-vendored-bundles.py --bundle backchain --from ../backchain`
   prints the upstream commit, version and changed paths. Read the actual diff:
   everything vendored becomes permanently public. The lint (home paths,
   email addresses, credential shapes, private IPs, hidden characters, and the
   operator's user name and git user.name) is heuristic and cannot recognize
   internal names or private context.
4. **Apply.** Rerun with `--write` and commit only `bundles/backchain` as an
   ordinary source commit (no note, no trailer). Then run
   `python3 scripts/release.py`: it releases every bundle whose upstream
   version differs from its `plugins/` package, with a
   `Skill-Craft-Release: backchain@<version>` trailer and a CHANGELOG entry.
   Do not run `sync-plugin-views.sh` or hand-write the trailer. A bundle needs
   no `changes/` note; its version comes from upstream.
5. **Verify.** `python3 test/vendored-bundles.test.py`, the core group, and the
   release gate for a multi-skill package on each host you ship to:
   `bash test/run-integration.sh marketplace-bundle-claude backchain` (also
   `-codex` and `-grok`). Record host versions.
6. **Lag check (optional, local).** `bash test/run-integration.sh vendored-bundle-lag backchain ../backchain`
   dry-runs a refresh against the checkout's fetched `origin/main` and never
   writes. Only exit 0 means the snapshot is current; every other exit means
   it is not shown current, and stderr says why:
   - 0: in sync.
   - 1: lag that a `--write` refresh would apply (payload or version differs),
     or a local bundle that fails its own verification.
   - 2: upstream unavailable or invalid, including drift that needs a
     deliberate edit (the upstream description no longer equals `bundle.json`,
     or a declared member is missing upstream).
   - 3: new upstream content fails the publication lint.
   - 4: lag the release policy refuses (bytes changed without an upstream
     version increase, a lower version, or a commit not on `origin/main`).
   - 5: `PROVENANCE.json` no longer matches its recorded upstream commit.
   - 64: usage error.

`install.sh` never installs bundle members: the canonical skill-directory links
keep pointing at the private checkout, and `--from` refuses `bundles/` and
generated `plugins/` paths plus copies whose plugin manifest names the
skill-craft repository, such as host plugin caches (exit 64).

## Guarded publication

Prepare and review a local merge candidate against the current remote base. The
candidate must contain that base and be clean, including non-ignored untracked files. Record
its full commit and tree IDs and the current remote branch ID. Run qualification
against those bytes; an identical tree may reuse recorded evidence. Then run:

```sh
python3 scripts/release-push.py --repo /absolute/release/worktree \
  --expected-head <full-candidate-commit> --expected-tree <full-candidate-tree> \
  --expected-base <full-remote-main-commit> \
  --check '["bash", "scripts/sync-plugin-views.sh", "--check"]' \
  --check '["python3", "scripts/check-marketplace-packages.py"]'
```

The checks are operator-selected argument arrays, executed sequentially without
a shell. They supplement the recorded qualification evidence; the helper does
not select tests or independently certify that evidence. A failing check stops
the operation. The helper rechecks the candidate, clean state and remote base
before one non-forced push of the frozen commit. A divergent remote update racing
the push is rejected by Git. It does not bypass hooks, server policy, or required
reviews; use the host's approved merge path where direct pushes are prohibited.
If a push result is uncertain, inspect the remote ref before retrying.
