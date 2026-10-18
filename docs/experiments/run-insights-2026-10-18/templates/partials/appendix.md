<!-- partial: appendix. The file-only tail (today's pause, pass-log, halt, run-context, last-accepted and deltas blocks):
locators a reader needs after a cut or a reset, never an instruction the stage needs. -->
=== appendix (file only) ===
Pause without consuming the action (only when the user asks or a real blocker stops authorized work): {{pause_command}}. Halt (only on the user's explicit stop): the same command with `halt` in place of `pause`.
Recovery command (reprints the current packet from saved state): {{next_command}}
Pass log (optional, never a completion gate; after a reset, open it first if it exists): RUN/notes/{{action}}.md
State: RUN/state.md (results/ and inbox/ beside it) · Run index: RUN/context-index.md · Long forms of the rules: RUN/reference.md (#policies, #rules, #recovery) · Scratch: RUN/scratch
WORKTREE is the isolated product checkout, returned to the original branch only at release or handoff.
Original request: RUN/request.md (verbatim, sentences S1..Sn).
Accepted results this packet quoted from: {{source_results}}
Last accepted transition: {{last_accepted}}
If this stage changes HOME/, ShipLoop checks and commits it when the stage is accepted; do not commit it yourself.
