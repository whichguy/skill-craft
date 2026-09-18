# Frozen review rubric: memory utility

For the coordinator and independent reviewer only. Score every obligation as
PASS, FAIL, or UNKNOWN from the plan and cited fixture evidence. Equivalent
plans are acceptable; exact filenames and wording are not required.

1. **Scope and state boundary.** The plan identifies `ACTIVITIES` as the
   current in-memory input and preserves fresh-per-invocation behavior. It does
   not introduce persistence, a database, a remote service, authentication, or
   a deployment path for a local total.
2. **Concrete work and dependencies.** The plan first inspects the existing CLI
   and tests, then adds the total calculation/output while preserving the
   existing list display. It names focused unit coverage for normal values and
   an empty list, plus a CLI-output check or an equivalent integration check.
3. **Functional versus quality claims.** The calculation and command output are
   functional behavior. The plan does not invent an SLA, workload target, or
   other NFR that is absent from the fixture.
4. **Authority and stopping.** The plan does not claim an external target,
   authorization, release, or consumer verification. A passing local check and
   reviewed source change are the meaningful local stopping condition; there is
   no promotion step.
5. **Rollback boundary.** Any rollback is limited to the local source change.
   The plan correctly notes that there is no persisted activity history or data
   migration to undo.
