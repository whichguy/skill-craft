Implemented schema-only v2 reuse, removed judgment markers, retained the pytest error fix, and added the requested regressions.

All 18 selected methods pass with stable source hashes; `git diff --check` passes. No commits, agents, release, deployment, or full bank.

[Handoff: exact changed paths, method IDs, commands, hashes, and raw log paths](/Users/dadleet/.codex/visualizations/2026/10/18/01a14c60-cd70-7921-b457-5cf870234201/r08-20261115/roll-forward/worker/handoff.json)

Fidelity retains v1 reporting and reads current v2 receipts. Runtime reuse requires v2. Frozen artifacts remain untouched.

Issue retained: the red run’s overall snapshot was unstable because an unselected historical fixture was restored during execution. Selected source files stayed stable; both green runs were fully stable.