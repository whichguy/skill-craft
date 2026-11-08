# Environment

Python standard library only. The seed records discovery and earlier stages synthetically; no provider, browser, credential or org has been tested. The test fixture's state is local to each process.

## Harnesses and suites

Existing test_existing.py uses unittest. The new acceptance suite is test_acceptance.py and runs through the same runner. No installation or external setup is required. Both APIs have a unit testing layer; no e2e or UI layer is claimed.

## Commands

Focused acceptance command, planned until tests are authored:

```sh
python3 -m unittest -v test_acceptance
```

Regression command, existing and newly authored files:

```sh
python3 -m unittest discover -s . -p 'test_*.py' -v
```

Implementation/preparation proof, available before the test stage writes new tests:

```sh
python3 -m unittest -v test_existing
```

## ID convention

The five planned focused IDs are Python unittest method names test_TC_1 through test_TC_5. Use each exactly as a method name so it appears as its own word in verbose unittest output. Additional boundary observations can be subTests under the applicable case; IDs must match the accepted test-spec.

Example of runner naming format, not a claimed execution:
test_TC_1 (test_acceptance.Acceptance.test_TC_1) ... ok

## Base evidence

This is test-only work against already correct production APIs. The test stage must distinguish coverage added now from product behavior that already works, and justify any red_na using the actual unchanged baseline. Do not fabricate a failing product baseline.
