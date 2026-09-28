# ShipLoop spec lifecycle: long-lived spec, per-run change spec

Owner, 2026-09-27: on a blank repository ShipLoop's first run creates the
spec. Thereafter the **long-lived spec** is the baseline, and the spec a run
works from is the **change spec**: the incremental changes that run is asked to
make. When the changes are done, the long-lived spec is updated. `repo-distill
--init` produces the long-lived spec for an existing repository that has never
run ShipLoop. The same applies to the architecture record.

## Today (verified 2026-09-27, skill-craft exp/repo-distill-fe584c)

- **The references already say "delta".** `project-knowledge.md` and
  `requirements-definition.md`: the spec and plans describe the delta from
  verified behaviour; each affected requirement is preserved, added, modified
  or retired; "edit the authoritative home narrowly when the active step
  permits product edits; until then retain the proposed delta in the assigned
  spec".
- **The scripts update the long-lived spec during planning.**
  `shiploop_knowledge_home.py`: the `spec` stage keeps both
  `docs/shiploop/spec.md` and `features/<slug>/spec.md` up to date, and the
  `prepare` close requires and commits `spec.md` (and `architecture.md`)
  before any work item is built. `release-verify` requires only
  `outcome.md`, `environment.md` and `README.md`.
- **Consequences.** The long-lived spec claims behaviour that does not exist
  yet; a run that pauses or fails (both marked T3 runs did) leaves the
  baseline describing undelivered work; the change spec and the baseline
  drift into two copies of the same requirements; a blank repository must
  write a full long-lived spec at `prepare`.
- **Stable-ID protection exists**: a committed living spec (or architecture
  record) may not drop an earlier `R-n` (`A-n`); retirement moves it under
  `## Retired` with a reason.

## Target model

| File | Meaning | Written | Committed |
|---|---|---|---|
| `docs/shiploop/spec.md` (long-lived spec) | Delivered and observed behaviour: every requirement with a stable `R-n`, its status (`observed` from recovery or `repo-distill --init`; `accepted` once a run delivers or changes it with a recorded basis) and its evidence | Only at the end of a run that delivered, by merging that run's change spec | At `release-verify` |
| `docs/shiploop/features/<slug>/spec.md` (change spec) | The run's contract: for each affected requirement **preserve / add / modify / retire**, before and after, the request or decision behind it, new IDs reserved as the next free `R-n`; it cites unchanged long-lived sections by ID instead of copying them | At `spec`, revised through the existing correction route | At `prepare`, as today |
| `docs/shiploop/architecture.md` (long-lived) + change entries in `features/<slug>/plan.md` | Same pattern for decisions: the plan records `A-n` preserve / add / modify / retire; the merge applies them | Plan and step-plan record changes; merge at the end | At `release-verify` |

- **Blank repository: no special case.** There is no long-lived spec yet; the
  first run's change spec adds every requirement, and the end-of-run merge
  creates `spec.md`. One mechanism for first and later runs.
- **Existing repository, initialized:** `repo-distill --init` writes only the
  long-lived files (all requirements `observed`, anchored), no feature
  directory. The first run reads them as the baseline (current-system
  recovery's "existing with an adequate baseline: reuse").
- **Existing repository, not initialized:** today's current-system recovery
  runs; what it recovers stays in the run's notes and the change spec's
  preserve entries, and the merge writes the recovered-and-touched
  requirements into a new long-lived spec (still no exhaustive rewrite).
- **Paused, failed or abandoned run:** the long-lived spec is unchanged; the
  change spec and `outcome.md` record what was intended and what was not
  delivered. A resumed run merges when it completes.
- **Observed to accepted:** a requirement stays `observed` until a run
  preserves-with-verification, modifies or adds it on a recorded basis; the
  merge marks it `accepted` with that basis. Untouched observed requirements
  stay observed (the owner can accept them separately).

## Changes

ShipLoop (`skills/shiploop`):

1. `shiploop_knowledge_home.py`
   - `STAGE_FILES["spec"]` = `("{feature}/spec.md",)`: the spec stage writes
     only the change spec and reads the long-lived one.
   - `CLOSES["prepare"]` drops `spec.md` and `architecture.md` (the change
     spec and plan carry the run's intent; the long-lived files may not exist
     yet on a blank repository).
   - `CLOSES["release-verify"]` adds `spec.md` (and `architecture.md` when the
     plan changed a decision); `STAGE_FILES["release-verify"]` names the
     merge.
   - A merge check at `release-verify`, in the same code path as the ID-drop
     check (one mechanism): every `R-n` the change spec adds or modifies
     appears in `spec.md`; every one it retires is under `## Retired` with a
     reason; nothing else was dropped. Same for `A-n` against the plan's
     decision entries. Refuse `done` with the missing IDs named.
2. References: `project-knowledge.md` (knowledge-home table and the
   authoritative-home rules), `requirements-definition.md` (when the home is
   edited: at the end-of-run merge), `current-system-baseline.md` ("retain
   across runs" now happens at the merge), the spec-stage and release-verify
   guidance, and the Improve review focus (review the change spec against the
   long-lived baseline; at release-verify, review the merge against the change
   spec and the delivered evidence).
3. Tests: `test/shiploop-knowledge.test.py` (spec stage files, prepare and
   release-verify closes, merge check: add, modify, retire, a dropped ID, an
   unmerged added ID, blank repository creating `spec.md`); the navigator
   packet tests that list stage files.
4. E2E: the existing follow-on case (`battleship` then `battleship-scoring`)
   shows the target behaviour end to end: after run 1 `spec.md` exists; run 2's
   change spec modifies or adds IDs; `spec.md` changes only at run 2's
   `release-verify`. Add one hermetic check for "a paused run leaves `spec.md`
   unchanged".

repo-distill (`skills/repo-distill`):

5. `prompts/initialize.md` and `SKILL.md`: say that the output is ShipLoop's
   long-lived baseline (not a change spec), that every requirement is
   `observed`, and that no `features/` directory is written; record the source
   commit in `docs/shiploop/README.md` so a run knows what the baseline
   describes.
6. `spec-judge` is unchanged: it grades a long-lived spec (or a change spec's
   cited requirements) against the repository.

## Change admission (test/shiploop_e2e/SPEC.md)

- **Anchor:** S-11 (knowledge retained: the next run builds on it), S-1
  (scripts own state: the merge is script-checked), S-12 (one ID-check
  mechanism). Evidence: both marked T3 runs paused before delivery with a
  long-lived spec already committed at `prepare` describing unbuilt work.
- **Adversarial evaluation:**
  - *A run that finishes but whose merge is wrong* drops or distorts
    requirements. Mitigated: the merge check refuses missing added/modified
    IDs and dropped IDs; Improve reviews the merge. Tested hermetically.
  - *Concurrent runs reserve the same next `R-n`.* Accepted for now: ShipLoop
    runs one run per checkout; the merge refuses an ID collision with a
    different title, naming both.
  - *Resumed or older runs* planned under the old rule have already committed
    `spec.md` at `prepare`. One supported version: the new check applies to
    runs started after the release; an old paused run is restarted, not
    migrated.
  - *Packet growth:* one fewer file at `spec`, one more at `release-verify`;
    no rule text repeated.
  - *Cost:* the merge is one short documentation step at a stage that already
    writes `outcome.md` and `README.md`.
  - *Gaming:* a run could "merge" by pasting the change spec wholesale; the
    check requires IDs, not text, so Improve's merge review is the guard.
- **Non-regression:** the ID-drop protection, credential screen, and every
  other close are unchanged; `features/<slug>/` stays the per-run record.

## Owner decisions (2026-09-27)

1. Merge at `release-verify`, after delivery is verified.
2. Observed requirements a run did not touch stay `observed`.
3. **Architecture keeps today's rule**: discovery, research, plan and
   step-plan keep `architecture.md` current during planning, and `prepare`
   still requires it. Only the spec moves to the end-of-run merge; the
   architecture rows of the target model and change 1 are dropped.
