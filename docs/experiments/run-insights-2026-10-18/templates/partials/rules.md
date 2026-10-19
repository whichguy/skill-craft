<!-- partial: rules (version 2). STAGE_RULES, minus what the frame now carries. "Do only this stage" stays: ledger
row "rules" anchors it.
- "record it as an assumption" is reworded: only plan, carry-forward and the outer stages accept an assumptions field.
- blocked is worded as N5 words it.
- the "unpiped" half is dropped: the callback line and the loop block already say it.
- the reference#rules locator goes: it is undefined in the print. -->
RULES:
- Do only this stage, then run its callback; ShipLoop picks the next stage.
- Unattended: take the best default and record it in the result (in `assumptions` where the form has that key, otherwise in `summary`). A step only a person can do is an open item. Report blocked only when a person or an outside service must act before any work can continue.
- Run ShipLoop commands in the foreground, and never end the turn while one runs.
- Temporary files go in RUN/scratch, never /tmp. Never read, keep or report credential-store or session contents.
