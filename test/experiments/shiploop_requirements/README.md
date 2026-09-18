# Spec reconciliation and NFR experiment

Preregistered 2026-09-17. Question: do the current ShipLoop prompts actually
retrieve existing requirements, preserve their conditions, resolve an explicit
change, and carry verifiable quality criteria across a fresh-context handoff?

## Plan and boundaries

1. Freeze the current dirty-worktree ShipLoop package, this plan, and `oracle.md`
   before any participant sees a fixture. Record hashes and exact Git HEAD.
2. Create four isolated on-disk repository fixtures. Requirements are in linked
   files, not pasted into trial prompts. No production data, credentials, remote
   calls, commits, deployment, or additional project dependencies are needed.
3. For each case, give a fresh host-default agent only its bootstrap and an
   actual rendered protocol-3 discovery packet. Let it inspect the repository
   and write discovery notes plus the current producer result. It must stop
   before the callback. Capture sources inspected and unresolved questions.
4. Copy each resulting repository and notes to a separate trial directory.
   Seed a separate spec-stage fixture and render its packet; this is not a live
   discovery-to-spec transition. A new agent receives no earlier conversation. It
   writes the spec candidate and verification plan in the run notes, preserving
   the source requirements. Missing material decisions must stay visible.
5. Independently grade all four discovery/spec chains against the frozen oracle.
   Re-run the two most consequential failures, or the override and ambiguity
   cases if all pass, in fresh contexts. Add a document-stage trial for those
   cases to inspect actual maintained-document edits and unaffected content.
6. Revise production guidance only for observed, attributable gaps. If revised,
   compare frozen old versus revised guidance on the same repository information
   in fresh paired trials (at least three cases, one held-out variant). Randomize
   pair presentation to a new judge; grade mandatory correctness before style,
   token estimates, or time. Retain failed outputs and original oracle unchanged.
7. Apply justified changes, rerun relevant routing/recovery checks, synchronize
   the generated plugin package, and independently review the final diff.

The coordinator creates **synthetic predecessor state** through the navigator's
pure APIs to obtain real packets at the selected stages. Its placeholder prior
results/Improve receipts solely establish the selected action's preconditions
and are marked fixture setup, never an observed Improve outcome. Participants
do not submit callbacks or invoke Improve. This tests repository retrieval,
specification, document changes, and cold interpretation of real packets; it is
not a complete ShipLoop/Improve execution, product test, or deployment benchmark.

Fresh sessions use `fork_turns=none`, host-default model/reasoning, and no model
override. Participant scope is an instruction boundary, not a filesystem sandbox.
Participants may read only their assigned fixture, frozen skill, and bootstrap;
they may edit only assigned notes/results and, at document stage, product docs.
No participant sees the oracle, other cases, another answer, or grading notes.
Each participant writes `sources.md`, `artifact.md`, the current producer's
`result.json`, and `status.md`. The latter separates `current_stage_status`
(drafted for review or blocked) from `feature_acceptance_status` (unproven).
`sources.md` identifies the actual product files personally inspected in that
session; a predecessor's summary is not evidence of independent source retrieval.
These are experiment observations, not new ShipLoop result fields.
Judges get frozen inputs, a private source map identifying linked required versus
optional sources, and unedited outputs. Missing evidence is UNKNOWN,
never PASS. No claims about arbitrary models/hosts or statistical reliability.

## Cases

| Case | Current change | Deliberate difficulty |
| --- | --- | --- |
| Preserve | Add a category filter to an offline inventory catalog | Approved p99/workload, keyboard picker, no raw-filter/item-description logging, 72-hour retention exception and unrelated exact text span multiple natural homes; code/test prose conflicts with privacy. |
| Override | Change p99 bound from 420 to 275 ms at the existing workload; add a category filter | Preserve units, percentile, workload and other clauses; newer unapproved draft suggests removing keyboard support. No extra approval for the explicit replacement. |
| Ambiguity | Make catalog filtering faster and add category filter | Two accepted sources disagree on retention (72 hours versus 14 days), a relevant linked accessibility appendix is missing, and no new latency target was specified. Preserve the known bound and isolate dependent decisions. |
| Proportional | Add sorting to an existing local command-line text tool | README is the authoritative contract; do not create service SLAs, browser accessibility levels, cloud infrastructure, invented numeric targets, or a competing spec. |

Fixtures and per-case oracles are frozen before launch. An oracle must not demand
an undiscoverable fact or a product behavior absent from accepted input evidence.
The held-out comparison variant, if a revision is needed, adds an explicit
same-request user clarification to Override: use 250 ms instead of 275 ms. The
participant receives this as a current user instruction in its bootstrap, while
an unapproved host note proposes 900 ms. The original packet request is retained.

## Budget and stopping

Target 45 minutes of experiment operation; maximum 75 minutes, with 10 minutes
reserved for grading and reporting. At most 18 participant contexts and four
judge contexts; at most four participants run concurrently. Each gets 6 minutes
and a recommendation to keep outputs under 1,200 words (not a success metric).
Timeouts and missing results remain incomplete. Do not tune the oracle after
seeing results or keep retrying until green. A material regression rejects a
candidate even if its overall wording score wins. A small clean replication
supports bounded adoption, not universal compliance.

Record start/completion-detection times and input/output character counts. Label
char/4 estimates and wall time as partial measurements: tool reads, hidden
reasoning, backend identity, and exact billed tokens are not controlled here.

## Evidence

Raw evidence is external to the product tree. The final report records its
local study identifier, frozen hashes, every launched/completed trial and judge,
PASS/FAIL/UNKNOWN criteria, changes made, rerun outcomes, partial text-size
measurements, and limitations. It does not claim measured billing costs or public
availability of the raw evidence.
No experiment output is treated as an accepted product or actual Improve receipt.

## Reusing the fixture helper

Preparing fixtures requires Python 3 and a working Git executable so initialization
can record the exact checkout HEAD. The focused unit tests mock that Git boundary;
the commands below exercise real initialization separately. From the repository
root, choose a new directory outside this checkout:

```sh
study_dir=$(mktemp -d /tmp/shiploop-requirements.XXXXXX)
python3 test/experiments/shiploop_requirements/study.py initialize --output "$study_dir"
python3 test/experiments/shiploop_requirements/study.py prepare --output "$study_dir"
```

The helper does not launch models. Give each fresh participant its generated
`bootstrap.md` and enforce the plan's boundaries. Once a discovery participant
has produced its four notes, prepare the corresponding cold spec trial:

```sh
python3 test/experiments/shiploop_requirements/study.py next --output "$study_dir" --case override
python3 test/experiments/shiploop_requirements/study.py audit --output "$study_dir"
python3 test/experiments/shiploop_requirements/test_study.py
```

Repeat `next` for each completed case. Audit reports structural observations,
never a semantic pass. The base helper covers discovery/spec; the recorded study
uses separately frozen supplemental setup scripts for document edits and paired
comparison. Their exact paths, hashes, grading corrections, timeouts and observed
diffs belong in the [study report](../../../docs/shiploop-nfr-validation-2026-09-17.md).
These opt-in model trials are not part of the hermetic test suite.
