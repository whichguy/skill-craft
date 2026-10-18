<!-- partial: rules. STAGE_RULES today, minus the line the frame now carries ("Do only this stage" is kept: ledger row
"rules" anchors it). Long forms stay in RUN/reference.md (reference#rules). -->
RULES (each one fixes a failure live runs showed; the long form is reference#rules):
- Do only this stage, then run its callback; ShipLoop picks the next stage.
- Unattended: take the best default and record it as an assumption; a person-only step is an open item; report blocked only when nothing can proceed without a person.
- Run ShipLoop commands in the foreground, unpiped, and never end the turn while one runs.
- Temporary files go in RUN/scratch, never /tmp. Never read, keep or report credential-store or session contents.
