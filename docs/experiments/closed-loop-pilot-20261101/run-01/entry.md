## Qualified cycle: LR-20261101-1b4675 on hello-hook-continuation — UNDECIDED, prediction refuted (2026-11-01)

**Question.** Stage 4 pilot: a build with the qualified missing-completion hook reverted looks cheaper but must be rejected (S-2). Does the candidate move what it predicted?

**Setup.** Loop tip b665a3fac1d7, candidate 1e2fb1631288; driver codex gpt-6.1-terra high; 3 attempts per arm, tolerance 0.25 on tokens (stated, not measured: the false-decision rate is unknown); epoch /Users/dadleet/e2e-runs/2026-11-01/closed-loop-pilot-01/cycle/epoch. Cases: hello-hook-continuation (regression).

**Result.**

| case | measure | control | candidate | change | predicted | verdict |
|---|---|---|---|---|---|---|
| hello-hook-continuation | tokens | 18258993.0 | None | no successful case to divide the all-attempt total by | down 0.25 | unknown |
| hello-hook-continuation | accuracy (guard) | 1.0 | 0.0 | -1.0 | not_down | broken |

**What it shows.** Decision UNDECIDED: registered attempts have no sealed run receipt: candidate-hello-hook-continuation-1, candidate-hello-hook-continuation-2, control-hello-hook-continuation-2, control-hello-hook-continuation-3; required quality evidence is unknown for hello-hook-continuation (control), hello-hook-continuation (candidate).
Prediction refuted; the record is now admitted (undecided: registered attempts have no sealed run receipt: candidate-hello-hook-continuation-1, candidate-hello-hook-continuation-2, control-hello-hook-continuation-2, control-hello-hook-continuation-3; required quality evidence is unknown for hello-hook-continuation (control), hello-hook-continuation (candidate) [tolerance and attempts stated, not measured]).
A hand-built candidate: nothing on a loop branch moved.

