#!/usr/bin/env python3
"""The write-grant probe is one module, vendored byte-identically into two packages."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest


sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
COPIES = (
    ROOT / "skills/ask-agent/scripts/host_write_grants.py",
    ROOT / "skills/shiploop/scripts/host_write_grants.py",
)


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(f"host_write_grants_{path.parts[-3]}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HostWriteGrantsTests(unittest.TestCase):
    def test_copies_are_byte_identical(self) -> None:
        ask_agent, shiploop = (path.read_bytes() for path in COPIES)
        self.assertEqual(ask_agent, shiploop,
                         "host_write_grants.py differs between ask-agent and shiploop; edit both together")

    def test_shiploop_freezes_the_module_with_the_ask_agent_package(self) -> None:
        # A managed chain hashes an explicit Ask-Agent file list; a module the
        # helper loads but the chain does not freeze could drift mid-run.
        chain = (ROOT / "skills/shiploop/scripts/shiploop_chain.py").read_text(encoding="utf-8")
        self.assertIn('"scripts/host_write_grants.py"', chain)

    def test_only_refused_targets_become_grants(self) -> None:
        grants = _load(COPIES[0])
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            open_dir, closed_dir = base / "open", base / "closed"
            open_dir.mkdir()
            closed_dir.mkdir()
            closed_dir.chmod(0o555)
            try:
                with self.assertRaises(grants.GrantError) as caught:
                    grants.require([(open_dir / "new", "open", open_dir),
                                    (closed_dir / "new", "closed", base / "stable")])
            finally:
                closed_dir.chmod(0o755)
            self.assertEqual([purpose for _, purpose, _ in caught.exception.blocked], ["closed"])
            self.assertEqual(caught.exception.grants, [(base / "stable").resolve()])
            self.assertEqual(sorted(os.listdir(open_dir)), [], "the probe removes its file")
            product = grants.Product("TOOL-GRANT-NEEDED", "Tool did not start.", "tool", "moving things")
            message = grants.report(caught.exception, "rerun it", product, {"GROK_AGENT": "1"})
            self.assertTrue(message.startswith("TOOL-GRANT-NEEDED: Tool did not start."), message)
            self.assertIn("[profiles.tool]", message)
            self.assertIn("mkdir -p " + str((base / "stable").resolve()), message)
            self.assertIn("around it by moving things, or changing sandbox settings yourself.", message)


if __name__ == "__main__":
    unittest.main()
