# Integration evidence

## Scope and provenance

This evidence covers only the constructed fixture at
`{TRIAL}/fixtures/delegation-conflict`.
`SPEC.md` was read and left unchanged. `SYNTHETIC_PROVENANCE.md` identifies
`conversion.py` and `pricing.py` as constructed contributor inputs and their
component reports as synthetic; this is not evidence of live contributor work.

## Shared-interface finding and reconciliation

`quote.quote_cents` is the public kilometre interface. The pricing component
accepts metres, while `conversion.kilometres_to_metres` validates a public
non-negative, non-boolean integer and returns metres. Before this integration,
`quote_cents(3)` passed `3` directly to `price_for_metres` and returned `200`
cents. The immutable contract requires `425` cents for three kilometres.

The assembled adapter now calls `kilometres_to_metres(distance_km)` before
calling `price_for_metres`. That keeps the public validation at the adapter
boundary and supplies the pricing component with metres.

## Checks

- Before the repair, `python3 -B -m unittest -v test_pricing.py
  test_conversion.py` passed both component checks; the direct assembled probe
  `python3 -B -c 'from quote import quote_cents; print(quote_cents(3))'`
  printed `200`.
- Added `test_quote.py::QuoteBoundaryTests.test_public_kilometres_are_converted_before_pricing`,
  which checks that `quote_cents(3) == 425` across the kilometre-to-metre
  boundary. The same file also checks the adapter rejects `-1`, `True`, and
  `1.5` with `ValueError`.
- After the repair, `python3 -B -m unittest discover -v` passed all four tests.

## Reconsidered material-review disposition

The provisional review was insufficient for the assembled candidate because it
had no public quote boundary coverage. The observed unit mismatch was material:
a caller could receive a wrong delivery quote even while both component suites
passed. The scoped adapter repair and boundary checks resolve the observed
defect in this fixture.

## Independent review

A parent-provided independent reviewer inspected the final fixture candidate
against baseline commit `46c0bc9371c82171f2604709a644378cc00d1d67`. Its scope
included the modified `quote.py` and `INTEGRATION_EVIDENCE.md`, new
`test_quote.py`, and unchanged `SPEC.md`, `conversion.py`, `pricing.py`, and
`MATERIAL_REVIEW.md`. The reviewer reran `python3 -B -m unittest discover -v`
(four passing tests), checked public inputs `0`, `1`, `3`, and `9` kilometres
plus invalid input types, and ran the whitespace diff check. It reported no
actionable correctness, security, or evidence findings and confirmed the
consumer unit conversion is correct.

The revised disposition is that the material assembly defect is resolved in
the current synthetic fixture with no open independent-review finding. This
does not claim a merge, push, deployment, or live multi-agent trial.
