#!/usr/bin/env python3
"""Real ShipLoop/Improve CLI composition; fixture judgments are synthetic."""
from pathlib import Path
import hashlib
import json
import re
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402


CLI = ROOT / "skills/shiploop/scripts/shiploop"
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

    def _start_parent_at_stage(self, stage, evidence_refs, card=CARD):
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
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def bind_current(self, card=CARD):
        self.invoke(CLI, "improve-bind", "--run-dir", self.run, "--action", self.action,
                    "--skill-card", card)
        self.bound = store.read_record(self.run / "state.md")["active_improve"]
        self.completion_path = self.run / "inbox" / (self.action + "-improve.md")
        self.parent_route_path = self.run / "parent-recovery.json"
        self._write_parent_route()

    def _parent_import_argv(self):
        return [sys.executable, "-B", str(CLI), "improve-complete", "--run-dir", str(self.run),
                "--action", self.action, "--result", str(self.completion_path)]

    def _workspace_return_argv(self):
        return [sys.executable, "-B", str(CLI), "workspace", "return", "--workspace-root", str(self.run.parent)]

    def _write_parent_route(self):
        store.write_record(self.parent_route_path, {
            "state": str(self.run / "state.md"),
            "completion_input": str(self.completion_path),
            "improve_complete_argv": self._parent_import_argv(),
            "workspace_return_argv": self._workspace_return_argv(),
        })

    def child_context(self):
        receipt = bridge.receipt_path(self.bound)
        resources = [
            {"purpose": "selected Improve skill", "locator": self.bound["skill"]["skill_card"]},
            {"purpose": "bound Until Loop runtime", "locator": self.bound["skill"]["runtime_cli"]},
            {"purpose": "ShipLoop parent state", "locator": str(self.run / "state.md")},
            {"purpose": "ShipLoop completion input", "locator": str(self.completion_path)},
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
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)],
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
                + ". Completion input: " + str(self.completion_path)
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

    def completion_receipt(self, *, final_result=None):
        evidence = bridge.receipt_path(self.bound).parent / "reviews"
        evidence.mkdir(parents=True, exist_ok=True)
        review_one, review_two, checks = (evidence / "review-one.md", evidence / "review-two.md", evidence / "checks.md")
        for path in (review_one, review_two, checks):
            path.write_text("Synthetic protocol evidence: " + path.name + "\n", encoding="utf-8")
        receipt = {
            "summary": "Runtime mechanics completed; no actual review claim.",
            "review_refs": [str(review_one), str(review_two)],
            "check_refs": [str(checks)],
            "lessons": "A terminal callback receipt is structural evidence, not semantic proof.",
        }
        if final_result is not None:
            receipt["final_result"] = final_result
        store.write_record(self.completion_path, receipt)
        return self.completion_path, receipt

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
                    "--action", self.action, "--result", completion)
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
                self.assertIn("Context-first opening: before start, write 'Current context and desired improvements'", packet)
                self.assertIn("Run the selected Improve card's ShipLoop whole-skill subcall in this conversation", packet)
                self.assertIn("Return order:", packet)
                self.assertIn("keep the frozen launch context unchanged", packet)
                self.assertIn("Binding line: copy the next line verbatim into frozen context.request exactly once, "
                              "first, alone on its own line", packet)
            else:
                self.assertIn("Parent assignment preparation:", packet)
                self.assertIn("Run /improve", packet)
                self.assertIn("navigator cannot supply conversation-only learnings", packet)
                self.assertIn("Parent-only return:", packet)
                self.assertIn("keep launch context immutable and continue the same child", packet)
                self.assertIn("Binding line: copy the next line verbatim into frozen context.request exactly once, "
                              "alone on its own line", packet)
            marker = packet.index(self.bound["contract_marker"] + "\n")
            self.assertIn("import matches the whole line:\n", packet[marker - 40:marker])
            self.assertIn("Start inputs owned by ShipLoop: required_trivial_reviews 2 (import rejects fewer)", packet)
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
                    "--action", self.action, "--result", completion)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(navigator.current_stage(after), "test-strategy")
        self.assertEqual(self.product_contract.read_text(encoding="utf-8"), updated)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

    def test_user_stopped_child_restarts_with_the_same_binding_then_imports(self):
        """A cancelled non-plan child is archived, restarted once and imported; no halt needed."""
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("rename packet.json to packet.stopped-<UTC timestamp>.json and the sibling reviews "
                      "directory to reviews.stopped-<same timestamp>", packet)
        self.assertIn("must be files the new child writes", packet)
        self.assertIn("never report cancelled for a pause", packet)
        _raw, first = self.start_ephemeral_child()
        stopped_raw, stopped = self.done_ephemeral(
            first, self.child_report("unresolved", "unknown", "cancelled", "explicit user stop"))
        self.assertEqual(stopped["status"], "stopped")
        completion, stopped_receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                    "--result", completion, status=2)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        archived = self.packet_path.with_name("packet.stopped-20260923T000000Z.json")
        self.packet_path.rename(archived)
        reviews = self.packet_path.with_name("reviews")
        stopped_reviews = reviews.with_name("reviews.stopped-20260923T000000Z")
        reviews.rename(stopped_reviews)
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                    "--result", completion)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(navigator.current_stage(after), "test-strategy")
        self.assertEqual(archived.read_bytes(), stopped_raw.stdout)
        self.assertEqual(sorted(path.name for path in stopped_reviews.iterdir()),
                         sorted(Path(ref).name for ref in stopped_receipt["review_refs"] + stopped_receipt["check_refs"]))

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
                            "--action", self.action, "--result", completion)
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
                # Cold recovery is the full packet: the locators are inline, not behind rules.md.
                self.assertNotIn("Run rules: " + str(self.run / "rules.md"), cold)
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
                    self.assertTrue(cold.startswith("Continue in this context and execute the prompt.\n"))
                    self.assertNotIn(chain_guide, cold)
                    self.assertNotIn("bind this action to the default parallel", cold)
                    self.assertIn("Delegation is inline: execute a reviewed multi-step plan directly", cold)
                else:
                    self.assertIn(chain_guide, cold)
                    self.assertIn("bind this action to the default parallel", cold)
                    self.assertIn("mode when the selected Plan Dispatcher and Ask-Agent contracts are compatible", cold)

    def test_default_ephemeral_callbacks_preserve_context_then_import_once(self):
        """Cumulative report transport, not proof of model review or summarization."""
        self.assertEqual(self.state["navigator_protocol_version"], 4)
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        self.assertEqual(self.bound["skill"]["runtime_version"], "0.6.0")
        selected_frontmatter = CARD.read_text(encoding="utf-8").split("---", 2)[1]
        selected_version = next(
            line.partition(":")[2].strip().strip("\"'")
            for line in selected_frontmatter.splitlines() if line.startswith("version:")
        )
        self.assertEqual(self.bound["skill"]["skill_version"], selected_version)
        parent_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        for text in (self.bound["contract_marker"], "Bound Until Loop CLI locator: " + str(EPHEMERAL.resolve()),
                     "Child latest packet receipt: " + str(bridge.receipt_path(self.bound)),
                     "Commit policy:",
                     "Save exact, complete raw JSON stdout", "Completion deletes the child's temporary state"):
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

        completion, receipt = self.completion_receipt()
        receipt.update(summary="Synthetic completed run. " + changes, lessons=lessons)
        store.write_record(completion, receipt)
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
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
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        self.assertEqual(after, (self.run / "state.md").read_bytes())
        store.write_record(completion, dict(receipt, summary="Conflicting callback"))
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.assertEqual(after, (self.run / "state.md").read_bytes())

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
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)], contract
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
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
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
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)],
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
                    "--action", self.action, "--result", completion)
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
            [sys.executable, "-B", str(EPHEMERAL), "start", "--directory", str(self.base)], contract
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
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-strategy")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], local_skill_refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        resumed_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("ShipLoop navigator | test-strategy |", resumed_packet)

    def test_active_stopped_and_missing_ephemeral_receipts_do_not_release_parent(self):
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        _raw, active = self.start_ephemeral_child()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        _raw, stopped = self.done_ephemeral(active, self.child_report("unresolved", "unknown", "blocked", "fixture blocker"))
        self.assertEqual(stopped["status"], "stopped")
        self.assertFalse(Path(stopped["state_file"]).exists())
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.packet_path.unlink()
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_linked_completion_inbox_cannot_be_read_or_advance(self):
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        original = completion.with_name("elsewhere.md")
        completion.replace(original)
        completion.symlink_to(original)
        before = (self.run / "state.md").read_bytes()
        result = self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action,
                             "--result", completion, status=2)
        self.assertIn("non-symlink", result.stderr)
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
        self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.action, "--result", completion)
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
        self.assertEqual(receipt["summary"], "Runtime mechanics completed; no actual review claim.")


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


if __name__ == "__main__":
    unittest.main()
