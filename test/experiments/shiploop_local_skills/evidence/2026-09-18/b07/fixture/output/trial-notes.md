# Trial notes

- Read the repository index, knowledge file, durable lesson, v1 contract, current
  bundle, existing local skill, and frozen `skill-assess` packet.
- Applied `specs/release-contract.md` to `data/bundle.json`: for
  `candidate-bravo` targeting `production`, the latest matching `unit` receipt
  is attempt 2 (`pass`) and the latest matching `integration` receipt is attempt
  1 (`pass`). The local decision is `clear`; deployment remains unauthorized.
- Skill disposition: reused `skills/release-evidence-triage/SKILL.md` unchanged.
  Its contract-first inputs, latest-attempt rule, local output boundary, and
  independent recomputation procedure fit this v1 task exactly.
- Wrote `output/decision.json`. A fresh `jq` recomputation from the bundle
  compared equal to the artifact (`true`), validating JSON parsing, exact shape,
  required-check order, selected receipts, decision, and authorization flag.
- No ShipLoop callback or Improve execution was performed.
