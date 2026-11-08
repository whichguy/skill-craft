# Product specification

## Requirements

R-1: Extend this local Python inventory tool with a JSON batch-import command. Import must be all-or-nothing: any invalid record, adapter error or interrupted import leaves the previously visible inventory unchanged; successful publication exposes the complete new batch and preserves unrelated existing SKUs. Repeating a successful import is idempotent. Keep the installed adapter for applying rows unless evidence shows an alternative is needed. The adapter's batch behavior has not been characterized. No concurrent writers are in scope; readers can reopen the database between commands. Use only Python's standard library. Temporary local experiments on disposable databases are authorized. Do not mutate the retained seed inventory. Add automated CLI, invalid-middle-record, interrupted-publication and recovery checks as implementation work. Existing tests must remain passing.

## Non-functional requirements

R-2: Keep data loss and false success visible; preserve the existing baseline and require repeatable behavioral tests for the new command. Use only the stated local standard-library runtime.

## Retired

None.
