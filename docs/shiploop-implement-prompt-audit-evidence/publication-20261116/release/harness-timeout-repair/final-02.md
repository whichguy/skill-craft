Changed only the fixture cleanup order in `test/test-harness.test.py`.

- Reproduced the baseline hang; external rescue was required.
- Same fault after repair returned truthful `TimeoutExpired`, with workers dead and no rescue.
- Positive run passed: 3 methods, 6 scenarios.
- Production/note hashes, original eight methods, and qualification-v1 remain unchanged.

[New handoff.json](/Users/dadleet/.codex/visualizations/2026/10/18/01a14c60-cd70-7921-b457-5cf870234201/r19-r16-publication-20261116/harness-timeout-repair/qualification-v2-fixture-cleanup/handoff.json) contains the diff, evidence, and fingerprints.

Parent review/revalidation remains pending. No commit or release.