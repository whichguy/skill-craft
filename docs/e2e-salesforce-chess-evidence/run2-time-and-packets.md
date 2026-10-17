# Run 2 (chess-salesforce, Grok 4.7 medium) — where time and bytes went

Measured 2026-10-16 from the run's events and timeline (`events.jsonl`, `timeline.jsonl`), 86 minutes in. Identifiers removed; paths are relative to the run.

## Time by ShipLoop stage (minutes, tool calls)
| Stage | Min | Calls |
|---|---|---|
| intake, discovery, research, spec | 11.6 | 64 |
| Improve of spec (8 passes) | 17.6 | 99 |
| test-strategy | 4.3 | 31 |
| Improve of test-strategy (5 passes) | 8.8 | 56 |
| plan, prepare | 4.8 | 33 |
| Improve of plan (4 passes) | 6.9 | 47 |
| W1 step-plan | 10.0 | 65 |
| Improve of step-plan (1 pass) | 2.8 | 17 |
| W1 test-spec | 7.2 | 51 |

Wall time: model generation 80% (about 22 min fixed per-turn latency, about 32 min reasoning, about 21 min visible output), tool and script time 11%, 5 compactions 8.7 min. Longest tool call 40 s. Zero refused submissions.

## Output composition (288.5k output tokens)
Reasoning 46%; absolute path strings retyped in tool arguments 22% (the run-directory prefix about 778 times); tool-call envelope 4.8%; prose-bearing text 23% (stage results 20k tokens, knowledge documents 17k, Improve done JSON 13k, Improve review files 10k, notes 6k, chat 2k). The chat a person would read is 0.7% of output, mostly the mandated status block.

## Packets (live, installed skill-craft 2.4.0)
intake 18 KB, discovery 32, research 29, spec 31, test-strategy 64, plan 102, prepare 40, step-plan 77, test-spec 80, implement 87 KB; the 17 files total 660 KB; 65.5% of the bytes are lines already sent in an earlier packet (0% at intake, 95% by the sixteenth). Largest parts of the plan packet: quoted knowledge 34.6%, the uncut spec diff 21.6% (20.7 KB of it duplicates the quote because the run baseline is an empty repository), duties 13%.
Offline node-fix-bug packets are 14 to 25 KB; in each, the Until Loop contract block is 5 to 8 KB.

## What the model read (191 read_file calls, about 2.0M characters)
Improve handoff 11 reads (327 KB); packet files 23 (274 KB); improve/SKILL.md 7 (203 KB); shiploop/SKILL.md 2 (163 KB); Until Loop ADAPTER.md 6 (147 KB); spec.md 8 (59 KB). `run/reference.md` 0 reads, `run/context-index.md` 0 reads, `run/status.md` 0 reads, `run/state.md` 1 read.

## Improve value (five stages, 21 passes, 41 minutes)
8 material passes (the first pass of each content-creating stage and spec passes 1 to 5), 10 passes made no change, 3 polish edits classed non-trivial reset the two-clean-pass streak. Recommended stop rule: end when a pass is trivial and the script-measured content tree is unchanged from the previous pass.

## The block
Grok's auto permission classifier refused `sf project deploy start --target-org de` three times ("Salesforce project deploy mutates remote org de and was not requested by the user"; "not authorized by the live continue-shiploop request"). ShipLoop recorded `blocked_by: access` awaiting an answer. Resumed with the owner's recorded reply and bypass permissions; the deploy then ran (guard log: allowed, exit 0) and 11 Apex tests passed in the org.
