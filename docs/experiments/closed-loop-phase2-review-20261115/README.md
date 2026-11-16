# Sol's reviews of the Phase 2 plan (2026-11-15)

Two focused reviews of `docs/closed-loop-phase2-plan-2026-11-15.md`, the plan for a ShipLoop adapter for the `closed-loop` skill.
Reviewer both times: Codex `gpt-6.1-sol` at max effort, one attempt, no fallback, read-only, in a neutral checkout of origin/main
`579af232f25dcc93fcf0ad9a21d5f1915701c73a` with the draft added. Findings, what I checked in the code and what each changed are in the plan's
appendix B; this folder holds the evidence.

| Round | On | Verdict | Run | Files |
| --- | --- | --- | --- | --- |
| 1 | draft 1 | not ready for real compute (nine findings) | 792 s | `round1-sol-brief.txt`, `round1-sol-answer.txt`, `round1-sol-run.json`, `round1-sol-kill-witness.json` |
| 2 | version 2 | not ready (seven findings) | 882 s | `round2-sol-brief.txt`, `round2-sol-answer.txt`, `round2-sol-run.json` |

| 3 | the BUILT facade (commit 441b9edb4f6fbb990d1401c56538ac8bad0c49f3: code, tests, manifest), gate G1 | not ready for the first real compute (eleven findings, ten verified bugs and one likely) | 974 s | `g1-sol-brief.txt`, `g1-sol-answer.txt`, `g1-sol-run.json`, `g1-sol-witness-*.json` |

| 4 | the fixes of round 3 (main at a9d40c307a9edec62d2a487d810e30e630710821, containing fc5b3d5e) | not ready (five findings fixed, six partly; seven verified bugs) | 872 s | `g1b-sol-brief.txt`, `g1b-sol-answer.txt`, `g1b-sol-run.json`, `g1b-sol-*-results.json`, `g1b-sol-kill-result-race.json` |

| 5 | the fixes of round 4 (main at 4e36b3ad486b30fce972e697096fcfa158c29e3d) | not ready (four of round 4's seven fixed, three partly; six verified bugs, one a regression) | 645 s | `g1c-sol-brief.txt`, `g1c-sol-answer.txt`, `g1c-sol-run.json`, `g1c-sol-witness-*.json` |

Round 3 is the plan's gate G1: Codex `gpt-6.1-sol` at max effort, one attempt, no fallback, `workspace-write` sandbox, in a neutral clone of the branch
under `/tmp` (its origin remote removed; the clone's status was identical before and after). The reviewer could not run `ps` in its sandbox, so
the steps and real-engine suites timed out for it (only the 28 queries tests ran there); the behaviours it reports were reproduced with its own
witness scripts, kept here as `g1-sol-witness-*.json`. Each finding was checked against the code before it was accepted; what each changed is in
the journal's round R8 (`docs/closed-loop-journal.md`).

Round 4 verified round 3's fixes in the same way (a neutral clone of main, no `ps` in the reviewer's sandbox, its own witness scripts). What each finding
changed is in the journal's round R9.

Round 5 verified round 4's fixes in the same way; its witnesses are `g1c-sol-witness-ownership.json` (repeated cleanup, cancel and cleanup of a prepared
step, a group recycled between signals), `g1c-sol-witness-core.json` (a write failure after the tip moved, a spawn after a cancel, two stale polls, the
barrier test with admission removed) and `g1c-sol-witness-evidence.json` (a changed sealed run, a misbound calibration report, a torn epoch ledger).
Every finding was checked against the code and held; the journal's round R10 has them and the replan they led to.

`g1d-mutations.py` and `g1d-mutations.txt` are the mutation check of replan B (journal R12): each fix broken on purpose, in a copy of the tree,
with the test that guards it run alone. Unlike `g1b-mutations.py` (round 4), a mutant counts as caught only when its named test fails on an
assertion, and the driver exits 1 when any mutant survives, is not applied, or ends in an error.

`identity-failure-evidence.txt` is not a review: it is the controlled experiment and the system records behind the real-engine suite's failure of
round 4 (a git identity the machine stopped being able to guess), journal round R10. `linux-ci-failure-evidence.txt` is the separate cause of the same
suite's failures on GitHub CI (a 175 KB prompt passed as one argument, over Linux's 128 KiB limit), reproduced offline in a Linux container.

`round1-sol-kill-witness.json` is the reviewer's own scratch result: a stubbed qualified cycle that appends two owner findings to the
ledger and is then SIGKILLed; the loop worktree keeps them as an uncommitted change and the output folder is empty. It shows the window
exists; it does not show that every real kill falls in it. Version 3 of the plan has not been reviewed again.
