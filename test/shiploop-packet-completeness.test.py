#!/usr/bin/env python3
"""Main tenet (README top, SPEC S-6): every packet stands alone, because the context may be cleared between any two stages.

A model holding only the next packet must find, in that packet: what the stage is for, how it operates, how its result is
checked or reviewed, what it must produce, and how to recover.  This renders the real packet of every stage, and the
Improve-phase packet of every stage whose result starts an Improve child, from a cold read of ``state.md`` (what a cleared
model sees), and checks each for the five.  Synthetic results; no model, no Improve execution.
"""
from __future__ import annotations

import json
import re
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
        # implement's rule is "step": an Improve child after every accepted step (owner, 2026-10-10).
        self.assertEqual(reviewed, set(stage_spec.reviewed_stages("stage")) | {"carry-forward"}
                         | stage_spec.with_improve("step"))

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
                # The one callback line names the result file it reads (the "Write the structured result to:" line
                # and the second "Call this when done:" callback are gone, 2026-10-11 dedupe).
                callback = next((line for line in packet.splitlines()
                                 if line.startswith("Callback for this stage (run once after its work, with the result "
                                                    "written to the file it names): ")), "")
                self.assertIn(" complete ", callback)
                self.assertIn(" --result=", callback)
                self.assertNotIn("Write the structured result to: ", packet)
                self.assertNotIn("Call this when done:", packet)
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
    # with the real refusal and an accepted correction.  Since the 8-stage inner loop (2026-10-10) every inner stage runs
    # a script check (its loop receipt), so this test no longer reaches step-plan and its rows below are vacuous;
    # skill_na is gone with the skill stages.
    GATE_WORDS = {
        # The plan's assumptions, and the open items of the later stages (consumer contract X10, 2026-10-11).
        "assumption": {"plan", "test-spec", "verify", "carry-forward", "system-test-author", "system-test",
                       "release-plan", "release-verify"},
        "criterion": {"step-plan"},
        "deps": {"step-plan"},
        "system_commands": {"system-test-author"},
        "consumer_checks": {"release-plan"},
        "consumer_entry": {"release-plan"},
        # The closes, plus the stages whose docs/shiploop change can lose an R-<n> or AD-<n> ID (L4 of the
        # architecture-file journal, 2026-10-10).
        "HOME": {"prepare", "test-spec", "release-plan", "spec", "plan", "step-plan"},
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

    def test_a_producer_with_a_script_run_check_still_names_the_other_faults_complete_refuses(self) -> None:
        # release-verify runs the consumer checks and closes the knowledge home.  Its line named only the run, so the
        # docs/shiploop gate (HOME in the packet's References symbols) was met first as a refusal in 4 runs (packet
        # review 2026-10-10, P-rv-1).
        # test-spec's close requires the item's test-spec.md under docs/shiploop, and its row now runs the loop
        # receipt check too, so its line belongs to this group (8-stage inner loop, 2026-10-10).
        closes = {"release-verify", "test-spec", "step-plan"}  # step-plan: the ID-retention line (L4)
        for (stage, kind), packet in sorted(self.found.items()):
            row = stage_spec.stage(stage)
            if kind != "producer" or not row.complete_runs:
                continue
            lines = [line for line in packet.splitlines() if line.startswith("Checked by: ")]
            with self.subTest(stage):
                self.assertEqual(len(lines), 1)
                self.assertEqual("HOME" in lines[0], stage in closes)
                self.assertIn("when you report done, ShipLoop", lines[0])

    def test_release_verify_done_when_names_the_files_and_sections_its_close_requires(self) -> None:
        packet = self.found[("release-verify", "producer")]
        done = packet[packet.index("Done when"):packet.index("Checked by: ")]
        for word in ("outcome.md", "environment.md", "README.md", "## Learned", "## Key considerations",
                     "## Open for the next run"):
            self.assertIn(word, done)


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
            # An inner stage's template prefills its Until Loop receipt locator: a run file, not product content.
            text = text.replace(str(next(iter(re.findall(r'"([^"]*/loops/[^"]*-terminal\.json)"', text)), "")), "")
            with self.subTest(stage):
                self.assertNotRegex(text, r"(?i)readme")
                self.assertNotRegex(text, r"[\w-]+\.(md|txt|py|js|json|html)\b")

    # row 6, second source: the verification run of 2026-10-10 (pc1i-checkers-sonnet) still built a README nobody asked
    # for; the step-plan duty's own `check` example named a README and a flag.  A duty example must not suggest product
    # content: the check example is a generic one.
    def test_the_step_plan_duty_suggests_no_product_file_as_its_check_example(self) -> None:
        duty = prompts.DUTIES["step-plan"]
        self.assertNotRegex(duty, r"(?i)readme[^/]")  # README/AGENTS links of repository-local skills stay (a path, not a product file)
        self.assertNotIn("--greeting", duty)
        self.assertIn("check: the lint, type and build commands HOME/environment.md records for these files, "
                      "judged by exit code", flat(duty))

    # row 7: the step plan declares the ids; test-spec titles its cases with them; check is a suite.
    def test_the_step_plan_declares_ids_it_will_title_and_names_every_suite(self) -> None:
        text = flat(self.found[("step-plan", "producer")])
        # The duty's `test_commands` item (4, 2026-10-10 rewrite) lists one bullet per suite: the focused one carries ids.
        self.assertIn("focused: this item's cases, with the ids they will carry", text)
        self.assertNotIn("of the test-spec cases", text)
        for suite in test_loop.SUITES:
            self.assertIn("- " + suite + ": ", text)

    def test_test_spec_titles_each_case_with_the_declared_ids_and_says_where_the_cases_go(self) -> None:
        text = flat(self.found[("test-spec", "producer")])
        # Consumer contract 3.3: the cases are the result's test_cases (quoted downstream by value), each id one the
        # step plan's focused commands list; the file keeps each case's full entry.
        self.assertIn("Record one case per id in the result's `test_cases`", text)
        self.assertIn("each id one a focused command in the step plan's `test_commands` lists", text)
        self.assertIn('Write each case\'s full entry under its "### <ID>" in FEATURE/test-spec.md.', text)
        for part in ("setup and fixture; action; independent oracle", "RED (", "GREEN;"):
            self.assertIn(part, text)

    # row 2: a check row carries no ids or min_tests (shiploop-callback-contract pairs the refusal with its correction).
    def test_the_stages_that_record_commands_say_a_check_row_carries_no_ids_or_min_tests(self) -> None:
        for stage in ("system-test-author", "release-plan"):
            with self.subTest(stage):
                self.assertIn("a check row carries no ids or min_tests", flat(self.found[(stage, "producer")]))
        # step-plan's duty (rewritten 2026-10-10) states the same rule in its own words.
        self.assertIn("judged by exit code, with no ids or min_tests", flat(self.found[("step-plan", "producer")]))

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
        # N9 (2026-10-10 review): spec and test-strategy hold no steps, so the steps condition is not theirs to meet.
        steps = [bullet for bullet in bullets if bullet.endswith("in the steps.")]
        self.assertEqual(len(steps), 1)
        for stage in FOCUS_STAGES:
            producer = flat(self.found[(stage, "producer")])
            with self.subTest(stage):
                # The child prints PLANNING_REVIEW_FOCUS at every stage in PLANNING_REVIEW_STAGES (after improve-bind,
                # which the cold packet of an unbound child does not yet show).
                self.assertIn(stage, prompts.PLANNING_REVIEW_STAGES)
                for bullet in bullets:
                    if bullet in steps:
                        self.assertNotIn(bullet[2:].rstrip(".;"), producer)
                    else:
                        self.assertIn(bullet[2:].rstrip(".;"), producer)
                self.assertIn("That review applies the Planning review focus in this stage's guidance and checks "
                              "the result against the Done-when conditions above.", producer)

    def test_without_an_improve_child_the_focus_is_still_a_checklist_and_no_review_is_promised(self) -> None:
        for stage in FOCUS_STAGES:
            text = flat(self.none[(stage, "producer")])
            with self.subTest(stage):
                # The lead states the duty only: a packet names Improve only where its stage runs a child (owner rule).
                self.assertIn("Planning review focus (meet these conditions before you submit):", text)
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
        # S-8: generic, with the browser as an example (F6 of the 2026-10-10 review).
        self.assertIn("either a case that drives it through its user interface (for example in a browser or on a "
                      "device), with the tool named and probed", text)
        self.assertNotIn("drives it in a browser", text)
        self.assertIn("or the outcome recorded as unverified with its owner and due stage", text)

    # #10 of the 2026-10-10 review: prepare's and test-spec's closes require files earlier stages wrote, so their
    # Checked-by line says what the close requires, not what this stage must have written.
    def test_a_close_states_the_files_its_close_requires_and_only_a_writer_says_it_must_have_written_them(self) -> None:
        for stage in knowledge.CLOSES:
            checked = next(line for line in self.found[(stage, "producer")].splitlines() if line.startswith("Checked by: "))
            with self.subTest(stage):
                if knowledge.required_earlier(stage):
                    self.assertIn("a HOME file this stage's close requires, missing or empty", checked)
                    self.assertNotIn("must have written", checked)
                else:
                    self.assertIn("a HOME file this stage must have written, missing or empty", checked)

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
        """{close: the paths the real gate asks for when nothing is written}, on an empty repository, as the packet's
        References symbols name them (the refusal prints absolute paths; the packet's prose prints HOME/ and FEATURE/)."""
        with tempfile.TemporaryDirectory(prefix="shiploop-knowledge-gate-") as temp:
            repo = Path(temp)
            subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, capture_output=True)
            state = dict(self.state, repo=str(repo))
            found = {}
            for close in knowledge.CLOSES:
                reply = knowledge.check(state, close)
                found[close] = [navigator.symbolic(str(Path(self.state["repo"]) / Path(line[2:]).relative_to(repo)),
                                                   repo / "run", self.state)
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
                path = name.replace("{feature}", "FEATURE") if "{feature}" in name else "HOME/" + name
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
        environment = "HOME/environment.md"
        self.assertEqual(mine.rsplit(": ", 1)[1], environment + ".")
        for path in refusals:
            with self.subTest(path):
                self.assertEqual(path in earlier, path != environment)
                self.assertIn(path, earlier + " " + mine)
        text = flat(self.found[("prepare", "producer")])
        self.assertIn("Record readiness, or the justified N/A, in HOME/environment.md", text)
        self.assertIn("cite in `evidence_refs` the runner output that shows each planned check starts", text)


class KnowledgeGroundingPacketTests(unittest.TestCase):
    """The knowledge home's packet lines (the E2E session's L8 pins, docs/shiploop-architecture-file-journal-2026-10-10.md)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.found = packets()

    def test_plan_step_plan_and_prepare_print_what_architecture_md_holds_verbatim(self) -> None:
        for stage in ("plan", "step-plan", "prepare"):
            with self.subTest(stage=stage):
                self.assertIn(knowledge.ARCHITECTURE_HOLDS, flat(self.found[(stage, "producer")]))

    def walk_to(self, repo: Path, run: Path, stage: str) -> str:
        """The cold packet at ``stage`` for a run on ``repo``, walked with synthetic results (no gates)."""
        state = navigator.new_state(str(repo), "Build a thing.", delegation="inline")
        for _ in range(80):
            if navigator.current_stage(state) == stage:
                store.write_record(run / "state.md", state)
                return navigator.render(None, run, store.read_record(run / "state.md"))
            here, action = navigator.current_stage(state), navigator.current_action(state)["id"]
            extra = ({"work_items": [{"id": "W1", "title": "one", "context": "context"}]} if here == "plan" else
                     {"steps": [{"id": "S1", "task": "Make it."}]} if here == "step-plan" else {})
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic", **extra})
            if state.get("active_improve") is not None:
                state = navigator.finish_improve(state, action, {"summary": "Synthetic review"})
        self.fail("the walk did not reach " + stage)

    def test_an_inner_packet_lists_every_grounding_file_and_marks_a_missing_one_with_its_writer(self) -> None:
        """The References block replaced the grounding line (owner, 2026-10-11): the same files, each listed in every
        packet; one that exists carries no marker, and a missing architecture.md is shown as not written, not dropped."""
        grounding = tuple(navigator.reference_name(name) for _label, name in knowledge._GROUNDING)
        self.assertEqual(len(grounding), len(knowledge.GROUNDING_LABELS))
        with tempfile.TemporaryDirectory(prefix="shiploop-grounding-") as temp:
            repo = Path(temp).resolve()
            run = repo / "run"
            run.mkdir()
            home = repo / knowledge.HOME
            home.mkdir(parents=True)
            for name in ("spec.md", "environment.md", "architecture.md", "test-strategy.md"):
                (home / name).write_text("# " + name + "\n\nContent.\n", encoding="utf-8")
            packet = self.walk_to(repo, run, "implement")
            state = store.read_record(run / "state.md")
            feature = repo / knowledge.feature_dir(state)
            feature.mkdir(parents=True)
            (feature / "spec.md").write_text("# Feature\n\nR-1 changes.\n", encoding="utf-8")
            packet = navigator.render(None, run, state)
            self.assertEqual(len(knowledge.grounding(state)), len(grounding))
            block = reference_block(packet)
            for name in grounding:
                with self.subTest(name):
                    rows = [row for row in block if row.startswith("- " + name + ":")]
                    self.assertEqual(len(rows), 1)
                    self.assertNotIn("not written yet", rows[0])
            self.assertNotIn("Ground this stage's decisions", packet)
            (home / "architecture.md").unlink()
            block = reference_block(navigator.render(None, run, store.read_record(run / "state.md")))
            row = next(row for row in block if row.startswith("- " + navigator.reference_name(knowledge.ARCHITECTURE) + ":"))
            self.assertTrue(row.endswith("(not written yet: " + navigator.reference_writer(knowledge.ARCHITECTURE) + ")"), row)
            self.assertEqual(navigator.reference_writer(knowledge.ARCHITECTURE), "plan writes it")
            self.assertEqual([row for row in block if "not written yet" in row and row.startswith(
                tuple("- " + name + ":" for name in grounding))], [row])


REFERENCE_DEFINITION = re.compile(r"^(HOME|FEATURE|RUN|WORKTREE) = ")
REFERENCE_ROW = re.compile(r"^(- |HOME = |FEATURE = |RUN = |WORKTREE = |Read at this stage|Results this stage builds on)")
NOT_WRITTEN = re.compile(r" \(not written yet: [^)]*\)$")


def reference_block(packet: str) -> list:
    """The References block's lines: from its head to the first line of another shape."""
    lines = packet.splitlines()
    start = lines.index(navigator.REFERENCES_HEAD)
    end = start + 1
    while end < len(lines) and REFERENCE_ROW.match(lines[end]):
        end += 1
    return lines[start:end]


def global_part(block: list) -> list:
    """The block's global part (the head and the four symbols with their files), "not written yet" markers removed."""
    end = next((i for i, row in enumerate(block) if row.startswith(("Read at this stage", "Results this stage"))),
               len(block))
    return [NOT_WRITTEN.sub("", row) for row in block[:end]]


def builds_on(block: list) -> list:
    """``[(label, path)]`` of the block's "Results this stage builds on" rows."""
    rows = block[next((i for i, row in enumerate(block) if row.startswith("Results this stage builds on")),
                      len(block)) + 1:]
    found = []
    for row in rows:
        label, rest = row[2:].split(": ", 1)
        found.append((label, re.sub(r" \([^()]*\)$", "", rest)))
    return found


def symbol_paths(block: list) -> dict:
    """{symbol: absolute path} from the block's definition lines (FEATURE is defined under HOME)."""
    found = {}
    for row in block:
        match = REFERENCE_DEFINITION.match(row)
        if match:
            found[match.group(1)] = row[len(match.group(0)):].split(": ", 1)[0]
    found["FEATURE"] = found["FEATURE"].replace("HOME", found["HOME"], 1)
    return found


def prose_lines(packet: str) -> list:
    """The packet's lines outside the References block that are prose, with the exemption rule applied.

    Exempt: (1) a command the model runs verbatim, which keeps its absolute paths so it still runs: any line holding a
    ShipLoop CLI call (``--run-dir``) or the Until Loop Start line; (2) the /until-loop argument, which the packet says
    to pass verbatim: the lines indented by four spaces under "Argument:".
    """
    lines = packet.splitlines()
    start = lines.index(navigator.REFERENCES_HEAD)
    block = set(range(start, start + len(reference_block(packet))))
    found, argument = [], False
    for number, line in enumerate(lines):
        if line == "Argument:":
            argument = True
            continue
        if argument and line.startswith("    "):
            continue
        argument = False
        if number in block or "--run-dir" in line or line.startswith("Start (the card runs exactly this"):
            continue
        found.append(line)
    return found


def dry_run_packets() -> dict:
    """{scenario: [packet, ...]}: every packet of each dry-run scenario (producers, Improve parents, paused, blocked)."""
    import shiploop_navigator_dry_run as dry_run
    return {name: [event["prompt"] for event in dry_run.run_scenario(name, scenario)["events"]]
            for name, scenario in dry_run.scenarios().items()}


def offline_slice_packets() -> list:
    """The offline step slice's packets (``packets.py --offline node-fix-bug``): an item's inner loop, cold-read."""
    sys.path.insert(0, str(ROOT / "test/shiploop_e2e"))
    import packets as slice_packets
    cases = json.loads((ROOT / "test/shiploop_e2e/step_cases.json").read_text())
    return list(slice_packets.offline_packets(cases["node-fix-bug"]).values())


class ReferencesBlockTests(unittest.TestCase):
    """Every packet references the knowledge artifacts once, symbolically (owner, 2026-10-11).

    Checked over every packet of each dry-run scenario and of the offline node-fix-bug slice, so producer, Improve,
    paused and blocked packets of every stage are covered.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.runs = {**{"dry:" + name: found for name, found in dry_run_packets().items()},
                    "offline:node-fix-bug": offline_slice_packets()}

    def each(self):
        for run, found in self.runs.items():
            for number, packet in enumerate(found):
                yield run, number, packet

    def test_each_symbol_is_defined_exactly_once(self) -> None:
        for run, number, packet in self.each():
            with self.subTest(run=run, packet=number):
                self.assertEqual(packet.count(navigator.REFERENCES_HEAD), 1)
                for symbol in navigator.REFERENCE_SYMBOLS:
                    self.assertEqual(len(re.findall("(?m)^" + symbol + " = ", packet)), 1, symbol)

    def test_each_knowledge_file_is_listed_with_its_sections_or_its_writer(self) -> None:
        """The files come from knowledge_home's tables (SECTIONS, FEATURE_LIST, the {feature} entries of STAGE_FILES),
        so a change there changes the block and this test with it."""
        home = [*knowledge.SECTIONS, str(Path(knowledge.FEATURE_LIST).relative_to(knowledge.HOME))]
        feature = sorted({name for names in knowledge.STAGE_FILES.values() for name in names if name.startswith("{feature}/")})
        self.assertEqual(navigator.reference_files(), (home, [name for name in navigator.reference_files()[1]]))
        self.assertEqual(sorted(navigator.reference_files()[1]), feature)
        for run, number, packet in self.each():
            block = reference_block(packet)
            block = block[:len(global_part(block))]
            for name in home + feature:
                symbol = navigator.reference_name(name)
                with self.subTest(run=run, packet=number, file=symbol):
                    rows = [row for row in block if row.startswith("- " + symbol + ":")
                            or row.startswith("- " + symbol + " (")]
                    self.assertEqual(len(rows), 1)
                    for heading in knowledge.SECTIONS.get(name, ()):
                        self.assertIn("## " + heading, rows[0])
                    writer = next((stage for stage in stage_spec.STAGES if name in knowledge.STAGE_FILES.get(stage, ())),
                                  None)
                    # Nothing exists in these walks, so every file is marked with the stage that writes it.
                    self.assertTrue(rows[0].endswith("(not written yet: " + (writer + " writes it" if writer else
                                    "ShipLoop writes it at its next knowledge commit") + ")"), rows[0])

    def test_no_absolute_home_or_feature_path_appears_in_prose_outside_the_block(self) -> None:
        for run, number, packet in self.each():
            paths = symbol_paths(reference_block(packet))
            with self.subTest(run=run, packet=number):
                for line in prose_lines(packet):
                    self.assertNotIn(paths["HOME"], line)  # FEATURE is under HOME

    def test_the_global_part_is_identical_in_every_packet_of_a_run(self) -> None:
        for run, found in self.runs.items():
            parts = {tuple(global_part(reference_block(packet))) for packet in found}
            with self.subTest(run=run):
                self.assertEqual(len(parts), 1)

    def test_an_artifact_has_one_label_and_one_path_in_every_packet_that_cites_it(self) -> None:
        """An artifact (its path) keeps one label across the run; a label names one artifact per packet.  A label may
        name a newer artifact in a later packet: after a revise the item's redone step plan is "W1 step-plan result"."""
        for run, found in self.runs.items():
            labels, cited = {}, 0
            for packet in found:
                rows = builds_on(reference_block(packet))
                cited += len(rows)
                self.assertEqual(len({label for label, _ in rows}), len(rows), run)
                for label, path in rows:
                    with self.subTest(run=run, label=label):
                        self.assertEqual(labels.setdefault(path, label), label)
                        self.assertRegex(label, r"^(W\d+ [a-z-]+ |[a-z-]+ stage result$)")
                        self.assertRegex(path, r"^(RUN|FEATURE|HOME|commit|the WORKTREE)\b")
            if run != "dry:halted":  # halted at intake: nothing earlier to build on
                self.assertTrue(cited, run)

    def test_a_packet_names_its_reads_and_quotes_each_file_whole_after_the_status(self) -> None:
        """Consumer contract section 5 (D1): the References block names the files ``knowledge.READS`` gives the stage,
        and the packet quotes each whole after the status block, or marks it not written yet."""
        for run, number, packet in self.each():
            stage = packet.split("ShipLoop navigator | ", 1)[1].split(" |", 1)[0]
            names = knowledge.READS.get(stage, ())
            block = reference_block(packet)
            with self.subTest(run=run, packet=number, stage=stage):
                # Only an active packet quotes the files, so only it names them (a paused or blocked one waits).
                active = not re.search(r"^(Paused|Blocked)[,:]", packet, re.M)
                pointer = navigator.reads_pointer(stage) if active else []
                self.assertEqual(bool(pointer), bool(names) and active)
                self.assertEqual(block[len(global_part(block)):len(global_part(block)) + len(pointer)], pointer)
                if not pointer or "=== end ShipLoop status ===" not in packet:
                    continue
                after = packet.split("=== end ShipLoop status ===", 1)[1]
                self.assertIn(navigator.READS_HEAD, after)
                for name in names:
                    self.assertTrue(("HOME/" + name + " (source: HOME/" + name + ", whole file):") in after
                                    or ("HOME/" + name + ": not written yet") in after, name)

if __name__ == "__main__":
    unittest.main()
