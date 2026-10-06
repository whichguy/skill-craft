# Planning review, 2026-10-05: the design and its evidence

The owner said "yes, do the planning review change" on 2026-10-05 and set a ceiling of 30 minutes for the planning
window (intake to the first `test-spec` accept). This directory keeps the read-only investigation that designed it, so
the evidence stays in the repository. The decision record is `docs/shiploop-planning-review-plan-2026-10-05.md`; the
SPEC carve-out is the second `S-10 carve-out` in `test/shiploop_e2e/SPEC.md`; the journal entry is `Planning review` in
`test/shiploop_e2e/LEARNINGS.md`. The run data the design rests on is in
`docs/experiments/shiploop-planning-time-20261005/`.

Labels in the files: [M] was read or run, [I] is inferred, "unknown" was not measured.

| File | What it is |
|---|---|
| `design-final.json` | The final design, pretty-printed from the investigation's last result: summary, option, modes (`stage`, `none`, and the conditional `once`, not built), engine changes, consumers, the SPEC carve-out text, increments I3, I0, I1, I2, I4, I5, quality risk, measurement plan, owner decisions D1 to D10, unknowns and the guard for the missing module. The owner resolved the decisions on 2026-10-05; the record lists them. |
| `design-draft.json` | The draft the two attacks read (it had a three-value option, an inert `once` and `none` in its first increment, and reworded the shared Improve sentences for every mode). Kept because the attacks' findings only make sense next to it. |
| `report-engine.txt`, `report-consumers.txt`, `report-value.txt`, `report-rules-and-wording.txt` | The four investigation reports: the engine and a prototype measured on a throwaway copy; who reads the schedule and what breaks; what the review is worth (minutes and quality); the owner's rules and the wording the host reads. Their scratch paths (`/private/tmp/...`) are gone with the session. |
| `attack-measurement-and-text.json` | Attack 1 (nine findings): the flip not gated on measurement, the window and clock, the one-sided quality statement, stage-mode byte identity, sequencing. |
| `attack-engine-correctness.json` | Attack 2 (ten findings): the probe judge accepting a run that ran nothing, the probe's refusal text, the `once` repeat clause and commit route, the flip's test footprint, fail-first claims, the packet scan, the first Improve card resolution. |
| `sonnet-plan-review-b1e196d.txt` | The commit message of a plan review catching a missing importable-server seam on a Sonnet 5.5 battleship run (skill-craft 1.16.0): the same defect class that cost Luna xhigh a 165.9-minute redo. The work repository is on the owner's machine and is not in this repository. |
| `e6b-excerpt.md` | The E6b result (the planning review with the platform-claim bullet caught 10 of 15 real plan-stage platform errors against 0 of 15), copied from `docs/shiploop-composition-state-experiments-2026-09-26.md` with its limits. |
| `probe_judge.py`, `probe_judge.out` | The first design of the test-author probe against the corrected one, on seven recorded outputs, using the judge this checkout ships. Re-runnable (`python3 -B probe_judge.py`); the rows are pinned as `PROBE_CASES` in `test/shiploop-test-loop.test.py`. Recorded at `7ad157cb`. |
| `passes.py`, `passes.out` | Per-pass minutes of the five Improve children of the Grok medium battleship run from review-file mtimes: 26 passes, the five first passes 13.3 minutes. The run directory is on the owner's machine, so the output is the record. |

## Readings

- Review is 54% (Luna xhigh) and 58% (Grok medium) of the planning window, 79 to 80% of that in the global trio.
- `none` leaves 26.8 to 30.3 of 72.7 minutes on Grok medium if no work moves into authoring, up to about 40 to 44 if the
  first-pass review work does (13.3 minutes in `passes.out`; the share that moves is unmeasured). On Luna xhigh it
  leaves 172.5 of 375.9 at best.
- Quality: Luna's 22 passes gave 5 warranted fixes; the planning review with the platform-claim bullet caught 10 of 15
  real plan-stage errors (E6b); a Sonnet plan review caught the no-loadable-seam class (`b1e196d`) that Luna's reviews
  missed at a cost of 165.9 minutes. The escape rate without review is unknown.
- The first design of the probe accepted a run that ran nothing; `probe_judge.out` shows the first design and the
  corrected one side by side.

## Notes on the files

- The task that asked for this directory named `result-4` and `result-5` of the investigation as the attacks. In the
  investigation's output `result-4` is the draft design and `result-5` and `result-6` are the two attacks; all three are
  here under the names above.
- The reports and the design cite figures labelled [M] that were measured in sessions whose run directories are not in
  this repository. Where the repository has the source (`docs/experiments/shiploop-planning-time-20261005/`), the
  figures were re-checked on 2026-10-05: window 72.7 and 375.9 minutes, Improve children 42.4 (26 passes) and 203.4 (22
  passes), the Luna redo 165.9 against 99.2, the E6b counts.
