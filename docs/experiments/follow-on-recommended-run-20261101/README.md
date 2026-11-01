# Round 6: the recommended-run path, live on a primed request (2026-11-01)

The write-up of journal Round 6 (`docs/shiploop-follow-on-run-journal.md`). The plan, its rules and its predictions were committed before any run
(7bcb2884e410adb362206f82bf93695ec14da163); addendum 1 registered link 3 before it ran (e6088502a9b60728717ec6c58b5ef290983c6e5e).

**Question.** When a real run files a `decision`, does ShipLoop write a request a person would start, print a command that works as printed, and does a
run started from that request ask for the answer and then deliver? The occasion is arranged (`request.txt` reserves one choice for the person), so this
shows that the path works and says nothing about how often it is used (M3) or whether a follow-on run repairs anything (M2b).

**Conditions.** Codex gpt-6.1-terra at xhigh, `--source checkout` from a detached worktree at d2c6a5ff62a323a0f29c9d9b06c2f9bb5031a8a7 (the release record of
skill-craft 2.30.0 / ShipLoop 1.29.0; every run loaded plugin tree 3efc9db89059, the published tree), planning review `stage`, custom `--prompt` runs with
`--check` commands (`launch.sh`), outputs under `/Users/dadleet/e2e-runs/2026-11-01/follow-on-live2-dacc9b/`. No fixed port. The machine was shared with other
sessions' cycles and calibration epochs (load average 56, 104 and 96 over 1, 5 and 15 minutes at 10:30; link2-b's runner printed 12.9 falling to 10.5 on 18 CPUs).

| Run | Started from | Turns | Minutes | Gates passed | Handoff | `follow_on` | `slug.py Café` |
|---|---|---|---|---|---|---|---|
| link1-a | `request.txt` | 172 | 11.5 | 6 of 6 | 1 attempt (exit 0) | one `decision`, source `lessons.open_next` | exit 2, "undecided: non-ASCII" |
| link1-b | `request.txt` | 159 | 10.6 | 6 of 6 | 1 attempt (exit 0) | one `decision`, source `lessons.open_next` | exit 2, "undecided: non-ASCII" |
| link2-a | link1-a's `follow-on-request.md` | 25 | 1.2 | 4 of 6 (`shiploop`, `committed`) | none: BLOCKED at spec | not reached | exit 2 (product unchanged) |
| link2-b | link1-b's `follow-on-request.md` | 25 | 1.4 | 4 of 6 (`shiploop`, `committed`) | none: BLOCKED at spec | not reached | exit 2 (product unchanged) |
| link3-a | link1-a's request file + `answer.txt` | 162 | 12.8 | 6 of 6 | 1 attempt (exit 0) | `[]` | `cafe`, exit 0 |
| link3-b | link1-b's request file + `answer.txt` | 144 | 11.3 | 6 of 6 | 1 attempt (exit 0) | `[]` | `cafe`, exit 0 |

**Rules.**
- R1 holds: both link-1 runs reached `done` with every verdict and kept the reservation (the reserved-behaviour check passed in both).
- R2 holds: both accepted handoffs list a `decision` (not a `gap`), cite `lessons.open_next`, and the cited lessons say the user's SEO decision is awaited (supported);
  both runs wrote `follow-on-request.md` and the report section, and the done packet and the report print the start command (`printed-command-link1-*.json`).
- R3 holds: the printed command ran as printed on a copy of each checkout: exit 0, no traceback, one workspace record, the stored request equal to the file but for
  its last newline. Calibrated beforehand on an adversarial request (backticks, `$(touch marker)`, quotes): the marker was not created.
- R4 as registered is **not met**: 0 of 2 link-2 runs reached `done`. Both ended BLOCKED at the spec stage, each accepting a blocked result that asks the requester
  one question with options and a `no_default` reason that quotes the earlier "do not choose" (`blocked-questions.txt`). They found the finding, followed the request
  file's pointer to the earlier request, and asked; they did not refuse or misread the request. The plan had registered the unanswered case and called its outcome
  "delivers"; that was the plan's mistake (a decision is delivered only once someone answers it), so the miss is recorded and the product is read as working.
- R5: link 2 changed no file (`runs.json`: `files_changed_vs_prior_head` is empty), so nothing "landed" except the question. Link 3 changed `slug.py`, `test_slug.py`,
  `README.md` and the three living knowledge files (`link3-changes.txt`); both specs now carry the settled rule and say it supersedes the earlier pending decision.
- R6: link 2 never reached a handoff. R7 holds (2 of 2 link-3 runs done, every verdict). R8 holds (tests exercise the answered rule; the committed spec and architecture
  no longer describe the policy as undecided; the only remaining mentions say the interim error is removed or superseded). R9 holds (both handoffs accepted on the first
  `complete`; neither filed the decision again: `follow_on` is `[]`).

**Predictions** (probability, written before the runs): P1 held (75%). P2 held, both runs (85%; 60% for both). P3 held (80%). P4 held (90%). **P5 missed** (65%: 0 of 2).
P6 (70%) is vacuous for link 2 (no file changed) and held for link 3 (only the product, its tests, README and the knowledge files). P7 (45%) did not apply: link 2 never
reached a handoff. P8 held (80%). P9 held (85%). P10 held (70%).

**Findings** (journal Round 6 has the numbered list and statuses).
- The path ran live end to end on a primed request, n = 2: a model filed a `decision`; the request file and the printed command worked; a run started from it asked
  the requester; a run started from it plus the answer delivered and did not file the decision again.
- A `decision` entry cannot be delivered unattended. The recommended run blocks at spec and asks (SPEC S-14); only a `gap` could run without a person, which is what
  the design's D2 already proposed for auto-start. This is the first live evidence for that restriction.
- Cosmetic: the request text has a double period when the model's `needs` ends with one ("...implement and test it.. Recorded in lessons.open_next.").
- Two slips in my readout (a hash compared with the wrong string; a folder filter that skipped link 3) were found on first use, before any value was read through them,
  and fixed in their own commits.

**Contrary evidence and limits.** The request is primed, so a pass shows the path and not its use; two replicates of one request are a mechanics check; the person is
simulated by one fixed answer chosen from the options the runs themselves offered; one host, one model, one effort; the comparison with a hand-written request on the same
base (design M2a's second half) was not run; link 3 was started with the answer in the prompt because the harness never resumes a blocked run as if answered.

**Files.** `request.txt`, `answer.txt`, `launch.sh`, `calibrate_checks.py`, `check_printed_command.py`, `readout.py` (the instruments); `readings.txt`, `runs.json`,
`verdicts.txt`, `printed-command-link1-a.json`, `printed-command-link1-b.json`, `requests.md`, `blocked-questions.txt`, `link3-changes.txt` (what they read). The six baseline
rows the runs appended are in `test/shiploop_e2e/baselines.jsonl` (`local_head` d2c6a5ff62a323a0f29c9d9b06c2f9bb5031a8a7). Raw run folders stay under the output root.
