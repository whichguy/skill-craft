#!/usr/bin/env python3
"""Main tenet (README top, SPEC S-6): every packet stands alone, because the context may be cleared between any two stages.

A model holding only the next packet must find, in that packet: what the stage is for, how it operates, how its result is
checked or reviewed, what it must produce, and how to recover.  This renders the real packet of every stage, and the
Improve-phase packet of every stage whose result starts an Improve child, from a cold read of ``state.md`` (what a cleared
model sees), and checks each for the five.  Synthetic results; no model, no Improve execution.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_assumptions as assumptions  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_test_counts as test_counts  # noqa: E402
import shiploop_test_loop as test_loop  # noqa: E402


# Declared here, not read from the engine: the producers whose packet restates the Improve child's review focus
# (packet review 2026-10-10, row 9).
FOCUS_STAGES = ("spec", "test-strategy")


def packets(planning_review: str = "stage", state_out: "dict | None" = None) -> dict:
    """{(stage, 'producer' | 'improve'): the packet text a cleared model would read}.

    ``state_out``, when given, receives the run's final state, whose ``repo``, ``prompt`` and ``run_id`` name the paths
    the packets print (the repository itself is gone when this returns).
    """
    with tempfile.TemporaryDirectory(prefix="shiploop-packet-completeness-") as temp:
        repo = Path(temp)
        run = repo / "run"
        run.mkdir()
        state = navigator.new_state(str(repo), "Build a thing.", delegation="inline", planning_review=planning_review)
        found = {}

        def cold(current):
            store.write_record(run / "state.md", current)
            return navigator.render(None, run, store.read_record(run / "state.md"))

        for _ in range(120):
            if state["status"] != "active":
                break
            stage = navigator.current_stage(state)
            action = navigator.current_action(state)
            found.setdefault((stage, "producer"), cold(state))
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "one", "context": "context"}]
            if stage == "step-plan":
                extra["test_commands"] = [{"command": "python3 -m unittest", "suite": "focused"}]
            waiting = navigator.apply(state, action["id"], {"outcome": "done", "summary": "Synthetic", **extra})
            if waiting.get("active_improve") is not None:
                found.setdefault((stage, "improve"), cold(waiting))
                waiting = navigator.finish_improve(waiting, action["id"], {"summary": "Synthetic review", "lessons": "x"})
            state = waiting
        if state_out is not None:
            state_out.update(state)
        return found


class PacketCompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.found = packets()

    def test_every_stage_has_a_packet_and_every_reviewed_stage_has_an_improve_packet(self) -> None:
        stages = {stage for stage, kind in self.found if kind == "producer"}
        self.assertEqual(stages, set(stage_spec.STAGE_SPEC))
        reviewed = {stage for stage, kind in self.found if kind == "improve"}
        self.assertEqual(reviewed, set(stage_spec.reviewed_stages("stage")) | {"carry-forward"})

    def test_a_producer_packet_states_purpose_operation_check_output_and_recovery(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "producer":
                continue
            flat = " ".join(packet.split())
            duty = " ".join(prompts.DUTIES[stage].split())[:60]
            with self.subTest(stage):
                self.assertIn("Goal: ", packet)                       # what the stage is for
                self.assertIn("Done when", packet)
                self.assertIn(duty, flat)                             # how the stage operates
                self.assertIn("Checked by: ", packet)                 # how the result is checked
                self.assertIn("Result template", packet)             # what it must produce
                self.assertIn("Write the structured result to: ", packet)
                self.assertIn("Recovery", packet)                    # how to recover

    def test_an_improve_packet_states_purpose_operation_check_output_and_recovery(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "improve":
                continue
            with self.subTest(stage):
                self.assertIn("Current action: Improve the completed " + stage + " result.", packet)  # purpose
                row = stage_spec.stage(stage)                         # what the review judges the result against
                self.assertIn("Goal: " + row.goal[0].upper() + row.goal[1:] + ".", packet)
                for condition in row.done_when:
                    self.assertIn("- " + condition, packet)
                self.assertIn("Load the actual Improve skill", packet)  # how it operates: the selected skill runs the review
                line = next((line for line in packet.splitlines() if line.startswith("Checked by: ")), "")
                self.assertIn("improve-complete", line)               # what it produces and how that is checked
                self.assertIn("Recovery", packet)

    def test_a_reviewed_producer_says_its_done_when_is_what_the_review_checks(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind == "producer" and stage in stage_spec.reviewed_stages("stage") \
                    and stage not in FOCUS_STAGES:
                with self.subTest(stage):
                    self.assertIn("That review checks the result against the Done-when conditions above.", packet)

    def test_a_producer_names_the_script_checks_its_stage_row_declares(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "producer":
                continue
            row = stage_spec.stage(stage)
            line = next(line for line in packet.splitlines() if line.startswith("Checked by: "))
            with self.subTest(stage):
                if row.complete_runs:
                    self.assertNotIn("nothing automatic", line)
                else:
                    self.assertIn("you confirm each Done-when condition", line)

    # Declared here, not read from the navigator: the words a stage's Checked-by line must carry because its gate
    # exists, and the only stages that may carry them.  test/shiploop-callback-contract.test.py pairs each named fault
    # with the real refusal and an accepted correction (the step plan's skill_na fault there, the document stage's in
    # test/shiploop-test-loop.test.py, which drives that stage's gate against a real diff).  The document stage names
    # skill_na only once the step plan recorded it (these synthetic plans record none), so it is absent here.
    GATE_WORDS = {
        "assumption": {"plan"},
        "criterion": {"step-plan"},
        "deps": {"step-plan"},
        "skill_na": {"step-plan"},
        "system_commands": {"system-test-author"},
        "consumer_checks": {"release-plan"},
        "consumer_entry": {"release-plan"},
        "docs/shiploop": {"prepare", "test-spec", "release-plan"},
        "unverified": {"product-acceptance"},
        "due_stage": {"product-acceptance"},
    }

    def test_a_producer_without_a_script_run_check_names_the_faults_complete_refuses(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            row = stage_spec.stage(stage)
            if kind != "producer" or row.complete_runs:
                continue
            lines = [line for line in packet.splitlines() if line.startswith("Checked by: ")]
            with self.subTest(stage):
                self.assertEqual(len(lines), 1)  # one line: shiploop-keepalive requires the head's lines to be one each
                line = lines[0]
                self.assertNotIn("nothing automatic", line)
                self.assertIn("ShipLoop refuses a result with a mechanical fault", line)
                self.assertIn("refusal does not advance the run", line)
                self.assertIn("run the same complete command again", line)
                self.assertIn("does not judge the work", line)
                # Claims no wider than the gates: relative evidence paths are not checked, and the credential screen is
                # conservative, not a guarantee.
                self.assertIn("absolute", line)
                self.assertIn("explicit credential pattern", line)
                for word, stages in self.GATE_WORDS.items():
                    self.assertEqual(word in line, stage in stages, f"{word!r} in the {stage} line")


def flat(text: str) -> str:
    return " ".join(text.split())


def template_of(packet: str) -> dict:
    """The JSON the producer packet prints under "Result template:"."""
    return store.loads(packet.split("Result template:\n", 1)[1].split("\nAllowed outcomes:", 1)[0])


class ObservedHarmPacketTests(unittest.TestCase):
    """Packet review 2026-10-10, rows 2, 6, 7, 9, 10 and 11: each fix is pinned to the engine fact it states.

    The rendered packet is compared with the gate or constant the sentence describes (the suite list, the assumption
    fields, the review focus, the files a close refuses), so a sentence cannot drift from the rule it names.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.state: dict = {}
        cls.found = packets(state_out=cls.state)
        cls.none = packets("none")

    # row 6: the step plan's template carried a README example that real outputs copied into products nobody asked for.
    def test_a_result_template_prints_placeholders_not_product_content(self) -> None:
        for (stage, kind), packet in sorted(self.found.items()):
            if kind != "producer":
                continue
            text = json.dumps(template_of(packet))
            with self.subTest(stage):
                self.assertNotRegex(text, r"(?i)readme")
                self.assertNotRegex(text, r"[\w-]+\.(md|txt|py|js|json|html)\b")

    # row 7: the step plan declares the ids; test-spec titles its cases with them; check is a suite.
    def test_the_step_plan_declares_ids_it_will_title_and_names_every_suite(self) -> None:
        text = flat(self.found[("step-plan", "producer")])
        self.assertIn("`ids` you will title the cases with", text)
        self.assertNotIn("of the test-spec cases", text)
        self.assertIn(" | ".join('"' + suite + '"' for suite in test_loop.SUITES), text)

    def test_test_spec_titles_each_case_with_the_declared_ids_and_says_where_the_cases_go(self) -> None:
        text = flat(self.found[("test-spec", "producer")])
        self.assertIn("Title each case with the ids in the step plan's `test_commands`", text)
        self.assertIn("one entry per case in test-spec.md: id, setup, action, independent oracle, RED, GREEN", text)

    # row 2: a check row carries no ids or min_tests (shiploop-callback-contract pairs the refusal with its correction).
    def test_the_stages_that_record_commands_say_a_check_row_carries_no_ids_or_min_tests(self) -> None:
        for stage in ("step-plan", "system-test-author", "release-plan"):
            with self.subTest(stage):
                self.assertIn("a check row carries no ids or min_tests", flat(self.found[(stage, "producer")]))

    def test_a_template_check_row_carries_no_ids_or_min_tests(self) -> None:
        for stage, field in (("step-plan", "test_commands"), ("system-test-author", "system_commands"),
                             ("release-plan", "consumer_checks")):
            rows = [row for row in template_of(self.found[(stage, "producer")])[field] if row["suite"] == "check"]
            with self.subTest(stage):
                self.assertTrue(rows)
                for row in rows:
                    self.assertFalse({"ids", "min_tests"} & set(row))

    # row 9: the producer packet restates how its result is reviewed (S-6), from the same text the child applies.
    def test_a_producer_restates_the_review_focus_its_improve_child_applies(self) -> None:
        bullets = [flat(line) for line in prompts.PLANNING_REVIEW_FOCUS.splitlines() if line.startswith("- ")]
        self.assertGreaterEqual(len(bullets), 5)
        for stage in FOCUS_STAGES:
            producer = flat(self.found[(stage, "producer")])
            with self.subTest(stage):
                # The child prints PLANNING_REVIEW_FOCUS at every stage in PLANNING_REVIEW_STAGES (after improve-bind,
                # which the cold packet of an unbound child does not yet show).
                self.assertIn(stage, prompts.PLANNING_REVIEW_STAGES)
                for bullet in bullets:
                    self.assertIn(bullet, producer)
                self.assertIn("That review applies the Planning review focus in this stage's guidance and checks "
                              "the result against the Done-when conditions above.", producer)

    def test_without_an_improve_child_the_focus_is_still_a_checklist_and_no_review_is_promised(self) -> None:
        for stage in FOCUS_STAGES:
            text = flat(self.none[(stage, "producer")])
            with self.subTest(stage):
                self.assertIn("no Improve child reviews this result in this run", text)
                self.assertNotIn("the Improve child applies these conditions", text)
                self.assertNotIn("That review applies", text)
                self.assertNotIn((stage, "improve"), self.none)

    # row 10: the whole-word rule the later gate enforces, and the either/or for a UI the request names.
    def test_test_strategy_states_the_whole_word_id_rule_the_gate_enforces(self) -> None:
        self.assertIn(flat(prompts.ID_WORD_RULE), flat(self.found[("test-strategy", "producer")]))
        # The rule is the gate's: TC-4a does not show TC-4, and TC-4 (a) does.
        self.assertEqual(test_counts.named("ok TC-4a works\n", ["TC-4"])["missing"], ["TC-4"])
        self.assertEqual(test_counts.named("ok TC-4 (a) works\n", ["TC-4"])["shown"], ["TC-4"])

    def test_test_strategy_makes_a_ui_the_request_names_either_a_browser_case_or_a_recorded_unverified_outcome(self) -> None:
        text = flat(self.found[("test-strategy", "producer")])
        self.assertIn("When the request names a page or screen people use", text)
        self.assertIn("either a case that drives it in a browser", text)
        self.assertIn("or the outcome recorded as unverified with its owner and due stage", text)

    # row 11a: an assumption takes exactly the printed fields.
    def test_the_plan_says_each_assumption_takes_exactly_the_printed_fields_and_a_plan_consumer(self) -> None:
        text = flat(self.found[("plan", "producer")])
        self.assertIn("takes exactly the fields printed in the template for its disposition", text)
        for disposition, fields in assumptions._FIELDS.items():
            names = ", ".join("`" + name + "`" for name in sorted(fields))
            with self.subTest(disposition):
                self.assertIn(disposition + ": " + names, text)
        self.assertIn("ShipLoop refuses any extra key", text)
        self.assertIn("`consumer` must be the id of a work item in this plan", text)

    # row 11b: a file written before a close names the close that refuses without it, taken from the gate itself.
    def refusals(self) -> dict:
        """{close: absolute paths the real gate asks for when nothing is written}, on an empty repository."""
        with tempfile.TemporaryDirectory(prefix="shiploop-knowledge-gate-") as temp:
            repo = Path(temp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
            state = dict(self.state, repo=str(repo))
            found = {}
            for close in knowledge.CLOSES:
                reply = knowledge.check(state, close)
                found[close] = [str(Path(self.state["repo"]) / Path(line[2:]).relative_to(repo))
                                for line in reply.splitlines() if line.startswith("- /")]
            return found

    def test_a_file_a_later_close_requires_names_that_close_in_the_stage_that_writes_it(self) -> None:
        refusals = self.refusals()
        order = list(stage_spec.STAGES)
        checked = 0
        for stage, names in knowledge.STAGE_FILES.items():
            if stage in knowledge.CLOSES:
                continue
            lines = [line for line in self.found[(stage, "producer")].splitlines() if "refuses " in line]
            for name in names:
                path = knowledge._expand([name], self.state)[0]
                path = str(Path(self.state["repo"]) / path)
                later = [close for close in refusals if order.index(close) > order.index(stage) and path in refusals[close]]
                if not later:
                    continue
                checked += 1
                with self.subTest(stage=stage, file=name):
                    self.assertTrue(any("ShipLoop refuses " + later[0] in line and path in line for line in lines),
                                    lines)
        self.assertGreaterEqual(checked, 5)  # intake, discovery, spec x2, test-strategy, plan x2 reach the prepare close

    # row 11c: prepare separates what earlier stages wrote from the one file it writes, and says where readiness goes.
    def test_prepare_separates_the_files_earlier_stages_wrote_from_the_one_it_writes(self) -> None:
        refusals = self.refusals()["prepare"]
        lines = self.found[("prepare", "producer")].splitlines()
        earlier = next(line for line in lines if line.startswith("Written by earlier stages"))
        mine = next(line for line in lines if line.startswith("This stage keeps these up to date"))
        self.assertIn("ShipLoop refuses prepare if any is missing or empty", earlier)
        environment = str(Path(self.state["repo"]) / "docs/shiploop/environment.md")
        self.assertEqual(mine.rsplit(": ", 1)[1], environment + ".")
        for path in refusals:
            with self.subTest(path):
                self.assertEqual(path in earlier, path != environment)
                self.assertIn(path, earlier + " " + mine)
        text = flat(self.found[("prepare", "producer")])
        self.assertIn("Record readiness, or the justified N/A, in environment.md", text)
        self.assertIn("cite in `evidence_refs` the runner output that shows each planned check starts", text)


if __name__ == "__main__":
    unittest.main()
