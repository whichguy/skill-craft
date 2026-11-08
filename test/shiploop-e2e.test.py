#!/usr/bin/env python3
"""No-model checks for the ShipLoop E2E harness (test/shiploop_e2e/).

Fake `grok` and `claude` executables stand in for the hosts, so these checks
cover the harness contract (empty start directory, isolated Grok profile,
argv, plugin and invocation grading, review parsing and the premise filter)
without launching a model. Every case passes its host and fake binary
explicitly and supplies a plugin build, so no real host or build is reached.
They say nothing about live ShipLoop behavior.
"""

import importlib as _aggregate_importlib
import pathlib as _aggregate_pathlib
import sys as _aggregate_sys

_aggregate_test_dir = str(_aggregate_pathlib.Path(__file__).resolve().parent)
if _aggregate_test_dir not in _aggregate_sys.path:
    _aggregate_sys.path.insert(0, _aggregate_test_dir)
_aggregate_support = _aggregate_importlib.import_module("shiploop-e2e-support")
globals().update({name: value for name, value in vars(_aggregate_support).items()
                  if not name.startswith("__") and name not in {"_tests_from_namespace", "_tests_from_modules"}})

_COMPONENT_MODULES = tuple(
    _aggregate_support._load_component_module(name)
    for name in ("analysis", "hosts", "resources")
)
for _component in _COMPONENT_MODULES:
    for _name, _value in vars(_component).items():
        if isinstance(_value, type) and _value.__module__ == _component.__name__:
            globals()[_name] = _value


def load_tests(loader, standard_tests, pattern):
    return _aggregate_support._tests_from_modules(loader, _COMPONENT_MODULES, pattern)


if __name__ == "__main__":
    unittest.main()
