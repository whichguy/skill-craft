# Environment

## Runtime and access

Local Python 3 standard library; no network, account, dependency download or deployment is needed or authorized. The supplied source and fixtures are the inspected application.

## Harnesses and suites

Python unittest is available and the unchanged baseline passed before this seed was frozen. It covers only the existing behavior, not the requested feature.

## Commands

Existing suite, all tests under tests/:
```sh
python3 -B -m unittest discover -s tests -v
```

## ID convention

The strategy must choose legal unittest method names and preserve traceability in titles or output.
