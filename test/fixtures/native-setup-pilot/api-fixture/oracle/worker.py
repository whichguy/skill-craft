"""Fresh-process unittest executor. Output is one machine-readable JSON object."""
import contextlib
import importlib.util
import io
import json
import sys
import traceback
import unittest
from pathlib import Path


class StrictResult(unittest.TestResult):
    def __init__(self, test_source):
        super().__init__()
        self.test_source = str(test_source.resolve())
        self.assertion_failures = []
        self.invalid_events = []
        self.skips = []

    @staticmethod
    def _case_method(test):
        case = getattr(test, "test_case", test)
        return case, getattr(case, "_testMethodName", None)

    def _classify_assertion(self, test, err):
        case, method = self._case_method(test)
        frames = traceback.extract_tb(err[2])
        # unittest assertions raise inside its own helper stack. Preserve the
        # nearest non-framework origin so product crashes cannot become kills.
        framework_root = Path(unittest.__file__).resolve().parent
        relevant = [frame for frame in frames
                    if not Path(frame.filename).resolve().is_relative_to(framework_root)]
        if (isinstance(case, unittest.TestCase) and method
                and issubclass(err[0], AssertionError) and relevant
                and Path(relevant[-1].filename).resolve().as_posix() == self.test_source
                and any(frame.name == method and Path(frame.filename).resolve().as_posix() == self.test_source
                        for frame in relevant)):
            self.assertion_failures.append({"test": test.id(), "message": str(err[1])})
        else:
            self.invalid_events.append({"test": str(test), "reason": "failure_outside_test_method",
                                        "message": str(err[1])})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._classify_assertion(test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            return
        if issubclass(err[0], AssertionError):
            self._classify_assertion(subtest, err)
        else:
            self.invalid_events.append({"test": subtest.id(), "reason": "subtest_error",
                                        "message": f"{err[0].__name__}: {err[1]}"})

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self.invalid_events.append({"test": test.id(), "reason": "expected_failure_not_acceptance"})

    def addError(self, test, err):
        super().addError(test, err)
        self.invalid_events.append({
            "test": str(test),
            "reason": "test_error",
            "message": f"{err[0].__name__}: {err[1]}",
        })

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.skips.append({"test": str(test), "reason": reason})

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self.invalid_events.append({
            "test": str(test),
            "reason": "unexpected_success",
        })


def emit(value):
    print(json.dumps(value, sort_keys=True))


def main():
    app_dir, test_path = map(Path, sys.argv[1:3])
    app_dir, test_path = app_dir.resolve(), test_path.resolve()
    sys.path.insert(0, str(test_path.parent))
    sys.path.insert(0, str(app_dir))
    try:
        spec = importlib.util.spec_from_file_location("generated_fixture_tests", test_path)
        if spec is None or spec.loader is None:
            raise ImportError("cannot load test source")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except BaseException as exc:
        emit({"status": "invalid", "phase": "import", "reason": f"{type(exc).__name__}: {exc}"})
        return 0

    for name in ("setup_app", "change_app"):
        loaded = sys.modules.get(name)
        if loaded is not None:
            origin = Path(getattr(loaded, "__file__", "")).resolve()
            if app_dir not in origin.parents:
                emit({"status": "invalid", "phase": "isolation", "reason": f"{name} loaded outside candidate"})
                return 0
    try:
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        count = suite.countTestCases()
    except BaseException as exc:
        emit({"status": "invalid", "phase": "discovery", "reason": f"{type(exc).__name__}: {exc}"})
        return 0
    if count == 0:
        emit({"status": "invalid", "phase": "discovery", "reason": "empty_suite", "tests": 0})
        return 0

    result = StrictResult(test_path)
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            suite.run(result)
    except BaseException as exc:
        emit({"status": "invalid", "phase": "execution", "reason": f"{type(exc).__name__}: {exc}"})
        return 0
    if result.invalid_events or result.skips or result.testsRun == 0:
        emit({
            "status": "invalid",
            "phase": "execution",
            "tests": result.testsRun,
            "reason": result.invalid_events or result.skips or "no_tests_run",
        })
    elif result.assertion_failures:
        emit({
            "status": "assertion_failures",
            "phase": "test_methods",
            "tests": result.testsRun,
            "failures": result.assertion_failures,
        })
    elif result.failures or result.errors or not result.wasSuccessful():
        emit({"status": "invalid", "phase": "execution", "tests": result.testsRun,
              "reason": "unclassified_unittest_failure"})
    else:
        emit({"status": "pass", "tests": result.testsRun})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
