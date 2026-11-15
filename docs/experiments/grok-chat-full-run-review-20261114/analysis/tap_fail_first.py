"""Run the TAP reader's new tests against the reader of a base commit, to show they fail first.

    python3 -I tap_fail_first.py --repo REPO --base BASE_COMMIT

Loads the BASE commit's ``shiploop_test_counts`` (``git show``) as the module every import resolves to, then runs the
new test classes of REPO (``TapStreamTests`` and ``TapJudgeTests`` in ``test/shiploop-test-counts.test.py``,
``TapCountRouteTests`` in ``test/shiploop-test-loop.test.py``).  Prints, per class, how many tests ran and which pass on
the base reader too: those are the controls that pin behaviour the change must keep.
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLASSES = (("test/shiploop-test-counts.test.py", ("TapStreamTests", "TapJudgeTests")),
           ("test/shiploop-test-loop.test.py", ("TapCountRouteTests",)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    repo = Path(args.repo)
    source = subprocess.run(["git", "-C", str(repo), "show", args.base + ":skills/shiploop/scripts/shiploop_test_counts.py"],
                            check=True, capture_output=True, text=True).stdout
    temp = Path(tempfile.mkdtemp(prefix="tap-fail-first-"))
    (temp / "shiploop_test_counts.py").write_text(source)
    spec = importlib.util.spec_from_file_location("shiploop_test_counts", temp / "shiploop_test_counts.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    sys.modules["shiploop_test_counts"] = module  # every later import of the reader gets the base one
    sys.path.insert(0, str(repo / "skills/shiploop/scripts"))
    print("new tests run against the reader of", args.base)
    for relative, names in CLASSES:
        path = repo / relative
        spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_").replace(".", "_"), path)
        tests = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tests)
        for name in names:
            suite = unittest.defaultTestLoader.loadTestsFromTestCase(getattr(tests, name))
            every = sorted(test.id().split(".")[-1] for test in suite)
            result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
            failing = {test.id().split(".")[-1] for test, _trace in result.failures + result.errors}
            print(f"{name}: {result.testsRun} ran, {len(failing)} fail or error on the base reader;"
                  f" pass on both: {[test for test in every if test not in failing] or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
