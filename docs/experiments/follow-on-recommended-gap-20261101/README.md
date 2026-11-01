# Round 7: the recommended gap, live on a primed request (2026-11-01)

The write-up of journal Round 7 (`docs/shiploop-follow-on-run-journal.md`). The plan, its rules and its predictions were committed before any run
(e7c05e6875679ad0a617923c41e1f9fd5c57079e).

**Question.** When a real run leaves a request outcome unmet that needs no person's answer, does it file a `gap` that maps to the request's sentence, and does a run
started from that request deliver it unattended while keeping what already works? The occasion is arranged (`request.txt` asks for a slug tool and an option, and tells the
run to build the option in a later run), so this shows that the path works and says nothing about how often it is used (M3).

**Conditions.** Codex gpt-6.1-terra at xhigh, `--source marketplace` (the published build the hosts run), custom `--prompt` runs with `--check` commands (`launch.sh`),
launched from a worktree whose HEAD was the plan commit e7c05e6875679ad0a617923c41e1f9fd5c57079e (an ancestor of origin/main, not its tip at launch), outputs under `/Users/dadleet/e2e-runs/2026-11-01/follow-on-gap-d79bc3/`. No fixed port. **The published build moved
during the round**: the two link-1 runs loaded skill-craft 2.31.0 / ShipLoop 1.30.0 (plugin tree b604dade538e); another session released skill-craft 2.32.0 / ShipLoop 1.30.1 /
Backchain 0.7.0 at 13:00, so the link-2 run, launched at 13:03, loaded that build (plugin tree 6aa0a67b2ac0). Between the two builds ShipLoop changed converge-mode packet text (the plan marker line and a repair/revise audit pointer; the default `one` packets are meant to be unchanged, 39af8ce04222fb49aa6d612e08b4dbabd73e5db3) and moved the backchain-check validator into Backchain (90b9ac99e02d89efa8102f8686321da9ccccf554): 6 files, 43 insertions, 769 deletions, none of which ran here (backchain records 0); it touches neither the follow-on module nor the handoff duty. Backchain 0.7.0 also changes its own default gate, which these default `one` runs do not use. (Corrected 2026-11-01, Round 8: this first named the marker line only.) So a request file written
by 1.30.0 was consumed by 1.30.1, which is the realistic upgrade case, and the comparison between links is not between identical builds.

| Run | Started from | Build | Turns | Minutes | Gates | Handoff | `follow_on` | `--max-length` |
|---|---|---|---|---|---|---|---|---|
| link1-a | `request.txt` | 2.31.0 / 1.30.0 | 141 | 8.5 | 6 of 6 | 1 attempt (exit 0) | one `note`, `lessons.open_next`, no request sentence | exit 2 (deferred, as asked) |
| link1-b | `request.txt` | 2.31.0 / 1.30.0 | 146 | 9.6 | 6 of 6 | 1 attempt (exit 0) | one `gap`, `lessons.open_next`, request sentence S3 | exit 2 (deferred, as asked) |
| link2-b | link1-b's `follow-on-request.md` | 2.32.0 / 1.30.1 | 167 | 9.0 | 6 of 6 | 1 attempt (exit 0) | `[]` | `hello-wo` for 8, `hello` for 6 |

**Rules.**
- R1 holds: both link-1 runs reached `done` with every verdict and respected the deferral (`--max-length 5` exits 2 in both).
- R2 holds on one of two. link1-b filed a `gap` whose `request_sentence` is S3, the sentence that asks for the option; its request file and report section exist and the done packet and the
  report print the command. link1-a filed the same deferral as a `note` ("The user explicitly deferred --max-length to a later run."), which recommends nothing, so it has no request file.
  The cited lessons say the same in both ("it is intentionally absent now" / "If requested later, implement --max-length ..."); the entries are supported, and the class differs.
- R3 holds: the printed command ran as printed on a copy of link1-b's checkout (exit 0, one workspace record, the stored request equal to the file but for its last newline;
  `printed-command-link1-b.json`).
- R4 holds, on one run: link2-b reached `done` with every verdict, both examples of the option and the basic checks included, with nobody answering anything.
- R5 (descriptive): link2-b changed `slug.py`, `test_slug.py`, `README.md`, the three living knowledge files and `SHIPLOOP.md`, the host-authored knowledge index (2cd8f33b30f3056a925e3636f624849aadf61982 made ShipLoop commit it on 2026-09-27, and 589bc03ebe4bb31759a371e10bbc261bb071aab3 removed that on 2026-10-11, so neither build commits it as knowledge; link2-b's model wrote it and the generic commit of files written after
  the last work item swept it in; neither link-1 run of this round nor any Round 6 run wrote one, and why this run did is not examined; corrected 2026-11-01, Round 8). The spec says the formerly
  deferred option is now supported (R-4) and every other unknown option still exits 2 (`link2-changes.txt`).
- R6 holds: link2-b's handoff was accepted on its first `complete` and filed `[]`, so the gap was not filed again.

**Predictions** (probability, written before the runs): P1 held (75%). P2 held for "at least one gap" (55%) and missed for "both" (30%): one `gap`, one `note`. P3 held (85%: the gap maps to S3).
P4 held (90%). P5 held (80%: 1 of 1). P6 held (85%). P7 missed on its registered wording (75%: slug.py, its tests, README.md and the living knowledge files; `SHIPLOOP.md` is not one of the three, and counting it as one was a reading chosen after the fact; corrected 2026-11-01, Round 8). P8 held (85%: no handoff refusal in either link-1 run).

**Findings** (journal Round 7 has the numbered list and statuses).
- The recommended gap ran live end to end and unattended: a model filed a `gap` that maps to the right request sentence, ShipLoop wrote a request and a command that work as printed, and a run started
  from it implemented the option with the request's two examples, kept the basic tool, updated the records and did not file it again. Primed, n = 1 for the delivery, on a build one patch newer than the one that wrote the request.
- A requester-deferred outcome sits on the boundary between `gap` and `note`: the same request was filed once as each (n = 2). The duty's words fit both ("a request outcome left unmet ... that needs no person's
  answer" and "knowledge for a later change; nothing is open"). Exploratory; the duty text is not changed on two runs.
- The request text carries the doubled period again in the unfixed build ("...updates tests.. Recorded in lessons.open_next."); the fix is committed separately with its test.
- `--source marketplace` is a moving target during a round: the harness prints the build it installs at each launch, and `result.json` records it per run (`versions`).

**Contrary evidence and limits.** The request is primed (a deferral the requester asked for is the easiest possible gap); two link-1 replicates and one link-2 run; one host, one model, one effort; the two links ran
on different builds; the comparison with a hand-written request on the same base was not run; M3 and U11 are untouched.

**Files.** `request.txt`, `launch.sh`, `calibrate_checks.py`, `readout.py` (the instruments); `readings.txt`, `runs.json`, `verdicts.txt`, `printed-command-link1-b.json`, `requests.md`, `link2-changes.txt` (what they read).
The three baseline rows the runs appended are in `test/shiploop_e2e/baselines.jsonl` (`local_head` e7c05e6875679ad0a617923c41e1f9fd5c57079e). Raw run folders stay under the output root.
