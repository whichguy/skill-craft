# Ratchet pilot (2026-11-20)

An experiment apparatus for the owner's idea: build a request in one pass, then let tests and what was learned drive
every further pass. Design, registered scenarios, readings and results: `docs/ratchet-pilot-journal.md`. This is not a
released skill, and nothing under `skills/` changes.

| File | What it is |
|---|---|
| `ratchet.py` | The loop: spec, then cycles of build, tests, fix and delta. It owns the order and writes every prompt. |
| `gate.py` | The script-run checks that decide: every clause's acceptance command, the project's own checks, a syntax check. Standard library only; a copy goes beside each run. |
| `grade.py` | Instruments no session sees: held-out checks at every recorded stage (`snapshots`), the frozen suite against calibrated defects (`strength`), one table (`report`). |
| `cases.json` | The pilot's cases: requests copied verbatim from the E2E harness's own cases. |
| `mutate.py` | Seeded faults (the E2E harness's catalog) on the lines a delivery changed, or with `--unchanged` on the existing lines of the files it touched, run against its tests. No model. |
| `prove_fail.py` | Can each acceptance check of a run be made to fail? The checks run on the starting product, on a copy with one existing test made to fail, and on copies with one seeded fault. No model. |
| `one_session.py`, `program/` | One model session in a prepared folder, outside the loop's stages, and the texts, answer sheet and readers of the program of journal section 26. |
| `shiploop-gaps/` | Tests that pin five behaviours of ShipLoop's own validators on made-up inputs. Nothing under `skills/` changes. |
| `selftest_fake.py` | A scripted stand-in for the model that misbehaves once in each guarded way, and the assertions on what the run must record. |
| `review/` | The question sent to Sol 6.1 at max effort before building, and its verbatim answer. |
| `evidence/` | Compact results of the runs, added with each journal entry. |

## Run

Python 3.13 or newer (the E2E harness's host launcher needs it on macOS). Run from a worktree, with an output folder
outside the repository.

```sh
# the apparatus's own check, no model
python3 ratchet.py run --case selftest --host fake --fake selftest_fake.py --output "$OUT/selftest"
python3 selftest_fake.py "$OUT/selftest"

# the whole loop from a request
python3 ratchet.py run --case shared-expenses --host codex --model gpt-6.2-sol --effort high --output "$OUT/expenses"

# test strength: a correct reference laid in as the build, stop once the tests are frozen
python3 ratchet.py run --case ticket-due-times --host codex --model gpt-6.2-sol --effort high \
    --build-from "$REFERENCE_TREE" --stop-after tests --output "$OUT/due-suite"
python3 grade.py strength "$OUT/due-suite"

# a repair start: a defective product under an earlier run's frozen spec and suite
python3 ratchet.py run --case ticket-due-times --host codex --model gpt-6.2-sol --effort high \
    --start-tree "$DEFECT_TREE" --frozen-from "$OUT/due-suite" --output "$OUT/due-repair-version-two"

python3 grade.py snapshots "$OUT"/*/        # held-out checks at each stage
python3 grade.py report "$OUT"/*/
```

A reference or defect tree comes from the harness's fixtures: `python3 test/fixtures/quality/reference_due_times.py
DEST --variant NAME` (and `reference_ticket_assignment.py`), or the `node-orders` fixture with one folder of
`test/shiploop_e2e/fixtures/stand-ins/stand-in-rules/` copied over it.

## What a run leaves

`work/` (the product's Git repository, one commit a stage), `sessions/NN-<stage>/` (the prompt, the event stream),
`gates/NN-<label>.json`, `loops/` (Until Loop contracts and receipts), `tools/` (the copies a session is pointed at) and
`run.json`: sessions with their seconds, every gate, every snapshot commit, clauses per cycle, paths the script put
back, changed clauses it refused, the tamper log, and why the run ended.

`--max-cycles` and `--max-fixes` are limits of this apparatus so an unattended run ends; a run they end records
`stop: max-cycles` or `max-fixes` and is reported as stopped, not as a result.
