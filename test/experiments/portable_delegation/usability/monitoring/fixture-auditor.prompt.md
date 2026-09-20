Assignment reminder: perform a read-only audit of frozen Git-integration fixtures and
their evidence claims. Do not edit source, production, fixture or operator files.

Inputs:
- Integration fixture root: <INTEGRATION_ROOT>
- Frozen U16 main path: <U16_MAIN_PATH>
- Frozen U16 reference path: <U16_REFERENCE_PATH>
- Report path outside source: <FIXTURE_REPORT_PATH>

Read all 19 fixture files under the integration root and the supplied U16 main/reference.
Check that the claimed G1/G2/G3 setup, target/sync/conflict/validation boundaries and
receipt requirements are internally recoverable from the supplied text. Report concrete
inconsistencies, missing recovery facts, and what a parent must independently verify.
You may use further native delegation for independent subchecks when useful and
supported; retain its native result rather than inventing it. If unavailable, continue
without simulating it.

Write a self-contained report at the report path. In the native final receipt state the
assignment reminder, reviewed paths/hashes, findings or no findings, any delegated
subcheck and its result, report reference, recommended next action, and unresolved
decisions. Do not claim acceptance or unverified success.
