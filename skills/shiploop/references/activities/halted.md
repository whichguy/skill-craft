# Terminal halted handoff

Use halt only when the run cannot continue. It writes an unfinished handoff
with the exact reason and durable journal pointer. It does not delete work,
turn a blocker into success, or permit legacy JSON state to reappear.
