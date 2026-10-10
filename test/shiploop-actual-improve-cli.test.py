#!/usr/bin/env python3
"""Real ShipLoop/Improve CLI composition; fixture judgments are synthetic."""
from pathlib import Path
import hashlib
import json
import re
import os
import shlex
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_loop_contract as loop_contract  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


CLI = ROOT / "skills/shiploop/scripts/shiploop"


def _packet_path_from_stdout(stdout: str) -> Path | None:
    """The ``Full packet: <path>`` locator an active-state head prints, if any."""
    marker = "Full packet: "
    for line in stdout.splitlines():
        if line.startswith(marker):
            return Path(line[len(marker):])
    return None


def _with_packet_file(stdout: str) -> str:
    """Append the full packet's file text when stdout only printed the head.

    An active-state ``emit()`` prints a short head with a ``Full packet:
    <path>`` line and writes the complete packet to that file; a non-active
    print (paused/blocked/halted/done) already carries the full text and has
    no such line, so it passes through unchanged.
    """
    packet_file = _packet_path_from_stdout(stdout)
    if packet_file is not None and packet_file.is_file():
        return stdout + "\n" + packet_file.read_text(encoding="utf-8")
    return stdout

CARD = ROOT / "skills/improve/SKILL.md"
EPHEMERAL = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
DEFAULT_COMMIT_AUTHORITY = (
    "After the meaningful checks required by the current scope, commit authorized "
    "scoped changed files, including tests, documentation, configuration and skills when in scope. Never commit runtime evidence or inherited "
    "unrelated staged work, and do not create an empty commit unless an explicit "
    "audit-every-iteration rule authorizes it."
)
EXPLICIT_NO_COMMIT_AUTHORITY = (
    "Explicit user no-commit authority: do not commit, merge, push, or broaden scope."
)



class ImproveCliFixture(unittest.TestCase):
    """Hermetic parent fixture shared by the inline and Ask-Agent ephemeral routes."""

    # None follows the CLI's new-run default (inline); subclasses pin ask-agent.
    delegation = None

    def delegation_args(self):
        return (("--delegation", self.delegation) if self.delegation else ())

    def inline(self):
        return self.delegation in (None, "inline")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-child-cli-")
        self.base = Path(self.temp.name).resolve()
        self.repo = self.base / "repo"
        self.run = self.base / "run"
        self.environment = {
            **os.environ,
            "PATH": "/Library/Developer/CommandLineTools/usr/bin:" + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.repo.mkdir()
        self.product_contract = self.repo / "product/contracts/cold-recovery.md"
        self.product_contract.parent.mkdir(parents=True)
        self.product_contract.write_text("# Product contract\n\n## child-contract-transfer\n", encoding="utf-8")
        self.product_test = self.repo / "test/product_contract_test.py"
        self.product_test.parent.mkdir()
        self.product_test.write_text("class ProductContractTests:\n    def test_child_contract_transfer(self):\n        pass\n", encoding="utf-8")
        self._start_parent(CARD)

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, executable, *args, status=0):
        result = subprocess.run(
            [sys.executable, "-B", str(executable), *map(str, args)], text=True,
            capture_output=True, cwd=self.base, timeout=30, env=self.environment,
        )
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        if result.stdout:
            result.stdout = _with_packet_file(result.stdout)
        return result

    def invoke_argv(self, argv, payload=None, status=0):
        input_bytes = None if payload is None else json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8")
        result = subprocess.run(
            [str(item) for item in argv], input=input_bytes, text=False,
            capture_output=True, cwd=self.base, timeout=30, env=self.environment,
        )
        detail = (result.stdout + result.stderr).decode("utf-8", "replace")
        self.assertEqual(result.returncode, status, detail)
        try:
            packet = json.loads(result.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self.fail(f"runtime did not return JSON: {detail}\n{exc}")
        self.assertIsInstance(packet, dict)
        return result, packet

    def _prepare_parent_evidence(self):
        self.run_note = self.run / "notes/parent-evidence.md"
        self.run_note.parent.mkdir(parents=True, exist_ok=True)
        self.run_note.write_text("# parent-evidence-transfer\n", encoding="utf-8")
        self.parent_evidence_refs = [
            str(self.product_contract) + "#child-contract-transfer",
            str(self.product_test) + "::ProductContractTests::test_child_contract_transfer",
            str(self.run_note) + "#parent-evidence-transfer",
        ]

    def _start_parent(self, card):
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", self.run,
                    "--prompt", "Protocol composition fixture", "--improve-skill", card,
                    *self.delegation_args())
        self._prepare_parent_evidence()
        state = store.read_record(self.run / "state.md")
        # intake, discovery and research are not planning stages; advance them
        # directly with a plain callback before the first checkpoint (spec).
        for predecessor in ("intake", "discovery", "research"):
            action = state["action"]["id"]
            setup = {
                "outcome": "done",
                "summary": "Synthetic predecessor navigation only for " + predecessor
                + "; not a checkpoint stage.",
            }
            path = self.run / "inbox" / (action + ".md")
            store.write_record(path, setup)
            self.invoke(CLI, "complete", "--run-dir", self.run, "--action", action, "--result", path)
            state = store.read_record(self.run / "state.md")
        self.state = state
        self.action = self.state["action"]["id"]
        self.producer = {"outcome": "done", "summary": "Fixture spec evidence.",
                         "evidence_refs": self.parent_evidence_refs}
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def _start_parent_at_stage(self, stage, evidence_refs, card=CARD, producer_extra=None):
        """Create a real CLI parent at a target stage after synthetic setup only.

        The pure navigator transitions below deliberately do not claim preceding
        Improve execution.  The test's target-stage bind, child runtime and
        parent import still use the actual command-line interfaces.
        """
        run = self.base / ("parent-" + stage)
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", run,
                    "--prompt", "Synthetic predecessor navigation for CLI composition.",
                    "--improve-skill", card, *self.delegation_args())
        state = store.read_record(run / "state.md")
        while navigator.current_stage(state) != stage:
            predecessor = navigator.current_stage(state)
            action = navigator.current_action(state)["id"]
            setup = {
                "outcome": "done",
                "summary": (
                    "Synthetic predecessor navigation only for " + predecessor
                    + "; no child Improve runtime executed."
                ),
            }
            if predecessor == "plan":
                setup["work_items"] = [{"id": "W1", "title": "Synthetic local-skill item"}]
            state = navigator.apply(state, action, setup)
            if state.get("active_improve") is not None:
                state = navigator.finish_improve(state, action, {
                    "summary": "Synthetic predecessor receipt only; no semantic review claim.",
                })
        navigator.save(run, state)
        self.run = run
        self.state = state
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(evidence_refs)
        self.producer = {
            "outcome": "done",
            "summary": "Fixture local-skill assessment; synthetic prior navigation is setup only.",
            "evidence_refs": self.parent_evidence_refs,
        }
        if stage == "plan":
            self.producer["assumptions"] = []
        if stage == "step-plan":
            self.producer["test_commands"] = []
            self.producer["test_commands_na"] = "Synthetic fixture; no test commands."
            self.producer["paths"] = ["src/**"]
            self.producer["steps"] = [{"id": "S1", "task": "Make the planned change."}]
        self.producer.update(producer_extra or {})
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def bind_current(self, card=CARD):
        self.invoke(CLI, "improve-bind", "--run-dir", self.run, "--action", self.action,
                    "--skill-card", card)
        self.bound = store.read_record(self.run / "state.md")["active_improve"]
        self.notes_path = self.run / "inbox" / (self.action + "-improve-notes.md")
        self.final_path = self.run / "inbox" / (self.action + "-final-result.md")
        self.parent_route_path = self.run / "parent-recovery.json"
        self._write_parent_route()

    def _parent_import_argv(self):
        return [sys.executable, "-B", str(CLI), "improve-complete", "--run-dir", str(self.run),
                "--action", self.action]

    def _workspace_return_argv(self):
        return [sys.executable, "-B", str(CLI), "workspace", "return", "--workspace-root", str(self.run.parent)]

    def _write_parent_route(self):
        store.write_record(self.parent_route_path, {
            "state": str(self.run / "state.md"),
            "review_evidence": str(bridge.receipt_path(self.bound).parent / "reviews"),
            "improve_complete_argv": self._parent_import_argv(),
            "workspace_return_argv": self._workspace_return_argv(),
        })

    def child_context(self):
        receipt = bridge.receipt_path(self.bound)
        resources = [
            {"purpose": "selected Improve skill", "locator": self.bound["skill"]["skill_card"]},
            {"purpose": "bound Until Loop runtime", "locator": self.bound["skill"]["runtime_cli"]},
            {"purpose": "ShipLoop parent state", "locator": str(self.run / "state.md")},
            {"purpose": "review evidence directory", "locator": str(bridge.receipt_path(self.bound).parent / "reviews")},
            {"purpose": "ShipLoop exact return commands", "locator": str(self.parent_route_path)},
            {"purpose": "latest child packet receipt", "locator": str(receipt)},
        ]
        resources.extend({"purpose": "opaque parent evidence locator", "locator": value}
                         for value in self.parent_evidence_refs)
        return {
            "request": "Synthetic ShipLoop v3 Improve composition fixture.\n" + self.bound["contract_marker"]
                       + "\nDo exactly one review cycle per returned callback.",
            "scope": "Review only this frozen ShipLoop action and its producer evidence.",
            "authority": DEFAULT_COMMIT_AUTHORITY,
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": resources,
        }

    def child_contract(self):
        return {
            "workspace": str(self.repo.resolve()),
            "work": "Review the frozen ShipLoop candidate, make only authorized fixes, and run current checks.",
            "exit_condition": "Current evidence establishes the requested result after two qualifying trivial reviews.",
            "repeat_condition": "Continue while useful authorized review work remains; otherwise stop incomplete.",
            "required_trivial_reviews": 2,
            "context": self.child_context(),
        }

    def receipt_args(self):
        """Start the child the way ShipLoop's packet says: the runtime writes the receipt itself."""
        path = bridge.receipt_path(self.bound)
        path.parent.mkdir(parents=True, exist_ok=True)
        return ["--receipt", str(path)]

    def save_packet(self, result):
        path = bridge.receipt_path(self.bound)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(result.stdout)
        self.assertEqual(path.read_bytes(), result.stdout)
        self.packet_path = path
        return path

    def start_ephemeral_child(self):
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        result, packet = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base), *self.receipt_args()],
            self.child_contract(),
        )
        self.assertEqual(packet["status"], "active")
        self.save_packet(result)
        return result, packet

    def child_report(self, classification, exit_assessment, continuation_assessment, label):
        return {
            "classification": classification,
            "exit_assessment": exit_assessment,
            "continuation_assessment": continuation_assessment,
            "evidence": "Synthetic runtime composition observation: " + label,
            "handoff": (
                "Synthetic only; this is not semantic review proof. Current packet receipt: "
                + str(bridge.receipt_path(self.bound)) + ". Parent state: " + str(self.run / "state.md")
                + ". Review evidence: " + str(bridge.receipt_path(self.bound).parent / "reviews")
                + ". Parent route file: " + str(self.parent_route_path)
                + ". Exact parent import argv: " + json.dumps(self._parent_import_argv())
                + ". Exact workspace return argv: " + json.dumps(self._workspace_return_argv())
                + ". Preserve the binding marker and opaque parent evidence locators."
            ),
        }

    def done_ephemeral(self, packet, report):
        result, successor = self.invoke_argv(packet["done_argv"], report)
        self.save_packet(result)
        return result, successor

    def finish_ephemeral(self, first=None):
        if first is None:
            _raw, first = self.start_ephemeral_child()
        _raw, second = self.done_ephemeral(
            first, self.child_report("non-trivial", "unsatisfied", "allowed", "material finding"))
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "first qualifying review"))
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "second qualifying review"))
        self.assertEqual(terminal["status"], "complete")
        self.assertFalse(Path(terminal["state_file"]).exists())
        return terminal_raw, terminal

    def completion_receipt(self, *, final_result=None, lessons="A terminal callback receipt is structural "
                           "evidence, not semantic proof."):
        """Write the child's review files; return improve-complete's extra flags and the record ShipLoop derives."""
        evidence = bridge.receipt_path(self.bound).parent / "reviews"
        evidence.mkdir(parents=True, exist_ok=True)
        material, review_one, review_two, checks = (evidence / "review-1.md", evidence / "review-2.md",
                                                    evidence / "review-3.md", evidence / "checks.md")
        for path in (material, review_one, review_two, checks):
            path.write_text("Synthetic protocol evidence: " + path.name + "\n", encoding="utf-8")
        self.notes_path.parent.mkdir(parents=True, exist_ok=True)
        self.notes_path.write_text(lessons + "\n", encoding="utf-8")
        flags = ["--notes", str(self.notes_path)]
        receipt = {
            "summary": "Improve reviewed the " + self.bound["stage"] + " result; it ended on 2 trivial passes.",
            "review_refs": [str(review_one), str(review_two)],
            "check_refs": [str(checks)],
            "lessons": lessons,
        }
        if final_result is not None:
            store.write_record(self.final_path, final_result)
            flags += ["--final-result", str(self.final_path)]
            receipt["final_result"] = final_result
        return flags, receipt

    def complete_current_stage_through_actual_improve(self, evidence_refs, summary):
        """Advance one current checkpoint stage through its real Improve callbacks."""
        state = store.read_record(self.run / "state.md")
        stage = navigator.current_stage(state)
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(evidence_refs)
        self.producer = {
            "outcome": "done",
            "summary": summary,
            "evidence_refs": self.parent_evidence_refs,
        }
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current()
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                    "--action", self.action, *completion)
        return stage, self.action, store.read_record(self.run / "state.md")

    def complete_current_stage_directly(self, evidence_refs, summary):
        """Advance one current non-checkpoint stage with a plain callback; no child starts."""
        state = store.read_record(self.run / "state.md")
        stage = navigator.current_stage(state)
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(evidence_refs)
        self.producer = {
            "outcome": "done",
            "summary": summary,
            "evidence_refs": self.parent_evidence_refs,
        }
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        return stage, self.action, store.read_record(self.run / "state.md")

class EphemeralImproveCliTests(ImproveCliFixture):
    def test_context_first_assignment_and_learning_header_survive_recovery(self):
        """Prompt obligations and real transport; semantic use is tested separately."""
        guide = ROOT / "skills/shiploop/references/improve-context.md"
        body = guide.read_text(encoding="utf-8")
        headings = ["## Current context and desired improvements",
                    "### Current learnings", "## Execute Improve",
                    "## Workspace, authority, and return"]
        offsets = [body.index(heading) for heading in headings]
        self.assertEqual(offsets, sorted(offsets))
        self.assertIn("Run /improve using <selected absolute Improve SKILL.md>.", body)
        for relative in ("skills/ask-agent/SKILL.md",
                         "skills/ask-agent/references/consumer-owned-workspace.md"):
            self.assertIn("Run /improve using <selected absolute Improve SKILL.md>",
                          (ROOT / relative).read_text(encoding="utf-8"))

        before = (self.run / "state.md").read_bytes()
        for _ in range(2):
            packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
            if self.inline():
                self.assertIn("Context-first opening: before start, write the opening file", packet)
                self.assertIn("## Current context and desired improvements\n...", packet)
                self.assertIn(" improve-start ", packet)
                self.assertIn("Run the selected Improve card's ShipLoop whole-skill subcall in this conversation", packet)
                self.assertIn("Return order:", packet)
                self.assertIn("keep the frozen launch context unchanged", packet)
                # improve-start writes the binding line and start inputs; the packet no longer restates them.
                self.assertNotIn(self.bound["contract_marker"], packet)
                self.assertNotIn("Start inputs owned by ShipLoop", packet)
            else:
                self.assertIn("Parent assignment preparation:", packet)
                self.assertIn("Run /improve", packet)
                self.assertIn("navigator cannot supply conversation-only learnings", packet)
                self.assertIn("Parent-only return:", packet)
                self.assertIn("keep launch context immutable and continue the same child", packet)
                # ShipLoop starts this child too; the worker continues it (551b8b49).
                self.assertIn(" improve-start ", packet)
                self.assertIn("continues the already-started loop from the receipt's next_argv", packet)
            # Both routes tell the model how many bytes its four opening sections may use (batch 1003, F3).
            self.assertRegex(packet, r"Size budget: the opening is frozen into the Until Loop's state, which the "
                                     r"runtime caps at 16,384 bytes.*refuses a contract over 9,216 bytes.*"
                                     r"sections about [\d,]+ bytes together")
            # Neither route asks the model to copy the binding line or state start inputs.
            self.assertNotIn(self.bound["contract_marker"], packet)
            self.assertNotIn("Start inputs owned by ShipLoop", packet)
            self.assertNotIn("Start the child runtime with --receipt", packet)
            self.assertIn("Selected Improve skill: " + str(CARD.resolve()), packet)
            self.assertIn("material unresolved findings, hypotheses, failed attempts", packet)
            self.assertIn("approvals, declines and pending decisions into child context.authority", packet)
        self.assertEqual((self.run / "state.md").read_bytes(), before)

        header = (
            "## Current context and desired improvements\n"
            "Improve this candidate's recovery behavior; preserve the accepted format.\n"
            "### Current learnings\n"
            "- Facts/corrections: caller work is staged; preserve its ownership.\n"
            "- Decisions: retain the format for existing consumers.\n"
            "- Hypotheses: cold recovery might drop context; not yet established.\n"
            "- Execution pitfalls: an earlier check used the wrong worktree.\n"
        )
        context = self.child_context()
        context["request"] = header + "\n" + context["request"]
        decisions = (
            "Approved: local preview at fixture target after checks; source: user launch instruction. "
            "Declined: production publication; source: user launch instruction. "
            "Pending: adding a service dependency; no approval received."
        )
        context["authority"] += "\n" + decisions
        self.child_context = lambda: context
        _raw, active = self.start_ephemeral_child()
        _raw, cold = self.invoke_argv(active["next_argv"])
        self.assertTrue(cold["context"]["request"].startswith(header))
        self.assertEqual(cold["context"]["request"].count(headings[0]), 1)
        self.assertEqual(cold["context"], context)
        self.assertIn(decisions, cold["context"]["authority"])
        report = self.child_report("unresolved", "unknown", "blocked", "transport fixture ends")
        learnings = (
            "## Current learnings\n"
            "- Facts/corrections: preserve caller-owned staging.\n"
            "- Decisions: retain the format for existing consumers.\n"
            "- Hypotheses: semantic context loss remains untested by this transport fixture.\n"
            "- Execution pitfalls: the earlier wrong-worktree check is not current validation.\n"
        )
        report["handoff"] = "## State and remaining work\nTransport fixture stopped.\n" + learnings + "\n## Evidence\n" + report["handoff"]
        delta = (
            "Simulated later decision supplied by this transport fixture, not native delivery proof: local preview approval "
            "revoked before publication; do not publish. Production remains declined "
            "and service dependency approval remains pending. No publication performed."
        )
        report["handoff"] += "\n" + delta
        _raw, stopped = self.done_ephemeral(cold, report)
        self.assertEqual(stopped["status"], "stopped")
        self.assertEqual(stopped["context"]["request"], context["request"])
        self.assertIn(learnings, stopped["last_report"]["handoff"])
        self.assertEqual(stopped["context"]["authority"], context["authority"])
        self.assertIn(delta, stopped["last_report"]["handoff"])
        self.assertNotIn(headings[0], stopped["last_report"]["handoff"])
        self.assertEqual((self.run / "state.md").read_bytes(), before)

    def test_consumer_owned_context_keeps_edits_and_parent_pending_until_import(self):
        """Actual CLI boundary; review judgments are synthetic, not native proof."""
        before = (self.run / "state.md").read_bytes()
        guide = ROOT / "skills/shiploop/references/improve-context.md"
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertTrue(guide.is_file())
        self.assertIn("Improve context ownership: " + str(guide), packet)
        owner_record = "Native owner record: " + str(bridge.receipt_path(self.bound).with_name("host-owner.md"))
        if self.inline():
            # Inline Improve has no native owner; import below still succeeds.
            self.assertTrue(packet.startswith("ShipLoop navigator | spec |"))
            anchor = "default-route-the-parent-runs-improve-delegation-inline"
            self.assertIn("Improve context ownership: " + str(guide) + "#" + anchor, packet)
            headings = [re.sub(r"[^a-z0-9 -]", "", line.lstrip("#").strip().lower()).replace(" ", "-")
                        for line in guide.read_text(encoding="utf-8").splitlines() if line.startswith("#")]
            self.assertIn(anchor, headings)
            self.assertIn("Parent callback; run only after the runtime returned complete", packet)
            self.assertIn("Delegation: inline. Run the selected Improve card's ShipLoop whole-skill subcall", packet)
            for delegated in ("consumer-owned", "host-owner.md", "delegation_owner", "improve-agent"):
                self.assertNotIn(delegated, packet)
            self.assertIn("Return order:", packet)
        else:
            self.assertIn("ask-agent/consumer-owned-workspace/v1", packet)
            self.assertIn("run the host-selected improve-agent card for this bound child", packet)
            self.assertIn("Workspace route: consumer-owned; delivery mode: in-place", packet)
            self.assertIn("execution_role: improve-executor; delegation_owner: parent", packet)
            self.assertIn(owner_record, packet)
            self.assertIn("Parent-only return:", packet)
        self.assertIn("Child workspace: " + str(self.repo), packet)
        self.assertIn("Commit policy:", packet)

        # The candidate is already the worker's workspace. Native completion
        # is simulated here only to test the real parent/import boundary.
        updated = self.product_contract.read_text(encoding="utf-8") + "\nRetained candidate improvement.\n"
        self.product_contract.write_text(updated, encoding="utf-8")
        terminal_raw, terminal = self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        cold = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("Current action: Improve the completed spec result.", cold)
        if self.inline():
            self.assertNotIn(owner_record, cold)
            self.assertFalse(bridge.receipt_path(self.bound).with_name("host-owner.md").exists())
        else:
            self.assertIn(owner_record, cold)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        self.assertEqual(self.product_contract.read_text(encoding="utf-8"), updated)
        self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                    "--action", self.action, *completion)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(navigator.current_stage(after), "test-strategy")
        self.assertEqual(self.product_contract.read_text(encoding="utf-8"), updated)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

    def test_user_stopped_child_restarts_with_the_same_binding_then_imports(self):
        """A cancelled non-plan child is archived, restarted once and imported; no halt needed."""
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        # Both routes restart through ShipLoop; neither renames files by hand (29786109, 551b8b49).
        self.assertIn("rerun the improve-start command with --restart-stopped: ShipLoop archives "
                      "packet.json as packet.stopped-<UTC timestamp>.json", packet)
        self.assertIn("Do not rename them yourself.", packet)
        self.assertIn("must be ones the new child writes", packet)
        self.assertIn("never report cancelled for a pause", packet)
        _raw, first = self.start_ephemeral_child()
        stopped_raw, stopped = self.done_ephemeral(
            first, self.child_report("unresolved", "unknown", "cancelled", "explicit user stop"))
        self.assertEqual(stopped["status"], "stopped")
        completion, stopped_receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                    *completion, status=2)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        opening = self.packet_path.with_name("opening.md")
        opening.write_text("## Current context and desired improvements\nThe user authorized continuing.\n\n"
                           "## Scope\nproduct/contracts/cold-recovery.md\n\n## Authority\nUser: continue.\n\n"
                           "## Environment\nPython fixture.\n", encoding="utf-8")
        start = [CLI, "improve-start", "--run-dir", self.run, "--action", self.action, "--opening", opening]
        self.assertIn("already started", self.invoke(*start, status=2).stderr)
        restarted_run = self.invoke(*start, "--restart-stopped")
        self.assertIn("Archived the stopped child", restarted_run.stderr)
        restarted = restarted_run.stdout
        json.loads(restarted)
        archived = next(self.packet_path.parent.glob("packet.stopped-*.json"))
        stopped_reviews = self.packet_path.parent / archived.name.replace("packet.", "reviews.").removesuffix(".json")
        self.assertTrue(stopped_reviews.is_dir())
        first = json.loads(restarted[restarted.index("{"):])
        self.assertEqual(first["status"], "active")
        self.finish_ephemeral(first)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                    *completion)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(navigator.current_stage(after), "test-strategy")
        self.assertEqual(archived.read_bytes(), stopped_raw.stdout)
        # The stopped child's whole review directory is archived, the material pass included.
        self.assertEqual(sorted(path.name for path in stopped_reviews.iterdir()),
                         ["checks.md", "review-1.md", "review-2.md", "review-3.md"])

    def test_renderer_preserves_an_explicit_user_no_commit_override(self):
        user_no_commit = "Explicit user no-commit instruction: do not commit this candidate."
        state = navigator.new_state(
            str(self.repo),
            user_no_commit,
            improve_skill=str(CARD),
        )
        # intake, discovery and research are not planning stages; advance
        # them directly before the first checkpoint (spec).
        for _predecessor in ("intake", "discovery", "research"):
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic advance."})
        action = navigator.current_action(state)["id"]
        waiting = navigator.apply(
            state,
            action,
            {"outcome": "done", "summary": "Synthetic pending Improve result."},
        )
        child = waiting["active_improve"]
        self.assertIsNotNone(child)
        waiting["active_improve"] = bridge.binding(
            waiting,
            action,
            navigator.current_stage(waiting),
            child["seed_result"],
            bridge.resolve_skill(str(CARD)),
        )
        navigator.validate(waiting)

        packet = navigator.render(None, self.run, waiting)

        self.assertIn(user_no_commit, packet)
        self.assertIn(
            "selected Improve card's scoped-commit policy with the task's explicit overrides",
            packet,
        )
        self.assertIn("Selected Improve skill: " + str(CARD.resolve()), packet)
        self.assertIn(
            "user- or repository-authorized no-commit override, including a frozen override",
            CARD.read_text(encoding="utf-8"),
        )

    def test_planning_improve_packet_carries_graph_identity_through_real_child_callbacks(self):
        """Synthetic predecessors reach both planning stages; child callbacks are real."""
        for stage, expected_stage in (("plan", "prepare"), ("step-plan", "test-spec")):
            with self.subTest(stage=stage):
                graph = self.repo / "plans" / (stage + "-execution-graph.json")
                graph.parent.mkdir(parents=True, exist_ok=True)
                graph_bytes = (json.dumps({
                    "version": 1,
                    "steps": [
                        {"id": "A", "deps": [], "contract": {
                            "task": "Prepare " + stage,
                            "ready": ["Planning inputs are available"],
                            "done": ["Preparation evidence is recorded"],
                        }},
                        {"id": "B", "deps": ["A"], "contract": {
                            "task": "Verify " + stage,
                            "ready": ["Preparation evidence is recorded"],
                            "done": ["Verification evidence is recorded"],
                        }},
                    ],
                }, sort_keys=True) + "\n").encode("utf-8")
                graph.write_bytes(graph_bytes)
                graph_identity = str(graph) + "#sha256=" + hashlib.sha256(graph_bytes).hexdigest()

                self._start_parent_at_stage(stage, [graph_identity])
                parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
                self.assertIn(graph_identity, parent_packet)
                # Check guidance routing, not paragraph wrapping or the model's judgment.
                guidance = " ".join(parent_packet.split())
                for clause in (
                    "Review the actual steps after their creation", "any linked execution graph",
                    "ready/done criteria", "independent paths", "resource exclusions",
                    "integration/verification ownership",
                ):
                    self.assertIn(clause, guidance)

                start_raw, first = self.start_ephemeral_child()
                cold_raw, cold = self.invoke_argv(first["next_argv"])
                self.assertEqual(start_raw.stdout, cold_raw.stdout)
                self.assertEqual(cold["context"], self.child_context())
                self.assertIn(
                    {"purpose": "opaque parent evidence locator", "locator": graph_identity},
                    cold["context"]["resources"],
                )
                self.save_packet(cold_raw)
                terminal_raw, terminal = self.finish_ephemeral(cold)
                self.assertEqual(terminal["context"], cold["context"])

                completion, _receipt = self.completion_receipt()
                self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                            "--action", self.action, *completion)
                resumed = store.read_record(self.run / "state.md")
                self.assertEqual(navigator.current_stage(resumed), expected_stage)
                self.assertEqual(
                    resumed["improve_results"][self.action]["seed_result"]["evidence_refs"],
                    [graph_identity],
                )
                self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

                if stage != "step-plan":
                    continue

                step_plan_action = self.action
                # test-spec is still a planning-review stage and starts a real
                # Improve child; baseline/test-author/test-red are not and
                # advance directly with a plain callback.
                for next_stage in ("test-spec", "baseline", "test-author", "test-red"):
                    self.assertEqual(navigator.current_stage(resumed), next_stage)
                    evidence = self.repo / "evidence" / (next_stage + ".md")
                    evidence.parent.mkdir(parents=True, exist_ok=True)
                    evidence.write_text("# " + next_stage + "\n", encoding="utf-8")
                    advance = (self.complete_current_stage_through_actual_improve
                              if next_stage == "test-spec" else self.complete_current_stage_directly)
                    observed_stage, _action, resumed = advance(
                        [str(evidence) + "#fixture"],
                        "Fixture advance through actual Improve for " + next_stage + ".",
                    )
                    self.assertEqual(observed_stage, next_stage)

                self.assertEqual(navigator.current_stage(resumed), "implement")
                self.assertNotEqual(resumed["history"][-1]["action"], step_plan_action)
                self.assertEqual(resumed["accepted"][step_plan_action]["evidence_refs"], [graph_identity])
                self.assertEqual(
                    resumed["improve_results"][step_plan_action]["seed_result"]["evidence_refs"],
                    [graph_identity],
                )

                cold = self.invoke(CLI, "next", "--run-dir", self.run).stdout
                self.assertIn("ShipLoop navigator | implement |", cold)
                # Cold recovery is the full packet: the locators are inline.
                self.assertIn("State: " + str(self.run / "state.md"), cold)
                self.assertIn(
                    "If this action depends on earlier accepted context, read the durable state and the relevant result record",
                    cold,
                )
                chain_guide = (
                    "Parallel-chain guide: "
                    + str(ROOT / "skills/shiploop/references/parallel-chain.md")
                    + "#parallel-implementation-chains"
                )
                if self.inline():
                    # The printed head no longer starts with the context prefix
                    # (it is not a stage step or run rule), but render() is
                    # unchanged, so the full packet file it writes still leads
                    # with it for a host that opens the file before acting.
                    cold_packet_path = _packet_path_from_stdout(cold)
                    self.assertIsNotNone(cold_packet_path, cold)
                    self.assertTrue(
                        cold_packet_path.read_text(encoding="utf-8").startswith(
                            "Continue in this context and execute the prompt.\n"),
                        cold,
                    )
                    self.assertNotIn(chain_guide, cold)
                    self.assertNotIn("bind this action to the default parallel", cold)
                    self.assertIn("Delegation is inline: this packet is for the one step named in its Step line.", cold)
                else:
                    self.assertIn(chain_guide, cold)
                    self.assertIn("bind this action to the default parallel", cold)
                    self.assertIn("mode when the selected Plan Dispatcher and Ask-Agent contracts are compatible", cold)

    def test_default_ephemeral_callbacks_preserve_context_then_import_once(self):
        """Cumulative report transport, not proof of model review or summarization."""
        self.assertEqual(self.state["navigator_protocol_version"], 4)
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        self.assertEqual(self.bound["skill"]["runtime_version"], "0.7.0")
        selected_frontmatter = CARD.read_text(encoding="utf-8").split("---", 2)[1]
        selected_version = next(
            line.partition(":")[2].strip().strip("\"'")
            for line in selected_frontmatter.splitlines() if line.startswith("version:")
        )
        self.assertEqual(self.bound["skill"]["skill_version"], selected_version)
        parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        for text in ("Bound Until Loop CLI locator: " + str(EPHEMERAL.resolve()),
                     "Child latest packet receipt: " + str(bridge.receipt_path(self.bound)),
                     "Commit policy:",
                     "Never write or edit the receipt",
                     "Completion deletes the child's temporary state"):
            self.assertIn(text, parent_packet)

        # Selected inputs are real before launch. Receipt/evidence paths are
        # outputs at this point, and must not become dispatch prerequisites.
        # This checks transport/lifecycle; native fixtures qualify model use.
        for label, key in (("Selected Improve skill", "skill_card"),
                           ("Bound Until Loop card", "runtime_card"),
                           ("Bound Until Loop CLI locator", "runtime_cli")):
            locator = Path(self.bound["skill"][key])
            self.assertTrue(locator.is_absolute())
            self.assertTrue(locator.is_file(), key)
            self.assertIn(label + ": " + str(locator), parent_packet)
        self.assertFalse(bridge.receipt_path(self.bound).exists())
        self.assertFalse((self.run / "inbox" / (self.action + "-improve.md")).exists())

        start_raw, first = self.start_ephemeral_child()
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], self.child_context())
        self.assertEqual(cold["context"]["resources"][-len(self.parent_evidence_refs):], [
            {"purpose": "opaque parent evidence locator", "locator": value}
            for value in self.parent_evidence_refs])
        self.save_packet(cold_raw)

        changes = "Synthetic change: preserve every selected report row, including the final row."
        lessons = (
            "Synthetic learning: a matching count alone does not prove row contents. "
            "Retired assumption: dropping the final row was intentional. "
            "Unresolved hypothesis: large iterables may need separate performance evidence."
        )
        cumulative = "\n## Key implemented changes\n" + changes + "\n## Current learnings\n" + lessons
        material_report = self.child_report("non-trivial", "unsatisfied", "allowed", "material finding")
        material_report["handoff"] += cumulative
        _raw, second = self.done_ephemeral(cold, material_report)
        self.assertEqual(second["progress"]["trivial_streak"], 0)
        first_review = self.child_report("trivial", "unsatisfied", "allowed", "first qualifying review")
        first_review["handoff"] = second["last_report"]["handoff"]
        _raw, third = self.done_ephemeral(second, first_review)
        self.assertEqual(third["progress"]["trivial_streak"], 1)
        self.assertIn(json.dumps(self._parent_import_argv()), third["last_report"]["handoff"])
        final_review = self.child_report("trivial", "satisfied", "allowed", "second qualifying review")
        final_review["handoff"] = third["last_report"]["handoff"]
        terminal_raw, terminal = self.done_ephemeral(third, final_review)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"], {"action_number": 3, "trivial_streak": 2, "required_trivial_reviews": 2})
        self.assertFalse(state_file.exists())
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        self.assertEqual(terminal["context"], self.child_context())
        self.assertIn(str(self.parent_route_path), terminal["last_report"]["handoff"])
        self.assertIn(json.dumps(self._workspace_return_argv()), terminal["last_report"]["handoff"])
        self.assertIn(cumulative, terminal["last_report"]["handoff"])
        self.assertFalse((self.repo / ".until-loop").exists())

        completion, receipt = self.completion_receipt(lessons=lessons)
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        after = (self.run / "state.md").read_bytes()
        state = store.read_record(self.run / "state.md")
        record = state["improve_results"][self.action]
        self.assertEqual(state["stage"], "test-strategy")
        self.assertIsNone(state["active_improve"])
        self.assertEqual(record["runtime_phase"], "complete")
        self.assertEqual(record["seed_result"]["evidence_refs"], self.parent_evidence_refs)
        self.assertEqual(record["receipt"]["summary"], receipt["summary"])
        self.assertEqual(record["receipt"]["lessons"], lessons)
        archive = self.run / "improve" / self.action / "terminal.json"
        self.assertEqual(archive.read_bytes(), terminal_raw.stdout)
        self.assertIn(cumulative, json.loads(archive.read_text())["last_report"]["handoff"])
        self.assertEqual(record["identities"]["terminal_packet_sha256"], hashlib.sha256(terminal_raw.stdout).hexdigest())
        self.assertNotEqual(before, after)
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        self.assertEqual(after, (self.run / "state.md").read_bytes())

    def test_inline_improve_packet_states_every_remaining_obligation_once(self):
        """P5 (SPEC S-6, S-7): script-owned steps are gone; each obligation the model keeps is stated once."""
        if not self.inline():
            self.skipTest("the delegated route keeps its manual start instructions")
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        full = Path(next(line for line in packet.splitlines() if line.startswith("Full packet: "))[13:]).read_text()
        # P13: the run's scratch directory exists and takes the reports piped to the runtime, not /tmp.
        scratch = self.run / "scratch"
        self.assertTrue(scratch.is_dir())
        self.assertIn("Temporary files, including each report you pass to the runtime on standard input, go in "
                      + str(scratch), " ".join(full.split()))
        obligations = {
            "write the opening": "Context-first opening: before start, write the opening file",
            "start through ShipLoop": " improve-start --run-dir=",
            "follow the runtime": "\"Follow the returned action\" section",
            "commit review edits through ShipLoop": " improve-commit --run-dir=",
            "never edit the receipt": "Never write or edit the receipt",
            "recover an active child": "use its exact next_argv once to recover",
            "restart a stopped child": "--restart-stopped",
            "return only after the terminal packet": "Return order:",
            "pause without losing the child": "Pause parent without losing child",
            "import through the parent callback": " improve-complete --run-dir=",
        }
        for name, text in obligations.items():
            with self.subTest(obligation=name):
                self.assertIn(text, full)
        for gone in ("Binding inputs: before start", "Start inputs owned by ShipLoop",
                     "Start the child runtime with --receipt", self.bound["contract_marker"]):
            self.assertNotIn(gone, full)
        self.assertEqual(full.count("Never write or edit the receipt"), 1)

    def test_improve_start_freezes_the_contract_and_starts_the_runtime(self):
        """The parent writes four opening sections; ShipLoop writes the contract and starts the child.

        On both routes: the Ask-Agent route's hand-built contract omitted the binding line in the
        Codex E2E run (551b8b49), so ShipLoop starts that child too.
        """
        receipt = bridge.receipt_path(self.bound)
        opening = receipt.with_name("opening.md")
        start = [CLI, "improve-start", "--run-dir", self.run, "--action", self.action, "--opening", opening]
        refused = self.invoke(*start, status=2)
        self.assertIn("write the opening file first", refused.stderr)
        opening.parent.mkdir(parents=True, exist_ok=True)
        opening.write_text("## Current context and desired improvements\nTighten the spec.\n\n## Scope\nspec.md\n",
                           encoding="utf-8")
        self.assertIn("## Authority", self.invoke(*start, status=2).stderr)
        sections = ("## Current context and desired improvements\nTighten the spec examples.\n\n"
                    "## Scope\nproduct/contracts/cold-recovery.md and test/product_contract_test.py\n\n"
                    "## Authority\nUser launch instruction: local edits and scoped commits; no push.\n\n"
                    "## Environment\nPython 3 fixture; no network.\n")
        opening.write_text(sections + self.bound["contract_marker"] + "\n", encoding="utf-8")
        self.assertIn("must not contain the binding line", self.invoke(*start, status=2).stderr)
        self.assertFalse(receipt.exists())
        before = (self.run / "state.md").read_bytes()

        opening.write_text(sections, encoding="utf-8")
        started = self.invoke(*start)
        # stdout is only the runtime packet, so a host can parse it as JSON.
        self.assertIn("Improve child started from the frozen contract", started.stderr)
        body = started.stdout
        first = json.loads(body)
        self.assertEqual(first["status"], "active")
        self.assertEqual(receipt.read_text(encoding="utf-8"), body)
        self.assertEqual(Path(first["state_file"]).parent, self.run / "until-loop")
        contract = json.loads(receipt.with_name("start.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["workspace"], self.bound["workspace"])
        self.assertEqual(contract["required_trivial_reviews"], 2)
        owner = str(receipt.with_name("host-owner.md"))
        locators = [row["locator"] for row in contract["context"]["resources"]]
        # The delegated route's worker coordinates through the owner record; inline has none.
        self.assertEqual(owner in locators, not self.inline())
        self.assertEqual(contract["context"]["request"].splitlines()[0], self.bound["contract_marker"])
        # S-10: the review loop's exit carries the reviewed stage's own done-when criteria.
        stage = self.bound["stage"]
        for criterion in navigator.stage_spec.stage(stage).done_when:
            self.assertIn(criterion, contract["exit_condition"])
        self.assertIn("The " + stage + " result meets its own done-when criteria", contract["exit_condition"])
        # A record without its fence is refused with its path and the expected shape.
        raw = receipt.parent / "raw.json"
        raw.write_text('{"summary": "x"}\n', encoding="utf-8")
        with self.assertRaisesRegex(navigator.store.StorageError, r"raw\.json: .*found 0.*raw JSON is not accepted"):
            navigator.store.read_record(raw)
        request = contract["context"]["request"]
        self.assertEqual(request.splitlines()[0], self.bound["contract_marker"])
        self.assertIn("Tighten the spec examples.", request)
        self.assertIn("Always excluded: .until-loop, .shiploop-improve", contract["context"]["scope"])
        self.assertIn("No push or merge", contract["context"]["authority"])
        locators = {r["purpose"]: r["locator"] for r in contract["context"]["resources"]}
        self.assertEqual(locators["latest child packet receipt"], str(receipt))
        self.assertEqual(locators["review evidence directory (review-<n>.md per pass, checks.md)"],
                         str(receipt.parent / "reviews"))
        route = Path(locators["exact parent return instructions"]).read_text(encoding="utf-8")
        self.assertIn("improve-complete", route)
        self.assertEqual(first["context"], contract["context"])
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        again = self.invoke(*start, status=2)
        self.assertIn("already started", again.stderr)

        self.packet_path = receipt
        self.finish_ephemeral(first)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        state = store.read_record(self.run / "state.md")
        self.assertIsNone(state["active_improve"])
        self.assertEqual(state["improve_results"][self.action]["runtime_phase"], "complete")

    def test_improve_start_refuses_an_oversized_opening_before_anything_is_written(self):
        """A contract that fills the runtime's state file could never save its first report (batch 1003, F3)."""
        receipt = bridge.receipt_path(self.bound)
        opening = receipt.with_name("opening.md")
        start = [CLI, "improve-start", "--run-dir", self.run, "--action", self.action, "--opening", opening]
        opening.parent.mkdir(parents=True, exist_ok=True)

        def sections(environment):
            return ("## Current context and desired improvements\nTighten the spec examples.\n\n"
                    "## Scope\nproduct/contracts/cold-recovery.md\n\n"
                    "## Authority\nLocal edits and scoped commits; no push.\n\n"
                    "## Environment\n" + environment + "\n")

        environment = ("Python 3 fixture; the long runtime inventory follows. " * 260).strip()
        opening.write_text(sections(environment), encoding="utf-8")
        refused = self.invoke(*start, status=2)
        self.assertIn("over its 9,216-byte budget", refused.stderr)
        # The refusal names the opening's own headings and how many bytes the sections may use, not contract parts.
        self.assertIn("Environment ", refused.stderr)
        self.assertNotIn("context.environment", refused.stderr)
        self.assertRegex(refused.stderr, r"may use about [\d,]+ bytes in all")
        # the sizes listed are the sections' own bytes, comparable to that allowance (F4), not whole contract fields
        self.assertIn(f"Environment {loop_contract.text_bytes(environment):,}", refused.stderr)
        self.assertIn("put long detail in a file whose path you name", refused.stderr)
        self.assertFalse(receipt.exists(), "nothing was started")
        self.assertFalse(receipt.with_name("start.json").exists(), "no contract was written")

        opening.write_text(sections("Python 3 fixture; no network."), encoding="utf-8")
        started = self.invoke(*start)
        self.assertEqual(json.loads(started.stdout)["status"], "active")

    def test_improve_commit_commits_only_the_reviews_uncommitted_changes(self):
        """The model writes the message with a file tool; ShipLoop stages and commits."""
        if not self.inline():
            self.skipTest("improve-commit is the inline route")
        git = lambda *a: subprocess.run(["git", "-C", str(self.repo), *a], check=True, capture_output=True,
                                        text=True, env=self.environment).stdout
        git("init", "-q")
        git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "add", "-A")
        git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        (self.repo / "scratch.txt").write_text("user's own uncommitted note\n", encoding="utf-8")
        self._start_parent_at_stage("test-strategy", [str(self.product_contract)])
        receipt = bridge.receipt_path(self.bound)
        message = receipt.with_name("commit-message.md")
        commit = [CLI, "improve-commit", "--run-dir", self.run, "--action", self.action, "--message", message]
        self.assertIn("improve-commit", self.invoke(CLI, "next", "--run-dir", self.run).stdout)
        self.assertIn("write the commit message with a file tool first", self.invoke(*commit, status=2).stderr)
        message.parent.mkdir(parents=True, exist_ok=True)
        message.write_text("docs: tighten the contract example\n\nReview found a vague example.\n", encoding="utf-8")
        self.assertIn("Nothing to commit", self.invoke(*commit).stdout)
        self.assertFalse(message.exists())  # a no-op consumes the message: it cannot be committed later by accident
        self.product_contract.write_text("# Product contract\n\n## child-contract-transfer\nExact.\n",
                                         encoding="utf-8")
        message.write_text("docs: tighten the contract example\n\nReview found a vague example.\n"
                           "\nKey learnings: an exact example catches drift.\n", encoding="utf-8")
        before = git("rev-parse", "HEAD").strip()
        done = self.invoke(*commit).stdout
        head = git("rev-parse", "HEAD").strip()
        self.assertNotEqual(head, before)
        self.assertIn("Committed this review's changes as " + head[:12], done)
        self.assertEqual(git("show", "--name-only", "--format=", "HEAD").split(),
                         ["product/contracts/cold-recovery.md"])
        self.assertEqual(git("log", "-1", "--format=%s").strip(), "docs: tighten the contract example")
        self.assertIn("?? scratch.txt", git("status", "--porcelain"))
        self.assertFalse(message.exists())

    def test_empty_initial_commit_retains_selected_untracked_scope_through_child_recovery(self):
        """Exercise immutable transport; synthetic reports do not prove review conduct."""
        def git(*args):
            result = subprocess.run(
                ["git", "-C", str(self.repo), *args], text=True, capture_output=True,
                timeout=30, env=self.environment,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            return result.stdout.strip()

        git("init", "-q")
        git("config", "user.email", "fixture@example.invalid")
        git("config", "user.name", "Fixture")
        git("config", "commit.gpgsign", "false")
        git("config", "core.hooksPath", "/dev/null")
        git("commit", "--allow-empty", "-qm", "empty initial scope baseline")
        initial_head = git("rev-parse", "HEAD")
        self.assertEqual(git("show", "--format=", "--name-only", "HEAD"), "")

        product = self.repo / "product/checkers.py"
        requirements = self.repo / "docs/requirements.md"
        scratch = self.repo / "scratch/notes.md"
        for path, body in (
            (product, "def move_piece():\n    return 'ok'\n"),
            (requirements, "# Requirements\n\n- A player can move a piece.\n"),
            (scratch, "Unrelated working note.\n"),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
        status_before_child = git("status", "--porcelain=v1", "--untracked-files=all")
        for path in (product, requirements, scratch):
            self.assertIn("?? " + str(path.relative_to(self.repo)), status_before_child)
        index_before = (self.repo / ".git/index").read_bytes()

        base_context = self.child_context()
        selected_resources = [
            {"purpose": "selected untracked product candidate", "locator": str(product)},
            {"purpose": "selected untracked requirements", "locator": str(requirements)},
        ]
        manual_context = {
            "request": (
                "Synthetic empty-history candidate-scope fixture.\n"
                + self.bound["contract_marker"]
                + "\nDo exactly one review cycle per returned callback."
            ),
            "scope": (
                "Frozen candidate inventory at " + initial_head + ": include "
                + str(product) + " and " + str(requirements) + "; exclude "
                + str(scratch) + ". The empty initial commit and unchanged HEAD "
                + "do not replace this candidate."
            ),
            "authority": EXPLICIT_NO_COMMIT_AUTHORITY,
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": base_context["resources"] + selected_resources,
        }
        self.assertNotIn(str(scratch), [resource["locator"] for resource in manual_context["resources"]])
        self.assertIn(str(scratch), manual_context["scope"])
        contract = self.child_contract()
        contract["context"] = manual_context

        start_raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base), *self.receipt_args()], contract
        )
        self.assertEqual(first["status"], "active")
        self.save_packet(start_raw)
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], manual_context)
        self.assertEqual(cold["context"]["resources"][-2:], selected_resources)
        self.save_packet(cold_raw)

        _raw, second = self.done_ephemeral(
            cold, self.child_report("non-trivial", "unsatisfied", "allowed", "synthetic fixture finding")
        )
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], manual_context)

        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        archive = self.run / "improve" / self.action / "terminal.json"
        archived = json.loads(archive.read_text(encoding="utf-8"))
        self.assertEqual(archive.read_bytes(), terminal_raw.stdout)
        self.assertEqual(archived["context"], manual_context)
        self.assertEqual(store.read_record(self.run / "state.md")["improve_results"][self.action]["runtime_phase"], "complete")

        self.assertEqual(git("rev-parse", "HEAD"), initial_head)
        self.assertEqual((self.repo / ".git/index").read_bytes(), index_before)
        status_after_child = git("status", "--porcelain=v1", "--untracked-files=all")
        for path in (product, requirements, scratch):
            self.assertIn("?? " + str(path.relative_to(self.repo)), status_after_child)
        self.assertEqual(product.read_text(encoding="utf-8"), "def move_piece():\n    return 'ok'\n")
        self.assertEqual(requirements.read_text(encoding="utf-8"), "# Requirements\n\n- A player can move a piece.\n")
        self.assertEqual(scratch.read_text(encoding="utf-8"), "Unrelated working note.\n")

    def test_current_system_baseline_and_delta_survive_bound_child_recovery(self):
        """Host-authored references survive real child CLI recovery and import.

        Predecessor navigation and judgments are synthetic. This does not prove
        the child interpreted the spec; it verifies the explicit handoff duty
        and transport of two distinct product artifacts through the bound runtime.
        """
        baseline = self.repo / "docs/current-system.md"
        delta = self.base / "incoming-spec.md"
        baseline.parent.mkdir(parents=True)
        baseline.write_text(
            "# Current system\n\n## as-of-v1\nObserved: polling runs missed jobs once.\n",
            encoding="utf-8",
        )
        delta.write_text(
            "# Incoming request\n\n## tag-filter\nAdd selection; preserve missed-run behavior.\n",
            encoding="utf-8",
        )
        refs = [str(baseline) + "#as-of-v1", str(delta) + "#tag-filter"]
        self._start_parent_at_stage("spec", refs)
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        for locator in refs:
            self.assertIn(locator, packet)
        handoff = " ".join(packet.split())
        self.assertIn("carry selected prior-baseline and incoming-spec sections", handoff)
        self.assertIn("into this child's existing contract before review", handoff)

        # The host must author this context; ShipLoop does not read the artifacts
        # or populate the semantic child contract automatically.
        contract = self.child_contract()
        context = self.child_context()
        context["resources"][-2:] = [
            {"purpose": "prior as-of baseline", "locator": refs[0]},
            {"purpose": "incoming change specification", "locator": refs[1]},
        ]
        contract["context"] = context
        raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base), *self.receipt_args()],
            contract,
        )
        self.save_packet(raw)
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(cold["context"], context)
        self.save_packet(cold_raw)
        _raw, second = self.done_ephemeral(
            cold, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            second, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], context)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run,
                    "--action", self.action, *completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-strategy")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

    def test_skill_assess_local_skill_bundle_survives_actual_child_cold_recovery(self):
        """A host-authored child contract retains concrete local-skill locators.

        Earlier navigation and the review judgments are synthetic fixtures.  The
        selected parent (spec; skill-assess is no longer a checkpoint stage),
        ephemeral callbacks, terminal receipt, and parent resume use the real
        ShipLoop/Improve CLIs.
        """
        index = self.repo / "SHIPLOOP.md"
        local_card = self.repo / "skills/release-evidence-triage/SKILL.md"
        input_contract = self.repo / "docs/release-contract.md"
        validation = self.repo / "test/test_release_evidence.py"
        index.write_text(
            "# Fixture repository index\n\n## Local skills\n\n"
            "- [Release evidence](skills/release-evidence-triage/SKILL.md)\n",
            encoding="utf-8",
        )
        local_card.parent.mkdir(parents=True)
        local_card.write_text("# Release evidence triage\n", encoding="utf-8")
        input_contract.parent.mkdir(parents=True)
        input_contract.write_text("# Release contract\n\n## current-input\n", encoding="utf-8")
        validation.parent.mkdir(exist_ok=True)
        validation.write_text("def test_current_contract():\n    pass\n", encoding="utf-8")
        local_skill_refs = [
            str(index) + "#local-skills",
            str(local_card) + "#release-evidence-triage",
            str(input_contract) + "#current-input",
            str(validation) + "::test_current_contract",
        ]
        self._start_parent_at_stage("spec", local_skill_refs)
        self.assertEqual(navigator.current_stage(self.state), "spec")
        parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("Current action: Improve the completed spec result.", parent_packet)
        for locator in local_skill_refs:
            self.assertIn(locator, parent_packet)

        # This separate-process cold packet must tell the host to author the
        # transfer below. Resource transport alone would pass without that duty.
        handoff = " ".join(parent_packet.split())
        for clause in (
            "When this candidate selects, uses or changes a repository-local skill",
            "effective input/default sources",
            "into this child's existing contract/review notes before the first review",
            "current defaults and preserved older uses",
            "A no-fit decision needs its inspected sources and rationale",
            "a successful runtime receipt alone cannot prove skill use",
        ):
            self.assertIn(clause, handoff)

        base_context = self.child_context()
        manual_context = {
            "request": (
                "Host-authored fixture child contract for the selected local skill; "
                "the parent packet cannot create this semantic handoff.\n"
                + self.bound["contract_marker"]
            ),
            "scope": "Review only the frozen spec evidence bundle and its retained locators.",
            "authority": EXPLICIT_NO_COMMIT_AUTHORITY,
            "environment": "Use the current fixture workspace and declared Python/Git commands only.",
            "resources": base_context["resources"][:6] + [
                {"purpose": "repository local skill index", "locator": local_skill_refs[0]},
                {"purpose": "selected repository local skill card", "locator": local_skill_refs[1]},
                {"purpose": "selected skill input contract", "locator": local_skill_refs[2]},
                {"purpose": "selected skill validation", "locator": local_skill_refs[3]},
            ],
        }
        contract = self.child_contract()
        contract["work"] = "Host-authored fixture review of a frozen local-skill selection."
        contract["context"] = manual_context
        start_raw, first = self.invoke_argv(
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base), *self.receipt_args()], contract
        )
        self.assertEqual(first["status"], "active")
        self.save_packet(start_raw)
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], manual_context)
        self.assertEqual(cold["context"]["resources"][-4:], manual_context["resources"][-4:])
        self.save_packet(cold_raw)

        _raw, second = self.done_ephemeral(
            cold, self.child_report("non-trivial", "unsatisfied", "allowed", "synthetic fixture finding")
        )
        _raw, third = self.done_ephemeral(
            second, self.child_report("trivial", "unsatisfied", "allowed", "synthetic first review")
        )
        terminal_raw, terminal = self.done_ephemeral(
            third, self.child_report("trivial", "satisfied", "allowed", "synthetic second review")
        )
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], manual_context)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-strategy")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], local_skill_refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        resumed_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("ShipLoop navigator | test-strategy |", resumed_packet)

    def test_active_stopped_and_missing_ephemeral_receipts_do_not_release_parent(self):
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion, status=2)
        _raw, active = self.start_ephemeral_child()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion, status=2)
        _raw, stopped = self.done_ephemeral(active, self.child_report("unresolved", "unknown", "blocked", "fixture blocker"))
        self.assertEqual(stopped["status"], "stopped")
        self.assertFalse(Path(stopped["state_file"]).exists())
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion, status=2)
        self.packet_path.unlink()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_a_reviewed_step_plan_that_pairs_skill_na_with_a_skill_file_is_refused_at_improve_complete(self):
        """The Improve child may revise the step plan; the gate that checks the producer result checks its final_result."""
        reason = "No repo-local skill applies: README.md is the index and names none."
        self._start_parent_at_stage("step-plan", [str(self.product_contract)], producer_extra={"skill_na": reason})
        self.finish_ephemeral()
        contradictory = dict(self.producer, paths=["src/**", ".claude/skills/review/SKILL.md"])
        completion, _receipt = self.completion_receipt(final_result=contradictory)
        before = (self.run / "state.md").read_bytes()
        refused = self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                              *completion, status=2)
        self.assertIn("skill_na", refused.stderr)
        self.assertIn(".claude/skills/review/SKILL.md", refused.stderr)
        self.assertIn("resubmit the step plan without skill_na", refused.stderr)
        # The same function serves complete and improve-complete, so its tail names neither verb.
        self.assertIn("run the same command again", refused.stderr)
        self.assertNotIn("complete command", refused.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())
        # The named exit: the final result without skill_na is accepted by the same command.
        plain = {key: value for key, value in contradictory.items() if key != "skill_na"}
        completion, _receipt = self.completion_receipt(final_result=plain)
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-spec")
        self.assertNotIn("skill_na", resumed["accepted"][self.action])

    def test_a_wrong_result_path_is_refused_with_the_expected_path(self):
        """Batch 1.12.1: Luna passed the worktree as --result; the refusal now names the path to use."""
        import types
        with self.assertRaisesRegex(navigator.NavigatorError, re.escape(str(self.run / "inbox" / (self.action + ".md")))):
            navigator._submitted_result(self.run, types.SimpleNamespace(action=self.action, result=str(self.repo)))

    def test_linked_review_file_cannot_be_imported_or_advance(self):
        self.finish_ephemeral()
        completion, receipt = self.completion_receipt()
        review = Path(receipt["review_refs"][-1])
        original = review.with_name("elsewhere.md")
        review.replace(original)
        review.symlink_to(original)
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_completion_names_the_review_files_it_needs(self):
        self.finish_ephemeral()
        evidence = bridge.receipt_path(self.bound).parent / "reviews"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "first pass.md").write_text("misnamed\n", encoding="utf-8")
        before = (self.run / "state.md").read_bytes()
        result = self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, status=2)
        self.assertIn("named review-<n>.md by pass number; found: none", result.stderr)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_relative_skill_selection_remains_bound_for_cold_recovery(self):
        selected = self.base / "selected-improve.md"
        selected.symlink_to(CARD)
        run = self.base / "relative-selection-run"
        self.invoke(CLI, "init", "--repo", self.repo, "--run-dir", run,
                    "--prompt", "Relative selection recovery fixture", "--improve-skill", selected.name)
        state = store.read_record(run / "state.md")
        # intake, discovery and research are not planning stages; advance them
        # directly before the first checkpoint (spec) binds the relative card.
        for _predecessor in ("intake", "discovery", "research"):
            action = state["action"]["id"]
            result_path = run / "inbox" / (action + ".md")
            store.write_record(result_path, {"outcome": "done", "summary": "Fixture producer"})
            self.invoke(CLI, "complete", "--run-dir", run, "--action", action, "--result", result_path)
            state = store.read_record(run / "state.md")
        action = state["action"]["id"]
        result_path = run / "inbox" / (action + ".md")
        store.write_record(result_path, {"outcome": "done", "summary": "Fixture producer"})
        self.invoke(CLI, "complete", "--run-dir", run, "--action", action, "--result", result_path)
        before = (run / "state.md").read_bytes()
        cold = subprocess.run([sys.executable, "-B", str(CLI), "next", "--run-dir", str(run)], cwd="/",
                              text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(cold.returncode, 0, cold.stderr)
        self.assertIn("--skill-card=" + str(selected), cold.stdout)
        bound = subprocess.run([sys.executable, "-B", str(CLI), "improve-bind", "--run-dir", str(run),
                                "--action", action, "--skill-card", state["improve_skill"]], cwd="/",
                               text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(bound.returncode, 0, bound.stderr)
        self.assertNotEqual(before, (run / "state.md").read_bytes())
        skill = store.read_record(run / "state.md")["active_improve"]["skill"]
        self.assertEqual(skill["skill_card"], str(CARD.resolve()))
        self.assertEqual(skill["runtime_cli"], str(EPHEMERAL.resolve()))

    def test_workspace_return_excludes_ephemeral_improve_artifacts(self):
        """Return is allowed only once at active release or handoff; no child ever binds there.

        Earlier navigation is synthetic setup; the spec parent's real Improve
        child (ephemeral runtime, terminal receipt, import) and the final
        return/exclusion checks use the actual command-line interfaces.
        """
        source = self.base / "source"
        source.mkdir()
        for args in (("init", "-q"), ("config", "user.email", "fixture@example.invalid"),
                     ("config", "user.name", "Fixture"), ("config", "commit.gpgsign", "false"),
                     ("config", "core.hooksPath", "/dev/null")):
            subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True, env=self.environment)
        (source / "product.txt").write_text("baseline\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(source), "add", "product.txt"], check=True, capture_output=True, env=self.environment)
        subprocess.run(["git", "-C", str(source), "commit", "-qm", "baseline"], check=True, capture_output=True, env=self.environment)
        workspace = self.base / "isolated"
        self.invoke(CLI, "workspace", "start", "--repo", source, "--workspace-root", workspace,
                    "--prompt", "Synthetic final return boundary fixture", "--improve-skill", CARD)
        self.repo, self.run = workspace / "worktree", workspace / "run"
        self.product_contract = self.product_test = self.repo / "product.txt"
        self._prepare_parent_evidence()
        state = store.read_record(self.run / "state.md")
        # intake, discovery and research are not planning stages; advance
        # them directly, then run one real Improve child at spec so its
        # `.shiploop-improve` artifacts exist to verify exclusion below.
        for _predecessor in ("intake", "discovery", "research"):
            action = navigator.current_action(state)["id"]
            state = navigator.apply(state, action, {"outcome": "done", "summary": "Synthetic setup"})
        navigator.save(self.run, state)
        self.action = navigator.current_action(state)["id"]
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, {"outcome": "done", "summary": "Fixture spec evidence.",
                                        "evidence_refs": self.parent_evidence_refs})
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(CARD)
        completion, receipt = self.completion_receipt()
        _raw, active = self.start_ephemeral_child()
        # Refused long before release/handoff, active child or not.
        self.invoke(CLI, "workspace", "return", "--workspace-root", workspace, status=2)
        self.assertEqual((source / "product.txt").read_text(encoding="utf-8"), "baseline\n")
        (self.repo / "product.txt").write_text("final child reviewed candidate\n", encoding="utf-8")
        # An Improve review commits its own changes; the import refuses them uncommitted.
        subprocess.run(["git", "-C", str(self.repo), "commit", "-qm", "review: final candidate", "--",
                        "product.txt"], check=True, capture_output=True)
        terminal_raw, terminal = self.finish_ephemeral(active)
        self.assertEqual(terminal["status"], "complete")
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, *completion)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

        # Advance the remaining checkpoints and stages to handoff.  Every
        # planning/contract result still starts and finishes a real Improve
        # child; every other stage (including release and handoff) advances
        # directly and never parks one.
        state = store.read_record(self.run / "state.md")
        while navigator.current_stage(state) != "handoff":
            stage = navigator.current_stage(state)
            action = navigator.current_action(state)["id"]
            setup = {"outcome": "done", "summary": "Synthetic " + stage + " advance."}
            if stage == "plan":
                setup["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state = navigator.apply(state, action, setup)
            if state.get("active_improve") is not None:
                state = navigator.finish_improve(state, action, {
                    "summary": "Synthetic predecessor receipt only; no semantic review claim.",
                })
        navigator.save(self.run, state)

        # handoff never parks a child, so return is allowed immediately. The
        # return gate for a parked child is pinned in shiploop-workspace.test.py.
        self.invoke(CLI, "workspace", "plan-return", "--workspace-root", workspace)
        plan_path = workspace / "return-plan.md"
        plan = store.read_record(plan_path)
        self.assertTrue(any(".shiploop-improve" in Path(row["path"]).parts for row in plan["paths"]))
        for row in plan["paths"]:
            if ".shiploop-improve" in Path(row["path"]).parts:
                self.assertEqual(row["disposition"], "exclude")
            else:
                row["disposition"] = "keep"
        store.write_record(plan_path, plan)
        self.invoke(CLI, "workspace", "return", "--workspace-root", workspace)
        self.assertEqual((source / "product.txt").read_text(encoding="utf-8"), "final child reviewed candidate\n")
        self.assertFalse((source / ".shiploop-improve").exists())

        action = navigator.current_action(state)["id"]
        input_path = self.run / "inbox" / (action + ".md")
        store.write_record(input_path, {"outcome": "done", "summary": "Final fixture handoff",
                                        "evidence_refs": self.parent_evidence_refs})
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", action, "--result", input_path)
        self.assertEqual(store.read_record(self.run / "state.md")["status"], "done")
        self.assertEqual(receipt["summary"], "Improve reviewed the spec result; it ended on 2 trivial passes.")


class LoopContractSizeTests(unittest.TestCase):
    """The Until Loop saves its whole state in 16 KiB; a contract must leave room for the first report."""

    @staticmethod
    def contract(request="r", environment="e"):
        return loop_contract.contract(
            workspace="/w", work="work", exit_condition="exit", repeat_condition="repeat",
            required_trivial_reviews=2, request=request, scope="s", authority="a", environment=environment,
            resources=[{"purpose": "p", "locator": "/l"}])

    @staticmethod
    def runtime():
        import importlib.util
        path = ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
        spec = importlib.util.spec_from_file_location("until_loop_ephemeral_for_test", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_the_state_limit_is_the_bound_runtime_s_own(self):
        runtime = (ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py").read_text()
        match = re.search(r"^MAX_STATE_BYTES = (\d+) \* 1024$", runtime, re.M)
        self.assertIsNotNone(match)
        self.assertEqual(loop_contract.STATE_LIMIT, int(match.group(1)) * 1024)
        self.assertEqual(loop_contract.CONTRACT_BUDGET + loop_contract.STATE_OVERHEAD + loop_contract.REPORT_RESERVE,
                         loop_contract.STATE_LIMIT)

    def test_contract_bytes_are_the_runtime_s_serialization_including_non_ascii_text(self):
        runtime = self.runtime()
        with tempfile.TemporaryDirectory() as workspace:  # the runtime requires an existing absolute directory
            for text in ("plain ascii", "日本語の環境", "em dash \u2014 and \u201cquotes\u201d", "emoji \U0001f600 text"):
                with self.subTest(text=text):
                    contract = self.contract(request=text * 40, environment=text)
                    contract["workspace"] = workspace
                    normalized = runtime._validate_contract(contract, input_contract=True)
                    expected = len(json.dumps(normalized, separators=(",", ":"), sort_keys=True).encode("utf-8"))
                    self.assertEqual(loop_contract.compact_bytes(contract), expected)
        # a non-ASCII character is escaped to 6 bytes (12 for an emoji), far above its UTF-8 length
        self.assertGreater(loop_contract.compact_bytes(self.contract(request="\u2014" * 100)),
                           loop_contract.compact_bytes(self.contract(request="x" * 100)) + 400)

    def test_a_small_contract_fits_and_the_budget_is_an_exact_boundary(self):
        self.assertIsNone(loop_contract.size_problem(self.contract()))
        base = loop_contract.compact_bytes(self.contract(request=""))
        exact = self.contract(request="x" * (loop_contract.CONTRACT_BUDGET - base))
        self.assertEqual(loop_contract.compact_bytes(exact), loop_contract.CONTRACT_BUDGET)
        self.assertIsNone(loop_contract.size_problem(exact))
        over = self.contract(request="x" * (loop_contract.CONTRACT_BUDGET - base + 1))
        self.assertIn("1 over its 9,216-byte budget", loop_contract.size_problem(over))

    def test_a_japanese_opening_is_refused_at_its_real_size(self):
        # 8,757 bytes counted as UTF-8 slipped through before; the runtime stores it at about 13.5 KB.
        problem = loop_contract.size_problem(self.contract(environment="環境" * 1900))
        self.assertIsNotNone(problem)

    def test_the_refusal_names_the_sections_the_model_wrote_and_how_far_over_it_is(self):
        contract = self.contract(environment="e" * 9000, request="r" * 4000)
        problem = loop_contract.size_problem(
            contract, writable={"context.request": "Current context and desired improvements",
                                "context.environment": "Environment"}, allowance=4300)
        total = loop_contract.compact_bytes(contract)
        self.assertIn(f"{total - loop_contract.CONTRACT_BUDGET:,} over its 9,216-byte budget", problem)
        self.assertLess(problem.index("Environment 9,"), problem.index("Current context and desired improvements 4,"))
        # given the sections' own sizes, those are listed instead of the wrapped contract fields
        own = loop_contract.size_problem(
            contract, writable={"context.request": "Current context and desired improvements",
                                "context.environment": "Environment"}, allowance=4300,
            sizes={"Environment": 9000, "Current context and desired improvements": 2600})
        self.assertIn("Environment 9,000, Current context and desired improvements 2,600", own)
        self.assertEqual(loop_contract.text_bytes("日本"), 12)  # escaped like the runtime: 6 bytes per character
        self.assertNotIn("context.", problem)
        self.assertIn("may use about 4,300 bytes in all", problem)
        self.assertIn("16,384 bytes", problem)
        # without a writable map the generic text lists contract parts
        self.assertIn("context.environment", loop_contract.size_problem(contract))

    def test_the_backchain_budget_is_stated_at_every_stage_that_can_start_a_loop(self):
        guidance = prompts._backchain_guidance("plan")
        self.assertIn("Until Loop state budget", guidance)
        self.assertIn("16,384 bytes", guidance)
        self.assertIn("at most 9,216 bytes", guidance)
        self.assertIn("separators=(',', ':'), sort_keys=True", guidance)
        self.assertNotIn("{state_limit", guidance)
        # every stage that can start a Backchain Until Loop child states it: plan, and the repair/revise
        # route at the audit stages (the 1.16.1 Luna run built an 11.9 KB step-plan contract without it)
        self.assertEqual(set(prompts.BACKCHAIN_STAGES), {"plan", "spec", "step-plan", "carry-forward", "product-acceptance"})
        for stage in prompts.BACKCHAIN_STAGES:
            with self.subTest(stage=stage):
                self.assertIn("Until Loop state budget", prompts._backchain_guidance(stage))
        # the Improve-owner text starts no whole Backchain child, and a stage with no Backchain action has no loop
        self.assertNotIn("Until Loop state budget", prompts._backchain_guidance("plan", improve_owner=True))
        self.assertNotIn("Until Loop state budget", prompts._backchain_guidance("step-plan", improve_owner=True))
        self.assertNotIn("Until Loop state budget", prompts._backchain_guidance("intake"))

    def test_the_measuring_command_in_the_guidance_gives_the_number_the_check_uses(self):
        guidance = prompts._backchain_guidance("plan")
        command = re.search(r"`(python3 -c \".*?\" CONTRACT_FILE)`", guidance).group(1)
        with tempfile.TemporaryDirectory() as temp:
            contract = Path(temp) / "contract.json"
            contract.write_text(json.dumps(self.contract(request="日本語 \u2014 " * 50)), encoding="utf-8")
            argv = [sys.executable, "-c", re.search(r'-c "(.*)" CONTRACT_FILE', command).group(1), str(contract)]
            out = subprocess.run(argv, capture_output=True, text=True, check=True).stdout.strip()
        self.assertEqual(int(out), loop_contract.compact_bytes(self.contract(request="日本語 \u2014 " * 50)))


class ImproveCommitContractTests(ImproveCliFixture):
    """improve-commit through the real CLI: what it checks, in what order, and that every refusal's named exit works.

    The shared helpers read LINE 1 of a refusal, take the command it ends with and run it, so a refusal that names
    an exit the gate then refuses cannot pass.  A neutral repository: nothing here comes from a saved run.
    """

    def _start_parent(self, card):
        """No parent yet: each test makes the repository a Git repository first, then binds at its stage."""

    def setUp(self):
        super().setUp()
        self.environment["HOME"] = str(self.base / "home")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True, text=True,
                              env=self.environment).stdout

    def begin(self, stage="test-strategy"):
        self.git("init", "-q")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "add", "-A")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-qm", "base")
        self.base_commit = self.git("rev-parse", "HEAD").strip()
        (self.repo / "scratch.txt").write_text("the user's own uncommitted note\n", encoding="utf-8")
        self._start_parent_at_stage(stage, [str(self.product_contract)])
        self.message = bridge.receipt_path(self.bound).with_name("commit-message.md")
        self.message.parent.mkdir(parents=True, exist_ok=True)
        self.commit_args = [CLI, "improve-commit", "--run-dir", self.run, "--action", self.action,
                            "--message", self.message]

    def edit(self, text="Exact.\n"):
        self.product_contract.write_text("# Product contract\n\n## child-contract-transfer\n" + text, encoding="utf-8")

    def write(self, text):
        self.message.write_text(text, encoding="utf-8")

    def refused(self, *extra):
        return self.invoke(*self.commit_args, *extra, status=2).stderr

    def line_one(self, stderr):
        first = stderr.splitlines()[0]
        self.assertTrue(first.startswith("ShipLoop navigator: "), stderr)
        return first[len("ShipLoop navigator: "):]

    def named_exit(self, stderr):
        """The command LINE 1 ends with: what a model that reads nothing else would run."""
        line = self.line_one(stderr)
        self.assertIn("run: ", line)
        return shlex.split(line.rsplit("run: ", 1)[1])

    def run_named(self, stderr, status=0):
        result = subprocess.run(self.named_exit(stderr), text=True, capture_output=True, cwd=self.base, timeout=60,
                                env=self.environment)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def head_message(self):
        return self.git("log", "-1", "--format=%B").rstrip("\n") + "\n"

    def test_lessons_are_required_for_a_commit_and_the_named_exit_commits(self):
        """Fail-first: any message used to be committed."""
        self.begin()
        self.edit()
        self.write("docs: tighten the contract example\n\nReview found a vague example.\n")
        before = self.git("rev-parse", "HEAD").strip()
        stderr = self.refused()
        line = self.line_one(stderr)
        self.assertTrue(line.startswith('Add a "Key learnings:'), line)
        self.assertIn(str(self.message), line)
        self.assertIn("or none", line)  # the honest exit is on line 1: a model that reads only that does not invent
        self.assertIn("do not invent a lesson", stderr.splitlines()[1])
        self.assertEqual(before, self.git("rev-parse", "HEAD").strip())
        self.write("docs: tighten the contract example\n\nKey learnings: exact examples catch drift.\n")
        done = self.run_named(stderr).stdout
        self.assertIn("Committed this review's changes as ", done)
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), ["product/contracts/cold-recovery.md"])
        self.assertIn("Key learnings: exact examples catch drift.", self.head_message())
        self.assertIn("?? scratch.txt", self.git("status", "--porcelain"))
        self.assertFalse(self.message.exists())

    def test_every_form_the_grammar_reads_and_the_honest_none_are_accepted(self):
        """Guard, not fail-first: every message was accepted before the gate; this pins what it must still accept."""
        self.begin()
        for number, lessons in enumerate(("Key learnings: none", "## Key learnings\n- the first\n\n- the second",
                                          "**Key learnings:** pin it", "Lessons:\n\nthe label alone, then the text"), 1):
            with self.subTest(lessons=lessons):
                self.edit("Version " + str(number) + ".\n")
                self.write("docs: edit " + str(number) + "\n\n" + lessons + "\n\nCo-Authored-By: T <t@example.invalid>\n")
                before = self.git("rev-parse", "HEAD").strip()
                self.invoke(*self.commit_args)
                self.assertNotEqual(before, self.git("rev-parse", "HEAD").strip())

    def test_an_empty_lessons_label_and_a_one_paragraph_message_are_refused_with_what_to_fix(self):
        self.begin()
        self.edit()
        self.write("docs: x\n\nKey learnings:\n\nRemaining work: none\n")
        empty = self.refused()
        line = self.line_one(empty)
        self.assertTrue(line.startswith('The "Key learnings" label'), line)
        self.assertIn("has no text", line)
        self.write("docs: x\n\nReview: a. Plan: b. Changes: c. Validation: d. Key learnings: e. Remaining work: f.\n")
        stderr = self.refused()
        self.assertTrue(self.line_one(stderr).startswith('Add a "Key learnings:'))
        self.assertIn("on a line of its own starting in column 1", stderr.splitlines()[1])
        self.write("docs: x\n\n## Key learnings\n\nCo-Authored-By: T <t@example.invalid>\n")
        self.assertTrue(self.line_one(self.refused()).startswith('The "Key learnings" label'))  # a trailer is no lesson
        self.write("docs: x\n\n## Key learnings\n\nthe label had no text in it\n")  # the fix line 1 asks for
        self.run_named(empty)
        self.assertIn("the label had no text in it", self.head_message())

    def test_a_review_that_changed_nothing_never_asks_for_lessons_makes_no_commit_and_consumes_the_message(self):
        """Guard (it passes but for the last line): an unchanged pass is never asked for lessons (D4)."""
        self.begin()
        before = self.git("rev-parse", "HEAD").strip()
        for text in ("docs: nothing changed\n\nReview found nothing to change.\n",
                     "docs: nothing\n\nKey learnings: none\nRemote change: none\n"):
            self.write(text)
            done = self.invoke(*self.commit_args).stdout
            self.assertIn("Nothing to commit", done)
            self.assertEqual(before, self.git("rev-parse", "HEAD").strip())
            self.assertFalse(self.message.exists(), "a stale message must not be committable later")
        # the stale message is gone: changing a file now needs a message written for it
        self.edit()
        self.assertIn("write the commit message with a file tool first", self.refused())

    def test_the_file_refusals_each_name_the_command_and_the_empty_file_does_not_ask_for_lessons(self):
        self.begin()
        self.edit()
        stderr = self.invoke(CLI, "improve-commit", "--run-dir", self.run, "--action", self.action,
                             "--message", self.base / "elsewhere.md", status=2).stderr
        self.assertIn("must be the printed file " + str(self.message), self.line_one(stderr))
        stderr = self.run_named(stderr, status=2).stderr
        self.assertIn("write the commit message with a file tool first", self.line_one(stderr))
        self.write("   \n")
        stderr = self.run_named(stderr, status=2).stderr
        line = self.line_one(stderr)
        self.assertIn("the commit message file is empty", line)
        self.assertNotIn("Key learnings", line)
        self.write("docs: fix\n\nKey learnings: none\n")
        self.run_named(stderr)
        self.assertNotEqual(self.base_commit, self.git("rev-parse", "HEAD").strip())

    def test_a_child_that_is_no_longer_bound_and_a_missing_bind_snapshot_each_get_a_remedy(self):
        self.begin()
        self.edit()
        self.write("docs: fix\n\nKey learnings: none\n")
        stderr = self.invoke(CLI, "improve-commit", "--run-dir", self.run, "--action", "someone-elses-action",
                             "--message", self.message, status=2).stderr
        line = self.line_one(stderr)
        self.assertIn("no bound current Improve child for this action", line)
        self.assertIn(" next ", line)
        self.assertIn("ShipLoop navigator | ", self.run_named(stderr).stdout)  # `next` reads the packet and exits 0
        bind = self.run / "improve" / (self.action + "-bind.md")
        bind.unlink()
        stderr = self.refused()
        line = self.line_one(stderr)
        self.assertIn("no bind snapshot", line)
        # the frozen contract lets the child run improve-commit and nothing else: improve-complete is the parent's
        self.assertIn("The bound child stops here", line)
        self.assertIn("Parent, run: ", line)
        self.assertEqual(self.named_exit(stderr)[2], "improve-complete")

    def test_a_credential_is_refused_by_line_without_echoing_it_even_in_a_learned_from_token(self):
        self.begin()
        self.edit()
        secret, token = "Bearer abcdefghijklmnop12345678", "sk-abcdefghijklmnop123456"
        self.write("docs: fix\n\nKey learnings: the header was\nAuthorization: " + secret + "\nLearned-from: " + token
                   + " the pattern\n")
        stderr = self.refused()
        line = self.line_one(stderr)
        self.assertTrue(line.startswith("Reword lines 4, 5 of " + str(self.message)), line)
        for fragment in (secret, "abcdefghijklmnop", token, "sk-abc"):
            self.assertNotIn(fragment, stderr)
        # a line number is the editor's: a form feed or U+2028 inside a line does not start a new one
        self.write("docs: fix\n\nKey learnings: a page\x0cbreak and a line\u2028separator\nAuthorization: " + secret + "\n")
        self.assertTrue(self.line_one(self.refused()).startswith("Reword line 4 of " + str(self.message)))
        self.write("docs: fix\n\nKey learnings: the header was named in the config, not copied here.\n")
        self.run_named(stderr)
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), "docs: fix")

    def test_a_lesson_that_mentions_a_token_in_prose_is_reworded_not_dropped(self):
        self.begin()
        self.edit()
        self.write("docs: fix\n\nKey learnings: use the session token: it expires hourly\n")
        stderr = self.refused()
        self.assertTrue(self.line_one(stderr).startswith("Reword line 3 of "), stderr)
        self.assertIn("the lesson stays", stderr)

    def test_citations_are_resolved_by_git_and_a_prefix_is_written_as_the_full_id(self):
        self.begin()
        self.edit()
        full = self.base_commit
        self.git("checkout", "-q", "-b", "elsewhere")
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "elsewhere")
        stray = self.git("rev-parse", "HEAD").strip()
        self.git("checkout", "-q", "-")
        self.write("\n".join([
            "docs: fix", "", "Co-Authored-By: T <t@example.invalid>", "",
            "Learned-from: 0000000 an id that does not exist",
            "Learned-from: " + stray + " a commit that is on another branch",
            "Learned-from: main a branch is not a commit id",
            "Learned-from: " + full[:9],
            "Learned-from: `" + full[:8] + "`: the file layout of the base commit", ""]))
        stderr = self.refused()
        lines = stderr.splitlines()
        # lessons are missing too: one refusal lists everything, and line 1 says both fixes
        self.assertTrue(self.line_one(stderr).startswith('Add a "Key learnings:'), stderr)
        self.assertIn("Learned-from", self.line_one(stderr))
        problems = [row for row in lines if row.startswith("- line ")]
        self.assertEqual([row.split(":")[0] for row in problems], ["- line 5", "- line 6", "- line 7", "- line 8"])
        self.assertIn("names no commit in this repository", problems[0])
        self.assertIn("is not reachable from HEAD", problems[1])
        self.assertIn("is not a commit ID", problems[2])
        self.assertIn("say what the commit contributed", problems[3])
        self.assertNotIn("main a branch", stderr)
        self.assertEqual(self.git("rev-parse", "HEAD").strip(), full)
        # the fix: one good line (delete a line if that commit did not help), plus the lesson
        self.write("docs: fix\n\nKey learnings: the layout is one file.\nLearned-from: `" + full[:8]
                   + "`: the file layout of the base commit\n\nCo-Authored-By: T <t@example.invalid>\n")
        self.run_named(stderr)
        stored = self.head_message()
        self.assertIn("Learned-from: " + full + " the file layout of the base commit", stored)
        self.assertNotIn("`", stored)
        self.assertTrue(stored.endswith("Co-Authored-By: T <t@example.invalid>\n"))
        self.assertNotIn("none cited", stored)

    def test_a_citation_of_an_older_commit_is_accepted_and_one_ahead_of_head_is_refused(self):
        """Guard (batch 1012 review): the other citation tests cite HEAD itself, so 'only HEAD' passed them."""
        self.begin()
        self.edit()
        older = self.base_commit
        self.git("-c", "user.name=T", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "later")
        later = self.git("rev-parse", "HEAD").strip()
        self.assertNotEqual(older, later)
        self.write("docs: fix\n\nKey learnings: the layout is one file.\nLearned-from: " + older[:9] + " the original layout\n")
        self.invoke(*self.commit_args)
        self.assertIn("Learned-from: " + older + " the original layout", self.head_message())
        # a commit that is ahead of HEAD exists but is not reachable from it
        self.git("reset", "-q", "--hard", older)
        self.edit("Version 2.\n")
        self.write("docs: fix again\n\nKey learnings: none\nLearned-from: " + later[:9] + " a commit from the future\n")
        stderr = self.refused()
        self.assertIn("- line 4: the ID is not reachable from HEAD", stderr)
        self.assertEqual(older, self.git("rev-parse", "HEAD").strip())

    def test_a_lesson_written_as_hyphenated_token_lines_is_read_as_the_lesson(self):
        """Route test for 7d9e4255: the last paragraph of Root-cause:/Fix-applied: lines was clipped as a trailer block,
        so this exact message was refused with 'the label has no text' (red with the old grammar, see the journal)."""
        self.begin()
        self.edit()
        self.write("docs: fix\n\nKey learnings:\n\nRoot-cause: the mock hid the seam\nFix-applied: guard the parse\n")
        self.invoke(*self.commit_args)
        self.assertIn("Root-cause: the mock hid the seam", self.head_message())

    def test_a_git_failure_while_committing_names_the_fix_and_the_command_on_line_one(self):
        """Fail-first: the raw Git text was the whole refusal, with no fix and no command."""
        self.begin()
        self.edit()
        self.write("docs: fix\n\nKey learnings: none\n")
        lock = self.repo / ".git" / "index.lock"
        lock.write_text("", encoding="utf-8")
        stderr = self.refused()
        line = self.line_one(stderr)
        self.assertTrue(line.startswith("Git could not make the commit: fix the repository problem named below"), line)
        self.assertIn("index.lock", stderr)
        self.assertEqual(self.base_commit, self.git("rev-parse", "HEAD").strip())
        lock.unlink()  # the fix
        self.run_named(stderr)
        self.assertNotEqual(self.base_commit, self.git("rev-parse", "HEAD").strip())

    def test_the_checks_run_credentials_first_and_the_lessons_and_citations_come_in_one_refusal(self):
        self.begin()
        self.edit()
        self.write("docs: fix\n\nAuthorization: Bearer abcdefghijklmnop12345678\nLearned-from: 0000000 no such commit\n")
        first = self.refused()
        self.assertTrue(self.line_one(first).startswith("Reword line 3 of "), first)
        self.write("docs: fix\n\nLearned-from: 0000000 no such commit\n")
        second = self.refused()
        # one refusal, not one turn per problem: line 1 asks for both fixes and the problem lines follow
        self.assertTrue(self.line_one(second).startswith('Add a "Key learnings:'), second)
        self.assertIn("Learned-from", self.line_one(second))
        self.assertIn("- line 3: the ID names no commit in this repository", second)
        self.write("docs: fix\n\nKey learnings: none\n")
        self.run_named(second)

    def test_a_message_without_any_citation_is_accepted_and_a_citation_alone_is_not_enough(self):
        self.begin()
        self.edit()
        self.write("docs: fix\n\nLearned-from: " + self.base_commit + " the layout\n")
        self.assertTrue(self.line_one(self.refused()).startswith('Add a "Key learnings:'))  # a citation is not a lesson
        self.write("docs: fix\n\nKey learnings: the layout is one file.\n")
        self.invoke(*self.commit_args)

    def test_a_remote_change_with_the_flag_and_nothing_pending_makes_a_commit_with_no_files(self):
        self.begin()
        self.git("add", "scratch.txt")  # someone else's staged work must stay staged
        self.write("chore: record the staging cache purge\n\nRemote change: staging-site, purged the CDN cache, "
                   "evidence in the release log\nKey learnings: purge after every deploy.\n")
        before = self.git("rev-parse", "HEAD").strip()
        done = self.invoke(*self.commit_args, "--remote-change").stdout
        head = self.git("rev-parse", "HEAD").strip()
        self.assertNotEqual(before, head)
        self.assertIn("Committed this review's remote change as " + head[:12] + ": it changed no file.", done)
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), [])
        self.assertEqual(self.git("diff", "--cached", "--name-only").split(), ["scratch.txt"])
        self.assertIn("Remote change: staging-site", self.head_message())
        self.assertFalse(self.message.exists())
        # one message, one commit: the same file again is refused as missing
        self.assertIn("write the commit message with a file tool first", self.invoke(*self.commit_args, "--remote-change",
                                                                                    status=2).stderr)
        self.assertEqual(head, self.git("rev-parse", "HEAD").strip())

    def test_a_remote_change_section_without_the_flag_changes_nothing(self):
        """Guard (passes before the flag exists): a `Remote change: none` label must not make an empty commit."""
        self.begin()
        before = self.git("rev-parse", "HEAD").strip()
        self.write("docs: x\n\nKey learnings: none\nRemote change: staging-site, purged the cache\n")
        done = self.invoke(*self.commit_args).stdout
        self.assertIn("Nothing to commit", done)
        self.assertEqual(before, self.git("rev-parse", "HEAD").strip())
        # ... but it says so: a model that really changed a remote system and forgot the flag is told what to do
        notice = next(row for row in done.splitlines() if "--remote-change" in row)
        self.assertIn("Remote change section", notice)
        self.assertIn(str(self.message), notice)
        self.assertFalse(self.message.exists())  # consumed, so the notice says to write the message again
        self.write("docs: x\n\nKey learnings: none\nRemote change: staging-site, purged the cache\n")
        again = subprocess.run(shlex.split(notice.rsplit("run: ", 1)[1]), text=True, capture_output=True, cwd=self.base,
                               timeout=60, env=self.environment)
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), [])
        self.assertNotEqual(before, self.git("rev-parse", "HEAD").strip())

    def test_no_remote_change_notice_when_the_message_has_no_such_section(self):
        self.begin()
        self.write("docs: x\n\nKey learnings: none\n")
        self.assertNotIn("--remote-change", self.invoke(*self.commit_args).stdout)

    def test_the_flag_with_files_pending_commits_the_files_and_the_section_rides_in_the_message(self):
        self.begin()
        self.edit()
        self.write("docs: x\n\nRemote change: staging-site, purged the cache\nKey learnings: none\n")
        self.invoke(*self.commit_args, "--remote-change")
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), ["product/contracts/cold-recovery.md"])
        self.assertIn("Remote change: staging-site", self.head_message())

    def test_the_flag_without_a_remote_change_section_is_refused_and_the_named_exit_works(self):
        self.begin()
        self.write("docs: x\n\nKey learnings: none\n")
        stderr = self.refused("--remote-change")
        line = self.line_one(stderr)
        self.assertTrue(line.startswith('Add a "Remote change:'), line)
        self.assertTrue(line.endswith("--remote-change"), line)  # the rerun keeps the flag
        self.write("docs: x\n\nRemote change: staging-site, purged the cache\nKey learnings: none\n")
        self.run_named(stderr)
        self.assertNotEqual(self.base_commit, self.git("rev-parse", "HEAD").strip())

    def test_an_empty_remote_commit_still_needs_lessons(self):
        self.begin()
        self.write("docs: x\n\nRemote change: staging-site, purged the cache\n")
        stderr = self.refused("--remote-change")
        self.assertTrue(self.line_one(stderr).startswith('Add a "Key learnings:'))
        self.assertTrue(self.line_one(stderr).endswith("--remote-change"))
        self.write("docs: x\n\nRemote change: staging-site, purged the cache\nKey learnings: none\n")
        done = self.run_named(stderr).stdout  # the named exit keeps the flag, so it makes the commit with no files
        self.assertIn("remote change", done)
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), [])

    OPENING = ("## Current context and desired improvements\nTighten the spec examples.\n\n"
               "## Scope\nproduct/contracts/cold-recovery.md\n\n## Authority\nLocal edits and scoped commits; no push.\n\n"
               "## Environment\nPython 3 fixture; no network.\n")

    def start_child(self):
        """improve-start through the CLI; the frozen contract and parent-return.md it wrote."""
        receipt = bridge.receipt_path(self.bound)
        opening = receipt.with_name("opening.md")
        opening.write_text(self.OPENING, encoding="utf-8")
        self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.action, "--opening", opening)
        contract = json.loads(receipt.with_name("start.json").read_text(encoding="utf-8"))
        return contract, receipt.with_name("parent-return.md")

    def test_the_frozen_authority_lets_the_child_run_improve_commit_only_and_parent_return_holds_its_rules(self):
        self.begin("plan")  # the planning child: its packet prints no improve-commit line, so the contract is its only carrier
        contract, parent_return = self.start_child()
        authority = contract["context"]["authority"]
        self.assertIn("No push or merge", authority)
        self.assertIn("commit only with improve-commit, never git commit", authority)
        self.assertIn("The child runs no ShipLoop callback except improve-commit", authority)
        self.assertIn(str(parent_return), authority)
        self.assertNotIn("never runs a ShipLoop callback", authority)
        self.assertIn("no empty commit except a recorded remote change", authority)
        route = parent_return.read_text(encoding="utf-8")
        for needed in (str(self.message), "improve-commit --run-dir=" + str(self.run), "--message=" + str(self.message),
                       "Key learnings: none", "Learned-from: <commit id> <what it contributed>",
                       "Remote change: <system alias>, <what changed>, <where its evidence is>", "--remote-change",
                       "Never run git commit yourself", "improve-complete --run-dir=" + str(self.run)):
            with self.subTest(needed=needed):
                self.assertIn(needed, route)
        self.assertLess(route.index("improve-commit --run-dir="), route.index("improve-complete --run-dir="))
        self.assertIn("The child never runs the improve-complete command", route)

    def test_the_command_parent_return_prints_runs_and_commits_at_the_planning_stage(self):
        """Route test: what a cleared child finds in the file the contract names is a command that works."""
        self.begin("plan")
        _contract, parent_return = self.start_child()
        listed = [row for row in parent_return.read_text(encoding="utf-8").splitlines()
                  if row.startswith("python3 ") and " improve-commit " in row]
        self.assertEqual(len(listed), 1)
        self.edit()
        self.write("docs: tighten\n\nKey learnings: exact examples catch drift.\n")
        before = self.git("rev-parse", "HEAD").strip()
        result = subprocess.run(shlex.split(listed[0]), text=True, capture_output=True, cwd=self.base, timeout=60,
                                env=self.environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual(before, self.git("rev-parse", "HEAD").strip())
        self.assertIn("Key learnings: exact examples catch drift.", self.head_message())

    # The commit-policy clause of 658ff4e3, before improve-commit joined the contract (the parent-return path follows it).
    BASE_COMMIT_CLAUSE = ("Commit policy: the selected Improve card's scoped-commit policy with the task's explicit overrides "
                          "above; stage only intended paths, never runtime receipts or unrelated staging, no empty "
                          "commit. No push or merge. The child never runs a ShipLoop callback: after the terminal "
                          "packet the parent runs the return in ")
    # Spike S (batch 1012): the thinnest of 92 saved Improve contracts is a carry-forward child with 1,081 of the 9,216
    # bytes left (r1-battleship-grok-none, 8,135 bytes); Sonnet and Grok contracts median 5,658 at spec.
    THINNEST_SAVED_HEADROOM = 1081
    IMPROVE_STAGES = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan",
                      "carry-forward")

    def test_the_commit_clause_costs_what_the_thinnest_saved_contract_can_spare_on_every_stage_and_route(self):
        """Guard (passes before the clause grows): the saved thinnest case still fits, on both routes."""
        self.begin("plan")
        state = store.read_record(self.run / "state.md")
        parent_return = str(bridge.receipt_path(self.bound).with_name("parent-return.md"))

        def build(stage, route, environment="x"):
            chosen = dict(state, active_improve=dict(state["active_improve"], stage=stage), delegation=route)
            return navigator.improve_start_contract(None, self.run, chosen, "".join(
                "## " + name + "\n" + (environment if name == "Environment" else "x") + "\n\n"
                for name in navigator.OPENING_SECTIONS))

        added_by_stage, rows = set(), set()
        for stage in self.IMPROVE_STAGES:
            inline = build(stage, "inline")
            authority = inline["context"]["authority"]
            clause = authority[authority.index("Commit policy:"):]
            added = (loop_contract.text_bytes(clause)
                     - loop_contract.text_bytes(self.BASE_COMMIT_CLAUSE + parent_return + "."))
            added_by_stage.add(added)
            # the saved case: the model-written Environment fills the inline contract until, under the old clause,
            # only the thinnest saved headroom was left
            pad = (loop_contract.CONTRACT_BUDGET - self.THINNEST_SAVED_HEADROOM
                   - (loop_contract.compact_bytes(inline) - added) + 1)
            for route in ("inline", "ask-agent"):
                with self.subTest(stage=stage, route=route):
                    thin = build(stage, route, "a" * pad)
                    self.assertLessEqual(loop_contract.compact_bytes(thin), loop_contract.CONTRACT_BUDGET)
                    self.assertIsNone(loop_contract.size_problem(thin))
            rows.add(loop_contract.compact_bytes(build(stage, "ask-agent")) - loop_contract.compact_bytes(inline))
        # one clause for every stage, so it costs the same everywhere; the delegated route's resource row is its own
        self.assertEqual(len(added_by_stage), 1)
        self.assertLessEqual(max(added_by_stage) + max(rows), self.THINNEST_SAVED_HEADROOM)

    def commit_gate_refusal(self):
        """Run the child to its terminal packet with an uncommitted edit; the refusal improve-complete gives."""
        self.begin("spec")
        self.edit()
        self.finish_ephemeral(self.start_ephemeral_child()[1])
        self.completion, _receipt = self.completion_receipt()
        return self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                           *self.completion, status=2).stderr

    def packet_lines(self):
        """The bound Improve packet as `next` writes it (head and full packet file)."""
        return self.invoke(CLI, "next", "--run-dir", self.run).stdout.splitlines()

    def test_a_message_written_as_the_packet_line_says_commits_and_one_without_lessons_is_refused(self):
        """Route test for the packet line (fail-first: the line said only "what the review fixed", so a message written
        as it said was refused for its missing Key learnings line, which no packet named)."""
        self.begin()
        lines = self.packet_lines()
        line = next(row for row in lines if row.startswith("To commit a review iteration's changes"))
        self.assertEqual(re.search(r"write the commit message to (\S+) with a file-writing tool", line).group(1),
                         str(self.message))
        for needed in ("`Key learnings: <what this iteration taught that a later iteration or run should reuse>`",
                       "`Key learnings: none`", "`Learned-from: <commit id> <what it contributed>`",
                       "`Remote change: <system alias>, <what changed>, <where its evidence is>`",
                       "append `--remote-change` to the command", "starting in column 1", "shell heredoc",
                       "run git commit yourself"):
            with self.subTest(needed=needed):
                self.assertIn(needed, line)
        argv = shlex.split(line.rsplit("Then run: ", 1)[1])  # the line ends with the command, nothing after it
        self.assertEqual(argv[2:], ["improve-commit", "--run-dir=" + str(self.run), "--action=" + self.action,
                                    "--message=" + str(self.message)])
        # The message the line describes: a subject, then the lesson and a credit, each on its own line in column 1.
        self.edit()
        self.write("docs: tighten the contract example\n\nReview found a vague example.\n\n"
                   "Key learnings: exact examples catch drift.\n"
                   "Learned-from: " + self.base_commit[:9] + " the base fixture the example was checked against\n")
        self.assertIn("Committed this review's changes as ", self.run_argv(argv).stdout)
        committed = self.head_message()
        self.assertIn("Key learnings: exact examples catch drift.", committed)
        self.assertIn("Learned-from: " + self.base_commit + " the base fixture", committed)
        # Each refusal the parent packet's Checked-by line names, through the same command.
        checked = next(row for row in lines if row.startswith("Checked by: "))
        self.assertIn("improve-commit refuses to commit a message with no `Key learnings:` line", checked)
        self.assertIn("improve-complete refuses a review that left its own edits uncommitted", checked)
        self.edit("Again.\n")
        before = self.git("rev-parse", "HEAD").strip()
        self.write("docs: again\n\nReview found drift.\n")
        self.assertTrue(self.line_one(self.run_argv(argv, status=2).stderr).startswith('Add a "Key learnings:'))
        self.write("docs: again\n\nKey learnings: none\nLearned-from: " + "e" * 12 + " nothing\n")
        self.assertIn("names no commit in this repository", self.run_argv(argv, status=2).stderr)
        self.assertEqual(before, self.git("rev-parse", "HEAD").strip())

    def test_the_planning_packet_names_parent_return_md_whose_command_commits(self):
        """Fail-first: the planning packet printed a Commit policy line and no way to commit (0 of 8 saved plan-stage
        packets named improve-commit); the frozen contract and parent-return.md were the only carriers."""
        self.begin("plan")
        lines = self.packet_lines()
        parent_return = bridge.receipt_path(self.bound).with_name("parent-return.md")
        policy = next(index for index, row in enumerate(lines) if row.startswith("Commit policy:"))
        self.assertEqual(lines[policy + 1],
                         "To commit a review iteration's changes, run the improve-commit command in " + str(parent_return)
                         + "; its message rules are there. ShipLoop commits exactly the files this review changed. "
                         "Do not run git commit yourself.")
        self.assertFalse([row for row in lines if " improve-commit --run-dir=" in row])
        _contract, written = self.start_child()
        self.assertEqual(written, parent_return)  # the file the packet names is the one improve-start writes
        listed = [row for row in written.read_text(encoding="utf-8").splitlines()
                  if row.startswith("python3 ") and " improve-commit " in row]
        self.edit()
        self.write("docs: tighten\n\nKey learnings: none\n")
        self.run_argv(shlex.split(listed[0]))
        self.assertIn("Key learnings: none", self.head_message())

    def test_the_uncommitted_edits_refusal_names_improve_commit_and_the_exit_commits(self):
        stderr = self.commit_gate_refusal()
        line = self.line_one(stderr)
        self.assertTrue(line.startswith("Commit this review's changes first"), line)
        self.assertIn(str(self.message), line)
        self.assertIn("- product/contracts/cold-recovery.md", stderr)
        self.assertNotIn("Stage exactly these paths", stderr)
        self.write("docs: tighten\n\nKey learnings: exact examples catch drift.\n")
        self.run_named(stderr)
        again = next(row for row in stderr.splitlines() if row.startswith("Then run the improve-complete command again: "))
        argv = shlex.split(again.split(": ", 1)[1])  # the refusal prints it: a cleared parent needs no other packet
        self.assertEqual(argv[2], "improve-complete")
        self.run_argv(argv)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

    def run_argv(self, argv, status=0):
        result = subprocess.run(argv, text=True, capture_output=True, cwd=self.base, timeout=60, env=self.environment)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def test_the_uncommitted_edits_refusal_names_the_no_commit_exit_and_improve_complete_accepts_it(self):
        stderr = self.commit_gate_refusal()
        exit_line = next(row for row in stderr.splitlines() if "--no-commit" in row)
        self.assertNotIn("receipt", exit_line)  # improve-complete has no receipt file to edit: it has a flag
        # the command is on the line itself, last, with the instruction placeholder: submitted through the real gate
        argv = shlex.split(exit_line.split(": ", 1)[1])
        self.assertEqual((argv[2], argv[-2:]), ("improve-complete", ["--no-commit", "<their instruction>"]))
        argv[-1] = "The user said not to commit."
        self.run_argv(argv)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])


class AskAgentEphemeralImproveCliTests(ImproveCliFixture):
    """The opt-in delegated route keeps its Ask-Agent packet contract."""

    delegation = "ask-agent"
    test_context_first_assignment_and_learning_header_survive_recovery = (
        EphemeralImproveCliTests.test_context_first_assignment_and_learning_header_survive_recovery)
    test_consumer_owned_context_keeps_edits_and_parent_pending_until_import = (
        EphemeralImproveCliTests.test_consumer_owned_context_keeps_edits_and_parent_pending_until_import)
    test_planning_improve_packet_carries_graph_identity_through_real_child_callbacks = (
        EphemeralImproveCliTests.test_planning_improve_packet_carries_graph_identity_through_real_child_callbacks)
    test_user_stopped_child_restarts_with_the_same_binding_then_imports = (
        EphemeralImproveCliTests.test_user_stopped_child_restarts_with_the_same_binding_then_imports)
    test_improve_start_freezes_the_contract_and_starts_the_runtime = (
        EphemeralImproveCliTests.test_improve_start_freezes_the_contract_and_starts_the_runtime)
    test_improve_start_refuses_an_oversized_opening_before_anything_is_written = (
        EphemeralImproveCliTests.test_improve_start_refuses_an_oversized_opening_before_anything_is_written)


if __name__ == "__main__":
    unittest.main()
