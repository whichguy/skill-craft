# U18b evidence: what an Improve stage reads of the Improve skill, before and after the route core

Consumer: whoever trims the Improve skill or ShipLoop's Improve handoff next, and the next live round that measures
`context_summary` again. Read with the journal row `docs/experiments/shiploop-eff-journal-rows/U18b.md`.

## Source

Live run 4 (2026-10-20, Grok driving ShipLoop 2.8.0 on a 3-work-item project), run folder
`/Users/dadleet/e2e-runs/20261020/chess-sf-full-9e52e8` (read-only; not in this repository). The harness's new
`context_summary` measure put ShipLoop's own skill files at 30-34% of all context (29.6% `shiploop_reads` in the recomputed
summary, 2,018,698 of 6,831,480 bytes), above packets (15.7%) and shell output (20.6%); product reads were 3.9%. The table
below is `trace_reads.py` (beside this file) over that run's `events.jsonl`: every `read_file` of the Improve route card,
the Improve `SKILL.md` and ShipLoop's `improve-context.md`, grouped by the Improve stage whose `handoff.md` was read last,
with the window the model asked for and the bytes the host returned (the event's `content`, JSON-encoded).

## Finding: a window does not shrink a read of a skill file on this host

Every read of the route returned all 48,419 bytes whatever its window (`1:150`, `70:50`, `70:180` and `whole` are the same
size), and so did every read of `SKILL.md` (10,624) and of `improve-context.md` (`55:100` returned the whole 35,607). Reads
of `handoff.md` (a run file) did honour the window (`1:50` returned 4,819 to 6,343 bytes; `150:80` 9,824). So "open only the
section" in a skill reference saves nothing here: only the size of the file the model opens bounds the read. That is why the
route became a small core file plus case files, not one file with anchors.

## Per-stage read trace (run 4)

| Improve stage (child dir) | file | window (offset:limit) | result bytes (JSON) |
|---|---|---|---|
| spec-85867466 | handoff.md | whole | 22437 |
| spec-85867466 | improve/SKILL.md | 1:200 | 10624 |
| spec-85867466 | shiploop-route.md | 1:150 | 48419 |
| spec-85867466 | improve/SKILL.md | 1:200 | 10624 |
| spec-85867466 | handoff.md | 1:250 | 22437 |
| spec-85867466 | shiploop-route.md | 1:200 | 48419 |
| test-strategy-1b63cbb3 | handoff.md | 1:50 | 6343 |
| test-strategy-1b63cbb3 | improve/SKILL.md | whole | 10624 |
| test-strategy-1b63cbb3 | handoff.md | whole | 19543 |
| test-strategy-1b63cbb3 | shiploop-route.md | whole | 48419 |
| test-strategy-1b63cbb3 | improve-context.md | 55:100 | 35607 |
| plan-5e48872e | handoff.md | whole | 29954 |
| plan-5e48872e | improve/SKILL.md | 1:250 | 10624 |
| plan-5e48872e | shiploop-route.md | whole | 48419 |
| step-plan-cc8f6802 | handoff.md | whole | 22394 |
| step-plan-cc8f6802 | improve/SKILL.md | 1:200 | 10624 |
| step-plan-cc8f6802 | shiploop-route.md | 1:180 | 48419 |
| test-spec-06549f3b | handoff.md | 1:50 | 6224 |
| implement-bbb68d4d | handoff.md | 1:150 | 16684 |
| implement-bbb68d4d | improve/SKILL.md | 1:120 | 10624 |
| implement-bbb68d4d | handoff.md | 150:80 | 9824 |
| implement-bbb68d4d | shiploop-route.md | 70:50 | 48419 |
| implement-bbb68d4d | improve/SKILL.md | 1:200 | 10624 |
| implement-45165a84 | handoff.md | whole | 28657 |
| implement-45165a84 | shiploop-route.md | 70:180 | 48419 |
| step-plan-31b9f136 | handoff.md | whole | 22449 |
| step-plan-31b9f136 | improve/SKILL.md | 1:150 | 10624 |
| test-spec-13a9da2e | handoff.md | whole | 20471 |
| test-spec-13a9da2e | improve/SKILL.md | 1:250 | 10624 |
| test-spec-13a9da2e | shiploop-route.md | 1:180 | 48419 |
| implement-7492781d | handoff.md | 1:50 | 4819 |
| implement-4b58f3cf | handoff.md | whole | 29298 |
| implement-4b58f3cf | improve/SKILL.md | 1:200 | 10624 |
| implement-4b58f3cf | shiploop-route.md | 70:180 | 48419 |
| carry-forward-56923aa8 | handoff.md | 1:200 | 21818 |
| carry-forward-56923aa8 | shiploop-route.md | 1:120 | 48419 |
| carry-forward-56923aa8 | handoff.md | whole | 26888 |
| carry-forward-56923aa8 | shiploop-route.md | 1:250 | 48419 |
| system-test-author-304a799f | handoff.md | 1:25 | 2752 |
| system-test-author-304a799f | shiploop-route.md | whole | 48419 |
| system-test-author-304a799f | handoff.md | whole | 23589 |
| system-test-author-304a799f | improve/SKILL.md | 1:200 | 10624 |
| system-test-author-304a799f | improve-context.md | 55:100 | 35607 |
| system-test-author-304a799f | improve/SKILL.md | whole | 10624 |
| release-plan-384ad9e8 | handoff.md | whole | 23530 |
| release-plan-384ad9e8 | shiploop-route.md | whole | 48419 |

Totals: the route 13 reads, 629,447 bytes; `SKILL.md` 12 reads, 127,488; `improve-context.md` 2 reads, 71,214.

## Before and after, per Improve stage (bytes on disk)

What a ShipLoop Improve child must read per stage besides its own handoff: the router the skill call loads, plus the route
the router and the handoff send it to (`Open ROUTE once per context`), plus what that tells it to open by default.

| | before (6ed81762) | after (this row) |
|---|---|---|
| `skills/improve/SKILL.md` (the skill call) | 10,226 | 10,384 |
| the route the handoff names (`ROUTE`) | 47,314 (`shiploop-route.md`, all of it) | 9,675 (`shiploop-route.md`, the core) |
| opened by default from the route | `improve-context.md` default-route section on "before start or recovery" (34,584 whole on this host; run 4 opened it 2 of 13 times) | nothing: each case file is named with its case, and the core says to open the `Improve context ownership:` line only for recovery, a restart or a dispatch |
| **per stage** | **57,540** (92,124 when the context file was opened) | **20,059** |

Per stage 37,481 bytes fewer (65%); the route itself 37,639 fewer (80%). At run 4's 13 route reads that is about 489 KB of
the 629 KB the route cost. The on-demand files, read only in their case: `shiploop-route-recovery.md` 9,014,
`shiploop-route-ask-agent.md` 4,417, `shiploop-review-inputs.md` 9,063 (one section per condition), `shiploop-route-cases.md`
6,386, `shiploop-route-rules.md` 20,522 (the long form of the core's rules; a normal pass does not open it). The handoff
itself is unchanged in size (its top sentence was replaced by one two characters shorter).
