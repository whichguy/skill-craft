"""Focused contract tests for the self-contained ShipLoop progress renderer."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import shiploop_progress_render as progress_render  # noqa: E402


def snapshot() -> dict:
    return {
        "schema": "shiploop-progress/v1",
        "run": {
            "id": "run-17",
            "prompt": "Add a --version flag to the CLI",
            "revision": 4,
            "status": "active",
            "stage": "test-author",
            "owner": "W1",
            "reason": "",
        },
        "observed_at": "2026-09-28T10:02:00Z",
        "source_changed_at": "2026-09-28T09:59:00Z",
        "observer": {
            "mode": "watch",
            "interval_seconds": 2,
            "refresh_seconds": 5,
            "stale_after_seconds": 30,
            "final": False,
        },
        "facts": {
            "phases": [
                {"name": "Preparation", "done": 7, "done_label": 7, "total": 7, "state": "done"},
                {"name": "Work items", "done": 0.25, "done_label": 0, "total": 2, "state": "current"},
                {"name": "Release", "done": 0, "done_label": 0, "total": 9, "state": "pending"},
            ],
            "now": {"label": "W1 (1 of 2) › Tests first › test-author", "text": "Write tests for the CLI flag."},
            "achieved": [{"label": "intake", "text": "Scope confirmed."}],
            "ahead": [{"label": "W1", "text": "Build → Check → Integrate"}],
        },
        "status_block": "=== ShipLoop status ===\nNext: test-author",
        "plan_accepted": False,
        "work_items": [],
        "documents": [
            {
                "id": "D1",
                "title": "Accepted behavior",
                "path": "spec.md",
                "uri": "file:///tmp/spec%20one.md",
                "content": "# CLI behavior\nShow <script>alert(1)</script> and exit 0.",
                "summary": "The flag prints the package version.",
                "sha256": "abc123",
                "observed_at": "2026-09-28T09:58:00Z",
                "status": "accepted-result",
                "acceptance": "Tests pass.",
            },
        ],
        "activity": [
            {
                "stream": "navigator",
                "seq": 12,
                "time": "2026-09-28T10:01:00Z",
                "stage": "test-author",
                "workitem": "W1",
                "outcome": "started",
                "summary": "The test author began the focused test file.",
            },
            {
                "stream": "chain-report",
                "seq": 13,
                "time": "2026-09-28T10:01:30Z",
                "stage": "test-author",
                "workitem": "W1",
                "outcome": "accepted",
                "summary": "The accepted chain report recorded the test work.",
            },
        ],
        "warnings": [],
        "terminal_report": "file:///tmp/run/report.html",
    }


class ProgressRenderTests(unittest.TestCase):
    def test_renders_three_phases_and_explicit_pending_plan(self) -> None:
        page = progress_render.render(snapshot())
        self.assertEqual(page.count('class="phase-card '), 3)
        self.assertIn("Plan pending", page)
        self.assertIn("The plan is pending; work items have not been accepted yet.", page)
        self.assertIn("Preparation", page)
        self.assertIn("Work items", page)
        self.assertIn("Release", page)

    def test_escapes_untrusted_text_and_rejects_scriptable_links(self) -> None:
        data = snapshot()
        data["run"]["prompt"] = '<img src=x onerror="alert(1)">'
        data["run"]["reason"] = "</header><script>alert(1)</script>"
        data["documents"][0]["title"] = '<svg onload="alert(1)">'
        data["documents"][0]["content"] = "</pre><script>alert(1)</script>"
        data["documents"][0]["uri"] = "javascript:alert(1)"
        data["status_block"] = "<script>alert(1)</script>"
        data["terminal_report"] = "https://example.test/report.html"

        page = progress_render.render(data)

        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", page)
        self.assertIn("&lt;/pre&gt;&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn('<script>alert(1)</script>', page)
        self.assertNotIn('<img src=', page)
        self.assertNotIn('href="javascript:', page)
        self.assertNotIn('href="https://', page)

    def test_renders_offline_preview_and_local_file_sources(self) -> None:
        page = progress_render.render(snapshot())
        self.assertIn('<details class="document" data-state-key="doc-D1">', page)
        self.assertIn("# CLI behavior", page)
        self.assertIn("Show &lt;script&gt;alert(1)&lt;/script&gt; and exit 0.", page)
        self.assertIn('href="file:///tmp/spec%20one.md"', page)
        self.assertIn("Open local source", page)
        self.assertIn('href="file:///tmp/run/report.html"', page)
        self.assertIn("SHA-256", page)
        self.assertIn("stream navigator", page)
        self.assertIn("stream chain-report", page)

    def test_watch_controls_use_escaped_data_settings_and_local_refresh_only(self) -> None:
        data = snapshot()
        data["observer"].update(interval_seconds=2, refresh_seconds=7, stale_after_seconds=19)
        page = progress_render.render(data)
        self.assertIn('data-mode="watch"', page)
        self.assertIn('data-final="false"', page)
        self.assertIn('data-refresh-seconds="7"', page)
        self.assertIn('data-stale-after-seconds="19"', page)
        self.assertIn("Pause updates", page)
        self.assertIn("Resume updates", page)
        self.assertIn("Refresh now", page)
        self.assertIn("location.reload()", page)
        self.assertIn("sessionStorage.setItem", page)
        self.assertIn("shiploop-view=", page)
        self.assertIn("paused: paused", page)
        self.assertIn("state.details[key]", page)
        self.assertIn("setInterval(updateFreshness, 1000)", page)
        self.assertIn("default-src 'none'", page)
        self.assertNotIn("fetch(", page)
        self.assertNotIn("<script src=", page)
        self.assertNotIn('<link rel="stylesheet"', page)
        self.assertNotIn("<img ", page)

    def test_snapshot_and_final_modes_disable_automatic_refresh(self) -> None:
        data = snapshot()
        data["observer"]["mode"] = "snapshot"
        page = progress_render.render(data)
        self.assertIn('data-mode="snapshot"', page)
        self.assertIn("Snapshot view · updates off", page)
        self.assertIn("Snapshot age: calculating…", page)

        data = snapshot()
        data["observer"]["final"] = True
        page = progress_render.render(data)
        self.assertIn('data-final="true"', page)
        self.assertIn("Final snapshot · updates off", page)
        self.assertIn("Final snapshot age: calculating…", page)

    def test_freshness_labels_are_separate_from_run_activity_and_page_open(self) -> None:
        page = progress_render.render(snapshot())
        self.assertIn('id="observer-age">Observer data age: calculating…', page)
        self.assertIn('id="source-changed-age">Source change time: calculating…', page)
        self.assertIn('id="last-activity-age">Latest run activity: calculating…', page)
        self.assertIn('id="page-opened">Page opened: calculating…', page)
        self.assertIn("Observer data age:", page)
        self.assertIn("Latest run activity:", page)
        self.assertNotIn("Live", page)

    def test_missing_fields_render_a_readable_snapshot(self) -> None:
        data = deepcopy(snapshot())
        data.clear()
        page = progress_render.render(data)
        self.assertIn("<!doctype html>", page)
        self.assertIn("ShipLoop run", page)
        self.assertIn("Plan pending", page)
        self.assertIn("No activity has been recorded.", page)
        self.assertIn("No files were included in this snapshot.", page)
        self.assertIn("No accepted generated graph is available.", page)

    def test_renders_dynamic_accepted_graph_and_accessible_dependency_list(self) -> None:
        data = snapshot()
        data["graphs"] = [{
            "label": "W1 · CLI flag",
            "status": "accepted",
            "dependencies_known": True,
            "nodes": [
                {"id": "parse", "title": "Add version argument", "status": "done", "plan": "Use argparse."},
                {"id": "test", "title": "Verify output", "status": "pending", "action": "test-author"},
                {"id": "docs", "title": "Document the flag", "status": "queued"},
            ],
            "edges": [
                {"from": "parse", "to": "test"},
                {"from": "parse", "to": "docs"},
            ],
        }, {
            "label": "W2 · documentation",
            "status": "accepted",
            "dependencies_known": True,
            "nodes": [{"id": "parse", "title": "Write usage notes", "status": "pending"}],
            "edges": [],
        }]
        page = progress_render.render(data)

        self.assertIn("W1 · CLI flag", page)
        self.assertIn("W2 · documentation", page)
        self.assertIn('class="dependency-svg"', page)
        self.assertIn('class="dependency-edge"', page)
        self.assertIn("marker-end=\"url(#dependency-arrow-0)\"", page)
        self.assertIn('id="dependency-arrow-1"', page)
        self.assertIn("parse", page)
        self.assertIn("Verify output", page)
        self.assertIn("test-author", page)
        self.assertIn("Write usage notes", page)
        self.assertIn("Depends on:</strong> parse", page)
        self.assertIn("graph-text-W1 · CLI flag", page)

    def test_unknown_dependencies_do_not_render_steps_as_independent(self) -> None:
        data = snapshot()
        data["graphs"] = [{
            "label": "W2 · accepted step plan",
            "status": "accepted",
            "dependencies_known": False,
            "nodes": [
                {"id": "implement", "title": "Implement the flag", "status": "accepted"},
                {"id": "verify", "title": "Run checks", "status": "pending"},
            ],
            "edges": [],
        }]
        page = progress_render.render(data)

        self.assertIn("Dependencies were not recorded; node positions do not imply order.", page)
        self.assertIn("Dependencies not recorded; order is unknown.", page)
        self.assertNotIn('class="dependency-edge"', page)

    def test_draft_and_unavailable_graphs_are_labeled_without_showing_speculative_steps(self) -> None:
        data = snapshot()
        data["graphs"] = [
            {
                "label": "W3 · draft",
                "status": "draft",
                "dependencies_known": False,
                "nodes": [{"id": "draft1", "title": "Unaccepted predicted step"}],
                "edges": [],
            },
            {"label": "W4 · report missing", "status": "unavailable", "nodes": [], "edges": []},
        ]
        page = progress_render.render(data)

        self.assertIn("A generated graph draft exists but is not accepted", page)
        self.assertIn("its steps are not shown as implementation work", page)
        self.assertIn("Graph data is unavailable for this scope.", page)
        self.assertNotIn("Unaccepted predicted step", page)
        self.assertNotIn('class="dependency-svg"', page)

    def test_missing_endpoints_and_cycles_are_diagnosed_without_stalling(self) -> None:
        data = snapshot()
        data["graphs"] = [{
            "label": "W1 · malformed graph",
            "status": "accepted",
            "dependencies_known": True,
            "nodes": [
                {"id": "A", "title": "First step", "status": "pending"},
                {"id": "B", "title": "Second step", "status": "pending"},
            ],
            "edges": [
                {"from": "A", "to": "B"},
                {"from": "B", "to": "A"},
                {"from": "B", "to": "ghost"},
            ],
        }]
        page = progress_render.render(data)

        self.assertIn("Cycle detected or cycle-dependent steps remain", page)
        self.assertIn("A, B", page)
        self.assertIn("missing step ID(s): ghost.", page)
        self.assertIn("First step", page)
        self.assertIn("Second step", page)


if __name__ == "__main__":
    unittest.main()
