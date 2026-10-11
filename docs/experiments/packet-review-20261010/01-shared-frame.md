# Packet review report: shared-frame

Verbatim final report of one read-only reviewer (2026-10-10). Packets: checkers-1, battleship-1, s6-after-spec (ShipLoop 0.58.0, release 1.26.0) and older runs. Scratch analysis scripts were not kept; counts are the reviewer's.

SHARED-FRAME REPORT (packets of checkers-1, ShipLoop 0.58.0: 38 producer + 8 Improve packets, 1.81 MB). Scratch scripts: /private/tmp/claude-501/-Users-dadleet-src-skill-craft/8ee9a7a0-b6e5-4ea7-af94-1c3edde60d84/scratchpad/pkt-review/sect.py. Nothing in any repo or run was changed.

METHOD. "Frame" = a line identical (action id and revision normalised) in at least 50% of producer packets. "Refs" = the 10 locator lines + 16 reading-list lines. "State" = snapshot + status + narrative + carried context + context index. Packet files are named nav-<id>.md, not by action; the stage is in the head line.

1. NUMBERS (mean per stage group; the %s are of the packet)
stage group | bytes | frame% | stage-specific% | refs% | state% | stage guidance%
intake | 28.3K | 81 | 19 | 16 | 9 | 31
discovery/research | 39.7K | 59 | 41 | 15 | 15 | 38
spec/test-strategy | 39.0K | 60 | 40 | 15 | 16 | 35
plan | 55.3K | 45 | 55 | 13 | 14 | 44
prepare | 31.8K | 78 | 22 | 17 | 17 | 26
get-next-work-item | 30.1K | 87 | 13 | 16 | 19 | 23
step-plan | 53.4K | 48 | 52 | 14 | 10 | 49
test-spec/test-author | 36.8K | 71 | 29 | 16 | 16 | 32
baseline/skill-assess/skill-validate | 31.1K | 84 | 16 | 18 | 18 | 24
test-red/green/refine/regression | 39.5K | 66 | 34 | 15 | 15 | 33
implement (x4) | 40.8K | 64 | 36 | 15 | 15 | 36
document/static-checks/verify | 41.3K | 63 | 37 | 14 | 15 | 29
integrate/integration-verify/carry-forward | 37.3K | 70 | 30 | 16 | 16 | 32
system-test-author/system-test/acceptance | 36.1K | 69 | 31 | 15 | 15 | 33
release-plan | 40.0K | 61 | 39 | 14 | 15 | 33
release-check/release/verify/operations | 32.8K | 75 | 25 | 16 | 16 | 28
handoff | 34.9K | 71 | 29 | 15 | 19 | 28
done | 17.2K | 80 | 20 | 27 | 29 | 0
Improve packets (8) | 50.2K | 80 identical across Improves | 20 | n/a | n/a | n/a
All producer packets: 67% frame, 33% stage-specific, mean 37.7K. Lines identical in at least 95% of stages total 22.5K per packet (60%). By section, mean share: guidance 32% (of which a 6.5K block is identical in every stage), reading list 12%, workspace/return 7% (2.4K identical), carried context 7%, progress rules 6.6% (2.45K identical), tail 5.5%, state dump 5%, result contract 4.6%, request 3.7%, locators 3.4%, context index 3.5%, goal 2.3%, callback 1.3%.
The model's slice (head line, callback, Goal, Done when, Checked by, Considerations, template) is 3.1K per packet, 8.3% of the bytes. Improve vs its producer packet: 44% of Improve bytes are lines also in the producer packet (about 22K per Improve, 175 KB per run).

2. WHAT THE MODEL READ (toolUse.packets plus events.jsonl of checkers-1)
Of 1.82 MB on disk the model Read 3 packets: the intake packet (29K) and one spec Improve packet (24K + 5K). It also ran 29 shell reads (62K chars) and received 46 printed heads (about 2.4K each). 24 of the 29 shell reads are `sed -n '/^Goal/,/^Write the structured/p'` or a targeted grep. So for 43 of 46 visits it worked from the printed head plus the Goal-to-template slice. battleship-1, r1/r2/r3 and v1230 show the same pattern (readWhole 1-2 per run). A cold session (s6-after-spec resume) ran `next`, then Read the whole 38K packet, and re-grounded in 21 s with 6 calls. So the full file is read only on a cold start or resume. The 90% outside the slice is mostly unused mid-run. Because the head tells the model to "Read the full packet before acting" and it does not, any obligation printed only in the tail goes unread. The model grepped for these four times: "keeps these up to date" (the docs/shiploop file list), "until_loop_ephemeral", "improve-commit", and the binding line. Every `carried` label is true in every packet except `inputs` at intake, which is correct. So `carried` shows presence, not use.

FINDINGS

P-frame-1 (high): the head is not enough after a clear for the 24 of 46 packets that open with a delegation preamble. Inner-loop producers and inline Improve packets start with "Continue in this context and execute the prompt." and an 8-12 line Delegation paragraph (shiploop_prompts.py:79-93). The first 12 non-empty lines then end at "Done when (...)" with zero bullets (24 of 24). The 3 inline Improve packets (step-plan, test-spec, carry-forward) show only the preamble: no stage, no callback, no goal. Fix: order the packet as stage line, Goal, Done when bullets, callback. Move the preamble below, folded to one line ("Delegation: inline; this conversation executes and submits callbacks"). Delete the non-instruction "Continue in this context...".

P-frame-2 (high, S-7 and S-6 tension): "Read the full packet before acting" (packet_head, shiploop_navigator.py:1355-1385) is not what happens, and the 37K file is not what a mid-run model uses. Do not trim the file (S-6). Make the first screen sufficient. Put "keeps these up to date" (knowledge files), the Improve bind/start line, and the one-line commit rule into Considerations or Done when. Reword the head to "re-read the full packet after a clear, or when a step needs a rule not shown here". Add a test that the head carries these lines.

P-frame-3 (medium, size): absolute paths are 23.1% of all packet bytes (420 KB of 1.81 MB; 3,510 paths). In the owner's 1.22.0 plan packet they are 26.7% (14.7 KB of 55 KB): the case root appears 94 times (6.2 KB), the work root 48 times, the plugin root 38 times. If the run root (`$RUN`), worktree, work root and plugin root (`$SL`) are stated once and referenced by short name outside literal command lines, a producer packet saves 4.8K (12.9%) and an Improve packet 5.7K (11.4%): 227 KB per run. If commands can use exported variables too, it is 6.1K and 7.5K per packet, 292 KB per run (16%). In the owner's plan packet the same is 5.3K plus 4.9K, about 18%. Keep callback, recovery, pause, halt and every workspace command literal and copy-pasteable. Source: locator and reading-list construction at shiploop_navigator.py:1210-1290, plus render() at 3122.

P-frame-4 (medium): the constant locator table is 5.1K per packet. Ten locators (State, Result records, Result inbox, Accepted history, Repository locator, CLI locator, skill card, Run directory, Scratch, Keepalive) take 1.27K. Sixteen reading-list lines take 2.86K; they are identical in all 38 stages and are not specific to a stage (Interaction design guide at release, Consumer testing guide at intake). Recovery takes 1.0K. Four workspace locators take about 0.6K. Replace them with one printed "Roots" block (run, worktree, skill, references) plus a brace-list of `references/<file>#<anchor>` names. Keep only the references the stage uses, with the full list one `references/INDEX` pointer away. Saves about 2.2K per packet (about 100 KB per run) before the root saving, about 37 KB after it. Two lines ("Environment lifecycle note ... if present", "Repository knowledge index ... if present") name a file that does not exist in 43 of 46 packets; the script knows, so print them only when the file exists (about 15 KB per run). Many rows are also repeated in the 8 Improve packets.

P-frame-5 (medium): the workspace and return block is unconditional, 2.4-2.7K (7%) in 36 stages. It teaches the plan-return, review-return and route commands, then says "The return operation is unavailable here; the script permits it only at active release or handoff". Gate the commands and route to release-plan, release and handoff (and to blocked or paused packets). Elsewhere keep Execution checkout, Workspace authority and the "all product work happens in the checkout" sentence (about 0.4K). Saves about 92 KB per run. Source: _workspace_return_packet_lines, shiploop_navigator.py:2841, and shiploop_workspace.py:1497.

P-frame-6 (medium): unconditional versus gated blocks. Always printed: callback, Goal/Done/Checked, template (about 1.7K), context index plus pass log (0.9K), snapshot+status (about 1.9K), locator table, request (1.4K), workspace (2.4K), "Navigator contract" generic guidance (6.5K), progress rules (2.45K, identical), tail (callback again, Improve, pause, halt, about 2K). Already gated by a script fact: the narrative (28 of 46), the lint block (static-checks and verify only, 13.9K per run), carried context (not at intake), the preamble. Candidates still printed in all 34 inner and outer stages although the stage or a fact decides relevance: "Requested runtime / entry point" (0.6K), "For identity or access discovery" (0.33K) and, at tier lower confidence, the maintained-requirements and handoff paragraphs (1.3K). Gate the first two to preparation and release stages: about 22 KB per run. The Progress snapshot (8 lines) and status block are printed in the head and again in the file; the file copy could keep just Where and Next (about 1.3K x 46 = 60 KB per run). I rate this one a risk to S-6 (a model re-reading only the file after compaction); decide deliberately.

P-frame-7 (medium, wording): one instruction in several forms. The callback is "Callback for this stage", "Next command (...)", "Callback for this Improve child" and then again "Call this when done" in the tail, the same 410-500 B twice per producer packet (S-7 forbids repeating run rules inside one packet; about 16 KB per run). The delegation preamble and "Execute this packet in this conversation, submit its current callback yourself" say the same thing twice. The model wraps `complete` in a helper script 33 times (scratch/sub.py: writes the result in the template shape, then runs complete). The ceremony is long: three path arguments, plus writing the shiploop-state block by hand. Medium fix in the CLI (S-5): let complete default `--result` to the printed inbox path.

P-frame-8 (medium, inconsistency): reading rules. The printed head says open "only the section a step needs, never a whole reference file, and do not re-read the skill cards". The packet text says "Read the bound Until Loop card in full once per context" (regression, static-checks, test-green; shiploop_prompts.py test-loop text) and the Improve packet says read the selected Improve skill's whole-skill-subcall section. The head also tells the model to read "the full packet" while saying not to print it. Choose one rule and word it identically in all three places.

P-frame-9 (low): commit ownership wording differs. Thirty producer packets say "If this stage changes docs/shiploop/ or SHIPLOOP.md, ShipLoop checks and commits them when accepted; do not commit them yourself". Four stages (prepare, release-plan, release-verify, test-spec) use a second wording ("On done ShipLoop checks these files, screens them for credentials and commits ..."). Integrate says ShipLoop commits the item's declared paths. Improve packets tell the reviewer "change what is warranted ... and commit it" via improve-commit. These agree in effect but should share one sentence from one constant (S-12 one implementation of each mechanism).

P-frame-10 (low): callback correctness, placeholders, stale names. Every callback in the checkers-1 and s6-after-spec packets matches the CLI parser (shiploop_protocol.py:549-620): complete takes --run-dir --action --result; improve-start takes --opening; improve-commit takes --message; pause and halt take --reason; the Improve parent callback is improve-complete and never complete. No `select-work` appears in any packet (only the _RENAMED_STAGES map at shiploop_navigator.py:218). All remaining `<...>` tokens are deliberate template placeholders. The only absolute paths that do not exist are the declared optional or create-later ones (pass log, notes, SHIPLOOP.md, environment-lifecycle note, opening.md, final-result, review notes). The Considerations list is absent from skill-assess, skill-validate and handoff (the others have it); the template text "drops the other template fields (work_items, assumptions, steps, ...)" appears at intake, where those fields do not exist.

P-frame-11 (low, S-7): the printed head is "short" in the spec, but in practice 2.8-5.7K per print: Done-when, Checked by (400 B), the full result template (0.9-2.1K), the status block and the narrative (1.4K). The narrative must be shown to the user, so that part is fine; the status block's "do not reprint" line is correct but the block adds about 0.5K.

5. IMPROVE PACKETS. 1.24.0 packets (r1-battleship-sonnet) had no Goal and no Done when (0 of 8); the 1.26.0 ones carry both (8 of 8), the Done-when identical to the producer's (verified for all 8), at the cost of about 1.3K per packet (mean 48.9K to 50.2K). A new Improve reviewer gets the goal, the Done-when with "correct the result, never the condition", the stage's review focus (planning focus or end-of-work code review focus), the producer result under review, and the opening-file contract. It does not get the stage's Considerations or guidance, and no line names the producer packet file (nothing points to nav-<action>.md), so a reviewer who needs the Develop/Test/Deploy/Tools considerations has no path to them. Add one line "Producer packet (stage rules and considerations): <path>". 44% of each Improve packet is lines also in the producer packet and 80% is shared across all Improve packets (locator table, workspace, request, progress rules). The roots, constant-table and workspace gates above give the same relative saving there (about 46 KB per run from roots alone, more from the gated block). The Improve packet is long on conditional prose (about 160 lines of "Follow the packet's ... guide" paragraphs for UI, interaction, remote-resident tests, repository-local skills, state and data), only some of which applies to a Node checkers app; gate these by the item's facts (stage kind, a UI in the plan, a remote target). The Improve Goal line begins "Reviewing the returned X result. Goal:", so the model's `sed '/^Goal/'` slice does not match it.

RECOMMENDED FRAME (keeps head, callback, recovery in the first screen)
1. Stage line, Goal, Done when bullets, Checked by (one sentence). 2. Callback (literal), result file path, template, outcomes. 3. Recovery, pause and halt (literal). 4. One "Roots" block (run, worktree, skill, references) and the constant-table pointer. Then the stage rules (Considerations and guidance), then the run state, with every non-command path relative to the roots.
Bytes per run (checkers-1, 46 packets, 1.81 MB), about 400 KB (22%), mean producer 37.7K to about 29K, overlaps removed:
- Roots once, commands literal: 227 KB (292 KB if commands may use variables).
- Gate workspace and return to release, release-plan and handoff: about 92 KB.
- Compact constant reference table after the roots: about 37 KB; existence-gate the two optional lines: about 15 KB.
- Drop the duplicate tail callback: about 16 KB.
- Gate the identity and runtime paragraphs: about 22 KB.
Optional and riskier: trim the snapshot to Where and Next in the file: about 60 KB. Nothing here removes an obligation; what leaves the packet moves to the references or is stated once.

FIX FIRST (in order)
1. P-frame-1: head order and the one-line delegation preamble (shiploop_prompts.py:79-93; shiploop_navigator.py:1355).
2. P-frame-3 and 4: roots stated once and a constant locator table (shiploop_navigator.py:1210-1290).
3. P-frame-5: gate the workspace and return block (shiploop_navigator.py:2841).
4. P-frame-2: lift the greppable obligations (knowledge file list, Improve binding) into the head, and reword "Read the full packet before acting".
5. P-frame-8 and 9: one reading rule and one commit sentence, plus the Improve packet's producer-packet pointer.

NOT ANSWERED FROM THE FILES
- Whether the unread 90% would change a result: no run varied it. The run docs show the model skipped it and passed, not that it was unnecessary.
- Grok runs have no toolUse.packets; whether Grok reads whole packets (the S-6 evidence says it does after a compaction) could not be measured.
- The actual compaction behaviour of this model after a clear inside a stage (the evidence is the single cold resume at s6-after-spec).
