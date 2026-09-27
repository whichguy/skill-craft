#!/usr/bin/env python3
"""Ask Agent's current-workspace route: the read-only `current-state` command and its card text.

Hermetic: each test builds a throwaway Git repository; no native agent runs.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ask-agent"
HELPER = SKILL / "scripts" / "ask_agent_workspace.py"
REFERENCE = SKILL / "references" / "current-workspace.md"


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                    "-c", "commit.gpgsign=false", *args], check=True, capture_output=True)


def tree(root: Path) -> list[str]:
    return sorted(str(path.relative_to(root)) for path in root.rglob("*") if ".git" not in path.parts)


class CurrentStateTests(unittest.TestCase):
    def setUp(self) -> None:
        temp = tempfile.TemporaryDirectory(prefix="ask-agent-current-")
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.repo = self.base / "repo"
        (self.repo / "src").mkdir(parents=True)
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "src" / "app.py").write_text("print(1)\n")
        (self.repo / ".gitignore").write_text("build/\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "init")

    def run_helper(self, *args: str, cwd: Path | None = None, stdin: str | None = None) -> tuple[int, dict]:
        env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        env.update(HOME=str(self.home), PYTHONDONTWRITEBYTECODE="1")
        completed = subprocess.run([sys.executable, str(HELPER), "current-state", *args],
                                   cwd=cwd or self.repo, env=env, input=stdin, text=True,
                                   capture_output=True, timeout=60)
        return completed.returncode, json.loads(completed.stdout)

    def baseline(self) -> dict:
        code, state = self.run_helper()
        self.assertEqual(code, 0, state)
        return state

    def compare(self, baseline: dict, *write_set: str) -> dict:
        args = [arg for path in write_set for arg in ("--write-set", path)]
        code, state = self.run_helper("--baseline", "-", *args, stdin=json.dumps(baseline))
        self.assertEqual(code, 0, state)
        return state

    def test_clean_state_is_deterministic_and_describes_the_checkout(self) -> None:
        first, second = self.baseline(), self.baseline()
        self.assertEqual(first, second)
        self.assertEqual((first["schema"], first["status"], first["branch"], first["entries"]),
                         ("ask-agent.current-state.v1", "ok", "main", []))
        self.assertEqual(first["root"], str(self.repo))
        self.assertRegex(first["fingerprint"], r"^[0-9a-f]{64}$")

    def test_dirty_paths_carry_status_and_digest(self) -> None:
        (self.repo / "src" / "app.py").write_text("print(2)\n")
        (self.repo / "notes.md").write_text("n\n")
        (self.repo / "build").mkdir()
        (self.repo / "build" / "out.bin").write_text("ignored\n")
        state = self.baseline()
        rows = {entry["path"]: entry for entry in state["entries"]}
        self.assertEqual(set(rows), {"src/app.py", "notes.md"})
        self.assertEqual((rows["src/app.py"]["status"], rows["notes.md"]["status"]), (" M", "??"))
        self.assertRegex(rows["notes.md"]["sha256"], r"^[0-9a-f]{64}$")

    def test_unchanged_within_write_set_and_drift(self) -> None:
        (self.repo / "src" / "app.py").write_text("print(2)\n")
        before = self.baseline()
        self.assertEqual(self.compare(before)["verdict"], "unchanged")

        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "summary.md").write_text("s\n")
        within = self.compare(before, "docs")
        self.assertEqual((within["verdict"], within["changed_paths"], within["outside_write_set"]),
                         ("changed-within-write-set", ["docs/summary.md"], []))
        self.assertEqual(self.compare(before, "docs/*.md")["verdict"], "changed-within-write-set")

        (self.repo / "src" / "app.py").write_text("print(3)\n")
        drift = self.compare(before, "docs")
        self.assertEqual((drift["verdict"], drift["outside_write_set"]), ("drift", ["src/app.py"]))
        # Report-only has no write set, so any change is drift.
        self.assertEqual(self.compare(before)["verdict"], "drift")

    def test_reverting_or_staging_a_dirty_path_is_a_change(self) -> None:
        (self.repo / "src" / "app.py").write_text("print(2)\n")
        before = self.baseline()
        git(self.repo, "add", "src/app.py")
        self.assertEqual(self.compare(before)["changed_paths"], ["src/app.py"])
        git(self.repo, "checkout", "HEAD", "--", "src/app.py")
        self.assertEqual(self.compare(before)["changed_paths"], ["src/app.py"])

    def test_a_commit_is_drift_even_inside_the_write_set(self) -> None:
        before = self.baseline()
        (self.repo / "src" / "app.py").write_text("print(2)\n")
        git(self.repo, "commit", "-qam", "worker commit")
        state = self.compare(before, "src")
        self.assertEqual((state["verdict"], state["head_moved"], state["changed_paths"]), ("drift", True, []))

    def test_expect_root_checks_the_process_directory(self) -> None:
        code, state = self.run_helper("--expect-root", str(self.repo), cwd=self.repo / "src")
        self.assertEqual((code, state["status"], state["cwd"]), (0, "ok", str(self.repo / "src")))
        other = self.base / "other"
        other.mkdir()
        git(other, "init", "-q")
        code, state = self.run_helper("--expect-root", str(self.repo), cwd=other)
        self.assertEqual((code, state["status"]), (2, "error"))
        self.assertIn("does not match the expected root", state["error"])

    def test_non_git_directory_reports_its_limitation(self) -> None:
        plain = self.base / "plain"
        plain.mkdir()
        code, state = self.run_helper(cwd=plain)
        self.assertEqual((code, state["status"]), (0, "not-git"))
        self.assertIn("only report-only", state["limitation"])
        code, state = self.run_helper("--expect-root", str(self.repo), cwd=plain)
        self.assertEqual((code, state["status"]), (2, "error"))

    def test_baseline_from_another_root_or_schema_is_refused(self) -> None:
        before = self.baseline()
        for bad in ({**before, "root": str(self.base)}, {**before, "schema": "x"}, {"status": "not-git"}):
            code, state = self.run_helper("--baseline", "-", stdin=json.dumps(bad))
            self.assertEqual((code, state["status"]), (2, "error"))

    def test_writes_nothing(self) -> None:
        (self.repo / "notes.md").write_text("n\n")
        repo_before, home_before = tree(self.repo), tree(self.home)
        before = self.baseline()
        self.compare(before, "notes.md")
        self.assertEqual((tree(self.repo), tree(self.home)), (repo_before, home_before))


class CardTests(unittest.TestCase):
    def test_card_declares_the_route_as_explicit_only(self) -> None:
        card = (SKILL / "SKILL.md").read_text()
        self.assertIn("      - ask-agent/consumer-owned-workspace/v1\n      - ask-agent/current-workspace/v1\n", card)
        flat = " ".join(card.split())
        self.assertIn("explicitly says `workspace_route: current`", flat)
        self.assertIn("improve-agent never select it", flat)
        reference = " ".join(REFERENCE.read_text().split())
        for phrase in ("Never infer it from a request for speed", "| `report-only` | yes |",
                       "Claude Code | `Agent` without `isolation`", "refuse; report `changed_paths`"):
            self.assertIn(phrase, reference)

    def test_links_resolve(self) -> None:
        def anchors(path: Path) -> set[str]:
            return {re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
                    for line in path.read_text().splitlines() if line.startswith("#")}

        for page in [SKILL / "SKILL.md", *sorted((SKILL / "references").glob("*.md"))]:
            for target in re.findall(r"\]\(([^)\s]+)\)", page.read_text()):
                if target.startswith("http"):
                    continue
                file_part, _, fragment = target.partition("#")
                resolved = (page.parent / file_part) if file_part else page
                self.assertTrue(resolved.exists(), f"{page.name}: missing {target}")
                if fragment:
                    self.assertIn(fragment, anchors(resolved), f"{page.name}: missing anchor {target}")


if __name__ == "__main__":
    unittest.main()
