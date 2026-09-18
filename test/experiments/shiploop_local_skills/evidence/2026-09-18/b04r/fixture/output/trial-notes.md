# b04r local-skill trial notes

## Actions

- Read the fixture README, repository knowledge, durable lesson, incident and
  release contracts, both supplied bundles, the existing local release skill,
  and the frozen `skill-assess` packet.
- Wrote `output/decision.json` from `docs/incident-contract.md` and
  `data/bundle.json`. The latest matching receipts are `unit` attempt 1 pass
  and `integration` attempt 1 fail, so the incident decision is `investigate`.
- Applied `docs/release-contract.md` to
  `data/v1-compatibility-bundle.json` using the existing
  `release-evidence-triage` procedure. With the contract defaults, both selected
  staging receipts pass, so the exact v1 result is `clear` and deployment
  authorization remains `false`.

## Local-skill disposition

The existing `skills/release-evidence-triage/SKILL.md` was reused for the v1
release-compatibility artifact. It is not suitable for the incident bundle:
the incident contract has a different request identity, output schema, and
decision vocabulary. Created the compatible separate
`skills/incident-evidence-triage/SKILL.md` and indexed it in `README.md`.
The new skill takes the applicable contract as an input and delegates its
contract-specific rules to that authority.

## Verification

Performed local validation with a clean Python process: both JSON artifacts
parsed; each had exactly its contract-defined key order and schema; independent
receipt recomputation matched the selected rows and decisions; and the new skill
had nonempty frontmatter, contract-authority guidance, and a README index entry.
No ShipLoop callback, Improve execution, installation, dependency change,
publication, or deployment was performed.
