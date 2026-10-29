#!/usr/bin/env python3
"""scripts/release.py refuses a ShipLoop release that has no E2E round on record.

Each case runs the real script as a subprocess inside a disposable git
repository (its own HOME and git config, no network). A refusal and its fix go
through the same entry point: the fix is built from the names the refusal
prints, then the release command is run again and must accept it.
"""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/release.py"
LEARNINGS = "test/shiploop_e2e/LEARNINGS.md"
CARD = "---\nname: {leaf}\nversion: 1.0.0\n---\nA fixture skill.\n"


class ReleasePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="release-preflight-")
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / "repo"
        home = root / "home"
        home.mkdir()
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env.update(HOME=str(home), XDG_CONFIG_HOME=str(home / "config"),
                        GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null",
                        GIT_AUTHOR_NAME="test", GIT_AUTHOR_EMAIL="test@example.invalid",
                        GIT_COMMITTER_NAME="test", GIT_COMMITTER_EMAIL="test@example.invalid")
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        (self.repo / "scripts").mkdir()
        shutil.copy(SCRIPT, self.repo / "scripts/release.py")
        for leaf in ("shiploop", "other"):
            self.write(f"skills/{leaf}/SKILL.md", CARD.format(leaf=leaf))
        self.write("catalog/skill-craft-plugin.json", json.dumps({"version": "1.0.0"}) + "\n")
        self.write("plugins/skill-craft/.gitkeep", "")
        self.commit("base")

    # -- helpers

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.repo), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def write(self, path, text):
        target = self.repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, subject, trailer=None):
        """Commit every written file, with an optional trailer in the final paragraph."""
        self.git("add", "-A")
        messages = ["-m", subject] + (["-m", trailer + "\nCo-Authored-By: Test <test@example.invalid>"] if trailer else [])
        self.git("commit", "-q", "--allow-empty", *messages)

    def release_commit(self):
        self.git("commit", "-q", "--allow-empty", "-m", "release: baseline", "-m",
                 "Skill-Craft-Release: skill-craft@1.0.0, shiploop@1.0.0, other@1.0.0")

    def note(self, leaf, subject="feat: change", trailer=None):
        self.write(f"changes/{leaf}/n.md", "---\nbump: patch\n---\nA fixture change.\n")
        self.commit(subject, trailer)

    def release(self, *flags):
        return subprocess.run([sys.executable, "-B", "scripts/release.py", *flags], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, timeout=60)

    def assertAccepted(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release: shiploop 1.0.0 -> 1.0.1", result.stdout)

    def assertRefused(self, result):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertIn("test/shiploop_e2e/LEARNINGS.md", result.stderr)
        self.assertIn("No-E2E-Round", result.stderr)
        return result.stderr

    def untouched(self):
        self.assertEqual(self.git("status", "--porcelain=v1", "--untracked-files=all"), "")
        self.assertTrue((self.repo / "changes/shiploop/n.md").is_file(), "the pending note must stay")

    # -- the rule

    def test_refused_with_no_learnings_commit_and_no_trailer(self):
        self.release_commit()
        self.note("shiploop")
        self.assertRefused(self.release("--dry-run"))

    def test_accepted_with_a_learnings_commit_after_the_change(self):
        self.release_commit()
        self.note("shiploop")
        self.write(LEARNINGS, "# Learnings\n\n## Run 1\n")
        self.commit("test(shiploop-e2e): run 1 and its learnings")
        self.assertAccepted(self.release("--dry-run"))

    def test_a_round_recorded_before_a_change_does_not_vouch_for_it(self):
        # 1.18.0 shipped three ShipLoop changes committed after the range's last LEARNINGS entry; the rule names them.
        self.release_commit()
        self.write(LEARNINGS, "# Learnings\n\n## Run 1\n")
        self.commit("test(shiploop-e2e): run 1 and its learnings")
        self.write("skills/shiploop/scripts/hook.py", "print('changed after the round')\n")
        self.commit("feat(shiploop): a change after the round")
        self.note("shiploop", subject="docs(shiploop): its note")
        message = self.assertRefused(self.release("--dry-run"))
        self.assertIn("2 change(s) committed after its latest E2E round", message)
        self.assertIn("feat(shiploop): a change after the round", message)
        self.assertIn("docs(shiploop): its note", message)
        self.git("commit", "-q", "--allow-empty", "-m", "chore: unrelated", "-m",
                 "No-E2E-Round: one trailer does not cover other commits\nCo-Authored-By: Test <test@example.invalid>")
        self.assertRefused(self.release("--dry-run"))
        self.write(LEARNINGS, "# Learnings\n\n## Run 1\n\n## Run 2\n")
        self.commit("test(shiploop-e2e): run 2 covers both")
        self.assertAccepted(self.release("--dry-run"))

    def test_accepted_with_a_trailer_that_has_a_reason(self):
        self.release_commit()
        self.note("shiploop", trailer="No-E2E-Round: docs-only release, no ShipLoop behaviour changed")
        self.assertAccepted(self.release("--dry-run"))

    def test_a_trailer_with_an_empty_reason_is_refused(self):
        self.release_commit()
        self.note("shiploop", trailer="No-E2E-Round:")
        self.assertRefused(self.release("--dry-run"))
        self.git("commit", "-q", "--amend", "-m", "feat: change", "-m", "No-E2E-Round:   \nCo-Authored-By: Test <test@example.invalid>")
        self.assertRefused(self.release("--dry-run"))

    def test_a_trailer_outside_the_final_paragraph_is_not_a_trailer(self):
        self.release_commit()
        self.write("changes/shiploop/n.md", "---\nbump: patch\n---\nA fixture change.\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "feat: change", "-m", "No-E2E-Round: written in the body\n\nand then more prose after it")
        self.assertRefused(self.release("--dry-run"))

    def test_a_learnings_commit_before_the_last_release_does_not_count(self):
        self.write(LEARNINGS, "# Learnings\n")
        self.commit("test(shiploop-e2e): an earlier run", "No-E2E-Round: an earlier release's reason")
        self.release_commit()
        self.note("shiploop")
        self.assertRefused(self.release("--dry-run"))

    def test_the_release_commit_itself_does_not_count(self):
        self.write(LEARNINGS, "# Learnings\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "release: baseline", "-m",
                 "Skill-Craft-Release: skill-craft@1.0.0, shiploop@1.0.0, other@1.0.0")
        self.note("shiploop")
        self.assertRefused(self.release("--dry-run"))

    def test_only_the_named_file_counts(self):
        self.release_commit()
        self.write("docs/LEARNINGS.md", "# not the E2E journal\n")
        self.commit("docs: another learnings file")
        self.note("shiploop")
        self.assertRefused(self.release("--dry-run"))

    def test_a_learnings_commit_merged_from_a_branch_counts_when_the_branch_has_the_change(self):
        self.release_commit()
        self.note("shiploop")
        self.git("switch", "-q", "-c", "side")
        self.write(LEARNINGS, "# Learnings\n")
        self.commit("test(shiploop-e2e): a run on a side branch")
        self.git("switch", "-q", "main")
        self.git("merge", "-q", "--no-ff", "-m", "merge side", "side")
        self.assertAccepted(self.release("--dry-run"))

    def test_a_side_branch_run_that_never_had_the_change_does_not_count(self):
        self.release_commit()
        self.git("switch", "-q", "-c", "side")
        self.write(LEARNINGS, "# Learnings\n")
        self.commit("test(shiploop-e2e): a run on a side branch")
        self.git("switch", "-q", "main")
        self.note("shiploop")
        self.git("merge", "-q", "--no-ff", "-m", "merge side", "side")
        self.assertRefused(self.release("--dry-run"))

    def test_a_release_that_does_not_ship_shiploop_is_not_asked(self):
        self.release_commit()
        self.note("other")
        result = self.release("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release: other 1.0.0 -> 1.0.1", result.stdout)

    def test_an_output_only_release_is_not_asked(self):
        # No notes at all: the preflight has no ShipLoop release to gate.
        self.release_commit()
        result = self.release("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("No-E2E-Round", result.stdout + result.stderr)

    def test_the_first_release_looks_at_all_of_history(self):
        # No Skill-Craft-Release commit exists yet, so the range is every commit up to HEAD.
        self.note("shiploop")
        self.assertRefused(self.release("--dry-run"))
        self.write(LEARNINGS, "# Learnings\n")
        self.commit("test(shiploop-e2e): the first run")
        result = self.release("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("release: shiploop 1.0.0 -> 1.0.1", result.stdout)

    # -- dry run and real run

    def test_a_dry_run_shows_the_refusal_and_writes_nothing(self):
        self.release_commit()
        self.note("shiploop")
        head = self.git("rev-parse", "HEAD")
        self.assertRefused(self.release("--dry-run"))
        self.untouched()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    def test_an_accepted_dry_run_writes_nothing(self):
        self.release_commit()
        self.note("shiploop", trailer="No-E2E-Round: fixture")
        tree = self.git("rev-parse", "HEAD^{tree}")
        self.assertAccepted(self.release("--dry-run"))
        self.untouched()
        self.assertEqual(self.git("rev-parse", "HEAD^{tree}"), tree)

    def test_a_real_run_is_refused_before_it_writes_anything(self):
        self.release_commit()
        self.note("shiploop")
        head = self.git("rev-parse", "HEAD")
        self.assertRefused(self.release())
        self.untouched()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)

    # -- the route: the refusal's named fixes, submitted through the same entry point

    def test_the_learnings_fix_the_refusal_names_clears_it(self):
        self.release_commit()
        self.note("shiploop")
        message = self.assertRefused(self.release("--dry-run"))
        named = re.search(r"\S*LEARNINGS\.md", message).group(0)
        self.write(named, "# Learnings\n\n## Run 7\n")
        self.commit("test(shiploop-e2e): run 7 and its learnings")
        self.assertAccepted(self.release("--dry-run"))

    def test_the_trailer_fix_the_refusal_names_clears_it(self):
        self.release_commit()
        self.note("shiploop")
        message = self.assertRefused(self.release("--dry-run"))
        key = re.search(r"'(No-E2E-Round): <reason>'", message).group(1)
        self.git("commit", "-q", "--amend", "-m", "feat: change", "-m", f"{key}: no live run for a prompt-only edit\nCo-Authored-By: Test <test@example.invalid>")
        self.assertAccepted(self.release("--dry-run"))


if __name__ == "__main__":
    unittest.main()
