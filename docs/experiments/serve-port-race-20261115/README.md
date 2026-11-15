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
| `bad_ports.py`, `macos-bad-ports.txt` | Why the same twelve port numbers failed in every run on macOS (addresses not kept). |
| `tap/sitecustomize.py`, `run_tap.sh`, `tap-summary.txt` | A tap that counts how many times each suite starts a candidate through serve.py and how those runs ended. |
| `lsof_shim.py` | The one lsof call serve.py makes, for the Linux container that has no lsof. Used only there. |

## What was run, and where

- **Linux**: a container (OrbStack, kernel 7.2.12, Node v26.12.1, Python 3.14.9, `--cpus 4`, no network) with this checkout mounted read-only. serve.py,
  `listeners.py` and the delivery are the repository's; only `lsof` is the shim. CI's runner is Ubuntu 26.04 with Node `v27.0.0-alpha.0.1.0` (the job
  log), so the kernel and Node differ and the Node frames of the CI record (`callSetupListenHandle`) are not Node 26.12.1's.
- **macOS**: this machine (Darwin 27.2.0, Node v26.12.1, Python 3.15.1, real lsof), at low priority, with the other work that was on it (load average 7 to 16).
- The candidate is the `reference` delivery of the `ticket-comments` case (`reference_ticket_comments.build`), started as the case's checks start it
  (`node src/server.js`), with `-- true` as the check, so each call is one `free_port()`, one Popen and one `wait_for_candidate()`.

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
| `user-directory` | 184 | `CalibrationBase.setUpClass`, three links | 0 |
| `user-chain` | 39 | `CalibrationTest.setUpClass`, the chain's cases | 0 |
| `brownfield` | 4 | `CaseChecksTest.checks` | 0 |
| `brownfield-tickets` | 13 | grades again (`26728edd`, `8c5b4d4e`) | 0 |
| `resources` | 57 | not a grading: tests of serve.py itself, most of whose runs are meant to fail | 0 |

None of the 439 runs outside `resources` exited early (0.5 would be expected at the macOS rate). The three "answered by pid" lines of each ticket suite are the new route test's own
(its held port is the test process's). Every `ChainRunTest` of these suites already grades a failed check once more; `InheritedAcceptanceTest` and the hidden acceptance
go through `quality.serve_on_free_port`, which starts a server whose port was taken again on another (`d9a92f05`). Counting what CI ran: 181 executions of `ticket-comments` times 54, 84 of
`ticket-sla` times 82, 130 of `user-chain` times 39, 68 of `user-directory` times 184, 214 of `brownfield` times 4 and 216 of `brownfield-tickets` times 13 is about 37,900 serve.py runs
in the history, with one early exit: 0.0026% (0.0001 to 0.015) per run, which is 45 times fewer than on macOS and fits mechanism (A) alone (`rates.txt`).

## Reading

- The error is `EADDRINUSE`: a candidate that is handed a port number another socket holds exits with rc 1 before it listens (reproduced on both platforms, with the CI's own line on
  Linux), and one reproduced without any synthetic neighbour (16 callers at once, 1 in 12,000 calls, on a port taken by another caller).
- Two mechanisms, one symptom. (A) The window: `free_port()` releases the number and the candidate binds it a moment later, so any socket that takes the number in between wins (Linux
  CI: other suites' candidates and test servers, in the shard that runs four suites at once). (B) Visibility: `free_port()` binds IPv4 loopback and the candidate binds the IPv6
  wildcard, so a number held by an IPv6 socket, or by a connection whose local address is not loopback, is handed out although the candidate cannot bind it (measured on macOS,
  where it needs no concurrency; on Linux it is unlikely because a `connect()` source port is even and `free_port()`'s is odd).
- The CI event is (A). Its holder cannot be named: it was not a listener when serve.py looked, and the record keeps nothing else. The CI rate is about one early exit in 181 executions
  of this suite (one in 85 full-tier executions), and no other suite has shown the signature since 2026-10-31.
- A regrade in the suites' tests ends the effect on the calibrations (a collision touches one server once). It does not touch the live checks, which run the same serve.py.

## Limits

- Linux here is a container on another kernel and another Node than CI's, and lsof is a shim; the early exit was reproduced under 16 callers and under heavy synthetic neighbours, not under
  the shard's real neighbours (4 and 16 `node --test` loops showed none in 2,000 calls). The CI rate is read from history, not reproduced.
- The macOS rate is for this machine on this day: it is the number of IPv6 sockets other programs hold, which changes.
- The rows were made by successive versions of `serve_race_probe.py`, each only adding what it records: `matrix-linux.jsonl` by the first (nothing recorded about a foreign listener),
  `matrix-linux-v2.jsonl` and `matrix-macos.jsonl` by the second (whether a foreign listener is another live candidate of the probe), `matrix-macos-v3.jsonl` by the third (adds lsof's
  holders when an early exit happens) and `matrix-macos-v4.jsonl` by the fourth (adds every socket in any state; on macOS `netstat` gave the Python process no TCP rows in this sandboxed
  shell, so those lists are empty and `bad_ports.py`, which reads `netstat` from the shell, is the macOS evidence). An earlier 400-call control of the 5,000-a-second row (1 early exit) was not kept.
- The tap counts come from macOS; the calls per execution are the same on CI, which runs the same code, except where a test is skipped there.

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
python3 -I docs/experiments/serve-port-race-20261115/ci_history.py CACHE_DIR OUT.json 2026-10-31
```

On a machine without lsof, put `lsof_shim.py` on PATH as `lsof` (Linux only).
