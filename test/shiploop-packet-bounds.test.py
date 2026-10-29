#!/usr/bin/env python3
"""Large-context recovery checks; synthetic results, no Improve execution."""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/shiploop/scripts"
sys.path.insert(0, str(SCRIPTS))
import shiploop_fields as fields  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


class PacketBoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-packet-bounds-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.run = self.repo / "run"
        self.run.mkdir()

    def state(self, prompt="Implement the requested behavior."):
        # Bounds were measured on the delegated route's longer packets.
        return navigator.new_state(str(self.repo), prompt,
                                   delegation="ask-agent")

    def complete(self, state, **extra):
        action = navigator.current_action(state)
        waiting = navigator.apply(state, action["id"], {
            "outcome": "done", "summary": "Synthetic packet fixture", **extra,
        })
        if waiting.get("active_improve") is None:
            return waiting
        return navigator.finish_improve(waiting, action["id"], {
            "summary": "Synthetic review; no semantic claim", "lessons": "Read relevant references.",
        })

    def cold_packet(self, state):
        path = self.run / "state.md"
        store.write_record(path, state)
        before = path.read_bytes()
        cold = store.read_record(path)
        packet = navigator.render(None, self.run, cold)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(cold, state)
        return packet

    def test_large_work_context_is_recoverable_without_copying_it_into_packet(self):
        state = self.state()
        long_context = "c" * 2_000_000 + "REQUIRED_CONTEXT_TAIL"
        long_title = "t" * 100_000 + "TITLE_TAIL"
        while navigator.current_stage(state) != "step-plan":
            extra = {}
            if navigator.current_stage(state) == "plan":
                extra["work_items"] = [{"id": "W1", "title": long_title, "context": long_context}]
            state = self.complete(state, **extra)
        packet = self.cold_packet(state)
        self.assertNotIn(long_context, packet)
        self.assertIn("Full value: RUN/state.md; field work_items[0].context", packet)  # RUN is defined by the References block
        self.assertIn("work_items[0].context", packet)
        self.assertIn("work_items[0].title", packet)
        self.assertIn("Read the complete required context before acting", packet)
        self.assertEqual(state["work_items"][0]["context"], long_context)
        self.assertIn(navigator.current_action(state)["id"], packet)

    def test_large_original_request_retains_full_scope_in_durable_field(self):
        request = "r" * 2_000_000 + "KEEP_THIS_USER_CONSTRAINT"
        state = self.state(request)
        packet = self.cold_packet(state)
        self.assertNotIn(request, packet)
        self.assertIn("field prompt", packet)
        self.assertEqual(state["prompt"], request)

    def test_large_pending_result_uses_exact_seed_locator_and_same_callback(self):
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)
        summary = "s" * 2_000_000 + "SEED_CONSTRAINT_TAIL"
        waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": summary})
        self.assertIsNotNone(waiting.get("active_improve"))
        packet = self.cold_packet(waiting)
        # Packet re-cut (2026-10-11): the Improve packet is two instructions; the seed result and its exact locator
        # are in the handoff file ShipLoop writes (navigator.improve_handoff_text).
        handoff = navigator.improve_handoff_text(None, self.run, waiting)
        self.assertIn("active_improve.seed_result", handoff)
        self.assertIn("Outcome: done", handoff)
        self.assertIn(action["id"], handoff)
        self.assertNotIn(summary, handoff)
        self.assertNotIn(summary, packet)
        # The Improve stage has its own action id (2026-10-11): the packet's callback names it, not the producer's.
        self.assertIn(navigator.improve_id(waiting), packet)
        self.assertNotIn(action["id"], packet)
        self.assertNotIn("active_improve.seed_result", packet)
        self.assertEqual(waiting["active_improve"]["seed_result"]["summary"], summary)

    def test_many_long_evidence_references_keep_full_record_and_bound_packet(self):
        refs = [f"evidence/{index}/" + "x" * 1000 for index in range(1000)]
        state = self.complete(self.state(), evidence_refs=refs)
        action = state["history"][-1]["action"]
        packet = self.cold_packet(state)
        self.assertIn(f"accepted.{action}.evidence_refs", packet)
        self.assertEqual(state["accepted"][action]["evidence_refs"], refs)

    def test_short_context_and_request_still_render_in_full(self):
        state = self.state("Keep the exact short user request.")
        packet = self.cold_packet(state)
        self.assertIn(state["prompt"], packet)
        self.assertNotIn("Read the complete required context before acting", packet)

    def test_large_block_reason_keeps_resume_route(self):
        state = navigator.control(self.state(), "pause", reason="b" * 2_000_000 + "REASON_TAIL")
        packet = self.cold_packet(state)
        self.assertIn("status_reason", packet)
        self.assertIn("Resume:", packet)

    def test_a_long_paused_packet_prints_within_the_host_output_limit(self):
        """X11 (e12_head_size.py): paused, halted and blocked packets printed whole past ~20 KB."""
        import contextlib, io
        from unittest import mock
        state = navigator.control(self.state(), "pause", reason="user asked")
        store.write_record(self.run / "state.md", state)
        for text, whole in (("short packet\n", True), (("x" * 60 + "\n") * 1000 + "TAIL\n", False)):
            with self.subTest(whole=whole), mock.patch.object(navigator, "render", return_value=text):
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed):
                    navigator.emit(None, self.run, state)
                self.assertTrue(printed.getvalue().endswith("\n" + navigator.HEAD_END + "\n"))
                if whole:
                    self.assertEqual(printed.getvalue(), text + navigator.HEAD_END + "\n")
                else:
                    self.assertLessEqual(len(printed.getvalue()), navigator.PRINT_LIMIT)
                    self.assertIn("Full packet: " + str(navigator.packet_path(self.run, state)), printed.getvalue())
                self.assertEqual(navigator.packet_path(self.run, state).read_text(), text)

    def test_an_improve_printing_does_not_overwrite_the_producer_packet_that_was_sent(self):
        """A reviewed stage printed its producer packet and then the Improve child's at the same path, so after a run the
        producer packet of spec, test-strategy, plan, step-plan and test-spec could not be audited (10 of 46 visits)."""
        import contextlib, io
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)["id"]
        store.write_record(self.run / "state.md", state)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, state)
        producer = navigator.packet_path(self.run, state)
        sent = producer.read_text()
        waiting = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic packet fixture"})
        self.assertIsNotNone(waiting.get("active_improve"))
        store.write_record(self.run / "state.md", waiting)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, waiting)
        improve = navigator.packet_path(self.run, waiting)
        self.assertNotEqual(improve, producer)
        self.assertEqual(producer.name, action + ".md")
        self.assertEqual(improve.name, navigator.improve_id(waiting) + "-bind.md")  # no card is bound yet: the bind packet
        self.assertEqual(producer.read_text(), sent)
        self.assertIn("Current action: Improve the completed spec result.",
                      navigator.improve_handoff_text(None, self.run, waiting))  # the handoff holds the detail (re-cut)

    def test_the_improve_bind_packet_keeps_its_own_file_when_improve_start_prints(self):
        """An Improve child prints two packets before the runtime starts: improve-bind (no card bound yet) and, once bound,
        the improve packet. Both went to <action>-improve.md, so the bind packet was lost on disk and could not be reviewed
        (packet compaction plan 2026-10-10, Phase 0; the producer-packet fix before it is 897733cb)."""
        import contextlib, io
        state = self.state()
        while navigator.current_stage(state) != "spec":
            state = self.complete(state)
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic packet fixture"})
        child = waiting["active_improve"]
        self.assertIsNone(child["skill"])
        store.write_record(self.run / "state.md", waiting)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, waiting)
        bind = navigator.packet_path(self.run, waiting)
        sent = bind.read_text()
        self.assertIn("improve-bind", sent)
        bound = dict(waiting)
        bound["active_improve"] = bridge.binding(waiting, action, navigator.current_stage(waiting),
                                                 child["seed_result"],
                                                 bridge.resolve_skill(str(ROOT / "skills/improve/SKILL.md")),
                                                 improve_action=child["improve_action"])
        navigator.validate(bound)
        store.write_record(self.run / "state.md", bound)
        with contextlib.redirect_stdout(io.StringIO()):
            navigator.emit(None, self.run, bound)
        start = navigator.packet_path(self.run, bound)
        self.assertNotEqual(start, bind)
        self.assertEqual(start.name, navigator.improve_id(bound) + ".md")
        self.assertEqual(bind.name, navigator.improve_id(waiting) + "-bind.md")
        self.assertEqual(bind.read_text(), sent)
        # Bound at the transition or by hand, the first packet is the two instructions: run the improve skill, then
        # improve-complete; there is no improve-bind step left in it (packet re-cut, 2026-10-11).
        started = start.read_text()
        self.assertIn("       ShipLoop Improve: " + str(navigator.improve_handoff_path(bound["active_improve"])), started)
        self.assertIn(" complete --run-dir=", started)
        self.assertIn("--action=" + navigator.improve_id(bound), started)
        self.assertNotIn("improve-complete", started)
        self.assertNotIn("improve-bind", started)
        # This state was bound by hand with no start behind it, so the packet may name the one route that works,
        # improve-start --restart-stopped; no other improve-start form (such as --opening) exists any more.
        self.assertTrue(all("--restart-stopped" in line for line in re.findall(r"improve-start[^\n]*", started)))

    def test_oversized_delivery_template_is_not_truncated_into_invalid_json(self):
        state = navigator.new_state(str(self.repo), "Observe local behavior.", delivery_contract=True)
        while navigator.current_stage(state) != "plan":
            state = self.complete(state)
        contract = {
            "consumer": "local CLI", "target": "local target", "behavior": "expected output",
            "candidate": "c" * 100_000, "operation": "local checks", "necessity": "not-required",
            "basis": "Explicit local-only request", "exclusions": [],
            "authority": {"status": "not-required", "kind": "request", "reference": "Local-only",
                          "target": "local target", "operation": "local checks"},
            "obligations": [{"id": "pre", "consumer": "local CLI", "target": "local target",
                             "kind": "pre-update", "phase": "system-test",
                             "expected": "Current local checks pass", "required": True},
                            {"id": "behavior", "consumer": "local CLI", "target": "local target",
                             "kind": "behavior", "phase": "release-verify",
                             "expected": "Observed output matches request", "required": True}],
        }
        state = self.complete(state, delivery_assessment={"kind": "contract", "contract": contract})
        while navigator.current_stage(state) != "system-test":
            state = self.complete(state)
        packet = self.cold_packet(state)
        self.assertIn("accepted (delivery_assessment records in history order)", packet)
        self.assertIn("does not waive any required observation", packet)
        result_text = packet.split("Result template:\n", 1)[1].split("\nCall this when done:", 1)[0]
        # The minimal fallback keeps the placeholder the script refuses, never
        # an empty list a worker could copy verbatim.
        self.assertEqual(store.loads(result_text), {"outcome": "done", "headline": navigator.HEADLINE_PLACEHOLDER,
                                                    "summary": "...",
                                                    "evidence_refs": [navigator.EVIDENCE_PLACEHOLDER]})
        self.assertIn(navigator.current_action(state)["id"], packet)


class FieldSpillTests(unittest.TestCase):
    """Plan F2: a required block prints a model-written field whole within its print budget, else what fits and the run
    file that holds it whole.  Nothing refuses a field for its length."""

    def test_a_field_that_fits_prints_whole_and_writes_no_file(self):
        self.assertEqual(fields.inline("Build it.", 700, "a", "S1-task"), fields.Shown(["Build it."], None))
        self.assertEqual(fields.block(["one", "two"], 7, 7, "a", "W1-concerns"), fields.Shown(["one", "two"], None))
        self.assertEqual(fields.path("step-plan-W1", "S1-task"), "fields/step-plan-W1-S1-task.md")

    def test_a_long_inline_field_prints_its_first_line_cut_and_names_the_file_holding_it_whole(self):
        text = "First line of the task.\n" + "detail " * 200
        shown = fields.inline(text, 40, "plan-1", "S1-task")
        self.assertEqual(len(shown.lines), 1)
        self.assertTrue(shown.lines[0].startswith("First line of the task."))
        self.assertIn("RUN/fields/plan-1-S1-task.md holds all " + f"{len(text):,}" + " characters", shown.lines[0])
        self.assertEqual(shown.file, ("fields/plan-1-S1-task.md", text.strip("\n") + "\n"))

    def test_a_long_block_prints_its_leading_lines_and_names_the_file_holding_every_line(self):
        lines = ["  row " + str(n) + " " + "r" * 40 for n in range(30)]
        size = len("\n".join(lines))
        shown = fields.block(lines, size, 300, "plan-1", "W1-concerns", indent="  ")
        printed, tail = shown.lines[:-1], shown.lines[-1]
        self.assertEqual(printed, lines[:len(printed)])
        self.assertTrue(0 < len(printed) < len(lines))
        self.assertIn("RUN/fields/plan-1-W1-concerns.md holds all 30 whole", tail)
        self.assertIn(f"{len(lines) - len(printed)} more lines not printed here", tail)
        self.assertEqual(shown.file, ("fields/plan-1-W1-concerns.md", "\n".join(lines) + "\n"))

    def test_the_first_line_of_a_block_is_cut_to_the_budget_when_it_alone_passes_it(self):
        shown = fields.block(["x" * 500, "y"], 501, 100, "a", "f")
        self.assertLessEqual(len(shown.lines[0]), 100)
        self.assertTrue(shown.lines[0].endswith("\u2026"))
        self.assertEqual(shown.file[1], "x" * 500 + "\ny\n")

    def test_a_multi_line_field_over_its_budget_prints_the_start_of_all_of_it_not_just_its_first_line(self):
        task = "Implement the loader:\n" + "\n".join("- bullet " + str(n) + " " + "w" * 40 for n in range(30))
        shown = fields.inline(task, 300, "plan-1", "S1-task")
        line = shown.lines[0]
        self.assertIn("- bullet 0", line)          # the second line of the field is printed too
        self.assertLessEqual(len(line.split(" (cut here:")[0]), 300)
        self.assertEqual(shown.file, ("fields/plan-1-S1-task.md", task + "\n"))

    def test_a_field_of_only_whitespace_over_its_budget_does_not_raise(self):
        shown = fields.inline("\n   \n" + " " * 50, 10, "plan-1", "S1-task")
        self.assertEqual(len(shown.lines), 1)
        self.assertIsNotNone(shown.file)

    def test_a_block_whose_label_alone_fits_still_prints_some_of_its_first_row(self):
        row = "  C1: " + "criterion text " * 100
        shown = fields.block(["  Serves (criteria):", row], len(row), 200, "plan-1", "S1-criteria", indent="    ", header=1)
        self.assertEqual(shown.lines[0], "  Serves (criteria):")
        self.assertTrue(shown.lines[1].startswith("  C1: criterion text"))
        self.assertLessEqual(len(shown.lines[1]), max(200, fields.MIN_SHOWN_CHARS))
        self.assertIn("RUN/fields/plan-1-S1-criteria.md holds all 2 whole", shown.lines[-1])
        self.assertEqual(shown.file[1], "\n".join(["  Serves (criteria):", row]) + "\n")

    def test_a_name_that_is_a_path_or_too_long_becomes_one_safe_component(self):
        for name in ("S1/../../../../outside", "S" * 230, "S1\0x", "..", "", ".hidden", "q/../nav-1-S1", "\u00e9"):
            with self.subTest(name=name[:20]):
                part = fields.component(name)
                self.assertTrue(part and "/" not in part and "\0" not in part and not part.startswith("."), part)
                self.assertLessEqual(len(part), fields.COMPONENT_MAX)
                relative = fields.path("nav-1", name + "-task")
                self.assertEqual(relative.count("/"), 1, relative)
                self.assertTrue(relative.startswith("fields/") and relative.endswith(".md"))
        self.assertEqual(fields.component("S1-task"), "S1-task")      # a safe name is kept as it is
        self.assertNotEqual(fields.component("a/b"), fields.component("a_b"))   # two names never share a file


# Every numeric limit in skills/shiploop/scripts, by kind (plan F2).  A "print budget" is the size up to which a required
# block prints a model-written field by value; past it the block prints what fits and the field's RUN/fields file holds
# it whole.  A "display cut" shortens what a reader sees and says where the rest is.  A "guard" protects a reader from a
# runaway or binary file.  No kind is a refusal of the model's own text: the gates accept a field of any length.
LIMIT_KINDS = {
    "shiploop_concerns.ROWS_PRINT": "print budget",
    "shiploop_fields.MIN_SHOWN_CHARS": "display cut",
    "shiploop_fields.COMPONENT_MAX": "guard",
    "shiploop_navigator.STEP_TASK_PRINT": "print budget",
    "shiploop_navigator.STEP_PROOF_PRINT": "print budget",
    "shiploop_navigator.STEP_CRITERIA_PRINT": "print budget",
    "shiploop_test_layers.LINES_PRINT": "print budget",
    "shiploop_context_index.SUMMARY_LIMIT": "display cut",
    "shiploop_expectations.OUTPUT_LIMIT": "display cut",
    "shiploop_lint.PAGE_BYTES": "display cut",
    "shiploop_narrative.NARRATIVE_LIMIT": "display cut",
    "shiploop_navigator.PRINT_LIMIT": "display cut",
    "shiploop_navigator.HEAD_LIMIT": "display cut",
    "shiploop_navigator.HEADLINE_SHOWN": "display cut",
    "shiploop_navigator._REQUIREMENT_LINE_LIMIT": "display cut",
    "shiploop_navigator._CONTENTS_LINES": "display cut",
    "shiploop_owner_notes.NOTE_LIMIT": "display cut",
    "shiploop_owner_notes.BLOCK_LIMIT": "display cut",
    "shiploop_protocol.OUTPUT_LIMIT": "display cut",
    "shiploop_skill_calls.ARGS_LIMIT": "display cut",
    "shiploop_test_counts.INSIDE_CHARS": "display cut",
    "shiploop_test_loop.TAIL_CHARS": "display cut",
    "shiploop_trace.TEXT_LIMIT": "display cut",
    "shiploop_trace.PAGE_PACKET_LIMIT": "display cut",
    "shiploop_trace.FIELD_LIMIT": "display cut",
    "shiploop_trace.ANSWER_LIMIT": "display cut",
    "shiploop_lint.MAX_FILE_BYTES": "guard",
    "shiploop_lint.DIFF_CELL_CAP": "guard",
    "shiploop_mutation.MAX_FILE_BYTES": "guard",
    "shiploop_planning_revision._MAX_ARCHIVE_BYTES": "guard",
    "shiploop_progress_data._MAX_STATE_BYTES": "guard",
    "shiploop_progress_data._MAX_DOCUMENT_BYTES": "guard",
    "shiploop_progress_data._MAX_REPORT_BYTES": "guard",
    "shiploop_standalone_improve._MAX_BYTES": "guard",
    "shiploop_trace.TRACE_LIMIT": "guard",
    "shiploop_trace.PAGE_TEXT_LIMIT": "guard",
    "shiploop_trace.SPEC_LIMIT": "guard",
}
_LIMIT_NAME = re.compile(r"(LIMIT|CAP|MAX|PRINT|SHOWN|CHARS|BYTES|BUDGET|ROWS|LINES|WIDTH|PAGE|TAIL|HEAD|SIZE|DEPTH|COUNT)$")


def _number(node):
    """The number a constant expression holds (a literal, or literals joined by * + - **), else None."""
    try:
        value = ast.literal_eval(node)
    except Exception:
        value = None
    if isinstance(node, ast.BinOp):
        left, right = _number(node.left), _number(node.right)
        if left is not None and right is not None:
            value = {ast.Mult: lambda: left * right, ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                     ast.Pow: lambda: left ** right}.get(type(node.op), lambda: None)()
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def numeric_limits():
    """``{module.NAME: value}`` for every module-level size constant of 20 or more in the shiploop scripts."""
    found = {}
    for path in sorted(SCRIPTS.glob("shiploop_*.py")):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            targets = (node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AnnAssign)
                       and node.value is not None else [])
            value = _number(node.value) if targets else None
            for target in targets:
                if isinstance(target, ast.Name) and target.id.isupper() or (
                        isinstance(target, ast.Name) and target.id.lstrip("_").isupper()):
                    if value is not None and value >= 20 and _LIMIT_NAME.search(target.id):
                        found[path.stem + "." + target.id] = value
    return found


# Inline length checks against a literal of 80 or more, which a scan of module constants cannot see.  Each is a display route
# (the text goes to a file or is cut, never refused), not a refusal of the model's text.
INLINE_LENGTH_CHECKS = {
    ("shiploop_navigator.py", 6000): "a result template or an Improve seed too long to print inline goes to the file that holds it",
    ("shiploop_progress_data.py", 280): "the progress view cuts an event summary",
    ("shiploop_trace.py", 160): "the trace cuts a headline",
}


def inline_length_checks():
    """``{(module file, literal): count}`` for each ``len(x) > N`` style comparison with a literal N of 80 or more."""
    found = {}
    for path in sorted(SCRIPTS.glob("shiploop_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and isinstance(node.left, ast.Call) and getattr(node.left.func, "id", "") == "len":
                for op, comparator in zip(node.ops, node.comparators):
                    if (isinstance(comparator, ast.Constant) and isinstance(comparator.value, int)
                            and not isinstance(comparator.value, bool) and comparator.value >= 80
                            and isinstance(op, (ast.Gt, ast.GtE, ast.Lt, ast.LtE))):
                        key = (path.name, comparator.value)
                        found[key] = found.get(key, 0) + 1
    return found


class SizeLimitInventoryTests(unittest.TestCase):
    """Plan F2 done-when: every numeric limit has a kind, and a new refusing cap on model text fails here."""

    def test_every_numeric_limit_in_the_scripts_has_a_kind(self):
        found = numeric_limits()
        self.assertEqual(sorted(set(found) - set(LIMIT_KINDS)), [],
                         "a new size constant: add it to LIMIT_KINDS as a print budget (a field spills to a RUN/fields "
                         "file past it), a display cut (the cut names the rest) or a guard (a runaway file); never as "
                         "a limit the gates refuse the model's own text for")
        self.assertEqual(sorted(set(LIMIT_KINDS) - set(found)), [], "a limit left LIMIT_KINDS stale: remove its row")

    def test_no_inline_length_check_is_a_new_cap(self):
        """A cap written inline (``if len(text) > 700:``) escapes the constant scan; each one is listed with its reason."""
        self.assertEqual(sorted(set(inline_length_checks()) - set(INLINE_LENGTH_CHECKS)), [],
                         "a new inline length check: if it refuses the model's text for its length, spill the text to a "
                         "RUN/fields file instead (shiploop_fields); if it is a display route, list it in INLINE_LENGTH_CHECKS")
        self.assertEqual(sorted(set(INLINE_LENGTH_CHECKS) - set(inline_length_checks())), [], "remove the stale row")

    def test_no_gate_refuses_the_models_text_for_its_length(self):
        """The refusals the D7 before-runs counted (3-5 per run) stated the size and a limit; none remains."""
        phrases = re.compile(r"the limit is|keep it within|characters? (?:together|long); (?:the )?limit|passes the limit")
        offenders = []
        for path in sorted(SCRIPTS.glob("shiploop_*.py")):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and phrases.search(node.value):
                    offenders.append(path.name + ":" + str(node.lineno) + " " + node.value[:80])
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
