Fixture v4: portable public API behavior
==========================================

This fixture contains deterministic, provider-free setup and record APIs. The
prompt-facing input is subject/: contract.txt, setup_app.py, change_app.py, and
test_existing.py. Keep oracle/ hidden from a candidate test author. Oracle
contains independent behavior tests, two correct implementations, six focused
mutants, and runner controls.

Run a candidate unittest file with the standard library:

  python3 oracle/run_fixture.py --tests /path/to/generated_tests.py

The runner checks both correct implementations before running mutants. A suite
is valid only when both pass it with no skips, errors, empty discovery, import
or loader failures, or other invalid events. Only an AssertionError originating
in a test method can kill a mutant, and only after that gate passes. A setup-only
suite can be valid while record mutants survive; each mutant's required
behavior is listed in oracle/run_fixture.py and in calibration output.

Run the complete reference and apparatus calibration with:

  python3 oracle/run_fixture.py --calibrate --output /path/to/receipt.json

The output path must be outside this fixture. Without --output, results print
to stdout and no checked fixture file is changed. Calibration includes all six
invalid-suite controls, all seven unittest classification controls, arity
contract controls, and the fixture-seeded-only false-positive control. Python
standard library only; no model, service, home-directory, or repository access
is used.

Public contract
---------------
subject/contract.txt is the authoritative public contract forwarded to the
native case. Make behavior clarifications there, including Python call-binding
errors outside application envelopes. This guide describes the apparatus;
it is not a second copy of the API contract.

Runtime: Python 3.9 or newer (standard library only).
