"""Same-text requests and explicit recovery must not be conflated."""
from copy import deepcopy
import unittest

from recovery_isolation import assess_isolation


class RecoveryIsolationTests(unittest.TestCase):
    def setUp(self):
        self.prompt = "/shiploop Add player highlights"
        self.initial = {"states": [{"source_path": "/prior/run/state.md", "state": {
            "run_id": "old", "prompt": self.prompt.removeprefix("/shiploop "), "stage": "discovery", "revision": 1}}]}

    def test_identical_prompt_next_on_old_run_is_a_new_request_violation(self):
        events = {"cli_calls": [{"call_id": "n", "argv_tail": ["next", "--run-dir=/prior/run"], "completed": True, "exit_codes": [0]}]}
        result = assess_isolation(self.initial, self.initial, events, prompt=self.prompt)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["prior_runs_recovered"][0]["run_id"], "old")

    def test_protocol_three_improve_complete_on_old_run_is_a_new_request_violation(self):
        self.initial["states"][0]["state"]["navigator_protocol_version"] = 3
        events = {"cli_calls": [{
            "call_id": "complete", "argv_tail": [
                "improve-complete", "--run-dir=/prior/run", "--action=old-action", "--result=/tmp/result.md",
            ], "completed": True, "exit_codes": [0],
        }]}
        final = deepcopy(self.initial)
        final["states"].append({"source_path": "/fresh/run/state.md", "state": {"run_id": "new", "prompt": self.prompt}})
        result = assess_isolation(self.initial, final, events, prompt=self.prompt)
        self.assertEqual(result["status"], "fail")
        self.assertEqual(result["prior_run_callbacks"], [{"run_id": "old", "call_id": "complete", "action": "old-action"}])

    def test_preserved_old_state_and_fresh_matching_identity_pass_this_scope_only(self):
        final = deepcopy(self.initial)
        final["states"].append({"source_path": "/fresh/run/state.md", "state": {"run_id": "new", "prompt": self.prompt}})
        self.assertEqual(assess_isolation(self.initial, final, {}, prompt=self.prompt)["status"], "pass")
        final["states"][0]["state"]["revision"] = 2
        self.assertEqual(assess_isolation(self.initial, final, {}, prompt=self.prompt)["status"], "unverified")

    def test_missing_exit_is_unknown_and_explicit_recovery_is_distinct(self):
        events = {"cli_calls": [{"call_id": "n", "argv_tail": ["next", "--run-dir", "/prior/run"], "completed": True, "exit_codes": []}]}
        self.assertEqual(assess_isolation(self.initial, self.initial, events, prompt=self.prompt)["status"], "unverified")
        self.assertEqual(assess_isolation(self.initial, self.initial, events, prompt=self.prompt, mode="explicit-recovery")["status"], "not-applicable")


if __name__ == "__main__":
    unittest.main()
