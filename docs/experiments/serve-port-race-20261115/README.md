# `serve.py`'s port race: a candidate that exits before it listens (2026-11-15)

**Question.** `shiploop-e2e-ticket-comments` failed once on CI (run 43669277848, attempt 2, job 132681484968, `full / shiploop-2`): the `persisted`
check's candidate "exited (rc 1) before it listened on PORT=55427", and the record cut off the error's name. What is the error, how often does it
happen, do `shiploop-e2e-ticket-sla` and the other suites that start servers through `checks/serve.py` share it, and what is the narrowest mend?

**Where the result is read.** `docs/local-validation-journal.md`, Round 6 (F23 updated, F24). This folder holds the evidence it cites. The CI failure's own
excerpt is `docs/experiments/git-maintenance-lock-20261114/ci-attempt2-failure-excerpt.txt`.

| File | What it is |
| --- | --- |
| `ci_history.py`, `ci-history.json.gz`, `ci_summary.py`, `ci-history-summary.txt` | The CI history (941 jobs of 476 runs since 2026-10-31): the collector (read-only `gh api` calls), its data, and the tables. |
| `pinned_port_demo.py`, `pinned-ports-linux.jsonl`, `pinned-ports-macos.jsonl` | What the candidate and serve.py do when the port they are handed is taken, by seven kinds of socket, on Linux and on macOS. |
| `port_pool.py`, `port-pool-linux.txt`, `port-pool-macos.txt` | Which port numbers the kernel hands out, by each way this harness asks for one. |
| `serve_race_probe.py`, `run_matrix.sh`, `matrix-linux.jsonl`, `matrix-linux-v2.jsonl`, `matrix-macos*.jsonl`, `rate_summary.py`, `rates.txt` | The rate half: the real serve.py called many times at once, with neighbours that bind ports, on Linux and on macOS; the rows and their intervals. |
| `matrix-linux-retry.jsonl`, `matrix-macos-retry.jsonl` | The same probe against serve.py with its retry (section 8). |
| `bad_ports.py`, `macos-bad-ports.txt` | Why the same twelve port numbers failed in every run on macOS (addresses not kept). |
| `tap/sitecustomize.py`, `run_tap.sh`, `tap-summary.txt` | A tap that counts how many times each suite starts a candidate through serve.py and how those runs ended. |
| `lsof_shim.py` | The one lsof call serve.py makes, for the Linux container that has no lsof. Used only there. |
| `wiring_probe.py`, `wiring-results.txt` | The follow-up (below): a suite's calibration classes run with the first grade of every delivery handed a held port, with the regrade as shipped and with `--regrades 0`. |

## What was run, and where

- **Linux**: a container (OrbStack, kernel 7.2.12, Node v26.12.1, Python 3.14.9, `--cpus 4`, no network) with this checkout mounted read-only. serve.py,
  `listeners.py` and the delivery are the repository's; only `lsof` is the shim. CI's runner is Ubuntu 26.04 with Node `v27.0.0-alpha.0.1.0` (the job
  log), so the kernel and Node differ and the Node frames of the CI record (`callSetupListenHandle`) are not Node 26.12.1's.
- **macOS**: this machine (Darwin 27.2.0, Node v26.12.1, Python 3.15.1, real lsof), at low priority, with the other work that was on it (load average 7 to 16).
- The candidate is the `reference` delivery of the `ticket-comments` case (`reference_ticket_comments.build`), started as the case's checks start it
  (`node src/server.js`), with `-- true` as the check, so each call is one `free_port()`, one Popen and one wait for the candidate.
- Sections 1 to 7 measured `checks/serve.py` as it was before its retry (commit `f8aa961c` and the ones before it); `matrix-*-retry.jsonl` (section 8) measured the
  serve.py that has the retry, which waits through `candidate_problem` where the older one waited through `wait_for_candidate`.

## Results

**1. CI history (`ci-history-summary.txt`).** Every one of the 941 job logs could be read. `shiploop-e2e-ticket-comments` ran 181 times (96 quick, 85 full), 180
OK and 1 FAIL, the failure in question; `shiploop-e2e-ticket-sla` 84 times, 84 OK. One job log in the 941 names a port collision with the words of serve.py or
Node (this one). Two other failures among these suites are in the family or near it, and are not this signature: `user-directory`'s calibration on 2026-11-05
(run 42133217612, a hidden check answered by another server; mended by `f1399b5b`'s ownership check) and `brownfield-tickets` on 2026-11-01 (a held-out check
raised `FileExistsError`, not a port). All 112 jobs on Node `v27.0.0-alpha.0.1.0` came on or after 2026-11-12; `ticket-comments` failed 1 of 22 times on it and 0 of 159
before (the chance that the one failure falls among those 22 by luck is 22 of 181, 12 percent, so a Node effect is neither shown nor excluded).

**2. What the CI record cut off.** serve.py's `tail()` keeps the last 600 characters of the candidate's whitespace-collapsed stderr, and the calibration test printed the
first 300 characters of the check's output. The visible text starts inside the first stack frame (`dle (node:net:...)`, the end of `setupListenHandle`), so the
error line before it fell off the front, and `code: 'EADDRINUSE'` after it fell off the end.

**3. The error and what produces the record's message (`pinned-ports-*.jsonl`).** On Linux every kind of socket on the port stops the candidate with
`Error: listen EADDRINUSE: address already in use :::PORT`, code `EADDRINUSE`. serve.py's message depends on whether the holder is still a *listener* when its first lsof
look comes: a listener (a Node wildcard, IPv4 or IPv6 listener) gives "port N is answered by pid H, not by the candidate", and a holder that is not a listener (a
bound socket, an established connection's local port) gives exactly the CI line, "the candidate exited (rc 1) before it listened on PORT=N: Error: listen EADDRINUSE: ...".
So in the CI event the holder was not a listener at that moment, or had gone. On macOS an IPv4 or IPv6-specific listener does not stop a candidate that binds the
IPv6 wildcard (both listen; serve.py's ownership check then refuses), only a wildcard IPv6 holder does, and neither a bound socket nor a loopback connection does (a connection from an address that is not loopback does: section 6).

**4. The pool a collision is drawn from (`port-pool-*.txt`).** Linux: `free_port()`'s port is always odd and drawn over the whole range 32768 to 60999 (14,116 numbers);
a Node `listen(0)` is always odd and from the lower half only (7,058); a `connect()` source port is always even. The count of distinct ports in 2,000 draws (1,868 and
1,733) is what uniform draws from 14,116 and 7,058 numbers give (about 1,865 and 1,742). macOS hands out one sequential counter (49152 to 65535) to binds, listens and
connects alike: 2,000 binds 54872 to 56872, then 2,000 listens 56873 to 58872, then connects.

**5. The rate on Linux (`rates.txt`, 33,000 calls).**

| neighbours | workers | calls | early exits | foreign listener | collisions, rate (95%) |
| --- | ---: | ---: | ---: | ---: | --- |
| none | 2 | 2,000 | 0 | 0 | 0, up to 0.18% |
| none | 8 | 4,000 | 0 | 0 | 0, up to 0.09% |
| none | 16 | 18,000 (two runs) | 1 | 6 | 7, 0.039% (0.016 to 0.080) |
| `node --test` of the base fixture, 4 loops | 2 | 1,000 | 0 | 0 | 0, up to 0.37% |
| `node --test`, 16 loops | 2 | 1,000 | 0 | 1 | 1 |
| 1,000 socket binds a second, each held 30 ms | 2 | 3,000 | 0 | 0 | 0, up to 0.12% |
| 5,000 socket binds a second, each held 30 ms | 2 | 2,000 | 11 (all `EADDRINUSE`) | 0 | 11, 0.55% (0.28 to 0.98) |
| 2,000 Node listens a second, each held 30 ms | 2 | 2,000 | 0 | 0 | 0, up to 0.18% |

An "early exit" is the CI signature. A "foreign listener" is the other signature of the same cause: serve.py names another process's listener (the three that the second run of
16 workers recorded were each another live candidate of the same probe: two callers had been handed the same number). The window (release of the port to the first time serve.py saw the
candidate listen, an upper bound that includes serve.py's 0.1 s poll) was 0.13 to 0.20 s at the median, 0.63 s with sixteen `node --test` loops on four CPUs. A model with no free
parameter is close: a candidate is lost when another socket takes its number during the window and still holds it when the candidate binds, about (sockets that hold a number then) /
14,116 per call. At 5,000 binds a second held 30 ms that is about 165 / 14,116 = 1.2% against 0.55% seen; at 16 callers about 0.1% against 0.04% seen. The observed rates are a third to a half of
it, as they should be when the measured window is an upper bound.

**6. The rate on macOS (`matrix-macos*.jsonl`, 18,000 calls).** 21 early exits, all `EADDRINUSE` (0.12%, 0.07 to 0.18): 8, 3 and 9 in three runs of eight workers and 1
in a run of two workers, on twelve port numbers that recur from run to run (`macos-bad-ports.txt`). Run from the shell, a bind of each of them succeeds for IPv4 loopback
(what `free_port()` does) and fails with `EADDRINUSE` for the IPv6 wildcard (what a Node candidate does), and `netstat` shows what holds them: eight long-lived IPv6
connections (remote port 443 or 80), one IPv6 wildcard listener, one IPv4 connection to port 5223; two were free by the time of the check. serve.py's `free_port()` asks the
IPv4 allocator, which does not see those sockets, so this mechanism does not need any concurrency at all.

**7. How many times each suite starts a candidate through serve.py** (`tap-summary.txt`: one unmodified run of each suite on macOS, four at a time, through the tap).

| suite | serve.py runs in one execution | single-shot grading of its own checks | early exits with `EADDRINUSE` |
| --- | ---: | --- | ---: |
| `ticket-comments` | 54 (57 with the 3 of the new route test) | `CalibrationTest.setUpClass`, 9 variants | 0 |
| `ticket-sla` | 82 (85 with the new route test's 3) | `CalibrationTest.setUpClass`, 11 variants | 0 |
| `user-directory` | 184 | `CalibrationBase.setUpClass`, three links [regraded since, later the same day: see "Follow-up"] | 0 |
| `user-chain` | 39 | `CalibrationTest.setUpClass`, the chain's cases [regraded since: see "Follow-up"] | 0 |
| `brownfield` | 4 | `CaseChecksTest.checks` [regraded since: see "Follow-up"] | 0 |
| `brownfield-tickets` | 13 | grades again (`26728edd`, `8c5b4d4e`) | 0 |
| `resources` | 57 | not a grading: tests of serve.py itself, most of whose runs are meant to fail | 0 |

None of the 439 runs outside `resources` exited early (0.5 would be expected at the macOS rate). The three "answered by pid" lines of each ticket suite are the new route test's own
(its held port is the test process's). Every `ChainRunTest` of these suites already grades a failed check once more; `InheritedAcceptanceTest` and the hidden acceptance
go through `quality.serve_on_free_port`, which starts a server whose port was taken again on another (`d9a92f05`). Counting what CI ran: 181 executions of `ticket-comments` times 54, 84 of
`ticket-sla` times 82, 130 of `user-chain` times 39, 68 of `user-directory` times 184, 214 of `brownfield` times 4 and 216 of `brownfield-tickets` times 13 is about 37,900 serve.py runs
in the history, with one early exit: 0.0026% (0.0001 to 0.015) per run, which is 45 times fewer than on macOS and fits mechanism (A) alone (`rates.txt`).

**8. With the retry in `checks/serve.py`** (the owner's "Yes, add retry"; `matrix-*-retry.jsonl`, `rates.txt`). The same probe, the same delivery, the same conditions:

| | calls | chosen again (passed on the next start) | failed on a port | the same row without the retry |
| --- | ---: | ---: | ---: | --- |
| Linux, 16 callers, no neighbour | 12,000 | 5 | 0 | 1 early exit and 3 foreign-listener lines in 12,000; 3 in 6,000 more |
| Linux, 5,000 socket binds a second held 30 ms | 2,000 | 15 | 0 | 11 early exits |
| macOS, 8 callers | 6,000 | 7 | 0 | 21 early exits in 18,000 (0.12%; 7 in 6,000 is 0.12%) |

Every collision of the three rows was chosen again and passed on the next start; none needed a third. On macOS 8 further calls failed for another reason: each
candidate had logged "listening" and exited 0, all eight within 0.6 s of each other, so something outside the probe sent the servers SIGTERM; serve.py did not start
them again (no `EADDRINUSE`), and the probe now labels such a call "stopped from outside". The retry costs one more candidate start for the call that needs it
(about 0.2 to 0.4 s) and nothing for the others.

## Reading

- The error is `EADDRINUSE`: a candidate that is handed a port number another socket holds exits with rc 1 before it listens (reproduced on both platforms, with the CI's own line on
  Linux), and one reproduced without any synthetic neighbour (16 callers at once, 1 in 12,000 calls, on a port taken by another caller).
- Two mechanisms, one symptom. (A) The window: `free_port()` releases the number and the candidate binds it a moment later, so any socket that takes the number in between wins (Linux
  CI: other suites' candidates and test servers, in the shard that runs four suites at once). (B) Visibility: `free_port()` binds IPv4 loopback and the candidate binds the IPv6
  wildcard, so a number held by an IPv6 socket, or by a connection whose local address is not loopback, is handed out although the candidate cannot bind it (measured on macOS,
  where it needs no concurrency; on Linux it is unlikely because a `connect()` source port is even and `free_port()`'s is odd).
- The CI event is (A). Its holder cannot be named: it was not a listener when serve.py looked, and the record keeps nothing else. The CI rate is about one early exit in 181 executions
  of this suite (one in 85 full-tier executions), and no other suite has shown the signature since 2026-10-31.
- A regrade in the suites' tests ends the effect on the calibrations (a collision touches one server once). ~~It does not touch the live checks, which run the same serve.py.~~
  [superseded 2026-11-15, later the same day: the owner said yes to a retry in serve.py itself, section 8; the live checks that go through it choose the port again too. The
  regrade stays, as a second line.]

## Limits

- Linux here is a container on another kernel and another Node than CI's, and lsof is a shim; the early exit was reproduced under 16 callers and under heavy synthetic neighbours, not under
  the shard's real neighbours (4 and 16 `node --test` loops showed none in 2,000 calls). The CI rate is read from history, not reproduced.
- The macOS rate is for this machine on this day: it is the number of IPv6 sockets other programs hold, which changes.
- The rows were made by successive versions of `serve_race_probe.py`, each only adding what it records: `matrix-linux.jsonl` by the first (nothing recorded about a foreign listener),
  `matrix-linux-v2.jsonl` and `matrix-macos.jsonl` by the second (whether a foreign listener is another live candidate of the probe), `matrix-macos-v3.jsonl` by the third (adds lsof's
  holders when an early exit happens) and `matrix-macos-v4.jsonl` by the fourth (adds every socket in any state; on macOS `netstat` gave the Python process no TCP rows in this sandboxed
  shell, so those lists are empty and `bad_ports.py`, which reads `netstat` from the shell, is the macOS evidence). An earlier 400-call control of the 5,000-a-second row (1 early exit) was not kept.
- The tap counts come from macOS; the calls per execution are the same on CI, which runs the same code, except where a test is skipped there.
- The retry rows are one run per platform, and a retry that is itself taken (about the square of the rate) was not seen. The retry rows came from the probe as committed here before one last
  edit: it counts the calls that `free_port()` served twice, and the "stopped from outside" label was added after the macOS row, so that row still says "early exit" for those 8.

## Follow-up (2026-11-15, later the same day): the regrade in the other three suites

`user-directory`, `user-chain` and `brownfield` now grade a variant's own checks again, alone, until the failed set is the declared one, as the ticket pair does (journal Round 6,
follow-up; F24 updated, F25). How many of each suite's serve.py runs are its variants' own checks, counted from the declarations (a script over `cases.json` and the reference modules, not
the tap): `user-directory` 123 of its 184 (13, 16 and 12 variants times three checks), `user-chain` 29 of its 39 (7, 8 and 7 variants times 2, 1 and 1 checks, and a `node --test` of the
delivery's own suite for each of the 22 variants besides), `brownfield` 3 of its 4 (three variants times one check, and two `node --test` checks each).

`wiring_probe.py` shows that each suite's own grading path goes through the regrade. It loads the suite, hands the FIRST grade of every delivery's own checks a port another socket holds
(serve.py's pin `E2E_SERVE_PORT`, by patching `run.run_checks`) and runs the named calibration classes unmodified. `wiring-results.txt` has the commands and the output (macOS, Node v26.12.1,
nice 10, three runs at a time):

| suite: classes | regrades | deliveries | graded once / twice / more | tests | failures |
| --- | ---: | ---: | --- | ---: | ---: |
| `user-directory`: `RolesCalibrationTest`, `TeamsCalibrationTest`, `PageSizeCalibrationTest` | 3 (shipped) | 41 | 4 / 37 / 0 | 16 | 0 |
| the same | 0 | 41 | 41 / 0 / 0 | 16 | 43 |
| `user-chain`: `CalibrationTest` | 3 (shipped) | 22 | 11 / 11 / 0 | 4 | 0 |
| the same | 0 | 22 | 22 / 0 / 0 | 4 | 17 |
| `brownfield`: `CaseChecksTest` | 3 (shipped) | 3 | 1 / 2 / 0 | 2 | 0 |
| the same | 0 | 3 | 3 / 0 / 0 | 2 | 2 |

A delivery is graded once when its first grade already is the declared one: the held port fails every check that starts a candidate through serve.py, so a base whose declared set is
all the own checks, or a defect whose declared set holds the checks that go through serve.py, agrees at once. The first own check of a `user-chain` link is `node --test`, which does not
start a candidate through serve.py; in `brownfield` only the third check does. "Failures" counts subtests. Not shown: the rescue of a natural collision (nothing counts regrades), and Linux.
The hidden acceptance of these classes is graded once and is not part of the probe: it goes through `quality.serve_on_free_port` and the listener-ownership check, not through serve.py.

## Follow-up (2026-11-15, evening): the `ticket-due-times` probe's own servers

`test/shiploop_e2e/checks/due_times_probe.py` starts its own servers (`Server`): `serve.free_port()`, its own Popen of `node src/server.js`, and, before this change,
`serve.wait_for_candidate`. The retry of `a669c801861fc06b260007d02c14df4674025aa8` lives in `serve.main`, so it did not reach them: a number another process took between the choice
and the bind failed the probe ("the <label> server did not start"). `Server` now asks `serve.candidate_problem(proc, port, stderr)` and, only when its `taken` is true, ends the group of
that start, reaps it and starts again on a fresh `serve.free_port()`, at most `serve.TRIES` starts in all (journal Round 6, the update on the probe). Every other refusal, and the last
start's, print one `FAIL:` line through `serve.fail` (what `wait_for_candidate` does with a refusal; its own contract is untouched) and exit 1.

`due_times_held_port.py` runs the probe's own `main()` for one mode from a delivery of the case, with one listening socket (a dual-stack IPv6 wildcard) held by the driver and the FIRST
`free_port()` of every `Server` handing that number out, the later ones real free ports. It is what a taken port looks like from the probe, made certain. The deliveries are the case's own
reference delivery (`test/fixtures/quality/reference_due_times.py DEST --variant reference`) and its base (`--variant base`: it must fail exactly `migrate`, `restart` and `switch`); the old
probe is `test/shiploop_e2e` of `b578deaa2fde848978e43031ec3aadebe8c0016b` (the tip of `main` before this change, `a669c801`'s serve.py beside it) cut with `git archive`; the new one is this
checkout's. 48 runs, one probe mode each in a process of its own, `due-times-held-port.jsonl` (macOS, Node v26.12.1, Python 3.15.1, load average 14 to 16 from other work):

| probe | delivery | condition | modes that pass | `FAIL:` lines per mode (migrate, restart, switch, rollback, off, cli) | servers made | starts taken | retry lines |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: |
| old | reference | control | 6 of 6 | 0, 0, 0, 0, 0, 0 | 15 | 15 | 0 |
| new | reference | control | 6 of 6 | 0, 0, 0, 0, 0, 0 | 15 | 15 | 0 |
| old | reference | first start held | 0 of 6 | 1, 1, 1, 1, 1, 1 ("a server did not start") | 6 | 6 | 0 |
| new | reference | first start held | 6 of 6 | 0, 0, 0, 0, 0, 0 | 15 | 30 | 15 |
| old | base | control | 3 of 6 (rollback, off, cli) | 11, 36, 9, 0, 0, 0 | 15 | 15 | 0 |
| new | base | control | 3 of 6 (rollback, off, cli) | 11, 36, 9, 0, 0, 0 | 15 | 15 | 0 |
| old | base | first start held | 0 of 6 | 1, 1, 1, 1, 1, 1 ("a server did not start") | 6 | 6 | 0 |
| new | base | first start held | 3 of 6 (rollback, off, cli) | 11, 36, 9, 0, 0, 0 | 15 | 30 | 15 |

- A full pass over the six modes makes 15 servers (1 + 3 + 2 + 4 + 4 + 1: `migrate`, `restart`, `switch`, `rollback`, `off`, `cli`; counted in the control rows), so 15 `free_port()` calls: the
  exposure of one live pass over the case's checks (journal F24 counts 3 to 12 serve.py runs for a link of the ticket or user chains).
- With the first start of every server held, the old probe fails all six modes on both deliveries: the six the reference passes in the control, the three the base passes, and the three the
  base fails (with one `FAIL:` line where the control has 11, 36 and 9). The collision decides the verdict. The new probe gives the control's verdict in all 12 cells, with the same number of
  `FAIL:` lines in the three modes the base fails, and one retry line on stderr per server (15 per delivery). A passing check keeps those lines: `run.run_checks` stores the last 2000
  characters of stdout plus stderr.
- The 12 failures of the old probe were all the foreign-listener face (`port N is answered by pid H, not by the candidate`): the held socket is a listener, so the ownership check refuses it at
  the first lsof look, before the candidate's bind fails. The early-exit face (the service exits with `EADDRINUSE` naming its port) is pinned by `CandidateProblemTest` (which refusals are a
  taken port) and by the second test of `DueTimesProbeServerTest`, which runs a real node service that exits that way.

Not measured: the probe's own natural collision rate (no churn neighbours here); its start is the same `free_port()`, Popen and `candidate_problem` sequence as serve.py's, whose rates are
above (0.0026% per run on CI, 0.12% on this Mac), so a full pass of 15 starts would hit about 0.04% on CI's rate and about 1.8% on this Mac's, if the per-start rates hold for it. The 12
failures also say nothing about a retry that is itself taken (the square of the rate), and Linux was not run.

## Reproduce

```sh
# the delivery: python3 -I -c "import sys; sys.path[:0]=['test/fixtures/quality','test/shiploop_e2e']; import reference_ticket_comments as c; from pathlib import Path; c.build(Path('/tmp/deliv'), 'reference')"
python3 -I docs/experiments/serve-port-race-20261115/pinned_port_demo.py /tmp/deliv
python3 -I docs/experiments/serve-port-race-20261115/port_pool.py 2000
python3 -I docs/experiments/serve-port-race-20261115/serve_race_probe.py /tmp/deliv 4000 8 TAG [--churn py-bind:5000:30]
bash docs/experiments/serve-port-race-20261115/run_matrix.sh /tmp/deliv matrix.jsonl      # the whole Linux matrix
python3 -I docs/experiments/serve-port-race-20261115/rate_summary.py matrix.jsonl
netstat -an | python3 -I docs/experiments/serve-port-race-20261115/bad_ports.py matrix-macos.jsonl
bash docs/experiments/serve-port-race-20261115/run_tap.sh "$PWD" /tmp/tap-out               # counts serve.py runs per suite
python3 -B docs/experiments/serve-port-race-20261115/wiring_probe.py user-directory RolesCalibrationTest TeamsCalibrationTest PageSizeCalibrationTest [--regrades 0]
python3 -B docs/experiments/serve-port-race-20261115/wiring_probe.py user-chain CalibrationTest [--regrades 0]       # the follow-up's probe
python3 -B docs/experiments/serve-port-race-20261115/wiring_probe.py brownfield CaseChecksTest [--regrades 0]
python3 -I docs/experiments/serve-port-race-20261115/ci_history.py CACHE_DIR OUT.json 2026-10-31
# the probe's own servers with the first port of every Server held (the evening follow-up); OLD is `git archive b578deaa2fde848978e43031ec3aadebe8c0016b test/shiploop_e2e/checks test/shiploop_e2e/listeners.py test/shiploop_e2e/fixtures/node-tickets | tar -x -C OLD`
python3 test/fixtures/quality/reference_due_times.py /tmp/due-reference --variant reference     # and /tmp/due-base --variant base, into empty folders
python3 -B docs/experiments/serve-port-race-20261115/due_times_held_port.py ALL due-times-held-port.jsonl old=OLD/test/shiploop_e2e new=$PWD/test/shiploop_e2e -- base=/tmp/due-base reference=/tmp/due-reference
python3 -B docs/experiments/serve-port-race-20261115/due_times_held_port.py ONE $PWD/test/shiploop_e2e /tmp/due-reference migrate held --tag new/reference   # one run
```

On a machine without lsof, put `lsof_shim.py` on PATH as `lsof` (Linux only).
