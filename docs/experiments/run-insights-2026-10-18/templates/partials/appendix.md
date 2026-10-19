<!-- partial: appendix (version 2). The file-only tail: locators a reader needs after a cut or a reset, never an
instruction the stage needs. Version 2:
- the recovery command goes: the frame prints it;
- Pause stays here (round 2 moved it to the frame; the budget moved it back);
- the context-index goes (decision 12);
- the WORKTREE line prints only on a worktree run. -->
=== appendix (file only) ===
Pause, only when the user asks or a blocker stops all authorized work (it keeps this action): {{pause_command}}. Halt (only on the user's explicit stop): the same command with `halt` in place of `pause`.
Pass log (optional, never a completion gate; after a reset, open it first if it exists): RUN/notes/{{action}}.md
State: RUN/state.md (results/ and inbox/ beside it) · Long forms of the rules: RUN/reference.md (#policies, #rules, #recovery)
{{#if worktree_run}}WORKTREE is the isolated product checkout, returned to the original branch only at release or handoff.
{{/if}}Original request: RUN/request.md (verbatim, sentences S1..Sn).
Accepted results this packet quoted from: {{source_results}}
Last accepted transition: {{last_accepted}}
If this stage changes KNOWLEDGE/, ShipLoop checks and commits it when the stage is accepted; do not commit it yourself.
