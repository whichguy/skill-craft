**Finding — P1: Improve seed import still bypasses settlement evidence-existence admission.**

At [shiploop_navigator.py:10205](/Users/dadleet/src/skill-craft-r07-20261115/skills/shiploop/scripts/shiploop_navigator.py:10205), evidence is checked only when `final_result` is supplied. Completion without `--final-result` checks the seed’s continuity, then imports that seed through `finish_improve`.

Reachable trigger:

1. A pending outcome is due at `release-plan`.
2. The producer submits `unverified: []` with a valid settlement referencing `RUN/observation.txt`; completion starts Improve.
3. That file disappears while Improve runs.
4. Improve completes without `--final-result`.

The seed still satisfies settlement shape and identity coverage. No downstream gate rechecks its nested reference, so the outcome can disappear from the accepted pending list despite missing evidence. Supplying the identical seed explicitly as `--final-result` would refuse.

**Smallest repair and validation:** apply evidence checking to the effective result—seed or final result. Extend the actual Improve CLI fixture with this sequence, asserting refusal at import and unchanged accepted state; retain an unchanged-file positive control. The current [Improve regression:443](/Users/dadleet/src/skill-craft-r07-20261115/test/shiploop-actual-improve-cli.test.py:443) exercises explicit final results only.

HEAD and all nine hashes matched the freeze before and after inspection. Both previously reported cache defects appear repaired. This finding is established by static call-path inspection, not a new execution. No tests, edits, agents, or advisors were run. Draft docs and the earlier 41-suite result do not establish current-candidate validation; reference acceptance establishes neither semantic truth nor authenticated authority.

