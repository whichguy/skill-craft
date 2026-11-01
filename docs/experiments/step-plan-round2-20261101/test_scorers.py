#!/usr/bin/env python3
"""The round's scorers on plans and summaries of known outcome, run before any scored sample (README.md, "Scorers").

    python3 -I docs/experiments/step-plan-round2-20261101/test_scorers.py
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import proofscore  # noqa: E402

DOCS = ["docs/shiploop/architecture.md", "docs/shiploop/environment.md", "docs/shiploop/spec.md"]


def fixture(name: str) -> dict:
    return json.loads((HERE / "fixtures" / name).read_text())


def judge(doc: dict) -> dict:
    return proofscore.classify(doc["plan"], doc["base_files"], doc["base_texts"])


class LiveProofs(unittest.TestCase):
    def test_a_s1_inline_wrapper_is_form_1_on_s1_only(self) -> None:
        found = judge(fixture("r3-A-s1-plan1.json"))
        self.assertEqual(found["form1"], [{"step": "S1", "path": "test/service.test.js"}])
        self.assertEqual(found["form2"], [])

    def test_a_s9_focused_suite_is_form_2(self) -> None:
        found = judge(fixture("r3-A-s9-plan1.json"))
        self.assertEqual(found, {"form1": [], "form2": [{"step": "S1", "command": "node --test"}]})

    def test_smoke_focused_suite_segment_is_form_2_and_its_replanned_scratch_proof_is_clean(self) -> None:
        self.assertEqual(judge(fixture("r3-smoke-b-s1-plan1.json"))["form2"], [{"step": "S1", "command": "node --test"}])
        self.assertEqual(judge(fixture("r3-smoke-b-s1-plan2.json")), {"form1": [], "form2": []})

    def test_csv_unittest_discovery_is_form_2_and_its_replanned_direct_proof_is_clean(self) -> None:
        self.assertEqual(judge(fixture("sp1-xhigh-csv-report-s1-plan1.json"))["form2"],
                         [{"step": "S1", "command": "python3 -m unittest -v"}])
        self.assertEqual(judge(fixture("sp1-xhigh-csv-report-s1-plan2.json")), {"form1": [], "form2": []})


class Exemptions(unittest.TestCase):
    PLAN = {"paths": ["src/a.js", "test/a.test.js"],
            "test_commands": [{"suite": "focused", "command": "node --test", "ids": ["TC-1"]}]}

    def plan(self, *steps: dict) -> dict:
        return {**self.PLAN, "steps": list(steps)}

    def test_a_later_step_may_run_an_earlier_steps_test(self) -> None:
        plan = self.plan({"id": "S1", "paths": ["src/a.js", "test/a.test.js"], "proof": "node -e \"require('./src/a')\""},
                         {"id": "S2", "paths": ["src/a.js"], "proof": "node --test test/a.test.js"},
                         {"id": "S3", "paths": ["src/a.js"], "proof": "node --test"})
        self.assertEqual(proofscore.classify(plan, DOCS, {}), {"form1": [], "form2": []})

    def test_a_direct_assertion_is_clean(self) -> None:
        plan = self.plan({"id": "S1", "paths": ["src/a.js"],
                          "proof": "node -e \"require('assert').equal(require('./src/a').f(1),2)\""})
        self.assertEqual(proofscore.classify(plan, DOCS, {}), {"form1": [], "form2": []})

    def test_an_all_tests_item_is_exempt(self) -> None:
        plan = {"paths": ["test/a.test.js"], "steps": [{"id": "S1", "paths": ["test/a.test.js"], "proof": "node --test"}],
                "test_commands": [{"suite": "focused", "command": "node --test", "ids": ["TC-1"]}]}
        self.assertEqual(proofscore.classify(plan, DOCS, {}), {"form1": [], "form2": []})

    def test_a_suite_whose_ids_a_base_test_holds_is_clean(self) -> None:
        plan = self.plan({"id": "S1", "paths": ["src/a.js"], "proof": "node --test"})
        texts = {"test/old.test.js": "test('TC-1 keeps working', () => {})"}
        self.assertEqual(proofscore.classify(plan, DOCS + ["test/old.test.js"], texts), {"form1": [], "form2": []})

    def test_ids_named_only_in_the_knowledge_home_do_not_count(self) -> None:
        plan = self.plan({"id": "S1", "paths": ["src/a.js"], "proof": "node --test"})
        texts = {"docs/shiploop/environment.md": "## ID convention\nTC-1 planned"}
        self.assertEqual(proofscore.classify(plan, DOCS, texts)["form2"], [{"step": "S1", "command": "node --test"}])

    def test_an_absolute_scratch_path_inside_inline_code_is_not_a_repository_path(self) -> None:
        self.assertEqual(proofscore.named_paths("python3 -c 'open(\"/tmp/x/test/a.test.js\")'"), [])


if __name__ == "__main__":
    unittest.main()
