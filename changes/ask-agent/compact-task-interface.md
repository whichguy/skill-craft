---
bump: minor
---
Make the compact task interface the standalone route for current workspaces and
explicitly selected worktrees. Support `mode: edit`, `report-only`, and
worktree-only `ephemeral`; worktree edits default to `delivery_mode: commits`,
with `patch` as an explicit alternative. Current edits have no automatic commit;
report-only makes no filesystem edits; ephemeral work returns findings and audit
metadata only, with no commit, patch, or code integration.

Before commit delivery, copy and verify the caller's exact `HEAD`, staged and
unstaged binary patches, nonignored untracked files, and existing root
`.gitignore` and `.claspignore` controls. Create base `S` in the child only: use
the original `HEAD` for a clean source; dirty layers that change the net tree
create a one-parent snapshot. A dirty net-zero source keeps `S` at its original
`HEAD` and records `snapshot.source_dirty`. Preserve the source capture and
patch layers, and do not rewrite copied worker files while updating the child
index. Have the worker commit only scoped contribution paths after `S` and
verify the complete ordered `S..C` range, residual paths, scope, and branch
position. Exclude `S` from returned commits.

After native completion, parent verification and target revalidation, allow a
clean captured source with an unchanged parent to cherry-pick the complete
verified range. For any source with `snapshot.source_dirty: true`, apply only
the verified contribution patch and preserve parent `HEAD` and index; never
add the private snapshot to parent history. Keep worker and
parent scripts limited to filesystem checks: native launch/collection,
integration, combined tests, acceptance and cleanup stay parent-owned. Preserve
the existing consumer-owned and orchestrated contracts, with separate source,
local-pilot and release claims.
