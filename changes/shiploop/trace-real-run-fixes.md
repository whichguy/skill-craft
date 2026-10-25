---
bump: patch
---
Run trace, after its first real host run: the request view now reads intake's sentence readings however the host words
them (`S1: outcome = …`, `S1: Outcome: …`, `S2 (paraphrase): boundary - …`, `S1 maps to …`, as well as `S1 outcome: …`);
before, 11 of 27 real intakes that cite every sentence read as "intake read 0 of N", and the terminal request view then
hid intake's summary too. An intake summary that cites no sentence now stays in that view. `workspace start` is one
command in the trace (it ran init, or next on a re-entry, and both were recorded); `trace --action` takes an id without
its `nav-` prefix (the hex the digest prints); and the digest's totals say "1 packet", "1 reprint", "1 check failed",
"of 1 sentence".
