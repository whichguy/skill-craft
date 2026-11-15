"""Focused contract tests for the self-contained ShipLoop progress renderer."""

from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
from pathlib import Path
import sys
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "shiploop" / "scripts"))

import shiploop_progress_render as progress_render  # noqa: E402
import shiploop_trace_page as trace_page  # noqa: E402


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


def story_snapshot() -> dict:
    """Coherent synthetic generation: no real run, core capture or provider required."""
    data = snapshot()
    data["run"]["status"] = "blocked"
    data["story"] = {
        "schema": "shiploop-progress-story/v1",
        "summary": {"now": "Engine blocked at verify.", "changed": "A check refused the callback.",
                    "waiting": "Recorded owner hold.", "next": "Collect source-return evidence."},
        "last_event_at": "2026-09-28T10:02:30Z",
        "visits": [
            {"id": "visit:a", "action": "a", "stage": "verify", "item": "W1", "status": "accepted",
             "summary": "First verification visit.", "started_at": "2026-09-28T10:00:00Z",
             "ended_at": "2026-09-28T10:01:00Z", "duration_seconds": 60,
             "duration_basis": "inferred visit dwell", "events": ["accepted:a"], "evidence": ["check:a"]},
            {"id": "visit:b", "action": "b", "stage": "verify", "item": "W1", "status": "blocked",
             "summary": "Verification reopened.", "duration_seconds": None, "duration_basis": None,
             "events": ["trace:gen:4", "trace:gen:5"], "evidence": ["until:b", "absent"]},
        ],
        "events": [
            {"id": "accepted:a", "kind": "accepted", "status": "accepted", "summary": "Accepted from state.",
             "binding": "explicit", "source": {"path": "state.md", "line": 4, "sha256": "abc"}},
            {"id": "trace:gen:4", "kind": "check", "status": "failed", "summary": "Check failed; preserve refusal.",
             "binding": "contextual", "duration_ms": 25, "source": {"path": "trace.jsonl", "line": 4, "sha256": "def"},
             "evidence": ["check:a"]},
            {"id": "trace:gen:5", "kind": "packet", "summary": "Packet re-emitted, same bytes.",
             "binding": "explicit", "source": {"path": "trace.jsonl", "line": 5}, "evidence": ["packet:b"]},
            {"id": "trace:gen:6", "kind": "hook", "summary": "Unbound continuation.", "binding": "unbound"},
        ],
        "evidence": [
            {"id": "check:a", "title": "Check receipt", "path": "tests/a.md", "line": 2, "selector": "result",
             "sha256": "source-hash", "status": "failed", "content": "FAIL <script>doBad()</script>",
             "summary": "Reused from prior check; copy is not another execution."},
            {"id": "until:b", "title": "Until receipt", "path": "loops/b-terminal.json", "status": "active",
             "content": '{"status":"active"}', "summary": "Filename does not establish terminal status."},
            {"id": "packet:b", "title": "Prompt as issued", "path": "packets/sent/b.md", "status": "withheld",
             "content": None, "summary": "Preview withheld by capture."},
        ],
        "lifecycle": {
            "engine": {"status": "blocked", "summary": "Engine awaits callback.", "producer": "state"},
            "execution": {"status": "exited", "summary": "Worker exited.", "producer": "fixture-harness"},
            "acceptance": {"status": "unknown", "summary": "No product verdict."},
            "source_return": {"status": "pending", "summary": "Return not observed."},
            "owner_hold": {"status": "held", "summary": "Owner preserving evidence.", "evidence": ["until:b"]},
        },
        "observations": [{"id": "o1", "kind": "interpretation", "producer": "fixture-owner", "scope": "source",
                          "title": "Later reading", "summary": "Retrospective note.", "event_at": None,
                          "observed_at": "2026-09-28T10:03:00Z", "logged_at": "2026-09-28T11:00:00Z"}],
        "sources": [
            {"id": "trace", "path": "trace.jsonl", "status": "partial", "rows": 6, "omitted": 2,
             "message": "Interior damaged row; incomplete tail pending.", "observed_at": "2026-09-28T10:02:00Z",
             "changed_at": "2026-09-28T10:01:59Z", "last_event_at": "2026-09-28T10:01:30Z"},
            {"id": "observations", "status": "stale", "message": "Retained previous generation."},
        ],
        "warnings": ["Optional source unavailable."],
    }
    data["trace_publication"] = {"status": "unavailable", "message": "Trace publication failed.",
                                  "observed_at": "2026-09-28T10:02:00Z"}
    return data


class PageNodes(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.nodes = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def attributes(self, tag):
        return [attrs for name, attrs in self.nodes if name == tag]


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
        self.assertIn('<details class="document" data-state-key="doc-D1" id="document-646f632d4431">', page)
        self.assertIn("# CLI behavior", page)
        self.assertIn("Show &lt;script&gt;alert(1)&lt;/script&gt; and exit 0.", page)
        self.assertIn('href="file:///tmp/spec%20one.md"', page)
        self.assertIn("Open local source", page)
        self.assertIn('href="file:///tmp/run/report.html"', page)
        self.assertIn("SHA-256", page)
        self.assertIn("stream navigator", page)
        self.assertIn("stream chain-report", page)

    def test_head_meta_tags_are_closed_so_the_policy_and_color_scheme_both_apply(self) -> None:
        # The policy tag once lacked its closing quote, so it swallowed the next tag and a browser warned that
        # form-action had an invalid source.
        metas = []

        class Head(HTMLParser):
            def handle_starttag(self, tag, attrs):
                if tag == "meta":
                    metas.append(dict(attrs))

        Head().feed(progress_render.render(snapshot()))
        policy = next(meta for meta in metas if meta.get("http-equiv") == "Content-Security-Policy")["content"]
        self.assertTrue(policy.endswith("form-action 'none'"), policy)
        self.assertNotIn("<", policy)
        self.assertIn("light", [meta.get("content") for meta in metas if meta.get("name") == "color-scheme"])

    def test_the_saved_report_link_can_be_pointed_at_the_viewer(self) -> None:
        page = progress_render.render(snapshot())
        self.assertIn('<a class="report-link" href="file:///tmp/run/report.html">Open the saved report</a>', page)
        self.assertIn('location.protocol === "http:"', page)
        self.assertIn('setAttribute("href", "report.html")', page)

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


def tag_text(page: str, name: str) -> str:
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.depth = 0
            self.parts = []

        def handle_starttag(self, tag, attrs):
            if tag == name:
                self.depth += 1

        def handle_endtag(self, tag):
            if tag == name:
                self.depth -= 1

        def handle_data(self, text):
            if self.depth:
                self.parts.append(text)
    parser = Text()
    parser.feed(page)
    return "".join(parser.parts)


class StoryRenderTests(unittest.TestCase):
    def test_long_visit_summary_is_compact_when_closed_and_complete_when_expanded(self):
        data = story_snapshot()
        full = "Accepted test plan.\n| Case | Expected |\n" + ("| <script>unsafe()</script> & input | exact result |\n" * 300) + "LAST VISIT REQUIREMENT"
        data["story"]["visits"][0].update(stage="system-test-author", summary=full)
        before = deepcopy(data)
        page = progress_render.render(data)
        visit_id = progress_render._anchor("visit", "visit:a")
        full_id = progress_render._anchor("visit-summary", "visit:a")
        visit = page[page.index('id="' + visit_id + '"'):]
        closed = visit[visit.index('<summary>'):visit.index('</summary>')]
        small = closed[closed.index('<small>') + len('<small>'):closed.index('</small>')]
        self.assertLessEqual(len(tag_text('<small>' + small + '</small>', "small")), 190)
        self.assertNotIn("LAST VISIT REQUIREMENT", closed)
        self.assertIn("system-test-author", closed)
        self.assertIn("accepted", closed)
        self.assertIn("1 min", closed)
        self.assertIn("inferred visit dwell", closed)
        self.assertIn(full, tag_text(page, "pre"))
        self.assertNotIn('<script>unsafe()</script>', page)
        self.assertIn('&lt;script&gt;unsafe()&lt;/script&gt; &amp; input', page)
        self.assertIn('id="' + full_id + '"', page)
        self.assertIn('aria-label="Full recorded visit summary"', page)
        self.assertEqual(data, before)
        data["story"]["visits"][0]["summary"] += "\nLater display content."
        rerendered = progress_render.render(data)
        self.assertIn('id="' + visit_id + '"', rerendered)
        self.assertIn('id="' + full_id + '"', rerendered)
        self.assertLess(page.index('id="' + visit_id + '"'), page.index('id="' + progress_render._anchor("visit", "visit:b") + '"'))
        data["run"]["reason"] = full
        data["story"]["visits"][0]["summary"] = full
        blocked_page = progress_render.render(data)
        self.assertIn('href="#recorded-blocker"', blocked_page)
        self.assertEqual(blocked_page.count("LAST VISIT REQUIREMENT"), 1)

    def test_long_request_has_bounded_heading_title_and_closed_complete_source_preview(self):
        for beginning in ("Build a useful tool. ", "A request without a sentence break " * 20):
            data = story_snapshot()
            prompt = beginning + ("Detailed requirement <tag> & exact spacing.\n" * 800) + "LAST ORIGINAL REQUIREMENT"
            data["run"]["prompt"] = prompt
            before = deepcopy(data)
            page = progress_render.render(data)
            self.assertEqual(data, before, "rendering must not truncate stored input")
            self.assertLessEqual(len(tag_text(page, "h1")), 110)
            self.assertLessEqual(len(tag_text(page, "title")), 90)
            if beginning == "Build a useful tool. ":
                self.assertEqual(tag_text(page, "h1"), "Build a useful tool.")
            self.assertIn(prompt, tag_text(page, "pre"))
            details = next(row for row in PageNodes(page).attributes("details") if row.get("id") == "original-request")
            self.assertNotIn("open", details)
            self.assertEqual(details["data-state-key"], "original-request")
            self.assertIn("Full original request", page)
            self.assertIn("Source: saved run prompt", page)
            self.assertIn("heading is a display excerpt", page)

    def test_missing_request_is_labeled_instead_of_relabeling_fallback_goal_as_original(self):
        data = snapshot()
        data["run"].pop("prompt")
        data["facts"]["goal"] = "A recorded goal."
        page = progress_render.render(data)
        self.assertEqual(tag_text(page, "h1"), "A recorded goal.")
        self.assertIn("Original request not included in this snapshot.", tag_text(page, "pre"))
        self.assertNotIn("A recorded goal.", tag_text(page, "pre"))

    def test_repeated_long_blocker_has_one_full_home_and_scoped_supporting_links(self):
        data = story_snapshot()
        reason = "Recorded outside dependency. " + "Exact retained blocker detail <unsafe> & scope. " * 120
        data["run"]["reason"] = reason
        data["facts"]["stop"] = {"kind": "blocked", "text": "Run condition: " + reason}
        data["story"]["summary"]["waiting"] = reason
        data["story"]["lifecycle"]["engine"].update(summary=reason, producer="state fixture", at="2026-09-28T10:00:00Z")
        data["story"]["visits"][-1]["summary"] = reason
        page = progress_render.render(data)
        full = "Recorded outside dependency. " + "Exact retained blocker detail &lt;unsafe&gt; &amp; scope. " * 120
        self.assertEqual(page.count(full), 1)
        self.assertIn(reason, tag_text(page, "pre"))
        details = next(row for row in PageNodes(page).attributes("details") if row.get("id") == "recorded-blocker")
        self.assertNotIn("open", details)
        self.assertGreaterEqual(page.count('href="#recorded-blocker"'), 4)
        self.assertIn("Run condition: <a", page)
        self.assertIn("Producer: state fixture", page)
        self.assertIn("Product acceptance</dt><dd><strong>unknown", page)
        self.assertIn("Source: saved run reason (run.reason)", page)

    def test_human_durations_keep_exact_recorded_values_and_unknowns(self):
        data = story_snapshot()
        data["story"]["visits"][0]["duration_seconds"] = 3723.25
        data["story"]["events"][1]["duration_ms"] = 125250
        page = progress_render.render(data)
        self.assertIn(">1 hr 2 min 3.25 sec</span>", page)
        self.assertIn('title="Recorded duration: 3723.25 s"', page)
        self.assertIn(">2 min 5.25 sec</span>", page)
        self.assertIn('title="Recorded duration: 125250 ms"', page)
        self.assertIn("aria-label=", progress_render._duration(0))
        self.assertIn(">0 sec</span>", progress_render._duration(0))
        self.assertIn(">unknown</span>", progress_render._duration(None))
        self.assertIn("unknown (invalid recorded duration)", progress_render._duration(-1))
        self.assertIn("unknown (invalid recorded duration)", progress_render._duration(float("nan")))
        self.assertIn("≈ 0 sec", progress_render._duration(0.00001))

    @unittest.skipUnless(shutil.which("node"), "Node required for isolated duration formatter probe")
    def test_trace_command_durations_are_readable_with_exact_tooltips(self):
        page = trace_page.PAGE
        span = page[page.index("  function span(s) {"):page.index("  function commandDuration(ms) {")]
        duration = page[page.index("  function commandDuration(ms) {"):page.index("  const short =")]
        script = "const assert = require('assert');\n" + span + duration + """
assert.equal(commandDuration(null), 'unknown');
assert.equal(commandDuration(25), '0.025 sec');
assert.equal(commandDuration(125000), '2m05s');
assert.equal(commandDuration(125250), '≈ 2m05s');
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('title: "Recorded duration: " + (ev.ms ?? "unknown") + " ms"', page)
        self.assertIn('"aria-label": commandDuration(ev.ms)', page)

    @unittest.skipUnless(shutil.which("node"), "Node required for isolated coverage presentation fixture")
    def test_trace_coverage_is_compact_closed_complete_and_remembers_disclosure(self):
        page = trace_page.PAGE
        source = page[page.index("  function sourceCoverage() {"):page.index("\n  function render() {", page.index("  function sourceCoverage() {"))]
        script = """
const assert = require('assert');
const memory = new Map();
const store = {get: (key, fallback) => memory.has(key) ? memory.get(key) : fallback,
               set: (key, value) => memory.set(key, value)};
const num = String, observer = {}, run = {last_event: 'core-clock'};
const TRACE = {generated: 'generation-clock', story: {sources: Array.from({length: 270}, (_, n) => ({
 id: 'source-' + n, path: 'safe/source-' + n, status: n === 269 ? 'partial' : 'ok',
 message: 'Complete source message ' + n, line: n + 1, selector: 'row-' + n, sha256: 'hash-' + n,
 observed_at: 'source-observed-' + n, rows: n, omitted: n === 269 ? 2 : 0})),
 warnings: ['Torn optional tail remains pending.', 'Source warning <text> retained.']}};
function el(tag, attrs, ...children) {
 return {tag, attrs: attrs || {}, open: !!(attrs && attrs.open), children: children.flat(Infinity).filter(x => x !== null && x !== undefined),
  listeners: {}, addEventListener(kind, fn) {this.listeners[kind] = fn;}};
}
function find(node, predicate) {
 if (!node || typeof node !== 'object') return null;
 if (predicate(node)) return node;
 for (const child of node.children) {const found = find(child, predicate); if (found) return found;}
 return null;
}
function text(node, visible = false) {
 if (typeof node !== 'object' || node === null) return String(node ?? '');
 const children = visible && node.tag === 'details' && !node.open ? node.children.filter(child => child.tag === 'summary') : node.children;
 return children.map(child => text(child, visible)).join(' ');
}
""" + source + """
let root = sourceCoverage();
let detail = find(root, node => node.tag === 'details');
assert.equal(detail.open, false);
assert(text(root, true).includes('270 source records · 269 ok · 1 partial'));
assert(!text(root, true).includes('safe/source-269'));
assert(text(root).includes('Complete source message 269'));
assert(text(root).includes('safe/source-269'));
assert(text(root).includes('Source-byte SHA-256: hash-269'));
assert(text(root).includes('selector: row-269'));
assert(text(root).includes('line: 270'));
assert(text(root).includes('Source warning <text> retained.'));
assert(text(root, true).includes('2 coverage warnings'));
const clock = find(root, node => node.tag === 'dl');
assert.equal(clock.children[0].children[0].tag, 'dt');
assert.equal(clock.children[0].children[1].tag, 'dd');
assert.equal(text(clock.children[0]), 'Observer last successful read unknown');
assert.equal(text(clock.children[1]), 'Recorded run activity core-clock');
detail.open = true; detail.listeners.toggle();
root = sourceCoverage(); detail = find(root, node => node.tag === 'details');
assert.equal(detail.open, true);
detail.open = false; detail.listeners.toggle();
assert.equal(find(sourceCoverage(), node => node.tag === 'details').open, false);
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('.coverage-clocks dt', page)
        self.assertIn('.coverage-clocks dd', page)
        self.assertIn('.coverage-clocks, .coverage-records .coverage-clocks { grid-template-columns: 1fr; }', page)

    @unittest.skipUnless(shutil.which("node"), "Node required for isolated run span label fixture")
    def test_trace_run_age_and_final_recorded_span_do_not_claim_execution_duration(self):
        page = trace_page.PAGE
        source = page[page.index("  function runSpanLabel(status) {"):page.index("  function header() {")]
        script = "const assert = require('assert');\n" + source + """
for (const status of ['active', 'blocked', 'paused', 'unknown']) assert.equal(runSpanLabel(status), 'Run age at capture');
for (const status of ['done', 'halted']) assert.equal(runSpanLabel(status), 'Recorded run span');
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Wall-clock run age at capture; not measured execution duration.', page)
        self.assertIn('Recorded start to last recorded event when available; not measured execution duration.', page)
        self.assertNotIn('"elapsed " + span(run.elapsed)', page)
        self.assertIn('&& !run.last_event ? null : run.elapsed', page)
        self.assertNotIn('execution', source.lower())

    def test_navigation_is_relative_and_all_primary_previews_resolve(self):
        page = progress_render.render(story_snapshot())
        nodes = PageNodes(page)
        ids = [attrs["id"] for _, attrs in nodes.nodes if "id" in attrs]
        self.assertEqual(len(ids), len(set(ids)), "duplicate anchors")
        links = [attrs.get("href", "") for attrs in nodes.attributes("a")]
        self.assertIn("trace.html", links)
        for href in links:
            if href.startswith("#"):
                self.assertIn(href[1:], ids)
        self.assertIn('href="progress.html"', trace_page.PAGE)
        self.assertIn("link.replaceWith(note)", page)
        self.assertIn("location.protocol === \"https:\"", page)
        self.assertIn("Inspect embedded preview", page)
        self.assertIn("offline file view only", page)

    def test_visits_keep_repeats_and_source_order_with_failures_and_unknowns(self):
        page = progress_render.render(story_snapshot())
        self.assertLess(page.index("First verification visit."), page.index("Verification reopened."))
        self.assertLess(page.index("Check failed; preserve refusal."), page.index("Packet re-emitted, same bytes."))
        self.assertIn("Binding: contextual (inferred association)", page)
        self.assertIn('title="Recorded duration: 25 ms"', page)
        self.assertIn(">0.025 sec</span>", page)
        self.assertIn('title="Recorded duration: 60 s"', page)
        self.assertIn(">1 min</span> · Basis: inferred visit dwell", page)
        self.assertIn('Elapsed: <span class="duration">unknown</span> · Basis: unknown', page)
        self.assertIn("Visit dwell is not compute time", page)
        self.assertIn("Other recorded events", page)
        self.assertIn("Unbound continuation.", page)
        self.assertIn("copy is not another execution", page)
        self.assertIn("Until receipt · active", page)
        self.assertIn("Source-byte SHA-256", page)
        self.assertIn("source-hash", page)
        self.assertIn("Evidence unavailable: absent", page)
        self.assertIn("Preview missing or withheld", page)

    def test_missing_or_null_story_fields_do_not_invent_lifecycle_or_timing(self):
        data = snapshot()
        for story in (None, {}, {"summary": None, "visits": None, "events": None, "evidence": None,
                                "lifecycle": None, "observations": None, "sources": None, "warnings": None}):
            data["story"] = story
            page = progress_render.render(data)
            self.assertIn("No visit history recorded", page)
            self.assertIn("Per-source coverage unavailable", page)
            self.assertIn("No bound producer observation recorded.", page)
            self.assertIn("Not recorded.", page)
            self.assertIn("Content generated: ", page)
            self.assertNotIn("Execution</dt><dd><strong>active", page)
        data["story"] = {"visits": [{"id": "x", "events": ["not-here"]}],
                         "lifecycle": {"engine": None}, "sources": [None]}
        page = progress_render.render(data)
        self.assertIn("Event unavailable: not-here", page)
        self.assertIn('Elapsed: <span class="duration">unknown</span> · Basis: unknown', page)

    def test_lifecycle_assertions_and_observation_knowledge_times_remain_independent(self):
        page = progress_render.render(story_snapshot())
        for label, status in (("Engine", "blocked"), ("Execution", "exited"), ("Product acceptance", "unknown"),
                              ("Source return", "pending"), ("Owner hold", "held")):
            self.assertIn(label + "</dt><dd><strong>" + status, page)
        self.assertIn("Producer: fixture-harness", page)
        self.assertIn("interpretation · fixture-owner · Scope: source", page)
        self.assertIn("Event time: unknown", page)
        self.assertIn("Logged (knowledge available): 2026-09-28T11:00:00Z", page)

    def test_per_source_clocks_coverage_and_publication_failure_are_visible(self):
        data = story_snapshot()
        data["generated_at"] = "2026-09-28T10:04:00Z"
        page = progress_render.render(data)
        self.assertIn("Content generated: 2026-09-28T10:04:00Z", page)
        self.assertIn('data-last-activity-at="2026-09-28T10:02:30Z"', page)
        self.assertIn('data-observed-at="2026-09-28T10:02:00Z"', page)
        for text in ("trace · partial", "observations · stale", "Rows: 6 · Omitted: 2",
                     "Interior damaged row; incomplete tail pending.", "Trace publication: unavailable",
                     "Trace publication failed.", "Optional source unavailable."):
            self.assertIn(text, page)

    def test_story_values_are_text_and_stable_ids_do_not_depend_on_position(self):
        data = story_snapshot()
        attack = '</summary><script>alert("x")</script>'
        data["story"]["summary"]["now"] = attack
        data["story"]["evidence"][0].update(id=attack, title=attack, path=attack, selector=attack, sha256=attack)
        data["story"]["events"][1]["evidence"] = [attack]
        data["story"]["sources"][0]["message"] = attack
        first = progress_render.render(data)
        data["story"]["evidence"].reverse()
        second = progress_render.render(data)
        anchor = progress_render._anchor("evidence", attack)
        for page in (first, second):
            self.assertIn('id="' + anchor + '"', page)
            self.assertIn('href="#' + anchor + '"', page)
            self.assertIn("&lt;/summary&gt;&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", page)
            self.assertNotIn(attack, page)
            self.assertIn("connect-src 'none'", page)
            self.assertNotIn("fetch(", page)
        self.assertNotEqual(progress_render._anchor("evidence", "a:b"), progress_render._anchor("evidence", "a-b"))

    def test_terminal_watch_refresh_waits_for_explicit_observer_finality(self):
        for status in ("done", "halted"):
            data = story_snapshot()
            data["run"]["status"] = status
            data["observer"].update(mode="watch", final=False)
            pending = progress_render.render(data)
            pending_nodes = PageNodes(pending)
            root = next(attrs for _, attrs in pending_nodes.nodes if "data-progress-view" in attrs)
            toggle = next(attrs for attrs in pending_nodes.attributes("button") if attrs.get("id") == "refresh-toggle")
            self.assertEqual(root["data-mode"], "watch")
            self.assertEqual(root["data-final"], "false")
            self.assertNotIn("disabled", toggle)
            self.assertIn('id="observer-age">Observer data age:', pending)
            data["observer"]["final"] = True
            final = progress_render.render(data)
            final_toggle = next(attrs for attrs in PageNodes(final).attributes("button") if attrs.get("id") == "refresh-toggle")
            self.assertIn('data-final="true"', final)
            self.assertIn("disabled", final_toggle)
            self.assertIn("Final snapshot · updates off", tag_text(final, "button"))
            for mode in ("snapshot", "stopped"):
                data["observer"].update(mode=mode, final=False)
                page = progress_render.render(data)
                toggle = next(attrs for attrs in PageNodes(page).attributes("button") if attrs.get("id") == "refresh-toggle")
                self.assertIn("disabled", toggle)
                self.assertIn('data-mode="' + mode + '"', page)
            # Only old captures with no finality field use terminal-engine fallback.
            data["observer"] = {"mode": "watch"}
            self.assertIn('data-final="true"', progress_render.render(data))

    @unittest.skipUnless(shutil.which("node"), "Node required for isolated progress scheduler fixture")
    def test_progress_scheduler_reloads_pending_terminal_capture_then_stops_at_final(self):
        source = progress_render._SCRIPT
        allowed = source[source.index('  const autoAllowed ='):]
        allowed = allowed[:allowed.index(';') + 1]
        schedule = source[source.index('  const schedule = () => {'):source.index('  if (toggle) {')]
        script = "const assert = require('assert');\n"
        for status in ("done", "halted"):
            for mode, final, expected in (("watch", False, 1), ("watch", True, 0),
                                          ("snapshot", False, 0), ("stopped", False, 0)):
                data = story_snapshot()
                data["run"]["status"] = status
                data["observer"].update(mode=mode, final=final)
                page = progress_render.render(data)
                root = next(attrs for _, attrs in PageNodes(page).nodes if "data-progress-view" in attrs)
                script += "{ const mode = " + json.dumps(root["data-mode"]) + "; const isFinal = " + root["data-final"] + ";\n"
                script += """
let timer = null, callback = null, reloads = 0, paused = false;
const interval = 5, announce = null, setTimeout = (fn) => {callback = fn; return 1;}, clearTimeout = () => {};
const hasSelection = () => false, focusedControl = () => false, reloadPage = () => reloads++;
""" + allowed + schedule + "\nschedule(); if (callback) callback();\nassert.equal(reloads, " + str(expected) + "); }\n"
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_lifecycle_acceptance_scope_is_visible_in_the_prominent_row_and_escaped(self):
        data = story_snapshot()
        scope = 'preview fixture only <img src=x onerror="bad()">'
        data["story"]["lifecycle"]["acceptance"].update(status="pass", producer="fixture-producer", scope=scope)
        page = progress_render.render(data)
        row = page.split('Product acceptance</dt><dd>', 1)[1].split('</dd>', 1)[0]
        self.assertIn('Producer: fixture-producer · Scope: preview fixture only &lt;img', row)
        self.assertIn('onerror=&quot;bad()&quot;&gt;', row)
        self.assertNotIn('<img', row)
        data["story"]["lifecycle"]["acceptance"].pop("scope")
        page = progress_render.render(data)
        row = page.split('Product acceptance</dt><dd>', 1)[1].split('</dd>', 1)[0]
        self.assertIn('Scope: unknown (not recorded)', row)
        engine = page.split('Engine</dt><dd>', 1)[1].split('</dd>', 1)[0]
        self.assertIn('Scope: unknown (not recorded)', engine)

    def test_new_reading_controls_extend_existing_state_and_anchor_restoration(self):
        page = progress_render.render(story_snapshot())
        for text in ('query: search ? search.value : ""', 'search.value = state.query', 'filterStory();',
                     'window.addEventListener("hashchange", revealAnchor)', 'node.tagName === "DETAILS"',
                     'node = node.parentElement', 'node.hidden = false', 'hasSelection() || focusedControl()'):
            self.assertIn(text, page)
        self.assertLess(page.index('  restoreViewState();'), page.index('  revealAnchor(restoredAnchor !== location.hash);'))
        self.assertIn("@media(max-width:600px)", page)
        self.assertIn('aria-labelledby="story-heading"', page)

    @unittest.skipUnless(shutil.which("node"), "Node required for isolated refresh logic probe")
    def test_trace_scheduler_handles_blocked_pause_final_and_selection(self):
        # Execute the actual schedule function with fake clocks/DOM; no browser or timers escape.
        start = trace_page.PAGE.index("  function schedule() {")
        end = trace_page.PAGE.index("\n  render();", start)
        schedule = trace_page.PAGE[start:end]
        predicate_start = trace_page.PAGE.index("  const observerFinal =")
        predicate_end = trace_page.PAGE.index("\n\n", predicate_start)
        predicate = trace_page.PAGE[predicate_start:predicate_end]
        header_start = trace_page.PAGE.index("  function runSpanLabel(status) {")
        header_end = trace_page.PAGE.index("  function nowCard() {", header_start)
        header = trace_page.PAGE[header_start:header_end]
        script = """
const assert = require('assert');
for (const [status, mode, final, live, selection, expected] of [
 ['blocked','watch',false,true,false,1], ['active','watch',false,true,false,1],
 ['done','watch',false,true,false,1], ['halted','watch',false,true,false,1],
 ['done','watch',true,true,false,0], ['halted','watch',true,true,false,0],
 ['done','snapshot',false,true,false,0], ['halted','stopped',false,true,false,0],
 ['blocked','stopped',false,true,false,0],
 ['active',undefined,undefined,true,false,1], ['done',undefined,undefined,true,false,0],
 ['halted',undefined,undefined,true,false,0],
 ['blocked','snapshot',false,true,false,0], ['blocked','watch',true,true,false,0],
 ['blocked','watch',false,false,false,0], ['blocked','watch',false,true,true,0]]) {
 const TRACE = {generated: '2026-11-14T12:00:00Z'};
 const run = {status, traced: true, id: 'fixture-run', revision: 1, elapsed: 0, goal: 'Fixture goal'}, observer = {}, ui = {live};
 const counts = {accepted: 0, packets: 0, reprints: 0, refusals: 0, continuations: 0, skills: 0, commands: 0};
 if (mode !== undefined) observer.mode = mode;
 if (final !== undefined) observer.final = final;
 let timer = null, callback = null, reloads = 0;
 const setTimeout = (fn) => { callback = fn; return 1; }, clearTimeout = () => {};
 const document = {activeElement: null}, viewer = {classList: {contains: () => false}};
 const window = {scrollY: 9, getSelection: () => ({isCollapsed: !selection, toString: () => selection ? 'chosen' : ''})};
 const store = {set: () => {}}, location = {reload: () => reloads++};
 const num = String, when = String, span = String, ZONE = 'UTC', save = () => {};
 const el = (tag, attrs, ...children) => ({tag, attrs: attrs || {}, children: children.flat(Infinity)});
 const flatten = node => !node || typeof node !== 'object' ? String(node ?? '') : node.children.map(flatten).join('');
 const find = (node, tag) => node && typeof node === 'object' && (node.tag === tag ? node : node.children.map(child => find(child, tag)).find(Boolean));
""" + predicate + schedule + header + """
 schedule();
 if (callback) callback();
 assert.equal(reloads, expected, JSON.stringify({status, mode, final, live, selection}));
 const control = find(header(), 'label');
 assert.equal(!!control, watchable);
 if (control) {
   assert.equal(flatten(control).trim(), 'watch display (reload every 10 s)');
   const checkbox = find(control, 'input');
   assert.equal(checkbox.attrs.checked, live);
   checkbox.attrs.onchange({target: {checked: false}});
   assert.equal(ui.live, false);
 }
}
"""
        result = subprocess.run([shutil.which("node"), "-e", script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Watching this display does not establish execution", trace_page.PAGE)


if __name__ == "__main__":
    unittest.main()
