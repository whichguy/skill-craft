#!/usr/bin/env python3
"""Cold callers can page every script-selected platform requirement exactly."""

import hashlib
import importlib.util
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "revalidation_context_fixture", ROOT / "test/shiploop-revalidation.test.py"
)
fixture = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fixture
spec.loader.exec_module(fixture)


class RevalidationContextTests(unittest.TestCase):
    def test_unicode_paging_preserves_all_requirements_and_action_binding(self):
        case = fixture.RevalidationCliTests("runTest")
        case.setUp()
        self.addCleanup(case.tearDown)
        state, _body = case.prepare_action()
        machine = fixture.outer_machine()
        machine["platform_discovery"]["platforms"][0]["identity"]["expected_role"] = "開発担当🙂" * 90
        body = fixture.environment_body(machine)
        (case.run_dir / "environment.md").write_text(body)
        state["environment_sha256"] = hashlib.sha256(body.encode()).hexdigest()
        fixture.store.write_record(case.run_dir / "state.md", state)
        before = (case.run_dir / "state.md").read_bytes()
        offset = 0
        digest = None
        fragments = []
        for _ in range(200):
            args = ["context", "--section", "platform-revalidation", "--offset", str(offset), "--limit", "97"]
            if digest:
                args += ["--digest", digest]
            response = case.cli(*args).stdout
            header, fragment = response.split("\n", 1)
            match = re.search(r"digest ([0-9a-f]{64}); characters (\d+):(\d+)/(\d+)", header)
            self.assertIsNotNone(match)
            digest, begin, end, total = match.groups()
            fragments.append(fragment[:int(end) - int(begin)])
            offset = int(end)
            if offset == int(total):
                break
        else:
            self.fail("requirements pages never completed")
        record = fixture.store.loads("".join(fragments))
        self.assertEqual(record["action_id"], state["action"]["id"])
        self.assertEqual(record["requirements"][0]["observed_role"], "開発担当🙂" * 90)
        self.assertEqual(record["requirements"][0]["environment_sha256"], state["environment_sha256"])
        self.assertEqual((case.run_dir / "state.md").read_bytes(), before)
        stale = case.cli("context", "--section", "platform-revalidation", "--digest", "0" * 64, code=2)
        self.assertIn("context changed between pages", stale.stderr)


if __name__ == "__main__":
    unittest.main()
