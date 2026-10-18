# Owner finding (2026-10-17): status block and narrative duplicate each other

Measured on the 36 packets of the chess run (`PR/in/*.packet.md`): 28 carry both `=== ShipLoop status ===` and `=== ShipLoop narrative ===`, 8 carry status only; 8 of the 11 Improve packets carry a narrative. Status ~570 chars, narrative ~1,000 chars per packet; 20,539 + 24,337 = 44.9 KB over the run (2.7%).

Overlap: Where = Now, Done = Achieved, Next = Ahead, Run = phase progress bar. Narrative alone adds goal and pace; status alone adds the Item plan line.

Readers: status block -> `shiploop_status_hook.py` (`status_block`, two-line systemMessage; only Claude Code CLI displays it) and the model; `status.md` and `shiploop status` are written separately (`shiploop_navigator.py` STATUS_BEGIN/STATUS_END, status writer) and do not need the packet block. Narrative -> the model shows it verbatim to the user (the only user-visible progress on desktop, VS Code, Codex); hook shows it at milestones (`narrative_text`). `references/status-display.md` says narratives appear only at milestones; this run shows them on 28 of 36 packets including Improve.

Proposal: one block per packet. Milestone packets: narrative only, hook reads Now/Achieved from it. Other packets: one line `Where … · Next …`. Improve packets: neither. status.md and `shiploop status` unchanged. Tests pinning both blocks change.

# Owner TODO (2026-10-17): per-step inner-loop series in order
After step-plan and its Improve, each planned step should get its own implement → checks → Improve, in plan order. Chess run: step-plan 1 had S1→S2→S3; implement S1 revised because the gate runs every `suite: check` command after every step and the only check (grep for S3's board files) cannot pass on S1; the second step-plan merged everything into one step (11 paths), so 1 implement + 1 Improve ran instead of 3 + 3. Engine cause: check commands are item-wide, not bound to the step that makes them true.
