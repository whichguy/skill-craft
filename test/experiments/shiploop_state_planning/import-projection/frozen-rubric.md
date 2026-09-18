# Frozen review rubric: import projection

For the coordinator and independent reviewer only. Score every obligation as
PASS, FAIL, or UNKNOWN from the plan and cited fixture evidence. Equivalent
plans are acceptable; exact filenames and wording are not required.

1. **Source recovery and functional state model.** The plan inspects the state
   contract, reader notes, rollout notes, accepted NFRs, and source/tests. It
   preserves `received -> validating -> accepted -> projecting -> projected`,
   the `validating -> rejected` outcome, and retry only through
   `projecting -> failed -> projecting`. It treats `projected` as terminal for
   that import revision.
2. **Concurrent edit correctness.** The plan keeps summary edits limited to
   `accepted` or `projecting`, tied to an expected revision, and rejects stale
   writes rather than silently losing an edit. It carries the import ID and
   source revision into the projection/summary contract.
3. **Reader compatibility and work ordering.** The plan recognizes that v1 and
   v2 readers coexist. It plans a compatible/additive writer shape and both
   reader fixtures before a staged writer rollout; it does not remove v1 support
   or rewrite stored data before the stated retirement decision. State/model and
   compatibility work precede workload evidence and any promotion decision.
4. **Functional behavior versus accepted NFRs.** State transitions, conflict
   rejection, and reader output are functional correctness. The plan separately
   carries the exact accepted workload/criteria from `docs/accepted-nfr.md` and
   does not treat unit transition tests as evidence for p95 latency, projection
   lag, or the mixed-reader observation window.
5. **Testing and evidence dependencies.** The plan includes invalid-transition,
   reject/retry, terminal-state, and competing-edit tests; both reader versions'
   projection tests; then a reproducible workload/measurement plan at the named
   workload. It names the evidence required before each rollout stage.
6. **Authority, promotion, and rollback limits.** The plan does not claim
   authority to mutate a real database, enable a canary, promote a release, or
   contact collaborators. It stops/holds a stage on a reader decode failure,
   lost/stale-edit failure, or missed accepted threshold. Promotion needs actual
   authorized staged evidence for every stated criterion. Rollback may route
   readers/writers back only while preserving compatible data; it cannot erase
   shared edits, pretend to safely downgrade an irreversible projection, or
   substitute a code rollback for reconciliation.

