# Trial notes

- Read `README.md`, `SHIPLOOP.md`, `docs/lessons.md`,
  `specs/release-contract.md`, `docs/release-contract-v2.md`,
  `data/bundle.json`, `data/v1-compatibility-bundle.json`, the existing local
  skill, `packets/skill-assess.md`, and its referenced reuse/local-skill
  guidance.
- The current bundle is `release-v1`, so `specs/release-contract.md` governed
  the result. Its matching latest receipts are `unit` attempt 1 (`pass`) and
  `integration` attempt 2 (`fail`); `decision.json` therefore records
  `blocked` with `deployment_authorized: false`.
- Reused and updated the indexed repository-local `release-evidence-triage`
  skill because its former `docs/release-contract.md` reference no longer
  exists. It now points to the v1 authority and directs v2 bundles to the
  additive v2 contract. The existing README index remained valid.
- Verified JSON parsing and exact v1 recomputation, a clear result for the v1
  compatibility bundle, skill frontmatter, both linked contract paths, and the
  README entrypoint. No ShipLoop callback, Improve run, installation,
  deployment, commit, or publication was performed.
