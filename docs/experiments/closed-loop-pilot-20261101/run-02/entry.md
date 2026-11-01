## Qualified cycle: LR-20261101-1b4675 on hello-hook-continuation — DROP, prediction refuted (2026-11-01)

**Question.** Stage 4 pilot: a build with the qualified missing-completion hook reverted looks cheaper but must be rejected (S-2). Does the candidate move what it predicted?

**Setup.** Loop tip 605a526e7cf9, candidate b04162c89445; driver codex gpt-6.1-terra high; 3 attempts per arm, tolerance 0.25 on tokens (stated, not measured: the false-decision rate is unknown); epoch /Users/dadleet/e2e-runs/2026-11-01/closed-loop-pilot-02/cycle/epoch. Cases: hello-hook-continuation (regression).

**Result.**

| case | measure | control | candidate | change | predicted | verdict |
|---|---|---|---|---|---|---|
| hello-hook-continuation | tokens | 18203931.333333332 | None | no successful case to divide the all-attempt total by | down 0.25 | unknown |
| hello-hook-continuation | accuracy (guard) | 1.0 | 0.0 | -1.0 | not_down | broken |

**What it shows.** Decision DROP: an established requirement fell: hello-hook-continuation.
Prediction refuted; the record is now refuted (dropped, and the prediction was refuted: an established requirement fell: hello-hook-continuation [tolerance and attempts stated, not measured]).
A hand-built candidate: nothing on a loop branch moved.

