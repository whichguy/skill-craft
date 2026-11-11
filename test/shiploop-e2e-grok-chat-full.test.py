#!/usr/bin/env python3
"""Full-case wiring must retain its ownership boundary and independent checks."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
CASES=json.loads((ROOT/"test/shiploop_e2e/cases.json").read_text())


class FullGrokCaseTest(unittest.TestCase):
    def test_original_exploratory_case_is_unchanged(self):
        old=CASES["grok-chat-salesforce"]
        self.assertEqual(hashlib.sha256(old["prompt"].encode()).hexdigest(),
                         "527d5b1ab456b7ad60a40f73666f02e230f3a23d5e2209916d0630bef0689712")
        self.assertEqual(len(old["checks"]),4)
        self.assertIn(" acceptance ",old["checks"][-1])

    def test_full_case_preserves_shared_org_guard_snapshot_and_cleanup(self):
        old=CASES["grok-chat-salesforce"]["platform"]
        new=CASES["grok-chat-salesforce-full"]["platform"]
        for key in ("kind","org","prefix","preflight","before","cleanup"):
            self.assertEqual(old[key],new[key],key)
        for key,value in old["model_bin"].items():
            expected = "env E2E_BIND_DEPLOY_SOURCE=1 " + value if key == "sf" else value
            self.assertEqual(new["model_bin"][key],expected,key)
        self.assertEqual(old["check_timeout"],900)
        self.assertEqual(new["check_timeout"],2700)
        self.assertNotIn("existing",new)

    def test_full_case_requires_separate_native_ui_and_quality_evidence(self):
        checks=CASES["grok-chat-salesforce-full"]["checks"]
        self.assertEqual(len(checks),6)
        self.assertTrue(any("grok_chat_full_salesforce.py" in c and c.endswith(" rules") for c in checks))
        self.assertTrue(any("grok_chat_full_ui.py" in c and c.endswith(" --mode run") for c in checks))
        self.assertTrue(any("grok_chat_full_quality.py" in c for c in checks))
        self.assertFalse(any("grok_chat_salesforce.py" in c and " acceptance " in c for c in checks))

    def test_builder_tools_are_fixed_wrappers_and_browser_is_required(self):
        case=CASES["grok-chat-salesforce-full"]
        self.assertEqual(case["needs"],["browser"])
        self.assertTrue(case["needs_source"])
        for name in ("grok-chat-ui","grok-chat-oracle","grok-chat-quality"):
            command=case["platform"]["model_bin"][name]
            self.assertTrue(command.startswith("env E2E_CHECK_PHASE=builder python3 "))
            self.assertIn('"$E2E_CHECKS/',command)

    def test_oracle_attempt_ledger_preserves_start_order_and_unfinished_attempts(self):
        spec=importlib.util.spec_from_file_location("grok_full_oracle_ledger",ROOT/"test/shiploop_e2e/checks/grok_chat_full_salesforce.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            first=module.register_oracle_attempt(root,"builder","1"*32)
            second=module.register_oracle_attempt(root,"builder","2"*32)
            self.assertEqual((root/"grok-chat-full-oracle/builder/attempts.log").read_text(),"1"*32+"\n"+"2"*32+"\n")
            self.assertTrue(first.is_dir() and second.is_dir())
            self.assertFalse((second/"receipt.json").exists(),"an unfinished newer attempt remains visible")
            with self.assertRaises(FileExistsError):
                module.register_oracle_attempt(root,"builder","2"*32)

    def test_oracle_prevalidation_failure_is_registered_before_fallible_work(self):
        spec=importlib.util.spec_from_file_location("grok_full_oracle_order",ROOT/"test/shiploop_e2e/checks/grok_chat_full_salesforce.py")
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(module.os.environ,{"E2E_CHECK_PHASE":"builder"}), \
                mock.patch.object(module,"do_project",return_value=(False,"injected prevalidation failure")), \
                mock.patch.object(module.uuid,"uuid4",return_value=mock.Mock(hex="b"*32)):
            root=Path(temporary)
            first=module.register_oracle_attempt(root,"builder","a"*32)
            (first/"receipt.json").write_text("{}\n")
            ok,_=module.do_rules(root,root)
            self.assertFalse(ok)
            ledger=root/"grok-chat-full-oracle/builder/attempts.log"
            self.assertEqual(ledger.read_text(),"a"*32+"\n"+"b"*32+"\n")
            latest=root/"grok-chat-full-oracle/builder"/("b"*32)
            self.assertTrue(latest.is_dir())
            self.assertFalse((latest/"receipt.json").exists())

    def test_full_prompt_preserves_secret_and_confirmation_boundaries(self):
        prompt=CASES["grok-chat-salesforce-full"]["prompt"]
        for clause in ("business record creation and changes always require the user's confirmation",
                       "Never change existing or foreign metadata or records",
                       "The browser must not hold a provider key",
                       "Do not create or modify credentials in this run",
                       "System.runAs", "SLGrokChatOracleTest", "Never edit the evaluator"):
            self.assertIn(clause,prompt)
        self.assertNotIn("The case cannot yet produce a qualified full-E2E PASS",prompt)
        self.assertNotIn("Its final acceptance check deliberately returns UNKNOWN",prompt)


if __name__=="__main__":
    unittest.main(verbosity=2)
