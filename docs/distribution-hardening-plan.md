# Distribution hardening plan

## Outcome

Keep one canonical skill body while making discovery, local status, and release
verification dependable across Grok, Claude, Cursor, and Codex. This plan covers
the marketplace work; parallel CI and skill-runtime changes retain their owners.

## Changes and acceptance criteria

1. **Canonical ownership and immutable pins.** An external catalog source must not
   reuse a name owned by `skills/<leaf>`. Every remote pin records a full commit
   SHA. This migration retains every existing release ref; future pins may omit
   that optional label because the SHA already identifies the commit. Tests reject redirected
   canonical names, missing SHAs, and an empty source checkout. Validate all pins
   at their recorded commits without changing versions or release tags.
2. **Generated inventory and empty-source protection.** Full plugin sync generates
   the README inventory from the same frontmatter as native catalogs. Checks
   reject missing, duplicated, or stale inventory and refuse an empty source
   set before writing. Leaf-only checks remain independent of root metadata.
   Setup prose uses host paths and catalog references instead of copied counts.
3. **Accurate plugin status.** A cached Claude plugin is an active duplicate only
   with literal `enabled: true` evidence. Disabled and unknown records remain
   visible without a false warning; an enabled record cannot be hidden behind a
   disabled preferred marketplace or an earlier installation record. Tests run
   offline through the existing inventory override.
4. **Host verification.** Run focused packaging, ownership, installer-status, and
   group-registration checks. Verify a temporary Cursor plugin through its UI
   if supported, then remove that owned fixture. Keep discovery, actual package
   loading, and public marketplace submission distinct in the report.

## Boundaries

Adopt the reproduced correctness fixes using existing scripts and no new runtime
dependencies. Preserve external Until Loop and canonical Improve ownership.
Do not replace the existing Codex Improve pilot. The publication follow-up is
authorized to commit, merge, and push the distribution changes. Cursor marketplace
submissions and credential grants remain separate operator steps.
Keep concurrent work intact; only claim verification against a coherent snapshot.

## Completion record

Implemented the source inventory generator, empty-source guards, exact canonical
ownership checks, immutable catalog pins, pinned-body CI verification, and
conservative Claude cache status.
The migration adds missing SHAs without advancing release refs or versions.

Focused verification on 2026-09-14:

- Source: full sync check, native adapter regressions (including add/remove skill,
  stale inventory, missing/duplicate marker, empty source, and orphan package),
  sync/symlink regressions, frontmatter checks, scaffold checks, installer status
  S1–S23, install targets, and eight test-group registration tests pass.
- Catalog: source ownership/coverage check, seventeen catalog regressions, and
  setup-matrix flag validation pass. Claude validates the catalog; its warnings
  identify Codex-only `interface` and `policy` fields that Claude ignores.
- Pins: eleven hermetic verifier tests pass, including subdirectory paths and
  SHA-only sources. The authenticated live run verified manifests and skill
  bodies for all 21 entries at their recorded commits. Improve's shorter curated
  catalog description is the sole advisory; its name, version, and body pass.
  CI now invokes this same extracted verifier.
- Grok discovers all 18 entries from the native source catalog. Codex discovers
  all 21 entries from the local pinned catalog. All 18 source skills are
  readable on each requested host. Grok, Claude, and Cursor resolve all eighteen
  to the canonical source. Codex resolves seventeen there and retains its existing
  Improve pilot under `until-loop-v2/examples/improve`.
- Cursor loaded a temporary local package using the generated manifest shape,
  displayed version `0.0.1` and its one skill in Customize, and reported no matches
  after the owned fixture was removed. This verifies local package discovery,
  not public marketplace import or skill execution.
- Publication preflight exposed a legacy review-coverage test that compared an
  installed Cursor symlink with the temporary checkout. Its check now uses a
  disposable Cursor directory and preserves the install, validation, and source
  assertions; actual-host checks remain in the explicit integration runner.
- Independent review found no remaining behavior defect in the inventory,
  ownership, or status changes.

Initial local verification used source `d8b8432` and catalog `2e39a3f` plus the
distribution changes. Publication integrates source `05d59f6` and catalog `718deaa`
from upstream and rechecks the isolated release candidates. Focused distribution
checks are complete;
this does not claim a full runtime test of every skill on every host.
The user authorized commit, merge, and push on 2026-09-14. Cursor marketplace
submission remains a separate operator step.
The marketplace repository currently has no repository Actions secrets; configure
`MARKETPLACE_READ_TOKEN` with read access to private Backchain before expecting
its remote CI pin check to pass. No credential grants are included in publication.
