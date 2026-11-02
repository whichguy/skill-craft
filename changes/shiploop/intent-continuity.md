---
bump: minor
---
Keep each run's full current spec in `RUN/current-spec.md`, initialized once from the exact prior aggregate. Planning, requirement checks, step packets, diffs and reviews use that candidate. Prior intent, deferred requirements and architecture decisions constrain the requested new work without becoming a repeated backlog.

Keep `docs/shiploop/spec.md` unchanged through early release returns. Final handoff reconciles prior intent and delivery evidence, requires the exact accepted review digest, and atomically promotes the full candidate with a recoverable, drift-checked record. Exact prior spec, architecture and environment snapshots remain in the run for continuity and recovery.

Returned planning packets and their reviews state the existing narrow protected-spec status-repair authority: use actual implementation/check evidence, preserve intent and prior work, and revalidate and review before accepting the step.

New runs use state version 12 and an explicit run binding. Older saved runs and mismatched copies are refused before mutation; retain their files and use their original ShipLoop package to resume, or start a fresh run.
