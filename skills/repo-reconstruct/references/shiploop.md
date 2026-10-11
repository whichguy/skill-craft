# Optional ShipLoop initialization

Use only for explicitly requested ShipLoop-ready documents. Inspect the selected
ShipLoop package's current knowledge-home contract when available; versions can
differ. Do not start a run or edit its state to import recovered knowledge.

The inspected 2026-10-11 contract uses `docs/shiploop/spec.md`,
`docs/shiploop/environment.md`, and `docs/shiploop/architecture.md`.
Use the roles and standard headings in [artifacts.md](artifacts.md). In environment
also use `## Skills`, `## ID convention`, `## Access and accounts`, and
`## Platform facts` for actual local skills, test naming/ID practice, access
aliases and platform evidence. Mark absent or unknown material explicitly.
There is no need to create an older test-strategy file, feature directory, or
extra knowledge-home index for this reconstruction.

Make the selected homes discoverable through the repository's existing README
or documentation index and its host-authored `SHIPLOOP.md` when present. Add
concise links during authorized initialization; reuse existing indexes instead
of introducing parallel ones. If no index exists, use the README as the entry
point. A missing `SHIPLOOP.md` does not require creating one solely for these
three files. With external output or an explicit files-only scope, report the
pending link/retention work rather than modifying files outside that scope.

Preserve `R-<n>` and `AD-<n>` IDs and `Retired`/`Superseded` histories. Link existing
team requirements and ADRs instead of replacing their authority. Mark recovered
records observed/documented, keep verification separate, and say initialization
does not accept intent. Do not invent test IDs or an ID scheme. A later ShipLoop
invocation revalidates this evidence and reconciles the requested change normally.

If the selected package cannot be inspected, state the convention used instead
of claiming current consumer validation. Writing these files is not evidence
that ShipLoop read, accepted, committed or delivered them.
