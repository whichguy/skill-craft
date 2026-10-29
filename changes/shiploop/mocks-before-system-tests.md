---
bump: minor
---
A test-spec case may name the mock it runs against, and the test stage builds those mocks first (design T sections
8.2 and 8.5, F5).
- A `test_cases` row may add `"mock": {"simulates": "...", "plays": "..."}`: what the mock stands in for, and the
  slow, failing or out-of-order behaviour it plays. Both are nonblank text; a mock of any other shape, or one still
  holding the shape's placeholders, is refused.
- The test-spec duty says a case whose code calls a dependency (the network, the clock, randomness, storage, a child
  process, a browser API) names its mock. Every packet that quotes the cases prints it under its case.
- The test duty opens with "Mocks first": build each named mock before its case's test, and give the mock a header
  that states what it stands in for and what it plays.
- No new gate: one is added only if a live run shows cases skipping their mock.
