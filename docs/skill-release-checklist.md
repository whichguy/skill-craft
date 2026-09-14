# Skill release checklist (skill-craft → skill-craft-market)

After shipping a skill package change to `main`:

1. **Green suite** for that skill (`bash test/<skill>.test.sh` or `bash test/run-all.sh`).
2. **Plugin views and native catalogs in sync:** `bash scripts/sync-plugin-views.sh`, then
   `bash scripts/sync-plugin-views.sh --check`. Full sync also regenerates the Grok/Cursor
   catalogs and README inventory. Commit generated metadata with the package change.
3. **Tag** skill-craft at the ship tip, e.g. `git tag -a v0.3.2 -m "…" && git push origin v0.3.2`.
4. **Market pin:** only root skill-craft-market `.claude-plugin/marketplace.json` (no second catalog under `faces/`):
   - `source.path` = `plugins/<skill>` (not bare `skills/`)
   - `source.sha` = the full 40-character commit SHA containing the package
   - `source.ref` = the new tag (optional reachability label; the SHA fixes package bytes)
   - Catalog repair fallback: if the current package is already published on `main`
     but untagged, use `source.ref: "main"` plus a full `source.sha`. Verify that
     commit is reachable from `main` and check the manifest at the SHA; do not
     represent it as a tagged release.
   - `version` = SKILL.md / `plugin.json` version field (must match at that SHA)
   - Advance **this leaf only** when its content/version changes — **no bulk retarget** of content-identical pins
5. **Verify the catalog** from skill-craft-market: run
   `python3 scripts/check-catalog.py --skill-craft-root ../skill-craft`,
   `python3 test/catalog.test.py`, `python3 test/pins.test.py`, and
   `python3 scripts/check-pins.py`. The remote check reads manifests and skill
   bodies at their SHAs; private sources require an existing `GH_TOKEN` with read access.
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

**External leaves** (e.g. lennox-s40): pin the standalone repo in the market; never re-add `skills/<same-name>/` to this monorepo (`test/dual-body-guard.test.sh`).
