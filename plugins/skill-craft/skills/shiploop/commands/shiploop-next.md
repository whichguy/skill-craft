# /shiploop next

Reprint the current packet without advancing the run:

~~~sh
python3 "$SKILL_ROOT/scripts/shiploop" next --run-dir "$RUN_DIR"
~~~

Use it after a context reset or interruption, then follow the reprinted packet.
`next` never chooses a successor, completes a step, imports an Improve child or
unpauses a run. The packet names the current
owner (a producer step or its bound Improve child) and its one legal callback on
the line after the header. A saved run from an older protocol is refused with an
error naming it; start a fresh run directory for that request.
