Real TAP output that `sf apex run test --result-format tap` printed in the independent Salesforce Grok chat trial of
2026-11-14 (Codex, GPT-6.1 Sol, ShipLoop 1.34.3), read by `test/shiploop-test-counts.test.py`. The sources are in that
run's `run/.shiploop-runs/work-20261114-161603-238276/run/notes/`; the review is
`docs/experiments/grok-chat-full-run-review-20261114/README.md`.

Neutralized, and nothing else changed:

- the class prefix `SLGrokChat` reads `Widget`;
- the org username in the `# Run "sf apex get test ..."` line reads `user@example.com`;
- org record IDs read `a00000000000000AAA`, and a record name lost the word "Grok";
- the wrapper's local evidence path reads `/work/.sf/native-tests/run-1`.

The plan, the points, their numbers and order, and every other line are as the run printed them.

| Fixture | Source | sha256 of the source | What it is |
| --- | --- | --- | --- |
| `apex-pass-9.tap` | `security-tests8.tap` | `c26921a1314908a0e59a07d286096ac5efb6f66ac463628b2aa0f64b7cfcc35c` | `1..9`, nine `ok N Class.method` points, one `# Run` comment: the output the trial's regression row was refused on as uncounted |
| `apex-pass-36.tap` | `controller-tests8.tap` | `859b37589d10a3a46cf2668b1221d6aa0121098b3dfe0513ad8373cc4ff105f2` | `1..36`, all passing: the focused row whose ids showed while `min_tests: 8` was never applied |
| `apex-fail-19.tap` | `controller-tests1.tap` | `1a29797d94e6f440d919ae4278a9d2d736d53e5bc284974859be2328cf8b8e5e` | `1..19` with 3 `not ok` points and their `#` diagnostic lines |
| `wrapped-38.tap` | `connection-red.tap` | `d3dfc3a85e7e2e2b8952dfbf8e709f65459592507591988277f248a430a4ccc0` | the builder's wrapper output: the native `1..38` points (2 failing) plus the `# tests / # pass / # fail / # cancelled` totals it added, which the node reader counts (so TAP is not read a second time) |
