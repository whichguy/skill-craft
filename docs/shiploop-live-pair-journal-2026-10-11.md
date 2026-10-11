# Live pair on the 8-stage build: journal (started 2026-10-10 evening)

Question: does the build that carries the commit contract, the spec retire step, `architecture.md` and the 8-stage inner loop run a normal case end to end, and what do the new counters show? Method: `python3 test/shiploop_e2e/run.py --case hello --host claude --source checkout` on `13d278dd` (skill-craft 1.27.0 tree plus the unreleased changes), Claude Sonnet 5.5, output `/Users/dadleet/e2e-runs/20261010/hello-8stage-13d278dd` (not committed; compact extract in `docs/experiments/live-runs-20261011/hello-8stage-13d278dd.json`). The Checkers run follows when A2 (section-heading notice) is on main.

## hello (smoke), 13d278dd

**Status: firm for what happened in this one run; no change claim against 1.27.0** (a same-build hello cell on 1.27.0 ranged $3.06 to $5.35 and 126 to 196 turns, n=5; a single run cannot show a difference).

| Measure | This run |
|---|---|
| Outcome | PASS: `shiploop done`, both case checks pass, committed |
| Cost, turns, wall | $2.69, 148 turns, 491 s (planning window closed at test-spec after 3.8 min) |
| Commits in the product repo | 12, all ShipLoop's own (`script` class), 1 with a lessons section (release-verify's `Learned`); 0 Improve commits (the 5 Improve children changed nothing); 0 model commits |
| Knowledge home at the end | `README.md`, `architecture.md`, `environment.md`, `spec.md`, `test-strategy.md`, `features/README.md`, one feature folder without `spec.md` |
| ShipLoop command failures | 3, none repeated: `evidence_refs` cite loop files that do not exist; a result path that was not the current generated path; focused command ids with no `### <ID>` entry in the test-spec file |
| Packet heads measured | 2 of 49 (the model pipes most replies) |

## Findings

1. **The retire step ran.** The terminal close committed `docs(shiploop): retire <folder> spec: checked its requirement IDs against the living spec`, printed that the removal was committed and returned (fast-forward), and the feature folder ends without `spec.md`. `architecture.md` was written at plan and accepted at the prepare close with no refusal.
2. **Defect, observed once: the model wrote `docs/shiploop/features/README.md` itself, so ShipLoop's generated list never existed.** The model wrote it at the spec stage (`1c57117`, "record ... knowledge after spec": a two-line `# Features` list). ShipLoop then left it alone, as designed for a file that does not begin with its mark, and printed the "left ... as it is" notice at the close (twice in the event stream). Cause, from the packets: the intake, plan and release-verify packets say to link the feature list `features/README.md` from `docs/shiploop/README.md`, and at that point the target does not exist yet, so a careful model creates it. Consequence: the four commands that find a requirement ID in the features and the "removed at handoff" header are missing from this run's list. **Fix proposed (two parts, neither built):** (a) packet text owned by the inner-loop session: the link sentence should say "ShipLoop writes that file at its next knowledge commit; do not create or edit it"; (b) engine, mine: decide whether `write_feature_list` should adopt a list the model wrote earlier in the same run (a hand-written file at that path is indistinguishable from a model-written one without run state). Trigger for (b): the packet fix does not stop it in the next pair.
3. **Packets mention the retire and list correctly**, with absolute paths; no prepare refusal; the `ShipLoop knowledge notice:` section notices do not exist yet (A2).
4. The three command failures belong to the inner-loop session's area (loop contract evidence, result path, test-spec command ids); reported to it.

## Next
Checkers (source=checkout) once A2 is on main and the build includes the packet fix for finding 2, then the counters (`metrics.commits`), kept-notices, `ShipLoop knowledge notice:` lines and the hello and Battleship deltas are read for both runs.
