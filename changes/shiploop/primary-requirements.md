---
bump: minor
---
- **The spec records primacy:** a done spec result lists `primary`, the requirements (R-<n>) that carry the request's
  primary outcomes: what the user asked for directly. ShipLoop refuses a missing or empty list, the template entry,
  an ID that is not R-<n> or is listed twice, and an ID with no current entry in KNOWLEDGE/spec.md. The gate runs on
  `complete` and on the Improve stage's import.
- **Every unverified row names its requirement and its lower-layer check:** each product-acceptance `unverified` entry
  is `{outcome, requirement, reason, lower_layer_check, settle, owner, due_stage}`. `requirement` is one R-<n> with a
  current entry in the spec; `lower_layer_check` is the executed check below the e2e layer that shows the outcome's
  logic works.
- **The gate on a primary requirement:** an outcome of a requirement in `primary` is accepted only when its
  `lower_layer_check` is the ID of a test that ShipLoop ran and saw pass (a passed run in its own test records of an
  accepted work-item stage) in a test case for that requirement. For any other requirement a stated reason may stand
  in for the check. The refusal names the passed IDs, or add-work with one corrective work item that adds the missing
  unit or component test, in the add-work shape the packets print.
- **Packets quote it by value:** product-acceptance prints a required Primary requirements block, with each primary
  requirement and the tests that passed for it. The unverified rows printed at their due stage and at handoff show the
  requirement and the lower-layer check, and the report's table gains both columns.
- **Texts:** the spec duty asks for `primary`; the product-acceptance duty names the two new fields; the Checked-by
  lines of both stages name the new refusals. The glossary defines "primary requirement" and "lower-layer check".
