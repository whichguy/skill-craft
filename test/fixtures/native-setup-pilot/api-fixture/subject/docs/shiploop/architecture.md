# Architecture

## AD-1: Local public-contract tests

Use stdlib unittest against public setup_app and change_app APIs. fixture_seed prepares known initial state. Test-only implementation work may be a no-op when no harness support is needed; the native test stage writes tests. Production APIs and contract are frozen for this experiment. No particular internal representation is part of the contract.

## Real-boundary checks

The required boundary is this Python API and its in-process state. There is no durable disk persistence, UI, browser, Salesforce org or external provider in this fixture; passing it establishes none of those. Assertions observe the documented public operations.
