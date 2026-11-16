**CHANGES_REQUIRED**

**P2 — Failure cleanup can hang before terminating fixture workers.** At [test-harness.test.py:244–254](/Users/dadleet/src/skill-craft-r19-r16-publish-harness-evidence-20261116/test/test-harness.test.py:244), `finally` calls unbounded `proc.communicate()` **before** killing the owned worker and descendant. Both inherit its output pipes. If supervision fails to terminate them, the timed communication at line 198 expires, but cleanup then waits indefinitely for pipe EOF; the worker-kill loop is unreachable. This converts the regression being tested into a hung suite.

Terminate fixture-owned processes before draining those pipes, preserving the original failure.

**Smallest confirming experiment, not run:** in a temporary fixture variant, suppress SIGKILL forwarding in its `killpg` wrapper and run only `cleanup`. The current fixture should remain blocked past its 2.5-second allowance until external cleanup kills the workers. The corrected fixture should report failure and clean up its processes.

No additional production correctness blocker found in the staging, no-replace publication, or reordered evidence attempt.

Reviewed HEAD `3d277e4ab7d5df678cd6aacfa9a970da608b5d3b`; all three current file hashes match the [frozen source receipt](/Users/dadleet/.codex/visualizations/2026/10/18/01a14c60-cd70-7921-b457-5cf870234201/r19-r16-publication-20261116/harness-repair-dirty-source.json), which records fingerprint `2f82bb948568b935d2f68d0e0db92ed716240c44d7f504bb764bef5b966fd382`. Whole-tree fingerprint was not recomputed.

Read-only review; no tests, probes, network, advisors, agents, or edits. Retained results do not establish current CI success or the historical interruption’s exact cause. Provider-served model/profile identity was not independently attested.