# Project knowledge

Read current source and docs/environment.md, then retain the discovery decision and exact evidence locators in this index.

## Discovery: name whitespace normalization

- Decision for a later implementation step: preserve string-only behavior and normalize names by trimming edges plus replacing each whitespace run with one ordinary space. The proposed Python expression is `" ".join(value.split())`; it is a proposal, not an applied edit.
- Current behavior: [src/app.py: normalize_name preserves internal runs](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/src/app.py:1). The existing edge-only assertion is [test_fixture.py: Baseline.test_edges](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/test_fixture.py:4).
- Baseline: [BASELINE.txt: unchanged fixture test result](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/BASELINE.txt:1), run with `python3 -B -m unittest discover -v`, passed one edge-trimming test. Its coverage does not include internal whitespace.
- Environment boundary: [docs/environment.md: local stateless helper](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/docs/environment.md:1) and [README.md: synthetic remote-observation boundary](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/README.md:6).
- Full discovery and required test additions: [DISCOVERY.md: findings and revalidation](/Users/dadleet/tmp/shiploop-discovery-implementation-20260920/semantic-v3/cases/local/workspace/DISCOVERY.md:1).
