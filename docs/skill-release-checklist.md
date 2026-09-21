# Skill release checklist (skill-craft → skill-craft-market)

Before publishing a changed skill package, freeze the candidate bytes:

1. **Version the changed leaf first**, including packaging-only changes. Do not
   change its version or package bytes after final verification without rerunning
   affected checks. Preserve unrelated work in shared checkouts.
2. **Plugin views and native catalogs in sync:** `bash scripts/sync-plugin-views.sh`, then
   `bash scripts/sync-plugin-views.sh --check`. Full sync also regenerates the Grok/Cursor
   catalogs and README inventory. Commit generated metadata with the package change.
3. **Verify the frozen candidate at the appropriate tier:** start with
   `bash test/run-all.sh --group smoke` and affected package checks such as
   `python3 scripts/check-marketplace-packages.py`. Smoke is partial evidence,
   not exhaustive regression evidence. Select additional suites from the changed
   behavior and its dependencies: runtime, durable-state, graph, callback and
   recovery changes need their affected regression suites, not automatically
   every repository suite. Use the complete hermetic aggregate
   (`bash test/run-all.sh`) or a manual CI full tier only for a concrete
   cross-subsystem risk that narrower checks cannot cover; record that reason.
   Delegate established-suite execution to the **test-runner** skill with the
   exact source identity, commands, expected evidence, deadline and retry policy.
   Keep selection and failure diagnosis with the parent.
   Do not repeat local full, PR full, and post-merge full runs when one qualifying
   run tested identical bytes; record the tested SHA and tree, and reselect only
   affected checks if bytes change. A manual full CI run is started with
   `gh workflow run ci.yml --ref <candidate-branch> -f tier=full`; confirm its
   tested SHA and tree still match the final candidate before relying on it. It is
   qualification evidence, not a replacement for the required PR smoke check.
   The opt-in `marketplace-claude`, `marketplace-grok`, `marketplace-codex`,
   and `marketplace-codex-ask-agent`
   targets of `test/run-integration.sh` require actual host CLIs and disposable
   profiles, not personal installs. Record host versions and separate parser,
   installation, installed-script and model-workflow evidence. For Ask Agent,
   record `identity --skill-card` from the host-selected package; a same-name
   skill-directory link does not identify an independently installed plugin copy.
   Any unavailable
   check stays explicitly unverified. Then, with publication authorization,
   commit/publish the source and **tag** the verified tip (no further byte changes).
   For an authorized direct fast-forward publication, use the guarded push below
   so a failed precondition cannot be followed accidentally by a separate push.
   Protected-branch reviews, checks and merge-queue requirements still apply.
4. **Market selection:** only root skill-craft-market `.claude-plugin/marketplace.json` (no second catalog under `faces/`):
   - `source.path` = `plugins/<skill>` (not bare `skills/`); Backchain uses its standalone package root.
   - Ask Agent, ShipLoop, Improve and Backchain follow the latest published `main` with `source.ref: "main"` and no `source.sha`. Validate the resolved commit once and retain that exact SHA in release evidence; a floating entry is not an immutable pin.
   - Other entries retain their full 40-character `source.sha` and optional tag/ref reachability label. Do not retarget unrelated leaves.
   - `version` must match the selected package's SKILL.md / `plugin.json` at the resolved commit. Bump each changed package on every release: hosts may cache by this version, so following `main` does not promise refresh for an unversioned intermediate commit.
   - Refresh the marketplace and installed plugin through the host before claiming local activation. Publication alone does not update an existing host session.
5. **Verify the catalog** from skill-craft-market: validate shape with
   `python3 scripts/check-catalog.py --skill-craft-root /absolute/source/checkout`
   and verify every changed release payload with
   `python3 scripts/check-release-payload.py --base <previous-catalog-commit>`.
   The release-diff gate reads complete packaged trees at each changed entry's
   exact pinned or once-resolved SHA; it does not silently upgrade unchanged
   legacy pins.
   Run affected verifier tests when changing verifier code, and collect required
   catalog CI for the exact candidate. Reuse its unchanged-tree evidence instead
   of repeating the same unit bank locally and after merge.
   `python3 scripts/check-pins.py --full-payload` remains available for a complete
   catalog audit or changed shared verification rules; an individual pin update need
   not requalify every unchanged payload. Private sources require an existing
   `GH_TOKEN` with read access. The default pin check without `--full-payload`
   explicitly reports that complete payload readiness was not checked.
6. **Push market** and operators run `claude plugin marketplace update skill-craft-market`
   or `codex plugin marketplace upgrade skill-craft-market` for a Git-backed catalog.
   Local registrations read their checkout. Codex reads the same Claude-compatible catalog;
   use `codex plugin list --marketplace skill-craft-market --available --json` to verify discovery.
7. skill-dir users: `./install.sh --skill <skill>` (tracks checkout; no tag required).
8. Grok/Cursor distribution: publish the source repo revision containing the generated
   native indexes and package manifests. See [distribution.md](distribution.md) for
   host refresh and Cursor submission/import steps. A local JSON file alone does not
   create a public marketplace listing.

Pin lag after ship is a bug: marketplace install must not serve pre-ship wording.

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
If a push result is uncertain, inspect the remote ref before retrying. Publish
tags and catalog pins only after verifying the source commit on the remote.

**External leaves** (e.g. lennox-s40): pin the standalone repo in the market; never re-add `skills/<same-name>/` to this monorepo (`test/dual-body-guard.test.sh`).
