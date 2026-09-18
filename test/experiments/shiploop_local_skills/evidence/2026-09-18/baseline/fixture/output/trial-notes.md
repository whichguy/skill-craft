# Trial notes

- Scope: bounded local triage of `candidate-alpha` under the fixture's
  `docs/release-contract.md`; no ShipLoop callback or Improve work was run.
- Evidence: target resolves to `staging`; required checks resolve in the contract
  order. Matching receipts select unit attempt 1 (`pass`) and integration attempt
  2 (`fail`). The later matching integration failure blocks the local decision.
- Reuse disposition: no existing fixture-local skill, helper, MCP capability, or
  library pattern was present. A repository-local prompt skill is warranted: the
  durable lesson records the exact stale-pass selection failure this repeatable
  triage needs to prevent. Added `skills/release-evidence-triage/SKILL.md` and
  indexed it in `README.md`; it directs consumers to the authoritative contract
  instead of duplicating its defaults.
- Validation: parsed `output/decision.json` and asserted its exact contract
  fields, selected rows, blocked decision, and false deployment authorization;
  verified the skill's authoritative-contract reference and README index.
