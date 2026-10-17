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
import types
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills/shiploop/scripts"))
import shiploop_loop_contract as loop_contract  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_privacy as privacy  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_standalone_improve as bridge  # noqa: E402
import shiploop_store as store  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

sys.path.insert(0, str(ROOT / "test"))
from shiploop_loop_support import finish_loop, with_receipt  # noqa: E402
import shiploop_knowledge_home as knowledge  # noqa: E402
import shiploop_stage_spec as stage_spec  # noqa: E402

sys.path.insert(0, str(ROOT / "test"))
from shiploop_loop_support import finish_loop, with_receipt  # noqa: E402


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
    text = stdout
    if packet_file is not None and packet_file.is_file():
        text = stdout + "\n" + packet_file.read_text(encoding="utf-8")
    # The Improve packet is two instructions (re-cut 2026-10-11); everything else it used to say is in the handoff file
    # its first instruction names, which the improve skill reads.  A test that asserts "the packet says X" asserts it
    # over the packet plus that file.
    named = re.search(r"/improve " + re.escape(navigator.IMPROVE_ARGUMENT_PREFIX) + r"(\S+)", text)
    if named is not None and Path(named.group(1)).is_file():
        text += "\n" + Path(named.group(1)).read_text(encoding="utf-8")
    return text

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
            # No host session markers and a keepalive home of its own: the Improve stage's complete asks the hooks'
            # record about the host session it runs in, and a suite run inside a Claude Code or Grok session must not
            # meet that session's real bindings.
            **{name: value for name, value in os.environ.items()
               if name not in ("CLAUDECODE", "CLAUDE_CODE_SESSION_ID", "GROK_AGENT", "GROK_SESSION_ID")},
            "SHIPLOOP_KEEPALIVE_HOME": str(self.base / "keepalive"),
            "PATH": "/Library/Developer/CommandLineTools/usr/bin:" + os.environ.get("PATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        }
        self.repo.mkdir()
        # The Improve review's unchanged-content gate measures a Git worktree; ShipLoop starts the child at the transition.
        subprocess.run(["git", "-C", str(self.repo), "init", "-q"], check=True, capture_output=True, env=self.environment)
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

    def _write_producer(self, stage):
        """Write self.producer as the current result; an INNER stage first runs its Until Loop for real.

        Every inner stage's complete checks its loop receipt (owner decision 2026-10-10), so the receipt joins the
        evidence_refs the way the printed template prefills it; parent_evidence_refs follows the submitted list.
        """
        if self.producer.get("outcome") == "done":
            # The consumer contract's hand-off fields (2026-10-11), when the test did not set them.
            if stage in ("test-spec", "verify", "carry-forward", "system-test-author", "system-test",
                         "release-plan", "release-verify"):
                self.producer.setdefault("assumptions", [])
            if stage == "step-plan":
                self.producer.setdefault("follows", [])
        if stage in stage_spec.INNER:
            self.producer = with_receipt(self.producer, finish_loop(self.run))
            self.parent_evidence_refs = list(self.producer["evidence_refs"])
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)

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
            self.producer["steps"] = [{"id": "S1", "task": "Make the planned change.", "paths": ["src/**"],
                                       "criteria": [], "skills": []}]
            self.producer["expectations"] = [{"id": "E1", "state": "absent", "statement": "src/ does not exist yet.",
                                              "steps": ["S1"], "paths": ["src/**"], "check": "test ! -e src"}]
        self.producer.update(producer_extra or {})
        self._write_producer(stage)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current(card)

    def bind_current(self, card=CARD):
        """Pick up the Improve stage ShipLoop set up at the transition (owner, 2026-10-11).

        The run recorded the Improve card at init, so the producer's complete left a bound child that ShipLoop started
        itself: opening.md, start.json and an active packet.json exist, and the model neither binds nor starts it.
        ``self.action`` is the reviewed producer action; ``self.improve`` is the Improve stage's own id, which every
        model-facing command (complete, improve-commit, improve-start --restart-stopped) names.
        """
        self.bound = store.read_record(self.run / "state.md")["active_improve"]
        self.assertIsNotNone(self.bound["skill"], "the transition bound the recorded card")
        self.improve = self.bound["improve_action"]
        self.assertNotEqual(self.improve, self.action)
        self.notes_path = self.run / "inbox" / (self.action + "-improve-notes.md")
        self.final_path = self.run / "inbox" / (self.action + "-final-result.md")
        self.parent_route_path = self.run / "parent-recovery.json"
        self._write_parent_route()

    def _parent_import_argv(self):
        return [sys.executable, "-B", str(CLI), "complete", "--run-dir", str(self.run),
                "--action", self.improve]

    def _workspace_return_argv(self):
        return [sys.executable, "-B", str(CLI), "workspace", "return", "--workspace-root", str(self.run.parent)]

    def _write_parent_route(self):
        store.write_record(self.parent_route_path, {
            "state": str(self.run / "state.md"),
            "review_evidence": str(bridge.receipt_path(self.bound).parent / "reviews"),
            "complete_argv": self._parent_import_argv(),
            "workspace_return_argv": self._workspace_return_argv(),
        })

    def child_contract(self):
        """The contract ShipLoop froze for the child it started (start.json beside the receipt)."""
        return json.loads(bridge.receipt_path(self.bound).with_name("start.json").read_text(encoding="utf-8"))

    def child_context(self):
        return self.child_contract()["context"]

    def save_packet(self, result):
        """Check that the runtime's own receipt is the packet it printed; the test never writes a receipt."""
        path = bridge.receipt_path(self.bound)
        self.assertEqual(path.read_bytes(), result.stdout)
        self.packet_path = path
        return path

    def start_ephemeral_child(self):
        """The child ShipLoop started at the transition: its receipt is the active packet; the test never starts a runtime."""
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        path = bridge.receipt_path(self.bound)
        raw = path.read_bytes()
        packet = json.loads(raw)
        self.assertEqual(packet["status"], "active")
        self.packet_path = path
        return types.SimpleNamespace(stdout=raw, stderr=b"", returncode=0), packet

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

    def commit_repo(self, message="review edit"):
        """Commit the review's edits the way improve-commit would, so the import's commit gate has nothing owed."""
        for args in (("add", "-A"), ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                                       "commit", "-qm", message)):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True,
                           env=self.environment)

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
        """Write the child's review files; return complete's extra flags and the record ShipLoop derives."""
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
            "summary": "Improve reviewed the " + self.bound["stage"] + " result; it ended on pass 3, a trivial pass "
                       "that left the content unchanged.",
            "review_refs": [str(review_two)],  # the one pass the runtime ended on (stop rule, 2026-10-16)
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
        self._write_producer(stage)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current()
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run,
                    "--action", self.improve, *completion)
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
        self._write_producer(stage)
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
        opening = bridge.receipt_path(self.bound).with_name("opening.md")
        for _ in range(2):
            packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
            # ShipLoop wrote the opening and started the child at the transition (owner, 2026-10-11): the packet asks
            # the model to write nothing and start nothing; `improve-start` is only the restart route.
            self.assertTrue(opening.is_file())
            self.assertIn("ShipLoop started this review when the Improve stage began", packet)
            self.assertIn("Do not write the opening or start the runtime yourself", packet)
            self.assertNotIn("Context-first opening: before start, write the opening file", packet)
            self.assertNotIn("## Current context and desired improvements\n...", packet)
            self.assertNotIn("--opening", packet)
            self.assertEqual(packet.count(" improve-start "), 1)
            self.assertIn("--restart-stopped", packet)
            if self.inline():
                self.assertIn("Run the selected Improve card's ShipLoop whole-skill subcall in this conversation", packet)
                self.assertIn("Return order:", packet)
                self.assertIn("the frozen launch context stays unchanged", packet)
            else:
                self.assertIn("Parent assignment preparation:", packet)
                self.assertIn("Run /improve", packet)
                self.assertIn("navigator cannot supply conversation-only learnings", packet)
                self.assertIn("Parent-only return:", packet)
                self.assertIn("keep launch context immutable and continue the same child", packet)
                # ShipLoop starts this child too; the worker continues it (551b8b49).
                self.assertIn("continues the already-started loop from the receipt's next_argv", packet)
            # Neither route states a byte limit for the opening: the Until Loop runtime has none.
            self.assertNotIn("Size budget", packet)
            self.assertNotRegex(packet, r"\bbytes together\b|16,384|9,216")
            # Neither route asks the model to copy the binding line or state start inputs; it appears once, as the
            # handoff file's first line (the improve skill's subcall trigger).
            self.assertEqual(packet.count(self.bound["contract_marker"]), 1)
            self.assertNotIn("Start inputs owned by ShipLoop", packet)
            self.assertNotIn("Start the child runtime with --receipt", packet)
            self.assertIn("Selected Improve skill: " + str(CARD.resolve()), packet)
            self.assertIn("material unresolved findings, hypotheses, failed attempts", packet)
            if self.inline():  # the conversation holds the approvals; a delegated worker is told them in the dispatch prompt
                self.assertIn("holds the current approvals, declines and pending decisions", packet)
            else:
                self.assertIn("approvals, declines and pending decisions: state them, with action/target", packet)
        self.assertEqual((self.run / "state.md").read_bytes(), before)

        # The context ShipLoop froze: its binding line first, the one opening heading once, and it survives cold recovery.
        header = "## Current context and desired improvements\n"
        decisions = ("Approved: local preview at fixture target after checks; source: user launch instruction. "
                     "Declined: production publication; source: user launch instruction. "
                     "Pending: adding a service dependency; no approval received.")
        context = self.child_context()
        self.assertEqual(context["request"].splitlines()[0], self.bound["contract_marker"])
        self.assertEqual(context["request"].count(headings[0]), 1)
        self.assertIn(header, context["request"])
        _raw, active = self.start_ephemeral_child()
        _raw, cold = self.invoke_argv(active["next_argv"])
        self.assertEqual(cold["context"], context)
        self.assertEqual(cold["context"]["request"].count(headings[0]), 1)
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
            "and service dependency approval remains pending. No publication performed. " + decisions
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
        self.assertIn("Improve context ownership: GUIDES/" + guide.name, packet)
        owner_record = "Native owner record: " + str(bridge.receipt_path(self.bound).with_name("host-owner.md"))
        if self.inline():
            # Inline Improve has no native owner; import below still succeeds.
            self.assertTrue(packet.startswith("ShipLoop navigator | improve | revision "))
            anchor = "default-route-the-parent-runs-improve-delegation-inline"
            self.assertIn("Improve context ownership: GUIDES/" + guide.name + "#" + anchor, packet)
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
        self.commit_repo()  # improve-commit's job; the import is refused while a review edit is uncommitted
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
        self.invoke(CLI, "complete", "--run-dir", self.run,
                    "--action", self.improve, *completion)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(navigator.current_stage(after), "test-strategy")
        self.assertEqual(self.product_contract.read_text(encoding="utf-8"), updated)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

    def test_user_stopped_child_restarts_with_the_same_binding_then_imports(self):
        """A cancelled non-plan child is archived, restarted once and imported; no halt needed."""
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        # Both routes restart through ShipLoop; neither renames files by hand (29786109, 551b8b49).
        restart_command = (" improve-start --run-dir=" + str(self.run) + " --action=" + self.improve
                           + " --restart-stopped: ShipLoop archives packet.json as packet.stopped-<UTC timestamp>.json")
        self.assertIn(restart_command, packet)
        self.assertIn("Do not rename them yourself.", packet)
        self.assertIn("must be ones the new child writes", packet)
        self.assertIn("never report cancelled for a pause", packet)
        _raw, first = self.start_ephemeral_child()
        start = [CLI, "improve-start", "--run-dir", self.run, "--action", self.improve, "--restart-stopped"]
        # The child is running: it is continued from its receipt, never restarted over, and the verb needs its flag.
        self.assertIn("still running", self.invoke(*start, status=2).stderr)
        self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.improve, status=2)
        # Only the Improve stage's own id names the stage; the reviewed action's id is refused.
        self.assertIn("no bound current Improve stage with this action",
                      self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.action,
                                  "--restart-stopped", status=2).stderr)
        stopped_raw, stopped = self.done_ephemeral(
            first, self.child_report("unresolved", "unknown", "cancelled", "explicit user stop"))
        self.assertEqual(stopped["status"], "stopped")
        completion, stopped_receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
                    *completion, status=2)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        restarted_run = self.invoke(*start)
        self.assertIn("Archived the stopped child", restarted_run.stderr)
        archived = next(self.packet_path.parent.glob("packet.stopped-*.json"))
        stopped_reviews = self.packet_path.parent / archived.name.replace("packet.", "reviews.").removesuffix(".json")
        self.assertTrue(stopped_reviews.is_dir())
        # ShipLoop wrote a fresh opening and started the new child itself; the model writes and starts nothing.
        self.assertTrue(self.packet_path.with_name("opening.md").is_file())
        first = json.loads(self.packet_path.read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "active")
        self.finish_ephemeral(first)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
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
            improve_action=child["improve_action"],
        )
        navigator.validate(waiting)

        packet = navigator.render(None, self.run, waiting)

        handoff = navigator.improve_handoff_text(None, self.run, waiting)  # the file the improve skill reads

        self.assertIn(user_no_commit, packet)
        self.assertIn(
            "selected Improve card's scoped-commit policy with the task's explicit overrides",
            handoff,
        )
        self.assertIn("Selected Improve skill: " + str(CARD.resolve()), handoff)
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
                # ShipLoop froze the child's contract (2026-10-11), so the graph identity is no longer a host-authored
                # resource row: the contract's scope names the result file whose evidence_refs hold it, and the handoff
                # prints the result (the parent packet above carries it).
                result_file = self.run / "inbox" / (self.action + ".md")
                self.assertIn(str(result_file), cold["context"]["scope"])
                self.assertIn(graph_identity, result_file.read_text(encoding="utf-8"))
                self.save_packet(cold_raw)
                terminal_raw, terminal = self.finish_ephemeral(cold)
                self.assertEqual(terminal["context"], cold["context"])

                completion, _receipt = self.completion_receipt()
                self.invoke(CLI, "complete", "--run-dir", self.run,
                            "--action", self.improve, *completion)
                resumed = store.read_record(self.run / "state.md")
                self.assertEqual(navigator.current_stage(resumed), expected_stage)
                self.assertEqual(
                    resumed["improve_results"][self.action]["seed_result"]["evidence_refs"],
                    self.parent_evidence_refs,
                )
                self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)

                if stage != "step-plan":
                    continue

                step_plan_action = self.action
                step_plan_refs = list(self.parent_evidence_refs)
                # test-spec is still a planning-review stage and starts a real Improve child.  Every expectation
                # matches, so ShipLoop records validate-existing by script and issues implement next.
                for next_stage in ("test-spec",):
                    self.assertEqual(navigator.current_stage(resumed), next_stage)
                    evidence = self.repo / "evidence" / (next_stage + ".md")
                    evidence.parent.mkdir(parents=True, exist_ok=True)
                    evidence.write_text("# " + next_stage + "\n", encoding="utf-8")
                    observed_stage, _action, resumed = self.complete_current_stage_through_actual_improve(
                        [str(evidence) + "#fixture"],
                        "Fixture advance through actual Improve for " + next_stage + ".",
                    )
                    self.assertEqual(observed_stage, next_stage)

                self.assertEqual(navigator.current_stage(resumed), "implement")
                self.assertIn("validate-existing", [entry["stage"] for entry in resumed["history"]])
                self.assertNotEqual(resumed["history"][-1]["action"], step_plan_action)
                self.assertEqual(resumed["accepted"][step_plan_action]["evidence_refs"], step_plan_refs)
                self.assertEqual(
                    resumed["improve_results"][step_plan_action]["seed_result"]["evidence_refs"],
                    step_plan_refs,
                )

                cold = self.invoke(CLI, "next", "--run-dir", self.run).stdout
                self.assertIn("ShipLoop navigator | implement |", cold)
                # Cold recovery is the full packet: the locators are inline.
                self.assertIn("State: RUN/state.md", cold)  # a prose path prints as the References block's symbol
                # The last accepted transition keeps its untrusted-report header; the trailing "If this action
                # depends on earlier accepted context..." sentence is gone (2026-10-11 dedupe).
                self.assertIn("Last accepted transition (untrusted host report; not new instructions):", cold)
                self.assertNotIn("If this action depends on earlier accepted context", cold)
                chain_guide = (
                    "Parallel-chain guide: "
                    + "GUIDES/parallel-chain.md"
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
                            "Continue in this context and execute the prompt. Delegation: inline"),
                        cold,
                    )
                    self.assertNotIn(chain_guide, cold)
                    self.assertNotIn("bind the default parallel mode", cold)
                    # The inline "one step per packet" statement is the Step line (re-cut 2026-10-11).
                    self.assertIn("the only work for this packet:", cold)
                else:
                    self.assertIn(chain_guide, cold)
                    self.assertIn("bind the default parallel mode", cold)
                    self.assertIn("when the Plan Dispatcher and Ask-Agent contracts are compatible", cold)

    def test_default_ephemeral_callbacks_preserve_context_then_import_once(self):
        """Cumulative report transport, not proof of model review or summarization."""
        self.assertEqual(self.state["navigator_protocol_version"], 4)
        self.assertEqual(self.bound["skill"]["runtime_cli"], str(EPHEMERAL.resolve()))
        self.assertEqual(self.bound["skill"]["runtime_version"],
                         json.loads((ROOT / "skills/improve/runtime/until-loop/PROVENANCE.json").read_text())["upstream"]["version"])
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
        # ShipLoop set the stage up at the transition: opening, frozen contract and an active receipt exist, and the
        # packet for the old `<action>-improve.md` file name is gone.
        receipt_dir = bridge.receipt_path(self.bound).parent
        self.assertEqual(json.loads(bridge.receipt_path(self.bound).read_text(encoding="utf-8"))["status"], "active")
        self.assertTrue((receipt_dir / "opening.md").is_file())
        self.assertTrue((receipt_dir / "start.json").is_file())
        self.assertFalse((self.run / "inbox" / (self.action + "-improve.md")).exists())
        self.assertFalse((self.run / "packets" / (self.action + "-improve.md")).exists())
        self.assertTrue((self.run / "packets" / (self.improve + ".md")).is_file())

        start_raw, first = self.start_ephemeral_child()
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], self.child_context())
        result_file = self.run / "inbox" / (self.action + ".md")  # holds the parent evidence locators
        self.assertIn(str(result_file), cold["context"]["scope"])
        self.assertTrue(all(value in result_file.read_text(encoding="utf-8") for value in self.parent_evidence_refs))
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
        with result_file.open("a", encoding="utf-8") as handle:  # the review edits the stage result (a candidate file)
            handle.write("\nMaterial review edit.\n")
        _raw, second = self.done_ephemeral(cold, material_report)
        self.assertEqual(second["progress"], {"action_number": 2, "required_trivial_reviews": 2,
                                              "last_pass_changed_tree": True})
        first_review = self.child_report("trivial", "unsatisfied", "allowed", "unchanged review, exit not yet met")
        first_review["handoff"] = second["last_report"]["handoff"]
        _raw, third = self.done_ephemeral(second, first_review)
        self.assertEqual(third["status"], "active")  # unchanged, but the exit is unsatisfied: nothing ends the loop
        self.assertEqual(third["progress"]["last_pass_changed_tree"], False)
        self.assertIn(json.dumps(self._parent_import_argv()), third["last_report"]["handoff"])
        final_review = self.child_report("trivial", "satisfied", "allowed", "qualifying review that changed nothing")
        final_review["handoff"] = third["last_report"]["handoff"]
        terminal_raw, terminal = self.done_ephemeral(third, final_review)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["progress"], {"action_number": 3, "required_trivial_reviews": 2,
                                                "last_pass_changed_tree": False})
        self.assertFalse(state_file.exists())
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        self.assertEqual(terminal["context"], self.child_context())
        self.assertIn(str(self.parent_route_path), terminal["last_report"]["handoff"])
        self.assertIn(json.dumps(self._workspace_return_argv()), terminal["last_report"]["handoff"])
        self.assertIn(cumulative, terminal["last_report"]["handoff"])
        self.assertFalse((self.repo / ".until-loop").exists())

        completion, receipt = self.completion_receipt(lessons=lessons)
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
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
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertEqual(after, (self.run / "state.md").read_bytes())

    def test_an_edit_to_the_stage_result_alone_keeps_the_review_going_until_a_pass_leaves_it_unchanged(self):
        """The file ShipLoop lists as the child's candidate path is the one the review edits (plan, step-plan, test-spec)."""
        result_file = self.run / "inbox" / (self.action + ".md")
        _raw, first = self.start_ephemeral_child()
        with result_file.open("a", encoding="utf-8") as handle:  # the worktree is untouched; only the result changes
            handle.write("\nTightened a check.\n")
        _raw, second = self.done_ephemeral(
            first, self.child_report("trivial", "satisfied", "allowed", "labelled trivial, but it edited the result"))
        self.assertEqual((second["status"], second["progress"]["last_pass_changed_tree"]), ("active", True))
        self.assertIn("cannot end the loop however it was labelled", second["instruction"])
        _raw, terminal = self.done_ephemeral(
            second, self.child_report("trivial", "satisfied", "allowed", "nothing left to change"))
        self.assertEqual((terminal["status"], terminal["progress"]["action_number"]), ("complete", 2))

    def test_inline_improve_packet_states_every_remaining_obligation_once(self):
        """P5 (SPEC S-6, S-7): script-owned steps are gone; each obligation the model keeps is stated once."""
        if not self.inline():
            self.skipTest("the delegated route keeps its manual start instructions")
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        full = packet  # the packet plus the handoff file it names (invoke appends both)
        # P13: the run's scratch directory exists and takes the reports piped to the runtime, not /tmp.
        scratch = self.run / "scratch"
        self.assertTrue(scratch.is_dir())
        self.assertIn("Temporary files, including each report you pass to the runtime on standard input, go in "
                      + str(scratch), " ".join(full.split()))
        obligations = {
            "continue the child ShipLoop started": "Continue the child from its receipt: run its next_argv once",
            "write nothing and start nothing": "Do not write the opening or start the runtime yourself",
            "restart a stopped child through ShipLoop": " improve-start --run-dir=",
            "follow the runtime": "\"Follow the returned action\" section",
            "commit review edits through ShipLoop": " improve-commit --run-dir=",
            "never edit the receipt": "Never write or edit the receipt",
            "recover an active child": "use its exact next_argv once to recover",
            "restart a stopped child": "--restart-stopped",
            "return only after the terminal packet": "Return order:",
            "pause without losing the child": "Pause parent without losing child",
            "import through the Improve stage's complete": "2. When the improve skill has completed, run: ",
        }
        for name, text in obligations.items():
            with self.subTest(obligation=name):
                self.assertIn(text, full)
        for gone in ("Binding inputs: before start", "Start inputs owned by ShipLoop",
                     "Start the child runtime with --receipt"):
            self.assertNotIn(gone, full)
        # The import is the Improve stage's own complete (improve-complete is gone), naming the stage's id.
        self.assertIn(" complete --run-dir=" + str(self.run) + " --action=" + self.improve, full)
        self.assertNotIn("improve-complete", full)
        self.assertEqual(full.count(self.bound["contract_marker"]), 1)  # the handoff file's head, once
        self.assertEqual(full.count("Never write or edit the receipt"), 1)

    def test_shiploop_writes_the_opening_freezes_the_contract_and_starts_the_runtime(self):
        """ShipLoop writes the four opening sections, the contract and the receipt at the transition.

        Both routes: the Ask-Agent route's hand-built contract omitted the binding line in the Codex E2E run
        (551b8b49), and the live run of 2026-10-11 had a model script its own Improve reviews, so the model starts nothing.
        """
        receipt = bridge.receipt_path(self.bound)
        opening = receipt.with_name("opening.md")
        self.assertTrue(opening.is_file())
        self.assertEqual(sorted(path.name for path in receipt.parent.iterdir()),
                         ["handoff.md", "opening.md", "packet.json", "parent-return.md", "reviews", "start.json"])
        sections = navigator._opening_sections(opening.read_text(encoding="utf-8"))
        self.assertEqual(tuple(sections), navigator.OPENING_SECTIONS)
        body = receipt.read_text(encoding="utf-8")
        first = json.loads(body)
        self.assertEqual(first["status"], "active")
        self.assertEqual(Path(first["state_file"]).parent, self.run / "until-loop")
        contract = json.loads(receipt.with_name("start.json").read_text(encoding="utf-8"))
        self.assertEqual(contract["workspace"], self.bound["workspace"])
        self.assertEqual(contract["required_trivial_reviews"], 2)
        # Stop rule (2026-10-16): one pass that leaves the content unchanged ends the review, and the stage result file
        # (outside the worktree, in the run directory) is part of that content.
        self.assertEqual(contract["candidate_paths"], [str(self.run / "inbox" / (self.bound["action_id"] + ".md"))])
        self.assertIn("exactly as the previous pass left it", contract["exit_condition"])
        self.assertNotIn("Two consecutive", contract["exit_condition"])
        self.assertIn("the latest pass changed the content", contract["repeat_condition"])
        self.assertNotIn("qualifying review remains", contract["repeat_condition"])
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
        # The request leads with the opening's own first section, so the improve skill finds the result to review.
        self.assertIn("## " + navigator.OPENING_SECTIONS[0] + "\n" + sections[navigator.OPENING_SECTIONS[0]].splitlines()[0],
                      request)
        self.assertIn("Review the " + stage + " result", request)
        self.assertIn("Always excluded: .until-loop, .shiploop-improve", contract["context"]["scope"])
        self.assertIn("No push", contract["context"]["authority"])
        locators = {r["purpose"]: r["locator"] for r in contract["context"]["resources"]}
        self.assertEqual(locators["latest child packet receipt"], str(receipt))
        self.assertEqual(locators["review evidence directory (review-<n>.md per pass, checks.md)"],
                         str(receipt.parent / "reviews"))
        route = Path(locators["exact parent return instructions"]).read_text(encoding="utf-8")
        self.assertIn(" complete --run-dir=" + str(self.run) + " --action=" + self.improve, route)
        self.assertNotIn("improve-complete", route)
        self.assertEqual(first["context"], contract["context"])
        # The opening is ShipLoop's text: a binding line inside it is refused by the contract builder.
        state = store.read_record(self.run / "state.md")
        with self.assertRaisesRegex(navigator.NavigatorError, "must not contain the binding line"):
            navigator.improve_start_contract(None, self.run, state,
                                             opening.read_text(encoding="utf-8") + self.bound["contract_marker"] + "\n")
        # The verb is only a restart: a running child is continued from its receipt, never started over.
        again = self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.improve,
                            "--restart-stopped", status=2)
        self.assertIn("still running", again.stderr)

        self.packet_path = receipt
        self.finish_ephemeral(first)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        state = store.read_record(self.run / "state.md")
        self.assertIsNone(state["active_improve"])
        self.assertEqual(state["improve_results"][self.action]["runtime_phase"], "complete")
        self.assertEqual(state["improve_results"][self.action]["improve_action"], self.improve)

    def test_the_producers_complete_leaves_the_improve_stage_started(self):
        """The producer's complete is the whole transition: the Improve stage is set up and its packet printed.

        Owner, 2026-10-11, after a live run where the model faked three of four Improve reviews with its own script:
        each stage is a proper stage, run in the same context.  ShipLoop writes the opening, freezes the contract and
        starts the runtime itself, so the printed packet asks the model for one thing: run the improve skill, then
        the Improve stage's complete.
        """
        run = self.base / "fresh-run"
        base = [sys.executable, "-B", str(CLI)]

        def cli(*argv):
            done = subprocess.run([*base, *map(str, argv)], text=True, capture_output=True, cwd=self.base,
                                  timeout=30, env=self.environment)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            return done.stdout

        cli("init", "--repo", self.repo, "--run-dir", run, "--prompt", "Producer transition fixture",
            "--improve-skill", CARD, *self.delegation_args())
        state = store.read_record(run / "state.md")
        for _predecessor in ("intake", "discovery", "research", "spec"):
            action = state["action"]["id"]
            result = run / "inbox" / (action + ".md")
            store.write_record(result, {"outcome": "done", "summary": "Fixture " + _predecessor + " result.",
                                        **({"evidence_refs": self.parent_evidence_refs} if _predecessor == "spec" else {})})
            printed = cli("complete", "--run-dir", run, "--action", action, "--result", result)
            state = store.read_record(run / "state.md")
        child = state["active_improve"]
        improve = child["improve_action"]
        folder = bridge.receipt_path(child).parent
        # ShipLoop wrote the opening, froze the contract and started the runtime: all three files exist now.
        for name in ("opening.md", "start.json", "packet.json"):
            self.assertTrue((folder / name).is_file(), name)
        self.assertEqual(json.loads((folder / "packet.json").read_text(encoding="utf-8"))["status"], "active")
        self.assertEqual(navigator.sequence_stage(state), "improve")
        self.assertNotEqual(improve, child["action_id"])
        # The printed packet is the Improve stage's: header, then the two instructions, naming the stage's own id.
        lines = printed.splitlines()
        self.assertTrue(lines[0].startswith("ShipLoop navigator | improve | revision "), lines[0])
        self.assertIn(" complete --run-dir=" + str(run) + " --action=" + improve, printed)
        self.assertNotIn("--action=" + child["action_id"], printed)
        self.assertNotIn("improve-start", printed)
        self.assertNotIn("write the opening", printed)
        self.assertTrue((run / "packets" / (improve + ".md")).is_file())

    def test_a_review_copied_from_another_improve_stage_is_refused_and_the_named_route_accepts_its_own(self):
        """Owner, 2026-10-11: a live run scripted three of four Improve reviews from one template, changing only the
        line that named the result.  A review of three or more sentences that shares all but one of its sentences with
        a review of another Improve stage of this run is refused; the refusal's command is run after the review is
        written for this result."""
        def review(stage, own=None):
            if own is not None:
                return own
            return (f"Checked the {stage} result against every done-when condition it states. "
                    "The result's evidence references resolve to files that exist. "
                    "No finding needs a change to code, tests or documents. "
                    "The check output is recorded in checks.md. "
                    "The review ends with nothing left to improve.\n")

        # The first Improve stage (spec): a templated review is accepted, since no other stage has one yet.
        first_folder = bridge.receipt_path(self.bound).parent
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        (first_folder / "reviews" / "review-1.md").write_text(review("spec"), encoding="utf-8")
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

        # The second Improve stage (test-strategy) copies that review, changing only the sentence naming its result.
        state = store.read_record(self.run / "state.md")
        stage = navigator.current_stage(state)
        self.assertEqual(stage, "test-strategy")
        self.action = navigator.current_action(state)["id"]
        self.parent_evidence_refs = list(self.parent_evidence_refs)
        self.producer = {"outcome": "done", "summary": "Fixture " + stage + " evidence.",
                         "evidence_refs": self.parent_evidence_refs}
        self._write_producer(stage)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.action, "--result", self.input)
        self.bind_current()
        second_folder = bridge.receipt_path(self.bound).parent
        self.assertNotEqual(first_folder, second_folder)
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        (second_folder / "reviews" / "review-1.md").write_text(review(stage), encoding="utf-8")
        before = (self.run / "state.md").read_bytes()
        refused = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
                              *completion, status=2).stderr
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        line = refused.splitlines()[0]
        self.assertIn("Review this " + stage + " result itself", line)
        self.assertIn(str(second_folder / "reviews" / "review-1.md"), line)
        self.assertIn("repeats the review " + str(first_folder / "reviews" / "review-1.md"), line)
        # The refusal's command: write what this review checked and found, then run it as printed.
        named = shlex.split(line.rsplit("then run: ", 1)[1])
        self.assertEqual(named[2:], ["complete", "--run-dir=" + str(self.run), "--action=" + self.improve])
        (second_folder / "reviews" / "review-1.md").write_text(review(stage, own=(
            "The test-strategy result names a check for each requirement it claims to cover. "
            "Two requirements shared one check, so each now has its own probe recorded in the result. "
            "The probes were read against the product contract file and match it. "
            "Nothing else in the strategy needed a change.\n")), encoding="utf-8")
        done = subprocess.run(named, text=True, capture_output=True, cwd=self.base, timeout=30, env=self.environment)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        after = store.read_record(self.run / "state.md")
        self.assertIsNone(after["active_improve"])
        self.assertEqual(after["improve_results"][self.action]["runtime_phase"], "complete")

    def test_improve_complete_is_not_a_command(self):
        """The Improve stage's import is `complete --action=<improve id>`; the old verb is gone (exit 2, invalid choice)."""
        refused = self.invoke(CLI, "improve-complete", "--run-dir", self.run, "--action", self.improve, status=2)
        self.assertIn("invalid choice", refused.stderr)
        self.assertIn("improve-complete", refused.stderr)

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
        commit = [CLI, "improve-commit", "--run-dir", self.run, "--action", self.improve, "--message", message]
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

        # The child ShipLoop started at the transition owns its frozen contract (2026-10-11): a host can no longer author
        # a candidate inventory into it, so the child runs over the empty-history checkout as ShipLoop froze it.
        context = self.child_context()
        _raw, first = self.start_ephemeral_child()
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], context)
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
        self.assertEqual(terminal["context"], context)

        completion, _receipt = self.completion_receipt()
        # The files stay untracked on purpose (the scope under test), so the import records the instruction not to commit.
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion,
                    "--no-commit", "Fixture: leave the selected untracked files uncommitted.")
        archive = self.run / "improve" / self.action / "terminal.json"
        archived = json.loads(archive.read_text(encoding="utf-8"))
        self.assertEqual(archive.read_bytes(), terminal_raw.stdout)
        self.assertEqual(archived["context"], context)
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

        # ShipLoop froze the child contract and started the child at the transition (2026-10-11); the two product
        # artifacts reach the child through the result file its scope names (their locators are its evidence_refs).
        context = self.child_context()
        result_file = self.run / "inbox" / (self.action + ".md")
        self.assertIn(str(result_file), context["scope"])
        for locator in refs:
            self.assertIn(locator, result_file.read_text(encoding="utf-8"))
        raw, first = self.start_ephemeral_child()
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
        self.invoke(CLI, "complete", "--run-dir", self.run,
                    "--action", self.improve, *completion)
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

        # ShipLoop froze the contract and started the child (2026-10-11): the local-skill locators are the result's
        # evidence_refs, which the contract's scope names, and the child's cold recovery returns that same contract.
        context = self.child_context()
        result_file = self.run / "inbox" / (self.action + ".md")
        self.assertIn(str(result_file), context["scope"])
        for locator in local_skill_refs:
            self.assertIn(locator, result_file.read_text(encoding="utf-8"))
        start_raw, first = self.start_ephemeral_child()
        self.assertEqual(first["status"], "active")
        state_file = Path(first["state_file"])
        before_cold_next = state_file.read_bytes()
        cold_raw, cold = self.invoke_argv(first["next_argv"])
        self.assertEqual(start_raw.stdout, cold_raw.stdout)
        self.assertEqual(before_cold_next, state_file.read_bytes())
        self.assertEqual(cold["context"], context)
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
        self.assertEqual(terminal["context"], context)
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        resumed = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(resumed), "test-strategy")
        self.assertEqual(resumed["improve_results"][self.action]["seed_result"]["evidence_refs"], local_skill_refs)
        self.assertEqual(self.packet_path.read_bytes(), terminal_raw.stdout)
        resumed_packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.assertIn("ShipLoop navigator | test-strategy |", resumed_packet)

    def test_active_stopped_and_missing_ephemeral_receipts_do_not_release_parent(self):
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        _raw, active = self.start_ephemeral_child()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        _raw, stopped = self.done_ephemeral(active, self.child_report("unresolved", "unknown", "blocked", "fixture blocker"))
        self.assertEqual(stopped["status"], "stopped")
        self.assertFalse(Path(stopped["state_file"]).exists())
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        self.packet_path.unlink()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    ARCHITECTURE = "# Architecture\n\nNode 22.\n\n### AD-1 In-memory board\n### AD-2 One module per concern\n"

    def commit_architecture(self) -> Path:
        """docs/shiploop/architecture.md with two decisions, committed in the product repository as an earlier run's home."""
        architecture = self.repo / "docs/shiploop/architecture.md"
        architecture.parent.mkdir(parents=True)
        architecture.write_text(self.ARCHITECTURE, encoding="utf-8")
        self.home_git("init", "-q")
        self.home_git("add", "-A")
        self.home_git("commit", "-qm", "an earlier run's home")
        return architecture

    def home_git(self, *argv) -> str:
        return subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=T", "-c", "user.email=t@example.invalid", *argv],
                              check=True, capture_output=True, text=True, env=self.environment).stdout

    def refused_import(self) -> list:
        """The Improve stage's complete refused (exit 2): its stderr lines, with the receipt files of the review written first."""
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        refused = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())  # a refusal changes nothing
        return refused.stderr.splitlines()

    def commit_the_review(self, message: str) -> None:
        """improve-commit, as a refusal's line 1 names it: write the message where ShipLoop prints it, then run the command."""
        path = bridge.receipt_path(self.bound).with_name("commit-message.md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(message, encoding="utf-8")
        self.invoke(CLI, "improve-commit", "--run-dir", self.run, "--action", self.improve, "--message", path)

    def import_the_review(self) -> None:
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)

    def test_a_reviewed_step_plan_that_drops_a_decision_id_is_refused_at_complete_and_the_named_sequence_is_accepted(self):
        """The review may rewrite docs/shiploop/architecture.md; the gate that checks the producer result checks that too.

        The knowledge gate runs before the gate for the review's uncommitted edits, so the fix the parent writes is that
        edit.  Line 1 names the whole sequence (fix, improve-commit, the Improve stage's complete), and each step is accepted: the
        commit refusal is not met on the way.
        """
        if not self.inline():
            self.skipTest("improve-commit is the inline route")
        architecture = self.commit_architecture()
        self._start_parent_at_stage("step-plan", [str(self.product_contract)])
        self.finish_ephemeral()
        architecture.write_text("# Architecture\n\nNode 22.\n\n### AD-1 In-memory board\n", encoding="utf-8")  # the review's edit
        lines = self.refused_import()
        # the template, not a column: where the cut falls depends on the length of this machine's temporary directory
        self.assertEqual(lines[0].replace(str(architecture), "<file>"),
                         "ShipLoop navigator: Restore AD-<n> in <file>; if the review changed it, improve-commit it; "
                         "then run complete again.")
        self.assertNotIn("AD-2", lines[0])
        self.assertIn("The architecture no longer mentions AD-2.", lines[1])
        # The named exit, read from the refusal (line 2 carries the heading): the heading it names, with the ID under it.
        heading = re.search(r"move it under a '([^']+)' heading", lines[1]).group(1)
        architecture.write_text(architecture.read_text(encoding="utf-8") + "\n## " + heading + "\n\nAD-2: split by layer instead.\n",
                                encoding="utf-8")
        self.commit_the_review("docs: keep the module decision\n\nKey learnings: a replaced decision moves under its heading.\n")
        self.import_the_review()  # the import that line 1 names; no commit refusal in between
        self.assertEqual(navigator.current_stage(store.read_record(self.run / "state.md")), "test-spec")
        self.assertIn("AD-2: split by layer instead.", self.home_git("show", "HEAD:docs/shiploop/architecture.md"))

    def test_test_spec_accepted_at_the_improve_stage_complete_with_validate_existing_after_it_is_no_close_and_prints_no_notice(self):
        """The import that accepts test-spec also records validate-existing.  test-spec is no close since consumer contract
        4b (its cases are in state): a home whose living files are prose is accepted, nothing is required of the feature
        folder, and no section notice prints (the notice belongs to the three closes)."""
        home = self.repo / "docs/shiploop"
        home.mkdir(parents=True, exist_ok=True)
        for name in knowledge.SECTIONS:
            (home / name).write_text("# " + name + "\n\nProse with no named sections.\n", encoding="utf-8")
        self._start_parent_at_stage("test-spec", [str(self.product_contract)])
        before = len(store.read_record(self.run / "state.md")["history"])
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        imported = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        state = store.read_record(self.run / "state.md")
        self.assertEqual([(row["stage"], row["outcome"]) for row in state["history"][before:]],
                         [("test-spec", "done"), ("validate-existing", "done")], "the route under test")
        self.assertNotIn("test-spec", knowledge.CLOSES)
        self.assertNotIn(knowledge.NOTICE_PREFIX, imported.stdout + imported.stderr)

    def test_a_review_that_restores_the_dropped_decision_exactly_has_nothing_to_commit_and_the_import_is_accepted(self):
        """"If the review changed it": a file back as it was at the bind has no edit of the review's left to commit."""
        architecture = self.commit_architecture()
        self._start_parent_at_stage("step-plan", [str(self.product_contract)])
        self.finish_ephemeral()
        architecture.write_text("# Architecture\n\nNode 22.\n\n### AD-1 In-memory board\n", encoding="utf-8")  # the review's edit
        lines = self.refused_import()
        self.assertIn("if the review changed it, improve-commit it; then run complete again.", lines[0])
        architecture.write_text(self.ARCHITECTURE, encoding="utf-8")  # the edit undone: no improve-commit
        self.import_the_review()
        self.assertEqual(navigator.current_stage(store.read_record(self.run / "state.md")), "test-spec")
        self.assertEqual(self.home_git("status", "--porcelain", "--", "docs"), "")

    def test_a_reviewed_step_plan_whose_architecture_looks_like_a_credential_is_committed_and_imported(self):
        """Owner decision 2026-10-16: no credential-pattern refusal. The review's architecture edit names auth shapes
        (`Password: bcrypt`, `token = get_token()`, `Auth: sf login (alias de)`), improve-commit commits it with a message
        that quotes one, and the Improve stage's complete imports it: no rewording is asked for on either route."""
        if not self.inline():
            self.skipTest("improve-commit is the inline route")
        architecture = self.commit_architecture()
        self._start_parent_at_stage("step-plan", [str(self.product_contract)])
        self.finish_ephemeral()
        written = self.ARCHITECTURE + "\nPassword: bcrypt, cost 12\ntoken = get_token()\nAuth: sf login (alias de)\n"
        architecture.write_text(written, encoding="utf-8")
        self.commit_the_review("docs: record the auth shapes\n\nKey learnings: the header was Authorization: Bearer "
                               "abcdefghijklmnop12345678 in the old client.\n")
        self.assertEqual(self.home_git("show", "HEAD:docs/shiploop/architecture.md"), written)
        self.assertEqual(self.home_git("status", "--porcelain", "--", "docs"), "")
        self.import_the_review()
        self.assertEqual(navigator.current_stage(store.read_record(self.run / "state.md")), "test-spec")

    def test_a_reviewed_stage_whose_summary_looks_like_a_credential_still_starts_its_improve_child(self):
        """CR-1 (owner decision 2026-10-16, no credential-pattern refusal): the Improve opening quotes the reviewed stage's
        summary, and a documentation line such as `Auth: sf login (alias de)` is what a run writes about its login. The
        producer's complete must start the child through the real gate on both routes: the opening holds the line as written,
        the contract is frozen from it and the runtime is active, with no refusal and no rewording asked for."""
        auth = "Auth: sf login (alias de)"
        summary = "Wrote the engine. " + auth + "; signature: static."
        self.assertTrue(privacy.sensitive_text(summary), "the screen the owner removed read this summary as a credential")
        self._start_parent_at_stage("step-plan", [str(self.product_contract)], producer_extra={"summary": summary})
        receipt = bridge.receipt_path(self.bound)
        self.assertTrue(receipt.is_file(), "the producer's complete started no Improve child")
        opening = receipt.with_name("opening.md").read_text(encoding="utf-8")
        self.assertIn("Its summary: " + summary, opening)
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "active")
        self.assertIn("Its summary: " + summary, self.child_context()["request"])
        self.assertEqual(store.read_record(self.run / "state.md")["active_improve"]["seed_result"]["summary"], summary)

    def test_the_notes_and_the_final_result_of_an_improve_import_may_quote_credential_looking_text(self):
        """Owner decision 2026-10-16: no credential-pattern refusal at the Improve stage's complete. The review's notes
        and a revised final result are taken as written; the accepted record holds the text and the run moves on."""
        self._start_parent_at_stage("step-plan", [str(self.product_contract)])
        self.finish_ephemeral()
        seed = store.read_record(self.run / "state.md")["active_improve"]["seed_result"]
        summary = "Auth: sf login (alias de); access token: not printed; Authorization: Bearer abcdefghijklmnop12345678"
        lessons = "The old client sent Authorization: Bearer abcdefghijklmnop12345678; use the session token: it expires."
        completion, _receipt = self.completion_receipt(final_result=dict(seed, summary=summary), lessons=lessons)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        state = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.current_stage(state), "test-spec")
        self.assertEqual(state["accepted"][self.action]["summary"], summary)
        self.assertEqual(state["improve_results"][self.action]["receipt"]["lessons"], lessons)

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
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion, status=2)
        self.assertEqual(before, (self.run / "state.md").read_bytes())

    def test_completion_names_the_review_files_it_needs(self):
        self.finish_ephemeral()
        evidence = bridge.receipt_path(self.bound).parent / "reviews"
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "first pass.md").write_text("misnamed\n", encoding="utf-8")
        before = (self.run / "state.md").read_bytes()
        result = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, status=2)
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
        # ShipLoop bound the recorded card itself at the transition (re-cut 2026-10-11): from any directory the cold
        # packet is the two instructions, with no bind step to run.
        self.assertNotIn("improve-bind", cold.stdout)
        self.assertIn("/improve " + navigator.IMPROVE_ARGUMENT_PREFIX, cold.stdout)
        bound_at_transition = store.read_record(run / "state.md")["active_improve"]["skill"]
        self.assertEqual(bound_at_transition["skill_card"], str(CARD.resolve()))
        self.assertEqual(bound_at_transition["runtime_cli"], str(EPHEMERAL.resolve()))
        # ShipLoop also started the child at that transition; the bind verb names the Improve stage's own id.
        improve_stage = store.read_record(run / "state.md")["active_improve"]["improve_action"]
        self.assertNotEqual(improve_stage, action)
        self.assertTrue(bridge.receipt_path(store.read_record(run / "state.md")["active_improve"]).is_file())
        reviewed = subprocess.run([sys.executable, "-B", str(CLI), "improve-bind", "--run-dir", str(run),
                                   "--action", action, "--skill-card", state["improve_skill"]], cwd="/",
                                  text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(reviewed.returncode, 2, reviewed.stdout + reviewed.stderr)
        self.assertIn("is not this run's Improve stage", reviewed.stderr)
        bound = subprocess.run([sys.executable, "-B", str(CLI), "improve-bind", "--run-dir", str(run),
                                "--action", improve_stage, "--skill-card", state["improve_skill"]], cwd="/",
                               text=True, capture_output=True, timeout=30, env=self.environment)
        self.assertEqual(bound.returncode, 0, bound.stderr)
        # the child is already bound to this card, so binding it by hand again records nothing new
        self.assertEqual(before, (run / "state.md").read_bytes())
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
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
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
        self.assertEqual(receipt["summary"], "Improve reviewed the spec result; it ended on pass 3, a trivial pass "
                                             "that left the content unchanged.")


class LoopContractShapeTests(unittest.TestCase):
    """A ShipLoop-written contract is in the Until Loop runtime's schema, whatever its size: the runtime has no limit."""

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

    def test_neither_the_runtime_nor_shiploop_limits_a_contract_s_size(self):
        runtime = (ROOT / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py").read_text()
        # Until Loop 0.8.1 removed its state-size cap (owner, 2026-10-11); ShipLoop's own 16 KiB budget went with it.
        self.assertNotIn("MAX_STATE_BYTES", runtime)
        for removed in ("STATE_LIMIT", "CONTRACT_BUDGET", "REPORT_RESERVE", "STATE_OVERHEAD", "compact_bytes",
                        "text_bytes", "size_problem"):
            with self.subTest(removed=removed):
                self.assertFalse(hasattr(loop_contract, removed))

    def test_the_runtime_accepts_a_large_contract_with_non_ascii_text(self):
        runtime = self.runtime()
        with tempfile.TemporaryDirectory() as workspace, tempfile.TemporaryDirectory() as state_dir:
            # the runtime requires an existing absolute workspace directory, and gate 2 a Git worktree it can measure
            subprocess.run(["git", "-C", workspace, "init", "-q"], check=True, capture_output=True)
            for text in ("plain ascii", "日本語の環境", "em dash \u2014 and \u201cquotes\u201d", "emoji \U0001f600 text"):
                with self.subTest(text=text):
                    contract = self.contract(request=text * 4000, environment=text * 400)
                    contract["workspace"] = workspace
                    self.assertGreater(len(json.dumps(contract, separators=(",", ":"), sort_keys=True).encode()), 20_000)
                    normalized = runtime._validate_contract(contract, input_contract=True)
                    self.assertEqual(normalized.pop("exit_checks"), [])
                    self.assertEqual(normalized.pop("candidate_paths"), [])  # the optional lists default to empty
                    self.assertEqual(normalized, contract)  # nothing else added, dropped or normalised
                    self.assertEqual(runtime.start(contract, state_dir)["status"], "active")

    def test_the_backchain_guidance_states_no_byte_limit_at_any_stage(self):
        for stage in sorted(prompts.BACKCHAIN_STAGES) + ["intake"]:
            with self.subTest(stage=stage):
                text = " ".join(prompts._backchain_guidance(stage).split())
                for gone in ("Until Loop state budget", "16,384", "9,216", "CONTRACT_FILE", "sort_keys=True"):
                    self.assertNotIn(gone, text)


class ImproveCommitContractTests(ImproveCliFixture):
    """improve-commit through the real CLI: what it checks, in what order, and that every refusal's named exit works.

    The shared helpers read LINE 1 of a refusal, take the command it ends with and run it, so a refusal that names
    an exit the gate then refuses cannot pass.  A neutral repository: nothing here comes from a saved run.
    """

    def _write_producer(self, stage):
        """Write self.producer as the current result; an INNER stage first runs its Until Loop for real.

        Every inner stage's complete checks its loop receipt (owner decision 2026-10-10), so the receipt joins the
        evidence_refs the way the printed template prefills it; parent_evidence_refs follows the submitted list.
        """
        if self.producer.get("outcome") == "done":
            # The consumer contract's hand-off fields (2026-10-11), when the test did not set them.
            if stage in ("test-spec", "verify", "carry-forward", "system-test-author", "system-test",
                         "release-plan", "release-verify"):
                self.producer.setdefault("assumptions", [])
            if stage == "step-plan":
                self.producer.setdefault("follows", [])
        if stage in stage_spec.INNER:
            self.producer = with_receipt(self.producer, finish_loop(self.run))
            self.parent_evidence_refs = list(self.producer["evidence_refs"])
        self.input = self.run / "inbox" / (self.action + ".md")
        store.write_record(self.input, self.producer)

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
        self.commit_args = [CLI, "improve-commit", "--run-dir", self.run, "--action", self.improve,
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

    def test_a_change_after_an_unchanged_first_pass_restarts_through_the_named_exit(self):
        """Fail-first: the refusal said to run the loop's next review, but the loop was already complete and
        --restart-stopped refused a complete child, so a live run (node-add-route, 2026-10-11) had to pause."""
        self.begin()
        _raw, first = self.start_ephemeral_child()
        _raw, terminal = self.done_ephemeral(first, self.child_report("trivial", "satisfied", "allowed", "one pass"))
        self.assertEqual(terminal["progress"], {"action_number": 1, "required_trivial_reviews": 2,
                                                "last_pass_changed_tree": False})
        self.edit()  # a fix made after the bind, then committed through improve-commit
        self.write("docs: fix the example\n\nKey learnings: none\n")
        self.invoke(*self.commit_args)
        completion, _receipt = self.completion_receipt()
        stderr = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
                             *completion, status=2).stderr
        line = self.line_one(stderr)
        self.assertIn("product/contracts/cold-recovery.md", line)
        # The refusal names its whole route on line 1: restart the review, run the improve skill on it, then complete.
        # Run the restart command it prints through the real CLI (the exit the refusal names must work).
        restart = shlex.split(re.search(r"start the review again with (.+? --restart-stopped)", line).group(1))
        self.assertEqual(restart[2:], ["improve-start", "--run-dir=" + str(self.run), "--action=" + self.improve,
                                       "--restart-stopped"])
        self.assertEqual(shlex.split(line.rsplit("then run: ", 1)[1])[2:],
                         ["complete", "--run-dir=" + str(self.run), "--action=" + self.improve])
        restarted = self.run_argv(restart)
        self.assertIn("Archived the stopped child", restarted.stderr)
        # ShipLoop wrote a fresh opening and started the new child itself; the model writes and starts nothing.
        receipt = bridge.receipt_path(self.bound)
        self.assertTrue(receipt.with_name("opening.md").is_file())
        self.finish_ephemeral(json.loads(receipt.read_text(encoding="utf-8")))
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

    def test_a_restarted_review_that_honestly_finds_nothing_more_is_accepted(self):
        """Review of 2026-10-12: the restart a refused unchanged pass names kept the original bind snapshot, so a
        restarted review that found nothing more to change ended on one unchanged pass and was refused again, with the
        same message, until the model contrived another edit.  The restart takes a fresh snapshot of the committed tree."""
        self.begin()
        _raw, first = self.start_ephemeral_child()
        self.done_ephemeral(first, self.child_report("trivial", "satisfied", "allowed", "one pass"))
        self.edit()
        self.write("docs: fix the example\n\nKey learnings: none\n")
        self.invoke(*self.commit_args)
        completion, _receipt = self.completion_receipt()
        line = self.line_one(self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
                                         *completion, status=2).stderr)
        restart = shlex.split(re.search(r"start the review again with (.+? --restart-stopped)", line).group(1))
        self.run_argv(restart)
        receipt = bridge.receipt_path(self.bound)
        restarted = json.loads(receipt.read_text(encoding="utf-8"))
        # the second review reads the committed tree and finds nothing: one honest unchanged pass
        _raw, done = self.done_ephemeral(restarted, self.child_report("trivial", "satisfied", "allowed", "nothing more"))
        self.assertEqual(done["progress"], {"action_number": 1, "required_trivial_reviews": 2,
                                            "last_pass_changed_tree": False})
        completion, _receipt = self.completion_receipt()
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

    def test_restarting_after_an_unchanged_pass_refuses_while_the_edit_is_uncommitted(self):
        """The fresh baseline must not hide an uncommitted edit: the restart names improve-commit first."""
        self.begin()
        _raw, first = self.start_ephemeral_child()
        self.done_ephemeral(first, self.child_report("trivial", "satisfied", "allowed", "one pass"))
        self.edit()  # not committed
        stderr = self.invoke(CLI, "improve-start", "--run-dir", self.run, "--action", self.improve,
                             "--restart-stopped", status=2).stderr
        self.assertIn("Commit this review's changes first", self.line_one(stderr))

    def test_check_only_on_the_improve_stage_is_refused_and_imports_nothing(self):
        """Review of 2026-10-12: --check-only on the Improve stage's id ran the real import.  It previews a producer
        stage's draft; the Improve stage has none, so it is refused with the command to run instead."""
        self.begin()
        self.finish_ephemeral()
        completion, _receipt = self.completion_receipt()
        before = (self.run / "state.md").read_bytes()
        stderr = self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, "--check-only",
                             *completion, status=2).stderr
        self.assertIn("--check-only previews a producer stage's draft result", self.line_one(stderr))
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve, *completion)  # the named command works
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

    def test_a_result_summary_with_opening_headings_still_starts_the_improve_stage(self):
        """Review of 2026-10-12 (P1): the opening pastes the result's summary, and a summary line "## Scope" made the
        contract parser read the opening as repeating that section, so the stage never started and the printed restart
        command refused for the same reason.  The summary is one line in the opening now."""
        run = self.base / "heading-run"
        base = [sys.executable, "-B", str(CLI)]

        def cli(*argv):
            done = subprocess.run([*base, *map(str, argv)], text=True, capture_output=True, cwd=self.base,
                                  timeout=30, env=self.environment)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            return done

        cli("init", "--repo", self.repo, "--run-dir", run, "--prompt", "Heading summary fixture",
            "--improve-skill", CARD, *self.delegation_args())
        state = store.read_record(run / "state.md")
        for stage in ("intake", "discovery", "research", "spec"):
            action = state["action"]["id"]
            result = run / "inbox" / (action + ".md")
            summary = ("Spec drafted.\n\n## Scope\nIn scope: the widget.\n\n## Environment\nPython.\n"
                       if stage == "spec" else "Fixture " + stage + " result.")
            store.write_record(result, {"outcome": "done", "summary": summary,
                                        **({"evidence_refs": [str(self.product_contract)]} if stage == "spec" else {})})
            done = cli("complete", "--run-dir", run, "--action", action, "--result", result)
            state = store.read_record(run / "state.md")
        self.assertNotIn("could not start", done.stdout + done.stderr)
        folder = bridge.receipt_path(state["active_improve"]).parent
        self.assertEqual(json.loads((folder / "packet.json").read_text(encoding="utf-8"))["status"], "active")
        opening = (folder / "opening.md").read_text(encoding="utf-8")
        self.assertEqual(opening.count("\n## Scope\n") + opening.startswith("## Scope\n"), 1)
        self.assertIn("Its summary: Spec drafted. ## Scope In scope: the widget.", opening)

    def test_the_plan_improve_stage_freezes_its_experiment_scratch_scope_when_it_starts(self):
        """Review of 2026-10-12 (P1): ShipLoop starts the plan child, so the scratch directory, the notebook and the
        experiment objective are in the frozen contract, not left for a model to freeze before a start that happened."""
        self.begin("plan")
        folder = bridge.receipt_path(self.bound).parent
        frozen = json.loads((folder / "start.json").read_text(encoding="utf-8"))
        state = store.read_record(self.run / "state.md")
        scratch = navigator.planning_scratch_dir(state, state["active_improve"])
        self.assertIn(str(scratch), frozen["context"]["scope"])
        self.assertIn(str(navigator.planning_notebook_path(state)), frozen["context"]["scope"])
        self.assertIn("Planning experiment objective", frozen["work"])
        handoff = navigator.improve_handoff_text(None, self.run, state)
        self.assertNotIn("freeze the exact candidate, this scratch directory", handoff)
        self.assertIn("ShipLoop froze the exact candidate, this scratch directory", handoff)

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
        stderr = self.invoke(CLI, "improve-commit", "--run-dir", self.run, "--action", self.improve,
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
        self.assertIn("no bound current Improve stage with this action", line)
        self.assertIn(" next ", line)
        self.assertIn("ShipLoop navigator | ", self.run_named(stderr).stdout)  # `next` reads the packet and exits 0
        bind = self.run / "improve" / (self.action + "-bind.md")
        bind.unlink()
        stderr = self.refused()
        line = self.line_one(stderr)
        self.assertIn("no bind snapshot", line)
        # the frozen contract lets the child run improve-commit and nothing else: the Improve stage's complete is the parent's
        self.assertIn("The bound child stops here", line)
        self.assertIn("Parent, run: ", line)
        self.assertEqual(self.named_exit(stderr)[2], "complete")

    def test_a_commit_message_with_credential_looking_text_is_committed_as_written(self):
        """Owner decision 2026-10-16: no credential-pattern refusal. The message is checked for its lessons and its
        citations only; a header line, a token-shaped citation and a prose mention of a token are all message text."""
        self.begin()
        self.edit()
        secret = "Bearer abcdefghijklmnop12345678"
        message = ("docs: fix\n\nKey learnings: the header was\nAuthorization: " + secret
                   + "\nUse the session token: it expires hourly\nAuth: sf login (alias de)\n")
        self.write(message)
        done = self.invoke(*self.commit_args)
        self.assertNotIn("Reword", done.stderr)
        self.assertNotIn("credential", done.stdout + done.stderr)
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), "docs: fix")
        self.assertIn("Authorization: " + secret, self.git("log", "-1", "--format=%B"))
        self.assertIn("Use the session token: it expires hourly", self.git("log", "-1", "--format=%B"))

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

    def test_the_lessons_and_citations_come_in_one_refusal_whatever_the_message_quotes(self):
        self.begin()
        self.edit()
        self.write("docs: fix\n\nAuthorization: Bearer abcdefghijklmnop12345678\nLearned-from: 0000000 no such commit\n")
        first = self.refused()
        # one refusal, not one turn per problem: line 1 asks for both fixes and the problem lines follow; the quoted
        # header is not a problem (no credential screen)
        self.assertTrue(self.line_one(first).startswith('Add a "Key learnings:'), first)
        self.assertIn("Learned-from", self.line_one(first))
        self.assertIn("- line 4: the ID names no commit in this repository", first)
        self.assertNotIn("Reword", first)
        self.write("docs: fix\n\nKey learnings: none\n")
        self.run_named(first)

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

    def start_child(self):
        """The frozen contract and parent-return.md ShipLoop wrote when it started the child at the transition."""
        receipt = bridge.receipt_path(self.bound)
        self.assertEqual(json.loads(receipt.read_text(encoding="utf-8"))["status"], "active")
        contract = json.loads(receipt.with_name("start.json").read_text(encoding="utf-8"))
        return contract, receipt.with_name("parent-return.md")

    def test_the_frozen_authority_lets_the_child_run_improve_commit_only_and_parent_return_holds_its_rules(self):
        self.begin("plan")  # the planning child: its packet prints no improve-commit line, so the contract is its only carrier
        contract, parent_return = self.start_child()
        authority = contract["context"]["authority"]
        self.assertIn("No push or merge", authority)
        self.assertIn("commit only with improve-commit, never git commit", authority)
        self.assertIn("The child runs no ShipLoop callback except improve-pass and improve-commit", authority)
        self.assertIn(str(parent_return), authority)
        self.assertNotIn("never runs a ShipLoop callback", authority)
        self.assertIn("no empty commit except a recorded remote change", authority)
        route = parent_return.read_text(encoding="utf-8")
        for needed in (str(self.message), "improve-commit --run-dir=" + str(self.run), "--message=" + str(self.message),
                       "Key learnings: none", "Learned-from: <commit id> <what it contributed>",
                       "Remote change: <system alias>, <what changed>, <where its evidence is>", "--remote-change",
                       "Never run git commit yourself", " complete --run-dir=" + str(self.run) + " --action=" + self.improve):
            with self.subTest(needed=needed):
                self.assertIn(needed, route)
        self.assertLess(route.index("improve-commit --run-dir="), route.index(" complete --run-dir="))
        self.assertLess(route.index("improve-pass --run-dir="), route.index("improve-commit --run-dir="))
        self.assertIn("The child never runs the complete command", route)

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

    IMPROVE_STAGES = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "system-test-author", "release-plan",
                      "carry-forward")

    def test_every_stage_builds_its_improve_contract_on_both_routes_with_the_commit_clause(self):
        """Size-free smoke over every Improve stage and route (the old guard measured the clause's byte cost)."""
        self.begin("plan")
        state = store.read_record(self.run / "state.md")
        parent_return = str(bridge.receipt_path(self.bound).with_name("parent-return.md"))
        for stage in self.IMPROVE_STAGES:
            for route in ("inline", "ask-agent"):
                with self.subTest(stage=stage, route=route):
                    chosen = dict(state, active_improve=dict(state["active_improve"], stage=stage), delegation=route)
                    built = navigator.improve_start_contract(None, self.run, chosen, "".join(
                        "## " + name + "\nx\n\n" for name in navigator.OPENING_SECTIONS))
                    authority = built["context"]["authority"]
                    self.assertIn("Commit policy:", authority)
                    self.assertIn(parent_return, authority)

    def commit_gate_refusal(self):
        """Run the child to its terminal packet with an uncommitted edit; the refusal the Improve stage's complete gives."""
        self.begin("spec")
        self.edit()
        self.finish_ephemeral(self.start_ephemeral_child()[1])
        self.completion, _receipt = self.completion_receipt()
        return self.invoke(CLI, "complete", "--run-dir", self.run, "--action", self.improve,
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
        self.assertEqual(argv[2:], ["improve-commit", "--run-dir=" + str(self.run), "--action=" + self.improve,
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
        self.assertIn("complete refuses a review that left its own edits uncommitted", checked)
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
        self.assertEqual(written, parent_return)  # the file the packet names is the one ShipLoop wrote at the start
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
        again = next(row for row in stderr.splitlines() if row.startswith("Then run the complete command again: "))
        argv = shlex.split(again.split(": ", 1)[1])  # the refusal prints it: a cleared parent needs no other packet
        self.assertEqual(argv[2], "complete")
        self.assertEqual(argv[-1], "--action=" + self.improve)  # the refusal names the Improve stage's id
        self.run_argv(argv)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])

    def run_argv(self, argv, status=0):
        result = subprocess.run(argv, text=True, capture_output=True, cwd=self.base, timeout=60, env=self.environment)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def test_the_uncommitted_edits_refusal_names_the_no_commit_exit_and_complete_accepts_it(self):
        stderr = self.commit_gate_refusal()
        exit_line = next(row for row in stderr.splitlines() if "--no-commit" in row)
        self.assertNotIn("receipt", exit_line)  # complete has no receipt file to edit: it has a flag
        # the command is on the line itself, last, with the instruction placeholder: submitted through the real gate
        argv = shlex.split(exit_line.split(": ", 1)[1])
        self.assertEqual((argv[2], argv[-2:]), ("complete", ["--no-commit", "<their instruction>"]))
        argv[-1] = "The user said not to commit."
        self.run_argv(argv)
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])


class ImprovePassTests(ImproveCliFixture):
    """improve-pass through the real CLI (rev 4 Step 6.3; IMP-2, IMP-5, IMP-8, IMP-11): the model writes review-<n>.md and,
    after an edit, a commit message and checks.md; ShipLoop checks them, commits, writes the runtime report and prints
    the runtime's done and the stage's complete, literal.  Every refusal's line 1 ends with the command to run next, and
    the tests run that command."""

    _write_producer = ImproveCommitContractTests._write_producer
    _start_parent = ImproveCommitContractTests._start_parent
    def setUp(self):
        super().setUp()
        self.environment["HOME"] = str(self.base / "home")

    git = ImproveCommitContractTests.git
    begin = ImproveCommitContractTests.begin
    edit = ImproveCommitContractTests.edit
    write = ImproveCommitContractTests.write
    line_one = ImproveCommitContractTests.line_one
    named_exit = ImproveCommitContractTests.named_exit
    run_named = ImproveCommitContractTests.run_named
    run_argv = ImproveCommitContractTests.run_argv

    REVIEW = ("---\nclassification: {label}\nexit: {exit}\ncontinuation: allowed\n---\n"
              "Read: the step result and the diff of product/contracts/cold-recovery.md.\n"
              "Found: {found}\n"
              "Changed: {changed}\n"
              "Checked: python3 -m pytest test/product_contract_test.py: 1 passed.\n"
              "Class: {why}\n"
              "## Handoff\nCandidate product/contracts/cold-recovery.md reviewed at pass {n}; nothing open.\n")

    def pass_args(self, *extra):
        return [CLI, "improve-pass", "--run-dir", self.run, "--action", self.improve, *extra]

    def reviews(self) -> Path:
        return bridge.receipt_path(self.bound).parent / "reviews"

    def write_review(self, n=1, *, label="trivial", exit="satisfied", found="nothing material.",
                     changed="none.", why="no change and nothing material.", text=None):
        path = self.reviews() / ("review-" + str(n) + ".md")
        path.write_text(text if text is not None else self.REVIEW.format(
            label=label, exit=exit, found=found, changed=changed, why=why, n=n), encoding="utf-8")
        return path

    def printed(self, stdout):
        """The three lines improve-pass prints for the model: the runtime's done, complete, and improve-pass again."""
        lines = stdout.splitlines()
        done = next(line for line in lines if " done --state " in line)
        complete = next(line for line in lines if line.startswith("When it returns status complete, run: "))
        again = next(line for line in lines if line.startswith("When it returns status active"))
        return done, complete.rsplit("run: ", 1)[1], again.rsplit("run: ", 1)[1]

    def run_done(self, line):
        """Run the printed done line as a host shell would (it reads its report from a redirect)."""
        result = subprocess.run(["/bin/sh", "-c", line], capture_output=True, text=True, cwd=self.base, timeout=60,
                                env=self.environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_an_unchanged_pass_gets_script_written_checks_and_the_printed_commands_finish_the_stage(self):
        self.begin()
        self.write_review()
        out = self.invoke(*self.pass_args()).stdout
        checks = (self.reviews() / "checks.md").read_text(encoding="utf-8")
        self.assertTrue(checks.startswith("Tree unchanged since improve-bind ("), checks)
        self.assertIn("producer checks: ", checks)
        report = json.loads((self.reviews() / "report-1.json").read_text(encoding="utf-8"))
        self.assertEqual({key: report[key] for key in ("classification", "exit_assessment", "continuation_assessment")},
                         {"classification": "trivial", "exit_assessment": "satisfied",
                          "continuation_assessment": "allowed"})
        self.assertIn("Found: nothing material.", report["evidence"])
        self.assertIn("files changed since the bind: none", report["evidence"])
        self.assertTrue(report["handoff"].startswith("Candidate product/contracts/cold-recovery.md reviewed"))
        done, complete, again = self.printed(out)
        # Literal and absolute: no shell variable, the receipt's own done_argv, the report by its absolute path.
        self.assertNotIn("$", done + complete + again)
        argv = json.loads(bridge.receipt_path(self.bound).read_text(encoding="utf-8"))["done_argv"]
        self.assertEqual(shlex.split(done), [*argv, "<", str(self.reviews() / "report-1.json")])
        self.assertEqual(shlex.split(again)[2:], ["improve-pass", "--run-dir=" + str(self.run),
                                                  "--action=" + self.improve])
        terminal = self.run_done(done)
        self.assertEqual(terminal["status"], "complete")
        self.run_argv(shlex.split(complete))
        self.assertIsNone(store.read_record(self.run / "state.md")["active_improve"])
        # IMP-11: passes.md at import, one row per pass with the listed fields.
        passes = (self.run / "improve" / self.action / "passes.md").read_text(encoding="utf-8")
        self.assertIn("| stage | pass | label | tree changed | seconds | skill call recorded |", passes)
        row = next(line for line in passes.splitlines() if line.startswith("| test-strategy | 1 |"))
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        self.assertEqual(cells[2:4], ["trivial", "n"])
        self.assertTrue(cells[4].isdigit(), row)
        self.assertEqual(cells[5], "not enforced")  # no Claude session bound this suite's run
        self.assertIn("Re-decide the Improve stop rule (IMP-4) at 10 step-stage reviews with at least 3 edits", passes)

    def test_an_edit_without_key_learnings_is_refused_and_the_named_exit_commits_and_records_the_pass(self):
        self.begin()
        self.edit()
        self.write_review(label="non-trivial", exit="unsatisfied", found="the example was wrong.",
                          changed="product/contracts/cold-recovery.md: fixed the example.", why="it changed a file.")
        refused = self.invoke(*self.pass_args(), status=2).stderr
        self.assertIn("left files uncommitted (product/contracts/cold-recovery.md)", self.line_one(refused))
        self.assertEqual(self.named_exit(refused)[2:3], ["improve-pass"])
        self.write("docs: fix the example\n")  # no Key learnings line
        refused = self.run_named(refused, status=2).stderr
        self.assertIn("Key learnings", self.line_one(refused))
        self.assertEqual(self.named_exit(refused)[2:3], ["improve-pass"])
        self.write("docs: fix the example\n\nKey learnings: an example must match the contract it shows.\n")
        (self.reviews() / "checks.md").write_text("python3 -m pytest: 1 passed\n", encoding="utf-8")
        out = self.run_named(refused).stdout
        self.assertIn("Committed this review's changes as ", out)
        self.assertIn("Key learnings: an example must match the contract it shows.", self.git("log", "-1", "--format=%B"))
        self.assertIn("checks.md written by the review after its last edit", out)
        facts = json.loads((self.reviews() / "pass-1.json").read_text(encoding="utf-8"))
        self.assertTrue(facts["changed"])
        self.assertEqual(len(facts["commit"]), 12)
        done, _complete, _again = self.printed(out)
        active = self.run_done(done)
        self.assertEqual(active["status"], "active")  # a pass that changed content never ends the loop

    def test_a_checks_file_older_than_the_last_edit_is_refused_and_the_named_exit_accepts_a_fresh_one(self):
        self.begin()
        checks = self.reviews() / "checks.md"
        checks.write_text("pre-filled before the edit: all green\n", encoding="utf-8")
        old = checks.stat().st_mtime - 60
        os.utime(checks, (old, old))
        self.edit()
        self.write("docs: fix the example\n\nKey learnings: none\n")
        self.write_review(label="non-trivial", exit="unsatisfied", changed="the example.", why="changed a file.")
        refused = self.invoke(*self.pass_args(), status=2).stderr
        self.assertIn("is older than the last edit", self.line_one(refused))
        checks.write_text("python3 -m pytest: 1 passed (after the edit)\n", encoding="utf-8")
        self.run_named(refused)
        self.assertTrue((self.reviews() / "report-1.json").is_file())

    def test_a_review_without_its_form_is_refused_with_what_is_missing_and_the_named_exit_accepts_it(self):
        self.begin()
        self.write_review(text="Findings: none material.\n")
        refused = self.invoke(*self.pass_args(), status=2).stderr
        line = self.line_one(refused)
        for missing in ("classification", "exit", "continuation", "Read:", "Checked:", "## Handoff"):
            self.assertIn(missing, line)
        self.assertFalse((self.reviews() / "report-1.json").exists())
        self.write_review()
        self.run_named(refused)
        self.assertTrue((self.reviews() / "report-1.json").is_file())

    def test_no_review_file_and_an_ended_loop_each_name_their_next_command(self):
        self.begin()
        refused = self.invoke(*self.pass_args(), status=2).stderr
        self.assertIn("review-1.md", self.line_one(refused))
        self.write_review()
        out = self.run_named(refused).stdout
        done, complete, _again = self.printed(out)
        self.run_done(done)
        ended = self.invoke(*self.pass_args(), status=2).stderr
        self.assertEqual(self.named_exit(ended), shlex.split(complete))

    def test_every_shiploop_command_the_improve_packet_and_improve_pass_print_drives_the_run_for_the_hooks(self):
        """IMP-8: the hooks bind and refresh a session only from a command they recognise; every ShipLoop command these
        prints name must be one, written literally with the run directory."""
        import shiploop_keepalive as keepalive
        self.begin()
        packet = self.invoke(CLI, "next", "--run-dir", self.run).stdout
        self.write_review()
        printed = self.invoke(*self.pass_args()).stdout
        commands = [match.group(0) for match in
                    re.finditer(r"python3 \S+/scripts/shiploop [a-z-]+ --run-dir=[^\s]+(?: --[a-z-]+=?[^\s]*)*",
                                packet + "\n" + printed)]
        verbs = {shlex.split(command)[2] for command in commands}
        self.assertTrue({"improve-pass", "complete"} <= verbs, verbs)
        for command in commands:
            with self.subTest(command=command):
                if shlex.split(command)[2] in ("pause", "improve-commit"):
                    continue  # not a driving command (a pause ends the turn; improve-commit prints no packet)
                self.assertTrue(keepalive.DRIVING_COMMAND.search(command), command)
                self.assertEqual(keepalive.command_run_dir({"tool_input": {"command": command}}), str(self.run))

    def test_the_implement_step_focus_names_an_unexercised_language_behaviour(self):
        """IMP-10 (kept only if the seeded string-comparison defect is caught at pass 1 in the live round, U31)."""
        self.assertIn("- a language or library behaviour the change relies on that no command has\n  exercised "
                      "(comparison and case rules, null and empty values, visibility,\n  ordering): run a one-line "
                      "probe or read its primary documentation;", prompts.IMPLEMENT_STEP_REVIEW_FOCUS)

    def test_focus_ids_are_off_by_default_and_when_on_a_review_must_answer_each_one(self):
        """IMP-6 (its own commit, default off): with FOCUS_IDS on, the handoff numbers the focus conditions F1..Fn and
        improve-pass refuses a review that leaves an id out; the named exit is accepted once each id is answered."""
        self.assertFalse(navigator.FOCUS_IDS)
        self.begin("test-strategy")
        state = store.read_record(self.run / "state.md")
        self.assertEqual(navigator.focus_ids(state, self.bound), [])
        with mock.patch.object(navigator, "FOCUS_IDS", True):
            ids = navigator.focus_ids(state, self.bound)
            lines = navigator._focus_lines(state, self.bound)
        self.assertGreater(len(ids), 2)
        self.assertIn("- F1: ", lines[0])
        self.assertIn("- " + ids[-1] + ": ", lines[0])
        self.assertIn("improve-pass refuses a review that leaves one out", lines[1])
        scripts = str(ROOT / "skills/shiploop/scripts")
        wrapper = [sys.executable, "-B", "-c",
                   "import runpy, sys; sys.path.insert(0, sys.argv[1]); import shiploop_navigator; "
                   "shiploop_navigator.FOCUS_IDS = True; cli = sys.argv[2]; sys.argv = [cli] + sys.argv[3:]; "
                   "runpy.run_path(cli, run_name='__main__')", scripts, str(CLI), "improve-pass",
                   "--run-dir", str(self.run), "--action", self.improve]
        review = self.write_review()
        refused = self.run_argv(wrapper, status=2).stderr
        self.assertIn(", ".join(ident + ":" for ident in ids), self.line_one(refused))
        review.write_text(review.read_text(encoding="utf-8") + "".join(ident + ": none\n" for ident in ids),
                          encoding="utf-8")
        self.run_argv(wrapper)
        self.assertTrue((self.reviews() / "report-1.json").is_file())

    def test_a_live_shaped_pass_needs_at_most_1500_characters_of_model_output(self):
        """6.3 exit 2 (projected, offline): what the model writes for one pass is the review file and the two printed
        commands it copies (improve-pass, then the runtime's done; complete runs once per stage, not per pass).  The
        report JSON, checks.md and the shell variables of the live tails (2.0 to 2.4 KB per tail, IMP-8) are gone.
        The commands carry this suite's paths (a run directory of about 100 characters)."""
        self.begin("step-plan")
        review = self.write_review(
            found="S2 relies on a case-insensitive comparison that no command exercised; a one-line probe showed the "
                  "language compares case-sensitively, so the step's criterion C3 held.",
            why="nothing to change after the probe; the content is as the previous pass left it.")
        out = self.invoke(*self.pass_args()).stdout
        done, _complete, _again = self.printed(out)
        command = shlex.join(["python3", *map(str, self.pass_args()[:1])]) + " " + shlex.join(
            ["improve-pass", "--run-dir=" + str(self.run), "--action=" + self.improve])
        written = len(review.read_bytes()) + len(command.encode()) + len(done.encode())
        self.assertLessEqual(written, 1500, (len(review.read_bytes()), len(command), len(done), len(str(self.run))))


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
    test_shiploop_writes_the_opening_freezes_the_contract_and_starts_the_runtime = (
        EphemeralImproveCliTests.test_shiploop_writes_the_opening_freezes_the_contract_and_starts_the_runtime)
    test_the_producers_complete_leaves_the_improve_stage_started = (
        EphemeralImproveCliTests.test_the_producers_complete_leaves_the_improve_stage_started)
    test_improve_complete_is_not_a_command = EphemeralImproveCliTests.test_improve_complete_is_not_a_command
    test_a_reviewed_stage_whose_summary_looks_like_a_credential_still_starts_its_improve_child = (
        EphemeralImproveCliTests.test_a_reviewed_stage_whose_summary_looks_like_a_credential_still_starts_its_improve_child)


if __name__ == "__main__":
    unittest.main()
