# Local trial notes

## Outcome

The release decision is `blocked`. The current request is `candidate-alpha` on
the default `staging` target. Its latest `unit` receipt passed at attempt 1, and
its latest `integration` receipt failed at attempt 2. The output preserves the
contract-required check order and leaves `deployment_authorized` false.

## Reuse disposition

Created the repository-local `release-evidence-triage` skill and indexed it in
the README. No existing local skill was available. The demonstrated stale-pass
failure in `docs/lessons.md` and this bundle's later failed integration attempt
show a repeatable selection boundary: match the request identity and use the
largest numeric attempt per required check. The skill links to the authoritative
contract rather than copying its changing defaults or output contract.

## Files used

- `README.md`
- `SHIPLOOP.md`
- `docs/lessons.md`
- `docs/release-contract.md`
- `data/bundle.json`
- `skills/release-evidence-triage/SKILL.md`

## Local verification

Ran an independent local recomputation of the selected receipts and full decision
JSON against the contract's resolved values. It passed. The same check exercised
an explicit target/check override, a later blocked receipt, and a missing receipt;
it also verified the skill's frontmatter, contract link, and README index. No
deployment, ShipLoop callback, or Improve run occurred.
