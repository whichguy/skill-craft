# Local skill trial notes

- Read the fixture README, repository knowledge, durable lesson, v1 and v2
  contracts, both bundles, the existing local skill, and the frozen
  `skill-assess` packet.
- Recomputed the v2 selection using the default target and checks. Both latest
  receipts pass, but integration age `5` exceeds `max_age` `3`; the v2 decision
  is therefore `blocked` and does not authorize deployment.
- Recomputed the v1 compatibility selection. Both latest receipts pass, so the
  v1 decision is `clear` with deployment authorization still `false`.
- Skill disposition: reuse unchanged. `skills/release-evidence-triage/SKILL.md`
  already requires the applicable contract and bundle, directs contract-defined
  output, latest numeric receipt selection, independent recomputation, and
  separate deployment authority. The additive v2 contract supplies the age rule
  without needing copied defaults or a prompt update.
- Validation: parsed both output JSON documents and independently checked their
  complete schemas and selected receipt values against the applicable bundles.
- No ShipLoop callback, Improve run, installation, dependency, publication,
  commit, deployment, or other work outside this fixture was performed.
