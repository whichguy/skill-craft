#!/usr/bin/env python3
"""Check local-skill guidance survives real v3 state save/reload and rendering.

Navigation setup is synthetic; this does not execute Improve or an LLM.
"""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as nav
import shiploop_store as store


class LocalSkillRoutes(unittest.TestCase):
    def test_cold_skill_stages_point_to_local_contract_and_repo_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo, run = root / "repo", root / "run"
            repo.mkdir()
            run.mkdir()
            state = nav.new_state(str(repo), "Review current evidence.", protocol_version=3)
            checked = []
            while nav.current_stage(state) != "static-checks":
                stage = nav.current_stage(state)
                action = nav.current_action(state)
                if stage in {"skill-assess", "skill-validate"}:
                    nav.save(run, state)
                    before = (run / "state.md").read_bytes()
                    recovered = store.read_record(run / "state.md")
                    packet = nav.render(None, run, recovered)
                    self.assertIn(str(repo / "SHIPLOOP.md"), packet)
                    self.assertIn(str(ROOT / "skills/shiploop/references/testing-and-documentation.md")
                                  + "#reusable-product-skills", packet)
                    self.assertEqual((run / "state.md").read_bytes(), before)
                    self.assertEqual(nav.current_action(recovered)["id"], action["id"])
                    checked.append(stage)
                result = {"outcome": "done", "summary": "Synthetic navigation setup only."}
                if stage == "plan":
                    result["work_items"] = [{"id": "W1", "title": "Review evidence"}]
                state = nav.apply(state, action["id"], result)
                if state["active_improve"] is not None:
                    # Only planning checkpoints and the last carry-forward park a child.
                    state = nav.finish_improve(state, action["id"], {
                        "summary": "Synthetic navigation setup, no Improve executed.",
                        "lessons": "No live work claimed.",
                    })
            self.assertEqual(checked, ["skill-assess", "skill-validate"])


if __name__ == "__main__":
    unittest.main()
