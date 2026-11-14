"""Hermetic failure control for the V7 collector's own cleanup boundary."""

import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from v7 import registration, report_context


class CollectorV7Test(unittest.TestCase):
    def test_setup_failure_removes_owned_auth_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            out = root / "collector"
            approval = root / "synthetic-authorization"
            approval.write_bytes(b"synthetic test authorization")
            target = root / "synthetic-target"
            content = b"inert fixture"
            target.write_bytes(content)
            target.chmod(0o640)
            before = target.stat()
            link = out / "home" / ".codex" / "auth.json"
            error = OSError("synthetic host setup failed after linking auth")

            def fail_after_linking(home):
                codex = home / ".codex"
                codex.mkdir(parents=True)
                (codex / "auth.json").symlink_to(target)
                raise error

            record = {
                "purpose": "smoke", "harness_root": str(root / "harness"),
                "harness_head": "synthetic", "authorization": {"path": "separate"},
                "codex_bin": "unused", "roles": {"subject": registration.ROLES["subject"]},
            }
            Path(record["harness_root"]).mkdir()
            launch = Mock(side_effect=AssertionError("unexpected model launch"))
            cleanup = Mock(return_value={"observed": True, "survived": [],
                                         "unverified": [], "protected": []})
            run = SimpleNamespace(install_termination_handlers=lambda: None,
                                  launch=launch, lifecycle=SimpleNamespace(cleanup=cleanup))
            host = SimpleNamespace(env=fail_after_linking)
            harness = SimpleNamespace(run=run, hosts=SimpleNamespace(host=lambda *_: host))
            # These adapters only exist in the assembled harness. The collector,
            # V7 cleanup and output writers come from the files under test.
            dispatch = SimpleNamespace(
                frozen_inputs=lambda *_: (record, None, "a" * 64),
                sha=lambda path: report_context.sha(path.read_bytes()),
                verify_runtime=Mock(side_effect=AssertionError("unexpected runtime check")),
            )
            runner = SimpleNamespace(
                load_harness=lambda *_: harness, _capture_invocation=None,
                _raw_translator=None, wall_time=None,
            )
            path = Path(__file__).resolve().parent / "v7" / "collector_smoke.py"
            spec = importlib.util.spec_from_file_location("_collector_v7_control", path)
            collector = importlib.util.module_from_spec(spec)
            # Keep real V7 imports cached normally when the adapter patch unwinds.
            importlib.import_module("v7.auth_cleanup")
            importlib.import_module("v7.telemetry")
            with patch.dict(sys.modules, {"dispatch": dispatch, "runner": runner}), \
                    patch.object(sys, "path", sys.path.copy()), \
                    patch.object(sys, "dont_write_bytecode", True):
                spec.loader.exec_module(collector)

            args = SimpleNamespace(authorize_live=True, authorization=approval, output=out, timeout=1)
            previous_umask = os.umask(0o077)
            try:
                with patch.object(registration, "read", return_value=record), \
                        patch.dict(os.environ, {}, clear=True), self.assertRaises(OSError) as caught:
                    collector.collect(args)
            finally:
                os.umask(previous_umask)

            self.assertIs(caught.exception, error)
            launch.assert_not_called()
            self.assertFalse(os.path.lexists(link), "synthetic auth link survived collector setup failure")
            cleanup.assert_called_once_with(out)
            receipt = json.loads((out / "cleanup.json").read_bytes())
            self.assertIs(receipt["observed"], True)
            self.assertEqual(receipt["auth_link"], {"status": "removed"})
            after = target.stat()
            self.assertEqual(after, before)
            self.assertEqual((after.st_atime_ns, after.st_mtime_ns, after.st_ctime_ns),
                             (before.st_atime_ns, before.st_mtime_ns, before.st_ctime_ns))
            self.assertEqual(target.read_bytes(), content)
