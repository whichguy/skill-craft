# Living specification

This test-only work item adds durable regression coverage for two existing correct local APIs. contract.txt is the complete public contract. No UI, remote deployment or live provider requirement belongs to this fixture.

## R-1: Setup success
For authorized valid save_setup calls, success and read_config follow the state contract in contract.txt, including its exact field semantics.

## R-2: Setup rejection
Denied or invalid setup writes leave configuration unchanged and return the documented error envelope.

## R-3: Proposal and confirmation
Record proposals and confirmation follow the documented owner, amount and version contracts. Proposing alone never changes the record; confirmation applies the proposed change.

## R-4: Record lifecycle
Record replay, cancellation, stale and unauthorized operations follow the state and error contracts in contract.txt.

## R-5: Read and call boundaries
Reads return copies or the specified None denial. Calls obey the documented Python signature and application error boundary.

## Preservation
Production setup_app.py, change_app.py and contract.txt remain unchanged. Existing test_existing.py behavior is preserved. Add only stdlib test/helper code and relevant knowledge. The required new test file is test_acceptance.py. Tests use the public API and documented fixture_seed helpers. No new packages or services.
