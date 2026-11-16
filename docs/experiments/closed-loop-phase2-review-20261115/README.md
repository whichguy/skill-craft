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

Round 3 is the plan's gate G1: Codex `gpt-6.1-sol` at max effort, one attempt, no fallback, `workspace-write` sandbox, in a neutral clone of the branch
under `/tmp` (its origin remote removed; the clone's status was identical before and after). The reviewer could not run `ps` in its sandbox, so
the steps and real-engine suites timed out for it (only the 28 queries tests ran there); the behaviours it reports were reproduced with its own
witness scripts, kept here as `g1-sol-witness-*.json`. Each finding was checked against the code before it was accepted; what each changed is in
the journal's round R8 (`docs/closed-loop-journal.md`).

`round1-sol-kill-witness.json` is the reviewer's own scratch result: a stubbed qualified cycle that appends two owner findings to the
ledger and is then SIGKILLed; the loop worktree keeps them as an uncommitted change and the output folder is empty. It shows the window
exists; it does not show that every real kill falls in it. Version 3 of the plan has not been reviewed again.
