#!/usr/bin/env python3
"""The owner page (test/shiploop_e2e/owner_page.py) and its Read first panel (flow.py `read_first`), from files only.

The figures are checked on the saved Claude step slice (test/fixtures/efficiency/claude-step-slice, the extract of the run
the cross review measured by hand): 21 ShipLoop commands, 20 of 20 `complete` calls piped, 1 status display, the packet
file opened in 3 of 8 producer stages, 4 gates skipped. The comparison must be the text `packets.py --compare` writes.
"""
from __future__ import annotations

import contextlib
import gzip
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = ROOT / "test" / "shiploop_e2e"
sys.path.insert(0, str(E2E))
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))
import flow  # noqa: E402
import owner_page  # noqa: E402
import packets  # noqa: E402

FIXTURE = ROOT / "test" / "fixtures" / "efficiency" / "claude-step-slice"
RUN = ".shiploop-runs/seed/run"


def materialise(into: Path, name: str = "run") -> Path:
    """The saved slice unpacked under ``into``: its .gz files expanded."""
    target = into / name
    shutil.copytree(FIXTURE, target)
    for packed in list(target.rglob("*.gz")):
        with gzip.open(packed, "rb") as handle:
            packed.with_suffix("").write_bytes(handle.read())
        packed.unlink()
    return target


class SavedSlice(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="shiploop-owner-page-")
        cls.out = materialise(Path(cls.temp.name))
        cls.first = flow.read_first(cls.out, repo=ROOT)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_commands_piped_variable_built_and_status_displays(self):
        c = self.first["commands"]
        self.assertEqual((c["invocations"], c["literal"], c["variable_built"], c["variable_run_dir"]), (21, 1, 20, 19))
        self.assertEqual(c["by_verb"]["complete"], {"invocations": 20, "piped": 20})
        self.assertEqual(c["by_verb"]["next"], {"invocations": 1, "piped": 0})
        self.assertEqual(c["status_displays"], 1, "one PostToolUse display in the stream for 21 commands")
        self.assertEqual((c["cut_by_pipe"], c["median_n"]), (20, 20.0), "a bare `| head` keeps 10 lines and counts")

    def test_producer_packet_files_opened_and_characters_seen(self):
        p = self.first["producers"]
        self.assertEqual((p["count_opened"], p["of"]), (3, 8))
        modes = {r["stage"]: r["opened"] for r in p["rows"]}
        self.assertEqual({s: m for s, m in modes.items() if m != "none"},
                         {"step-plan": "whole", "test-spec": "slice", "carry-forward": "slice"})
        rows = {r["stage"]: r for r in p["rows"]}
        packet = self.out / rows["step-plan"]["file"]
        self.assertEqual(rows["step-plan"]["written"], len(packet.read_text()), "written is the packet file's characters")
        # The extract shortens the run's absolute paths, so its prints are shorter than the raw run's (12,417 and 7,361).
        self.assertEqual((rows["step-plan"]["seen"], rows["step-plan"]["cut_by"]), (10536, []), "the literal `next` printed whole")
        self.assertEqual(rows["test-spec"]["cut_by"], ["head -50"])
        self.assertTrue(all(r["seen"] < r["written"] for r in p["rows"]))

    def test_gates_refusals_item_commit_skills_and_cannot_show(self):
        g = self.first["gates"]
        self.assertEqual((g["count"], g["ran"]), (4, 0))
        self.assertEqual([x["gate"] for x in g["gates"]], ["base", "mutation", "inventory", "item_commit"])
        r = self.first["refusals"]
        self.assertEqual(r["count"], 3)
        self.assertEqual({x["stage"] for x in r["rows"]}, {"test-spec"})
        self.assertFalse(any("/" in x["cause"].replace("<path>", "") for x in r["rows"] if "<path>" in x["cause"]),
                         "absolute paths in a cause are replaced")
        ic = self.first["item_commit"]
        self.assertEqual((ic["measured"], ic["present"]), (True, False))
        self.assertEqual((self.first["skills"]["improve_invoked"], self.first["skills"]["improve_stages"]), (1, 4))
        self.assertEqual(self.first["skills"]["calls"], {"until-loop": 1, "skill-craft:improve": 1})
        self.assertTrue(any("n=1" in line for line in self.first["cannot_show"]))
        self.assertEqual(self.first["seeded"], ["intake", "discovery", "research", "spec", "test-strategy", "plan", "prepare"])

    def test_every_figure_names_a_file_that_exists(self):
        f = self.first
        for name in [f["commands"]["file"], f["gates"]["file"], f["producers"]["file"], f["item_commit"]["file"],
                     *(r["file"] for r in f["producers"]["rows"])]:
            self.assertTrue((self.out / name).exists() or name == f"{RUN}/lint/items", name)

    def test_read_first_mode_prints_json_and_writes_nothing(self):
        before = sorted(p.relative_to(self.out) for p in self.out.rglob("*"))
        done = subprocess.run([sys.executable, "-B", str(E2E / "flow.py"), "--read-first", str(self.out)],
                              capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(json.loads(done.stdout)["commands"]["invocations"], 21)
        self.assertEqual(sorted(p.relative_to(self.out) for p in self.out.rglob("*")), before)


class PageTests(unittest.TestCase):
    """The page's comparison, sizes, time and turn rows, decisions and markup."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="shiploop-owner-page-")
        base = Path(cls.temp.name)
        cls.now = materialise(base, "now")
        cls.before = materialise(base, "before")
        # The earlier run: the step-plan packet 1,000 characters longer, the seeded intake packet 50.
        state_packets = cls.before / RUN / "packets"
        for path in state_packets.glob("nav-*.md"):
            head = path.read_text()[:4000]
            if "| step-plan |" in head:
                path.write_text(path.read_text() + "x" * 1000)
                cls.step_plan = path.name
            if "| intake |" in head:
                path.write_text(path.read_text() + "y" * 50)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_the_comparison_is_the_text_packets_py_writes(self):
        data = owner_page.build(self.now, self.before)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(packets.main([str(self.now), "--compare", str(self.before)]), 0)
        self.assertEqual(data["compare_text"], (self.now / packets.COMPARE_MD).read_text())
        (self.now / packets.COMPARE_MD).unlink()
        for folder in (self.now, self.before):
            for name in (packets.REPORT_JSON, packets.REPORT_MD):
                (folder / name).unlink(missing_ok=True)

    def test_sizes_are_on_disk_characters_and_leave_out_seeded_stages(self):
        data = owner_page.build(self.now, self.before)
        rows = {r["stage"]: r for r in data["sizes"]}
        self.assertNotIn("intake", rows, "a stage the harness recorded without the model is not a size result")
        self.assertEqual(rows["step-plan"]["delta"], -1000)
        self.assertEqual(rows["step-plan"]["now"], len((self.now / RUN / "packets" / self.step_plan).read_text()))
        self.assertEqual(rows["step-plan"]["percent"], round(-100000.0 / rows["step-plan"]["before"], 1))

    def test_time_and_turn_deltas_carry_n_and_the_aa_spread(self):
        data = owner_page.build(self.now, self.before)
        self.assertTrue(all(r["n"] == "1 per side" and r["aa_spread"] is None for r in data["deltas"]))
        page = owner_page.render(data)
        self.assertIn("A/A spread: not measured", page)
        with_control = owner_page.build(self.now, self.before, control=[self.now, self.before])
        self.assertEqual({r["measure"]: r["aa_spread"] for r in with_control["deltas"]}, {"seconds": 0.0, "turns": 0})
        self.assertIn("A/A spread from 2 control runs", owner_page.render(with_control))

    def test_the_page_is_self_contained_and_its_data_cannot_close_a_script(self):
        decisions = [{"id": "D-1", "title": "</script><b>not markup</b>", "status": "open"}]
        data = owner_page.build(self.now, self.before, decisions=decisions)
        page = owner_page.render(data)
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('name="viewport"', page)
        self.assertEqual(page.count("</script>"), 2, "the decision seed and the page script, nothing from the data")
        self.assertNotIn("<script src", page, "no external library, so none is left unpinned")
        self.assertIn("Seen by the model (after any head pipe)", page)
        self.assertIn('claude.use("db")', page)
        self.assertIn('collection("decisions")', page)
        self.assertIn("Copy update prompt", page)
        self.assertIn("packet-generator commit", page)
        self.assertIn('id="cannot-show"', page)
        self.assertFalse(owner_page.render(data, standalone=False).startswith("<!doctype"))

    def test_cli_writes_the_page(self):
        target = Path(self.temp.name) / "page.html"
        decisions = Path(self.temp.name) / "decisions.json"
        decisions.write_text(json.dumps([{"id": "P-6", "title": "Owner page", "status": "accepted"}]))
        done = subprocess.run([sys.executable, "-B", str(E2E / "owner_page.py"), str(self.now), "--earlier", str(self.before),
                               "--html", str(target), "--decisions", str(decisions)], capture_output=True, text=True,
                              env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn('"id": "P-6"', target.read_text())


class StalenessTests(unittest.TestCase):
    def test_counts_generator_commits_after_the_recorded_head(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-owner-page-git-") as temp:
            repo, out = Path(temp) / "repo", Path(temp) / "out"
            out.mkdir()
            git = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True, text=True).stdout.strip()  # noqa: E731
            repo.mkdir()
            git("init", "-q", "-b", "main")
            git("config", "user.email", "t@example.invalid")
            git("config", "user.name", "t")
            (repo / "skills/shiploop/scripts").mkdir(parents=True)
            (repo / "skills/shiploop/scripts/gen.py").write_text("a\n")
            git("add", "-A")
            git("commit", "-qm", "one")
            recorded = git("rev-parse", "HEAD")
            (repo / "skills/shiploop/scripts/gen.py").write_text("b\n")
            (repo / "other.txt").write_text("c\n")
            git("add", "-A")
            git("commit", "-qm", "two")
            (repo / "other.txt").write_text("d\n")
            git("commit", "-qam", "three")
            (out / "invocation.json").write_text(json.dumps({"local_head": recorded}))
            (out / "timeline.jsonl").write_text(json.dumps({"line": 0, "t": 1791778315.0}) + "\n")
            found = flow.staleness(out, repo)
            self.assertEqual(found["generator_commits"], 1)
            self.assertEqual(found["text"], f"recorded 2026-10-12 on {recorded[:8]}, main {git('rev-parse', 'HEAD')[:8]}, "
                                            "1 packet-generator commit since")
            (out / "invocation.json").write_text(json.dumps({"local_head": "f" * 40}))
            self.assertIsNone(flow.staleness(out, repo)["generator_commits"])
            self.assertIn("not measured (the recorded commit is not in this repository)", flow.staleness(out, repo)["text"])


class InjectedTextTests(unittest.TestCase):
    def test_text_the_host_injects_is_not_the_models(self):
        with tempfile.TemporaryDirectory(prefix="shiploop-owner-page-inject-") as temp:
            out = Path(temp)
            rows = [{"type": "assistant", "message": {"content": [{"type": "text", "text": "I will review."},
                                                                  {"type": "tool_use", "id": "t0", "name": "Skill", "input": {"skill": "x"}}]}},
                    {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t0", "content": "ok"}]}},
                    {"type": "user", "message": {"content": [{"type": "text", "text": "Base directory for this skill: /s"}]}}]
            (out / "events.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
            items, _heads, _reads, _t0 = flow.claude_items(out, flow.Shortener(out, out / "run"), "nav-" + "a" * 32)
            kinds = [(i["kind"], i["body"]["text"]) for i in items if i["kind"] in ("say", "injected")]
            self.assertEqual(kinds, [("say", "I will review."), ("injected", "Base directory for this skill: /s")])
        viewer = (E2E / "flow_viewer.html").read_text()
        self.assertIn('e.kind === "injected"', viewer)
        self.assertIn("host-injected", viewer)
        self.assertIn("Seen by the model (after any head pipe)", viewer)


if __name__ == "__main__":
    unittest.main()
