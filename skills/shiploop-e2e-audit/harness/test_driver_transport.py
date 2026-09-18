#!/usr/bin/env python3
"""Focused bounded-process checks for the composite UI-driver transport."""
from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import textwrap
import time
import unittest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import driver_transport as transport  # noqa: E402


DRIVER_SOURCE = r'''
import json
import hashlib
import os
import sys
import time

mode = sys.argv[1]
request = json.load(sys.stdin)
request_sha256 = hashlib.sha256(json.dumps(
    request, sort_keys=True, ensure_ascii=False, separators=(",", ":")
).encode("utf-8")).hexdigest()
repo = str(__import__("pathlib").Path(request["repo"]).resolve())

def emit(observations, **overrides):
    response = {"schema": "shiploop-e2e-driver-response/1", "request_sha256": request_sha256,
                "repo": repo, "observations": observations}
    response.update(overrides)
    print(json.dumps(response))

if mode == "timeout":
    time.sleep(5)
elif mode == "huge":
    print("x" * 200000)
elif mode == "bad-schema":
    emit([], schema="wrong")
elif mode == "missing-schema":
    print(json.dumps({"request_sha256": request_sha256, "repo": repo, "observations": []}))
elif mode == "not-list":
    emit({})
elif mode == "wrong-request":
    emit([], request_sha256="0" * 64)
elif mode == "wrong-repo":
    emit([], repo="/wrong-repo")
elif mode == "environment":
    emit([{"environment": sorted(os.environ)}])
else:
    emit([{"ok": True}])
'''


class DriverTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.driver = self.root / "driver.py"
        self.driver.write_text(textwrap.dedent(DRIVER_SOURCE), encoding="utf-8")
        self.request = {
            "schema": transport.REQUEST_SCHEMA,
            "step_id": "fixture-step",
            "family": "fixture-family",
            "repo": str(self.root.resolve()),
            "actions": [{"type": "probe"}],
        }

    def invoke(self, mode: str, **kwargs: object) -> dict:
        return transport.invoke(
            [sys.executable, str(self.driver), mode], self.request, cwd=self.root,
            timeout_seconds=float(kwargs.get("timeout", 1)),
            max_output_bytes=int(kwargs.get("maximum", 4096)),
            configuration={"fixture": mode},
        )

    def test_success_retains_protocol_and_configuration_digests(self) -> None:
        result = self.invoke("good")

        self.assertEqual(result["observations"], [{"ok": True}])
        self.assertEqual(result["request_sha256"], transport.sha256_bytes(transport.canonical_json_bytes(self.request)))
        self.assertEqual(result["adapter_configuration_sha256"], transport.digest_json({"fixture": "good"}))
        self.assertEqual(len(result["response_sha256"]), 64)
        self.assertEqual(result["exit_code"], 0)

    def test_timeout_is_bounded_and_recordable(self) -> None:
        started = time.monotonic()
        with self.assertRaisesRegex(transport.DriverTransportError, "driver-timeout") as raised:
            self.invoke("timeout", timeout=0.05)
        self.assertEqual(raised.exception.code, "driver-timeout")
        self.assertLess(time.monotonic() - started, 2)

    def test_oversized_output_is_rejected_before_loading_into_memory(self) -> None:
        with self.assertRaisesRegex(transport.DriverTransportError, "driver-output-exceeded-bound"):
            self.invoke("huge", maximum=1024)

    def test_bad_response_shapes_are_protocol_failures(self) -> None:
        for mode, expected in (("bad-schema", "driver-response-schema-mismatch"),
                               ("missing-schema", "driver-response-schema-mismatch"),
                               ("not-list", "driver-observations-not-list")):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(transport.DriverTransportError, expected):
                    self.invoke(mode)

    def test_response_must_bind_the_exact_request_and_repository(self) -> None:
        for mode, expected in (("wrong-request", "driver-request-binding-mismatch"),
                               ("wrong-repo", "driver-repo-binding-mismatch")):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(transport.DriverTransportError, expected):
                    self.invoke(mode)

    def test_child_does_not_inherit_arbitrary_host_environment(self) -> None:
        previous = os.environ.get("SHIPLOOP_E2E_TEST_SECRET")
        os.environ["SHIPLOOP_E2E_TEST_SECRET"] = "must-not-reach-adapter"
        self.addCleanup(
            lambda: os.environ.__setitem__("SHIPLOOP_E2E_TEST_SECRET", previous)
            if previous is not None else os.environ.pop("SHIPLOOP_E2E_TEST_SECRET", None)
        )

        result = self.invoke("environment")

        environment = result["observations"][0]["environment"]
        self.assertNotIn("SHIPLOOP_E2E_TEST_SECRET", environment)
        self.assertEqual(result["child_environment_keys"], sorted(
            key for key in transport.CHILD_ENVIRONMENT_KEYS if key in os.environ
        ))

    def test_shell_strings_and_unbounded_argv_are_not_accepted(self) -> None:
        with self.assertRaises(ValueError):
            transport.parse_argv("python adapter.py")
        with self.assertRaises(ValueError):
            transport.parse_argv(["x"] * (transport.MAX_ARGV_ITEMS + 1))


if __name__ == "__main__":
    unittest.main()
