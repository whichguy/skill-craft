# The brownfield calibration's noise: another project's server answering on the same port (2026-11-01)

**Question.** `shiploop-e2e-brownfield-tickets` (24 tests that grade the variants of two cases and, since `4b62715e`, of a third, `ticket-import`) failed in most local executions: 1 to 2 of its tests,
for example `test_a_disagreeing_grade_is_rare` with 6 results re-graded against a cap of 4 at load 88, and 11 at load 64 on the unchanged parent (2026-10-31). The cause on record was load ("about one
reset in two hundred concurrent `node --test` runs, never twice in a row, and never in a run alone"). What is it, and what should the suite do?

**What was run.** All at low priority (`nice -n 10`), on a machine whose load average was 21 to 230 from other sessions. The drivers and probes are in this folder and take their checkouts as arguments.
- `flake_probe.py` (driven by `run_probes.sh`): the suite's own `graded()` once, with every first grade that disagreed logged; pool 16 and pool 6 alternately.
- `node_probe.py`: only the part that fails, the base's own `node --test` run 16 at a time in 16 copies of the fixture, for 8, 10 and 40 rounds.
- `compare_flake.sh`: the whole suite, the logic of main against the new logic, alternating.

**Results.**

| probe | what | result |
|---|---|---|
| d1, s1, d2, s2 | `graded()`: pool 16, 6, 16, 6; 126, 170, 111, 152 s; load at the end 106, 64, 122, 66 | first grades that disagreed: 4, 8, 0, 1 (the cap was 4). All 13 were `node --test` runs of the base's tests. |
| n1 | 128 concurrent `node --test` runs | 8 failed (6.3%): 4 resets, 4 wrong answers |
| n2 | 160 runs | 1 failed (0.6%): a reset |
| n3 | 640 runs | 23 failed (3.6%): 14 resets, 9 other (the 6 kept in `nodeprobe-n3.json` are all failed assertions) |
| n1 to n3 | 928 runs | 32 failed (3.4%): 19 resets, 13 wrong answers |
| listeners | `listeners-snapshot.txt`, during n3 | 560 on the IPv6 wildcard (557 node), 32 bound to a specific IPv4 address (25 of them node or Python servers on 127.0.0.1) |

**What a wrong answer looks like** (n3, `nodeprobe-n3.json`): `AssertionError: {"game":"g"}` with `200 !== 404`; `{"gameId":"x2","size":10}` with `200 !== 400`; and four with a null body and a status of 404 where 200,
400 or 409 was expected. The first two bodies are JSON of another project's API (a game service), not of the tickets service under test; the other four are answers the test's own server, which has the
tickets the test just created, would not give. A reset reads `Error: socket hang up` with `code: 'ECONNRESET'`, 2 to 30 ms into a test whose server and client were both created for it.

**Reading.**
- Firm: the base's own tests fail in about 3 percent of runs when 16 run at once on this machine; a first grade of the suite disagrees 0 to 8 times an execution; the old cap of 4 sat in the middle of that. A pool of 6
  against 16 showed no difference in four executions (4, 0 against 8, 1).
- Firm for what was read, inferred for the mechanism: a request reached a server that is not the test's own. The base's tests start a server with `listen(0)`, which Node binds on the IPv6 wildcard, and the client
  connects to `127.0.0.1`. Other work holds listeners bound to `127.0.0.1` in the same port range. On this system a wildcard listener can be handed a port number that an IPv4 listener holds, and an IPv4 client then
  reaches that one. It fits both game bodies and the resets (the other server closing the connection), and it needs no load. It was not proven by watching the two sockets.
- Superseded (`docs/shiploop-brownfield-baseline-journal.md`, 2026-10-28): "about one reset in two hundred concurrent runs, never twice in a row, under load averages of 40 to 90". The rate was 3.4 percent on the day it was
  measured, half of it wrong answers and not resets, and what grows it is the number of other listeners, not the load. "Never in a run alone" was not tested here.
- Not fixable from the calibration: the fixture is pinned by its digest and is the E2E subject (changing it is the owner's call); Node refuses `--test-concurrency` in `NODE_OPTIONS`; and a classifier of resets
  (`NETWORK_FAILURE` in `checks/ticket_test_adequacy.py`) would have missed the 13 wrong answers.

**What changed** (`test/shiploop-e2e-brownfield-tickets.test.py`). A result that disagrees with its variant is graded again, alone, until a grade agrees, at most three more times (`settle`); the suite counts the
results whose first regrade disagreed too (`repeated`, at most 4) and puts the first disagreements (`regraded`) in the failure text. `CaseChecksTest`, which compared whole verdict lists once, gets the same regrade
(`expect`). A defect still disagrees every time, so it fails after four grades; a collision does not repeat, so it never reaches the cap. The first version of the change left `CaseChecksTest` alone and failed once
in two runs because of it (`cmp-v1/`).

**Comparison of the two logics** (alternating, the same machine, load 55 to 130; `compare-flake.txt`, `cmp-v1/compare-flake-v1.txt`):

| execution | old logic (main) | new logic |
|---|---|---|
| 1 | FAILED: `test_a_disagreeing_grade_is_rare` | passed, 28 tests (v1) |
| 2 | FAILED: the follow-on regression test | FAILED, 4 failures in `CaseChecksTest` (v1, before `expect`) |
| 3 | FAILED: `test_a_disagreeing_grade_is_rare` | (stopped, v1) |
| 4 (v2 1) | passed, 24 tests | passed, 28 tests |
| 5 (v2 2) | FAILED, 3 failures in `CaseChecksTest` | passed, 28 tests, 503 s |

Old logic: 1 execution of 5 passed. New logic with `expect` (v2): 2 of 2 passed; the first version, 1 of 2. Two more pairs were stopped so that they would not load a live Round 4 run.

**Limits.** Five and two executions are small samples. The probes ran at low priority, which starves the probed processes more than a normal run would and may overstate the rate. The mechanism is read from two
bodies and one listener count. One machine, one day. The live scoring (`checks/base_tests.py` on a delivery, which E7-F saw reset once) is not changed: a retry there could hide a delivery whose own server resets
connections, so whether it needs a treatment is left open.
