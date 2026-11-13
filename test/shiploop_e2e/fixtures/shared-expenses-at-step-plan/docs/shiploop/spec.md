# Shared expenses specification

## Requirements

### R-1: Runtime and persistence
Run server.js with PORT and DATA_FILE, no npm dependencies. Groups and expenses persist across restart; a successful response means the update was saved. Confirm by starting, writing, restarting and reading over HTTP. Basis: request S1-S2, S11. New system; no preserved behaviour. State is owned by one server process, persists until file removal, and is readable by its clients; no authentication was requested. Concurrent requests must all survive. Confirm by concurrent POSTs and restart.

### R-2: Groups
POST /groups creates a group with ID and at least two distinct nonempty member names, returning 201; existing ID returns 409 and invalid members return 400. Confirm via HTTP, including duplicates and empty names. Basis: S3. Default: reject empty or non-string IDs and names. New system, no previous state.

### R-3: Expenses
POST /groups/<id>/expenses accepts a member payer, positive whole safe integer cents, and equal or exact split; equal distributes remainders to earliest members; exact shares list valid members with nonnegative whole cents summing to the amount. Return 201 and per-group 1-based sequential expense number; invalid input returns 400. Confirm via HTTP and balances, including omitted exact members and invalid amounts and shares. Basis: S4-S7. New data persists with its group. Safe integer limit avoids numeric corruption.

### R-4: Balances and settlements
GET balances gives each member paid minus owed, summing to zero. GET settlements repeatedly pays largest debtor to largest creditor, tie broken by member order, for the smaller amount. Confirm exact outputs and payment application via HTTP. Basis: S8-S9. New data; no preserved behaviour.

### R-5: Missing groups
All routes under an unknown group return 404. Confirm via HTTP for reads, writes and unrecognized subpaths. Basis: S10.

### R-6: Tests
Run node --test for tests under test/ covering the stated behaviour. Confirm command exits successfully. Basis: S12.

## Non-functional requirements
No specific throughput, UI, identity, or deployment target requested. Concurrent update correctness and durable restart are covered by R-1. Availability under filesystem errors must not return false success. Test via local process and isolated files; no remote target.

## Replayable examples
Create group g with members [A, B, C] (R-2); A pays 100 cents equally (R-3). Shares are 34, 33, 33 and balances are {A: 66, B: -33, C: -33} (R-4). Settlements are B to A 33, then C to A 33: debtor tie follows member order. Start with a fresh data file; no earlier expenses. Separately A pays 10 exact with shares {A: 0, B: 10}; balances become {A: 10, B: -10, C: 0}. Each action is permitted by R-2 and R-3. These are planned checks, not observed execution.
