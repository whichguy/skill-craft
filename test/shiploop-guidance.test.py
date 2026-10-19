#!/usr/bin/env python3
"""Focused ShipLoop prompt, reference-routing, and cold-context guidance checks.

These tests verify the durable material supplied to a fresh agent. They do not
claim that an LLM interpreted a locator correctly or that Improve executed.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
REFERENCES = SCRIPTS.parent / "references"
IMPROVE_CARD = ROOT / "skills" / "improve" / "SKILL.md"
STANDALONE_ROUTE = ROOT / "skills" / "improve" / "references" / "standalone-route.md"   # the card's five standalone sections (plan U18)
# Packet re-cut (2026-10-11): the stages that place or revalidate the harness cite the guide; test-spec,
# validate-existing, implement, verify and system-test dropped the label (their drafts never cite it).
TEST_HARNESS_STAGES = (
    "test-strategy", "step-plan", "test", "system-test-author",
)
REPEATABLE_TEST_SUITE_ROUTE = (
    "Repeatable test-suite guide: "
    + str(REFERENCES / "repeatable-test-suites.md#select-or-revalidate-the-harness")
)
TEST_FACILITY_STAGES = (
    "test-strategy", "plan", "step-plan", "test-spec", "test",
    "carry-forward", "system-test-author", "release-plan",
)
REUSABLE_TEST_FACILITY_ROUTE = (
    "Reusable test facilities: "
    + str(REFERENCES / "repeatable-test-suites.md#reuse-and-define-test-facilities")
)
RELEASE_OPERATION_STAGES = (
    "release-plan",
    "release-check",
    "release",
    "release-verify",
)
RELEASE_OPERATION_LABEL = "Release operation guidance"
RELEASE_OPERATION_REFERENCE = "environment-lifecycle.md#release-operation-ownership"
RELEASE_OPERATION_PATH = REFERENCES / "environment-lifecycle.md"
RELEASE_OPERATION_ANCHOR = "release-operation-ownership"
RELEASE_OPERATION_ROUTE = (
    RELEASE_OPERATION_LABEL + ": " + str(REFERENCES / RELEASE_OPERATION_REFERENCE)
)

# Deliberately independent of the prompt catalog: these are the only stages
# where a local skill must be discoverable before or during a skill decision.
LOCAL_SKILL_ROUTE_STAGES = (
    "discovery", "carry-forward",
)
# Packet re-cut (2026-10-11): step-plan dropped the guide label (its draft never cites it); it still prints the
# repository knowledge index line, so its `skills` item can reread the index.
LOCAL_SKILL_INDEX_STAGES = (
    "discovery", "step-plan", "carry-forward",
)
LOCAL_SKILL_GUIDE_ROUTE = (
    "Repository-local skill guidance: "
    + str(REFERENCES / "testing-and-documentation.md#reusable-product-skills")
)
CODING_GUIDE_STAGES = ("step-plan", "implement", "verify")
CODING_GUIDE_ROUTE = (
    "Coding decision guide: " + str(REFERENCES / "coding-guidance.md#select-guidance")
)
SERVICE_DISCOVERY_GUIDE = "service-discovery.md"
SERVICE_DISCOVERY_GUIDANCE_LABEL = "Service discovery guidance"
SERVICE_DISCOVERY_ANCHORS = (
    "select-scope",
    "remote-capabilities-and-state",
    "runtime-state-placement",
    "cache-and-authorization",
    "asynchronous-cooperation",
    "observability-coverage",
    "development-handoff",
    "verification",
)
# Packet re-cut (2026-10-11): document dropped the label; its duty never cites the guide (draft document.md).
SERVICE_DISCOVERY_STAGE_ANCHORS = {
    "discovery": "select-scope",
    "research": "select-scope",
    "spec": "verification",
    "test-strategy": "verification",
    "plan": "development-handoff",
    "step-plan": "development-handoff",
    "implement": "development-handoff",
    "verify": "verification",
    "operations": "observability-coverage",
    "handoff": "development-handoff",
}
SERVICE_DISCOVERY_ROUTES = {
    stage: (
        SERVICE_DISCOVERY_GUIDANCE_LABEL
        + ": "
        + str(REFERENCES / (SERVICE_DISCOVERY_GUIDE + "#" + anchor))
    )
    for stage, anchor in SERVICE_DISCOVERY_STAGE_ANCHORS.items()
}

DISCOVERY_INVESTIGATION_GUIDANCE_LABEL = "Discovery investigation guidance"
DISCOVERY_INVESTIGATION_GUIDE = "research-loop.md"
DISCOVERY_INVESTIGATION_ANCHOR = "plan-the-investigation"
DISCOVERY_INVESTIGATION_STAGES = ("discovery", "research")

CONNECTED_KNOWLEDGE_DISCOVERY_LABEL = "Connected knowledge discovery"
CONNECTED_KNOWLEDGE_DISCOVERY_GUIDE = "project-knowledge.md"
CONNECTED_KNOWLEDGE_DISCOVERY_ANCHOR = "connected-knowledge-discovery"
CONNECTED_KNOWLEDGE_DISCOVERY_STAGES = ("discovery", "research")

DISCOVERY_EVIDENCE_HANDOFF_LABEL = "Discovery evidence handoff"
DISCOVERY_EVIDENCE_HANDOFF_GUIDE = "project-knowledge.md"
DISCOVERY_EVIDENCE_HANDOFF_ANCHOR = "discovery-evidence-handoff"
DISCOVERY_EVIDENCE_HANDOFF_STAGES = ("discovery", "research")

CURRENT_SYSTEM_BASELINE_GUIDE = "current-system-baseline.md"
CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL = "Current-system baseline guide"
CURRENT_SYSTEM_BASELINE_ANCHORS = (
    "establish-or-refresh",
    "evidence-and-authority",
    "remote-only-systems",
    "planning-and-review-handoff",
    "retain-across-runs",
)
# Deliberately independent of the prompt catalog: only these stages receive the
# current-system baseline guide, with the named section for their decision.  Packet re-cut (2026-10-11): test-strategy,
# plan and step-plan read the baseline note directly and never cite the guide, so their label is dropped.
CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS = {
    "discovery": "establish-or-refresh",
    "research": "evidence-and-authority",
    "spec": "planning-and-review-handoff",
    "validate-existing": "evidence-and-authority",
    "document": "retain-across-runs",
    "carry-forward": "retain-across-runs",
    "product-acceptance": "retain-across-runs",
    "handoff": "retain-across-runs",
}
CURRENT_SYSTEM_BASELINE_ROUTES = {
    stage: (
        CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL
        + ": "
        + str(REFERENCES / (CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor))
    )
    for stage, anchor in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.items()
}
HOUSE_STYLE_GUIDE = "house-style.md"
HOUSE_STYLE_GUIDANCE_LABEL = "House-style guidance"
# Deliberately independent of the prompt catalog: extract at discovery, contract
# at step planning, reread while building, retain at carry-forward.  Packet re-cut (2026-10-11): test code follows Code
# craft rule 1 and verify checks the diff against the step plan's contract, so those two stages dropped the label.
HOUSE_STYLE_STAGE_ANCHORS = {
    "discovery": "extract-the-house-style",
    "step-plan": "write-the-match-contract",
    "implement": "match-while-building",
    "carry-forward": "retain-the-house-style",
}
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_context_index as context_index  # noqa: E402
import shiploop_knowledge_home as knowledge_home  # noqa: E402
import shiploop_navigator as navigator  # noqa: E402
import shiploop_planning_revision as planning_revision  # noqa: E402
import shiploop_packet_symbols as symbols  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_reference as run_reference  # noqa: E402
import shiploop_standalone_improve as standalone_improve  # noqa: E402
import shiploop_store as store  # noqa: E402


def render_with_guides(*args, **kwargs) -> str:
    """The packet, with GUIDES/<file> written as the guide's absolute path: these tests pin WHICH guide a packet routes to
    (a packet prints guides as GUIDES/<file> since 2026-10-16; the References block defines the symbol)."""
    return symbols.guides_expanded(navigator.render(*args, **kwargs))


def handoff_with_guides(*args, **kwargs) -> str:
    """The Improve handoff file's text, guides expanded as in ``render_with_guides``."""
    return symbols.guides_expanded(navigator.improve_handoff_text(*args, **kwargs))


def heading_anchor(text: str) -> str:
    """Match the simple anchor IDs emitted by the package Markdown headings."""
    value = text.strip().lower()
    value = re.sub(r"\s+#+$", "", value)
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"-+", "-", re.sub(r"\s+", "-", value)).strip("-")


def normalized(text: str) -> str:
    """Compare prompt clauses without making line wrapping part of the contract."""
    return " ".join(text.split())


def result(stage: str, **extra: object) -> dict[str, object]:
    """Return a deliberately synthetic producer result for prompt traversal."""
    return {
        "outcome": "done",
        "summary": f"Synthetic producer result for {stage}.",
        "evidence_refs": [f"synthetic://evidence/{stage}"],
        **extra,
    }


def receipt(stage: str) -> dict[str, object]:
    """Return a synthetic receipt accepted by the pure navigator state API."""
    return {
        "summary": f"Synthetic Improve completion for {stage}.",
        "review_refs": [f"synthetic://review/{stage}"],
        "check_refs": [f"synthetic://check/{stage}"],
        "lessons": f"Synthetic lesson for {stage}.",
    }



# A blocked result waits on a person or an outside service and says which (run-insights N5: `awaiting` replaced
# blocked_by).  Synthetic waits for the fixtures below; the old external value became a service wait, an access or
# user value a present or answer wait.
RELEASE_HOST_WAIT = {"kind": "service", "service": "the release host",
                     "check": "test -f release-host.ready",
                     "no_default": "Nothing can be released until the host is reachable."}
STRATEGY_HOST_WAIT = {"kind": "service", "service": "the test-runner host",
                      "check": "test -f test-runner.ready",
                      "no_default": "No test strategy can be chosen without the host."}
PLAN_HOST_WAIT = {"kind": "service", "service": "the supplier's storage service",
                  "check": "test -f storage.ready",
                  "no_default": "The storage prerequisite is the supplier's and no recorded default replaces it."}
SPEC_ANSWER_WAIT = {"kind": "answer", "question": "Which fixture does the test spec use?",
                    "options": ["the isolated fixture", "the shared fixture"],
                    "no_default": "Either fixture changes what the cases observe and the request does not say."}


_REAL_READ_TEXT = Path.read_text


def _knowledge_reads_only():
    """A ``Path.read_text`` that lets a render read only the knowledge home and the run baseline.

    The packet quotes the living files whole (consumer contract D1, knowledge_home.reads_quotes) and names the run's
    spec-diff baseline; any other read, such as a host evidence locator, is the defect this guard catches.
    """
    def read_text(self, *args, **kwargs):
        text = str(self)
        if "/docs/shiploop/" in text or text.endswith("/" + knowledge_home.RUN_BASELINE):
            return _REAL_READ_TEXT(self, *args, **kwargs)
        raise AssertionError("render read evidence: " + text)
    return read_text

class GuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-guidance-")
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.run = Path(self.temp.name) / "run"
        self.run.mkdir()

    def state(self) -> dict:
        # These route checks were written against the delegated route; the
        # inline default is pinned by the delegation suite.
        return navigator.new_state(
            str(self.repo),
            "Build a small capability with the repository's approved convention.",
            improve_skill="",
            delegation="ask-agent",
        )

    def produce(self, state: dict, **extra: object) -> tuple[dict, dict]:
        """Apply one synthetic producer result; a checkpoint stage parks its child."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        return navigator.apply(state, action["id"], result(stage, **extra)), action

    def pending_improve(self, state: dict, **extra: object) -> tuple[dict, dict]:
        """Return the state parked with the real Improve child of a checkpoint stage."""
        stage = navigator.current_stage(state)
        waiting, action = self.produce(state, **extra)
        self.assertIsNotNone(waiting.get("active_improve"),
                             stage + " is not an Improve checkpoint")
        return waiting, action

    def complete_stage(self, state: dict, **extra: object) -> tuple[dict, str]:
        """Advance one synthetic producer (and its Improve pair, if checkpointed)."""
        stage = navigator.current_stage(state)
        action = dict(navigator.current_action(state))
        waiting = navigator.apply(state, action["id"], result(stage, **extra))
        if waiting.get("active_improve") is None:
            return waiting, action["id"]
        return navigator.finish_improve(waiting, action["id"], receipt(stage)), action["id"]

    def complete_stage_with_final(
        self, state: dict, final_result: dict[str, object], **extra: object
    ) -> tuple[dict, str]:
        """Import an Improve-revised result through the normal current parent transition."""
        stage = navigator.current_stage(state)
        waiting, action = self.pending_improve(state, **extra)
        return (
            navigator.finish_improve(waiting, action["id"], receipt(stage), final_result),
            action["id"],
        )

    def save_reload(self, state: dict) -> dict:
        navigator.save(self.run, state)
        return store.read_record(self.run / "state.md")

    def packet_with_handoff(self, state: dict, *, guarded: bool = False) -> str:
        """The packet a cleared model reads; for an Improve child, the packet then the handoff file it names.

        Packet re-cut R3: the Improve packet is two instructions and everything else the child needs is in the handoff
        file (``improve_handoff_text``), so one string holds both.  ShipLoop binds the run's recorded card at the
        transition; a state parked unbound here is bound the same way for the render only.
        """
        shown = state
        child = state.get("active_improve")
        if child is not None and child["skill"] is None:
            shown, _ = navigator._improve_entry(self.run, {**state, "improve_skill": str(IMPROVE_CARD)})
        if guarded:
            with patch.object(Path, "read_text", new=_knowledge_reads_only()):
                packet = render_with_guides(None, self.run, shown)
        else:
            packet = render_with_guides(None, self.run, shown)
        if shown.get("active_improve") is not None and shown["active_improve"]["skill"] is not None:
            packet += "\n" + handoff_with_guides(None, self.run, shown)
        return packet

    def cold_packet(self, state: dict) -> tuple[dict, str]:
        recovered = self.save_reload(state)
        before = (self.run / "state.md").read_bytes()
        packet = self.packet_with_handoff(recovered, guarded=True)
        self.assertEqual((self.run / "state.md").read_bytes(), before)
        return recovered, packet

    def assert_policy_route(self, packet: str, route: str, state: dict) -> None:
        """A policy locator is printed once when the packet's text names its label, else only in reference.md.

        2026-10-11 dedupe: the long policy list moved to reference.md#policies; a packet prints a
        locator only for a label its own text names, and always points at that file for the rest.
        """
        label = route.split(": ", 1)[0]
        printed = packet.count(route)
        named = packet.count(label) - printed
        self.assertLessEqual(printed, 1, packet)
        if named > 0:
            self.assertEqual(printed, 1, packet)
        self.assertIn(route, run_reference.render(state, self.run))
        self.assertIn("reference.md (#policies", packet)

    def test_stage_reference_catalog_is_complete_and_resolves(self) -> None:
        self.assertEqual(set(prompts.STAGE_REFERENCES), set(prompts.STAGES))
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = prompts.STAGE_REFERENCES[stage]
                self.assertIsInstance(entries, tuple)
                self.assertTrue(entries)
                for label, locator in entries:
                    self.assertIsInstance(label, str)
                    self.assertTrue(label.strip())
                    filename, separator, anchor = locator.partition("#")
                    self.assertEqual(separator, "#")
                    self.assertTrue(filename)
                    self.assertTrue(anchor)
                    path = REFERENCES / filename
                    self.assertTrue(path.is_file(), locator)
                    text = path.read_text(encoding="utf-8")
                    headings = {
                        heading_anchor(match.group(2))
                        for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text)
                    }
                    # An explicit HTML anchor keeps a stable locator across a heading rename.
                    headings.update(re.findall(r"<a id=\"([^\"]+)\"></a>", text))
                    self.assertIn(anchor, headings, locator)

    def test_current_system_baseline_stage_routes_are_exact_and_selective(self) -> None:
        """Keep the guide's graph projection independent of the prompt catalog."""
        observed: list[str] = []
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (label, locator)
                    for label, locator in prompts.STAGE_REFERENCES[stage]
                    if label == CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL
                ]
                anchor = CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.get(stage)
                if anchor is None:
                    self.assertEqual(entries, [])
                else:
                    self.assertEqual(
                        entries,
                        [(
                            CURRENT_SYSTEM_BASELINE_GUIDANCE_LABEL,
                            CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor,
                        )],
                    )
                    observed.append(stage)
        self.assertEqual(tuple(observed), tuple(CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS))

    def test_house_style_stage_routes_are_exact_and_selective(self) -> None:
        """Only the stages that extract, contract, build, check or retain the style get it."""
        observed: list[str] = []
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (label, locator)
                    for label, locator in prompts.STAGE_REFERENCES[stage]
                    if label == HOUSE_STYLE_GUIDANCE_LABEL
                ]
                anchor = HOUSE_STYLE_STAGE_ANCHORS.get(stage)
                if anchor is None:
                    self.assertEqual(entries, [])
                else:
                    self.assertEqual(
                        entries,
                        [(HOUSE_STYLE_GUIDANCE_LABEL, HOUSE_STYLE_GUIDE + "#" + anchor)],
                    )
                    observed.append(stage)
        self.assertEqual(tuple(observed), tuple(HOUSE_STYLE_STAGE_ANCHORS))

    def test_match_contract_reaches_every_stage_that_builds_or_checks_the_item(self) -> None:
        """The contract lives in the step-plan result; work items take context only at plan."""
        for stage in ("implement", "test", "verify", "document"):
            with self.subTest(stage=stage):
                self.assertIn("item:step-plan", context_index.STAGE_READS[stage])

    def test_current_system_baseline_guide_relocates_with_recovery_cue(self) -> None:
        """The portable guide retains anchors and a minimal stale/missing recovery cue.

        This checks durable guide material only, not whether a host detects or
        refreshes a live snapshot.
        """
        guide = REFERENCES / CURRENT_SYSTEM_BASELINE_GUIDE
        self.assertTrue(guide.is_file(), guide)
        if not guide.is_file():
            return
        body = guide.read_text(encoding="utf-8")
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", body)
        }
        for anchor in CURRENT_SYSTEM_BASELINE_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, headings)

        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        copied_guide = relocated / CURRENT_SYSTEM_BASELINE_GUIDE
        copied_body = copied_guide.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", copied_body)
        recovery = normalized(copied_body).lower()
        self.assertRegex(recovery, r"\b(?:missing|absent|stale|outdated)\b")
        self.assertRegex(recovery, r"\b(?:refresh|re-establish|rebuild|recover)\b")
        for stage, anchor in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS.items():
            with self.subTest(stage=stage, anchor=anchor):
                filename, separator, route_anchor = (
                    CURRENT_SYSTEM_BASELINE_GUIDE + "#" + anchor
                ).partition("#")
                self.assertEqual(separator, "#")
                destination = relocated / filename
                self.assertTrue(destination.is_file(), destination)
                destination_headings = {
                    heading_anchor(match.group(2))
                    for match in re.finditer(
                        r"(?m)^(#{1,6})\s+(.+?)\s*$",
                        destination.read_text(encoding="utf-8"),
                    )
                }
                self.assertIn(route_anchor, destination_headings)

        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", copied_body):
            if link.startswith(("https://", "http://")):
                continue
            with self.subTest(link=link):
                path, _, anchor = link.partition("#")
                destination = (copied_guide.parent / path).resolve() if path else copied_guide
                self.assertTrue(destination.is_relative_to(relocated), link)
                self.assertTrue(destination.is_file(), link)
                if anchor:
                    destination_headings = {
                        heading_anchor(match.group(2))
                        for match in re.finditer(
                            r"(?m)^(#{1,6})\s+(.+?)\s*$",
                            destination.read_text(encoding="utf-8"),
                        )
                    }
                    self.assertIn(anchor, destination_headings)

    def test_current_system_baseline_routes_survive_cold_lifecycle_and_pending_improve(self) -> None:
        """Cold packets preserve only the relevant locator through one synthetic run.

        This exercises save/reload and normal producer/Improve transitions. It
        proves route plumbing and explicitly supplied handoff locators, not that
        a model validated a source, understood a baseline, or performed a real
        review.
        """
        routes = tuple(dict.fromkeys(CURRENT_SYSTEM_BASELINE_ROUTES.values()))
        notes = self.run / "notes"
        notes.mkdir()
        prior_baseline = notes / "prior-baseline.md"
        incoming_spec = notes / "incoming-spec.md"
        prior_baseline.write_text(
            "# Prior product baseline\n\n## Accepted baseline\n\nFixture baseline.\n",
            encoding="utf-8",
        )
        incoming_spec.write_text(
            "# Incoming specification\n\n## Requested delta\n\nFixture delta.\n",
            encoding="utf-8",
        )
        prior_baseline_ref = str(prior_baseline) + "#accepted-baseline"
        incoming_delta_ref = str(incoming_spec) + "#requested-delta"
        product_refs = [prior_baseline_ref, incoming_delta_ref]
        item_context = (
            "W1 host-authored current-system handoff: reopen prior baseline "
            + prior_baseline_ref
            + " and incoming delta "
            + incoming_delta_ref
            + "; retain their selected sections and revalidation condition."
        )
        observed: list[str] = []
        state = self.state()

        def assert_packet(stage: str, packet: str) -> None:
            expected = CURRENT_SYSTEM_BASELINE_ROUTES.get(stage)
            for route in routes:
                with self.subTest(stage=stage, route=route):
                    self.assertEqual(packet.count(route), int(route == expected), packet)

        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, producer_packet = self.cold_packet(state)
            self.assertEqual(navigator.current_stage(recovered), stage)
            assert_packet(stage, producer_packet)
            if stage == "plan":
                # The preceding host-authored test-strategy result explicitly
                # carries these locators; the navigator did not discover them.
                self.assertIn(prior_baseline_ref, symbols.expanded(producer_packet))
                self.assertIn(incoming_delta_ref, symbols.expanded(producer_packet))
            if stage == "step-plan":
                self.assertEqual(navigator._current_work_item(recovered), "W1")
                self.assertIn("Work item context: " + item_context, producer_packet)
                self.assertIn(prior_baseline_ref, symbols.expanded(producer_packet))
                self.assertIn(incoming_delta_ref, symbols.expanded(producer_packet))

            extra: dict[str, object] = {}
            if stage in {"discovery", "test-strategy", "plan", "step-plan"}:
                # These are synthetic host-authored handoffs in ordinary result
                # fields, never inferred by the navigator from the fixture files.
                extra["evidence_refs"] = product_refs
            if stage == "plan":
                extra["work_items"] = [
                    {
                        "id": "W1",
                        "title": "Retain current-system baseline",
                        "context": item_context,
                    }
                ]
            waiting, action = self.produce(recovered, **extra)
            if waiting["active_improve"] is None:
                state = waiting
                continue
            # Only planning stages and the final carry-forward park a child.
            pending, pending_packet = self.cold_packet(waiting)
            self.assertEqual(navigator.current_stage(pending), stage)
            self.assertIn("Current action: Improve the completed " + stage, pending_packet)
            assert_packet(stage, pending_packet)
            if stage in {"test-strategy", "step-plan"}:
                self.assertIn(prior_baseline_ref, pending_packet)
                self.assertIn(incoming_delta_ref, pending_packet)
            if stage == "step-plan":
                self.assertIn("Work item context: " + item_context, pending_packet)
            if stage in CURRENT_SYSTEM_BASELINE_STAGE_ANCHORS:
                observed.append(stage)
            state = navigator.finish_improve(pending, action["id"], receipt(stage))

        # Packet re-cut: test-strategy, plan and step-plan dropped the baseline guide label, so only the stages that still
        # cite it and park an Improve child are observed.
        self.assertEqual(tuple(observed), ("spec", "carry-forward"))

    def test_cold_lifecycle_packets_keep_clause_surface_and_due_phase(self) -> None:
        """A compact requirement survives planning and due-stage reconciliation.

        This tests supplied guidance and recovery, not whether a host obeys it.
        The expected stages/clauses are declared here independently of routing.
        """
        duties = {
            "spec": "independently verifiable clauses",
            "test-strategy": "required surface, due stage, owner, prerequisites",
            "test-spec": "One `test_cases` row per ID the step plan's focused commands list",
            "test": "Each case ends as:",
            "step-plan": "Confirm by: <command, observation or inspection>; pass when <expected result>",
            "implement": "Each iteration edits first.",
            "verify": "Criterion or check unachievable as planned: report send-back naming it.",
            "product-acceptance": "pending release verification",
            "release-verify": "the consumer entry reached after authentication",
        }
        reconciles = {"verify", "system-test",
                      "product-acceptance", "release-verify", "handoff"}
        locator = str(REFERENCES / "testing-and-documentation.md#stage-readiness-and-completion")
        state = self.state()
        clause = "docs/requirements.md#capture: observe capture in the deployed UI; due release-verify"
        visited = set()
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            with self.subTest(stage=stage):
                # The long rules and the policy locators live once in the run reference file
                # (2026-10-11 dedupe); every packet points at it.
                reference = normalized(run_reference.render(recovered, self.run))
                self.assertIn(locator, reference)
                self.assertIn("reference.md", packet)
                self.assertIn("Definition of Ready", reference)
                self.assertIn("Definition of Done", reference)
                if stage in duties:
                    self.assertIn(duties[stage], normalized(packet))
                if stage in reconciles:
                    self.assertIn("required surface and due phase", normalized(packet))
                    # Packet re-cut: "A pass on another surface only supports" replaced "supporting evidence".
                    self.assertIn("A pass on another surface only supports", normalized(packet))
                    if stage != "release-verify":
                        # release-verify's draft dropped "A case not yet due keeps its phase": every case it verifies
                        # is due once the release is out (reported in the pin-update report).
                        self.assertIn("not yet due", normalized(packet))
                if navigator._current_work_item(recovered) is not None:
                    self.assertIn(clause, packet)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Capture behavior", "context": clause}]
            state, _ = self.complete_stage(state, **extra)
            visited.add(stage)
        self.assertEqual(len(visited), 24)

    def test_quality_guidance_keeps_planning_review_and_product_review_distinct(self) -> None:
        for stage in ("spec", "test-spec", "validate-existing", "release-verify"):
            with self.subTest(stage=stage):
                text = normalized(prompts.improve_prompt(stage))
                self.assertIn("selected staged/unstaged/untracked candidate paths", text)
                self.assertIn("required surface and due phase", text)
                self.assertIn("Follow the selected Improve card's review, commit and completion policies", text)
                self.assertIn("does not require future product checks to pass", text)
        self.assertIn(
            "Repeated templated wording is an audit cue only",
            normalized(IMPROVE_CARD.read_text() + STANDALONE_ROUTE.read_text()),
        )
        # Inspection of an untracked candidate must not grant edit authority.  The guard
        # is discovery's alone now: validate-existing may make a preparatory fix and has
        # no Improve child.
        discovery = normalized(prompts.improve_prompt("discovery"))
        self.assertIn("may not edit product source, tests", discovery)

    def test_each_current_packet_renders_its_selected_stage_references(self) -> None:
        state = self.state()
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            packet = render_with_guides(None, self.run, state)
            for label, locator in prompts.STAGE_REFERENCES[stage]:
                with self.subTest(stage=stage, locator=locator):
                    self.assertIn(label + ": " + str(REFERENCES / locator), packet)
            if stage == "plan":  # packet re-cut: step-plan no longer cites the Git-history guide (draft step-plan.md)
                # Independent of the catalog: removing this route must not
                # redefine the expected guidance available after cold recovery.
                _recovered, cold_packet = self.cold_packet(state)
                self.assertIn(
                    str(REFERENCES / "project-knowledge.md#investigate-git-history-for-planning"),
                    cold_packet,
                )
            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _action_id = self.complete_stage(state, **extra)

    def test_cold_packets_route_the_repeatable_test_suite_guide_to_each_testing_stage(self) -> None:
        """Persisted current states retain the direct guide route at testing checkpoints."""
        state = self.state()
        observed: list[str] = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            if stage in TEST_HARNESS_STAGES:
                navigator.save(self.run, state)
                before = (self.run / "state.md").read_bytes()
                recovered = store.read_record(self.run / "state.md")
                packet = render_with_guides(None, self.run, recovered)

                self.assertEqual((self.run / "state.md").read_bytes(), before)
                self.assertEqual(navigator.current_stage(recovered), stage)
                self.assertEqual(packet.count(REPEATABLE_TEST_SUITE_ROUTE), 1, packet)
                observed.append(stage)

            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _action_id = self.complete_stage(state, **extra)

        self.assertEqual(tuple(observed), TEST_HARNESS_STAGES)

    def test_cold_release_operation_route_recovers_outer_parents_and_partial_blocker(self) -> None:
        """Synthetic records exercise recovery only; no Improve or release is run."""
        self.assertTrue(RELEASE_OPERATION_PATH.is_file(), RELEASE_OPERATION_PATH)
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(
                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                RELEASE_OPERATION_PATH.read_text(encoding="utf-8"),
            )
        }
        self.assertIn(RELEASE_OPERATION_ANCHOR, headings)

        state = self.state()
        observed: list[str] = []
        release_blocked_once = False
        partial_release_refs = [
            "synthetic://release/candidate-identity",
            "synthetic://release/target-evidence-pending",
        ]

        while True:
            stage = navigator.current_stage(state)
            if stage not in RELEASE_OPERATION_STAGES:
                extra: dict[str, object] = {}
                if stage == "plan":
                    extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
                state, _action_id = self.complete_stage(state, **extra)
                state = self.save_reload(state)
                continue

            action = dict(navigator.current_action(state))
            recovered, producer_packet = self.cold_packet(state)
            self.assertEqual(navigator.current_stage(recovered), stage)
            self.assertEqual(navigator.current_action(recovered)["id"], action["id"])
            self.assertEqual(producer_packet.count(RELEASE_OPERATION_ROUTE), 1, producer_packet)

            if stage == "release" and not release_blocked_once:
                # release never starts an Improve child: the producer's partial
                # result is accepted directly and blocks the run.
                release_blocked_once = True
                blocked, _action = self.produce(
                    recovered,
                    outcome="blocked", awaiting=RELEASE_HOST_WAIT,
                    summary="Synthetic release evidence is partial.",
                    evidence_refs=partial_release_refs,
                )
                self.assertIsNone(blocked["active_improve"])
                blocked, blocked_packet = self.cold_packet(blocked)
                self.assertEqual(blocked["status"], "blocked")
                self.assertEqual(navigator.current_stage(blocked), stage)
                self.assertEqual(
                    blocked["accepted"][action["id"]]["evidence_refs"], partial_release_refs
                )
                self.assertNotIn(action["id"], blocked["improve_results"])
                self.assertEqual(blocked_packet.count(RELEASE_OPERATION_ROUTE), 1, blocked_packet)

                resumed = navigator.control(blocked, "resume", observed="The release host answers its status check.")
                state, resumed_packet = self.cold_packet(resumed)
                self.assertEqual(state["status"], "active")
                self.assertEqual(navigator.current_stage(state), stage)
                self.assertEqual(
                    state["accepted"][action["id"]]["evidence_refs"], partial_release_refs
                )
                self.assertEqual(resumed_packet.count(RELEASE_OPERATION_ROUTE), 1, resumed_packet)
                continue

            seed_refs = ["synthetic://release-operation/" + stage + "/candidate"]
            waiting, _action = self.produce(recovered, evidence_refs=seed_refs)
            if stage == "release-plan":
                # The only planning stage here: its child carries the route too.
                binding_id = waiting["active_improve"]["binding_id"]
                pending, improve_packet = self.cold_packet(waiting)
                child = pending["active_improve"]
                self.assertEqual(navigator.current_action(pending)["id"], action["id"])
                self.assertEqual(child["action_id"], action["id"])
                self.assertEqual(child["stage"], stage)
                self.assertEqual(child["binding_id"], binding_id)
                self.assertEqual(child["binding_id"], pending["run_id"] + "/" + action["id"])
                self.assertEqual(child["seed_result"]["evidence_refs"], seed_refs)
                self.assertEqual(improve_packet.count(RELEASE_OPERATION_ROUTE), 1, improve_packet)
                state = navigator.finish_improve(pending, action["id"], receipt(stage))
            else:
                self.assertIsNone(waiting["active_improve"])
                state = waiting
            state = self.save_reload(state)
            observed.append(stage)
            if stage == "release-verify":
                break

        self.assertEqual(tuple(observed), RELEASE_OPERATION_STAGES)

    def test_consumer_testing_guide_survives_cold_producer_and_improve_handoffs(self) -> None:
        """The browser evidence policy remains reachable; no live browser is tested."""
        route = (
            "Consumer testing guide: "
            + str(REFERENCES / "testing-and-documentation.md#lightweight-and-browser-checks")
        )
        state = self.state()
        observed: list[str] = []
        improved: list[str] = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            with self.subTest(stage=stage, boundary="producer"):
                self.assert_policy_route(packet, route, recovered)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic browser case"}]
            waiting, action = self.produce(recovered, **extra)
            observed.append(stage)
            if waiting["active_improve"] is None:
                state = waiting
                continue
            pending, packet = self.cold_packet(waiting)
            with self.subTest(stage=stage, boundary="Improve"):
                self.assert_policy_route(packet, route, pending)
                self.assertIn("Current action: Improve the completed " + stage, packet)
            state = navigator.finish_improve(pending, action["id"], receipt(stage))
            improved.append(stage)
        self.assertEqual(tuple(observed), prompts.STAGES)
        self.assertEqual(
            tuple(improved),
            tuple(stage for stage in prompts.STAGES
                  if stage in prompts.PLANNING_REVIEW_STAGES or stage in {"implement", "carry-forward"}),
        )

    def test_the_procedure_condition_reaches_where_procedures_originate_and_every_planning_review(self) -> None:
        """W2-C (implement-step fix plan 4.2, T34): one procedure-validity text, in the shared review focus, reaches the
        spec and test-strategy producers (their "Before you submit" item), every planning review's handoff, and the
        test-spec producer, whose own item applies it to its cases and says where a procedure's locator rides.  This
        pins the text a cleared model is given; whether a model reviewer acts on it is a live qualification."""
        walk = normalized(prompts.PROCEDURE_WALK)
        own = ("A plan is not a run; a setup change makes an earlier observation stale.",
               "its locator in `oracle` or the open item's `check`", "An unreachable start is an open prerequisite")
        state = self.state()
        producers: list[str] = []
        reviews: list[str] = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            text = normalized(packet)
            if stage in prompts.REVIEW_FOCUS_DUTY_STAGES:
                with self.subTest(stage=stage, boundary="producer"):
                    duty = text[text.index("Before you submit, fix any of these in"):]
                    self.assertIn("an ordered procedure (calls, commands, interactions) that cannot happen as written. "
                                  + walk, duty)
                    producers.append(stage)
            if stage == "test-spec":
                with self.subTest(stage=stage, boundary="producer"):
                    self.assertIn("A case's setup and actions are an ordered procedure. " + walk, text)
                    for phrase in own:
                        self.assertIn(phrase, text)
                    # ... and its loop does not exit on a case whose procedure cannot happen (an exit condition)
                    self.assertIn("each case's procedure can happen as written from its stated start, or its "
                                  "unreachable start is an open item", text)
                    producers.append(stage)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic procedure case"}]
            waiting, action = self.produce(recovered, **extra)
            if waiting["active_improve"] is None:
                state = waiting
                continue
            pending, packet = self.cold_packet(waiting)
            with self.subTest(stage=stage, boundary="Improve"):
                if stage in prompts.PLANNING_REVIEW_STAGES:
                    self.assertEqual(normalized(packet).count(walk), 1)
                    reviews.append(stage)
                else:
                    self.assertNotIn(walk, normalized(packet))
            state = navigator.finish_improve(pending, action["id"], receipt(stage))
        self.assertEqual(sorted(producers), ["spec", "test-spec", "test-strategy"])
        self.assertEqual(sorted(reviews), sorted(prompts.PLANNING_REVIEW_STAGES))

    def test_a_procedure_locator_reaches_every_stage_that_consumes_its_case_or_open_item(self) -> None:
        """W2-C (implement-step fix plan T26, T29): a procedure is carried by its locator, not copied.  The case's
        `oracle` and an open item's `check` name it; every stage that quotes the case (implement and its Improve, test,
        verify, system-test-author) or the open item (its consumer) is given that locator cold, and the later-owned
        procedure stays an open item, its observer unresolved, until its consumer stage.  The observing outer stages
        say a changed setup voids an earlier observation (their own duty text: the consumer's half of the rule).  This
        is the data a cleared model is given, not proof that it runs the procedure."""
        sys.path.insert(0, str(ROOT / "test"))
        import shiploop_assumptions as assumptions
        import shiploop_head_plans as plans
        case_locator = "HOME/architecture.md ## Real-boundary checks RB-1"
        open_locator = "HOME/architecture.md ## Real-boundary checks RB-2"
        cases = [dict(plans.TEST_CASES[0], oracle="Procedure " + case_locator + ", through the public call"),
                 plans.TEST_CASES[1]]
        later = {"id": "A1", "disposition": "open", "consumer": "release-verify", "owner": "a person with access",
                 "assumption": "TC-1's criterion C1 (R-1) on the released consumer surface is unobserved",
                 "check": "Run " + open_locator + " on the released candidate; report what it shows",
                 "reason": "no route to that surface from this host"}
        extras = {"plan": {"work_items": [plans.CASE["work_item"]]}, "step-plan": plans.PLAN,
                  "test-spec": {"test_cases": cases, "assumptions": [later]}}
        quotes_case = ("implement", "test", "verify", "system-test-author")
        voids = {"system-test": "rerun the affected observations",
                 "release-check": "invalidates the observations it affects",
                 "release-verify": "invalidates the observations it affects"}
        for route in (prompts.INLINE, prompts.ASK_AGENT):
            state = navigator.new_state(str(self.repo), "Change how a stored value is updated.", improve_skill="",
                                        delegation=route)
            seen: list[str] = []
            while state["status"] != "done":
                stage = navigator.current_stage(state)
                recovered, packet = self.cold_packet(state)
                with self.subTest(route=route, stage=stage):
                    open_ids = [found.row["id"] for found in assumptions.open_items(recovered)]
                    if stage in quotes_case:
                        self.assertIn(case_locator, packet)
                        self.assertIn("A1", open_ids)
                        seen.append(stage)
                    if stage in voids:
                        self.assertIn(voids[stage], normalized(packet))
                        seen.append(stage)
                    if stage == "release-verify":
                        self.assertIn(open_locator, packet)
                        self.assertIn("A1", open_ids)
                producer = navigator.current_action(recovered)["id"]
                waiting, action = self.produce(recovered, **extras.get(stage, {}))
                if waiting["active_improve"] is None:
                    state = waiting
                    continue
                pending, packet = self.cold_packet(waiting)
                if stage == "implement":
                    with self.subTest(route=route, stage="implement Improve"):
                        # The step's review reads the case where the producer's packet quotes it (by file since U2).
                        self.assertIn("its packet RUN/packets/" + producer + ".md", packet)
                        quoted = next(line for line in packet.splitlines()
                                      if line.startswith("- Hand-offs, quoted there by value: "))
                        self.assertIn("test_cases", quoted)
                        seen.append("implement-improve")
                state = navigator.finish_improve(pending, action["id"], receipt(stage))
            with self.subTest(route=route, check="every consumer reached"):
                self.assertEqual(set(seen), set(quotes_case) | set(voids) | {"implement-improve"})

    def test_cold_local_skill_routes_cover_early_and_late_decisions(self) -> None:
        """Fresh producer and pending-child packets retain the local skill route.

        Navigation and child state here are synthetic protocol setup only.  The
        assertions prove packet routing and cold recovery, not that a host
        interpreted an index or authored a child contract.
        """
        index = self.repo / "SHIPLOOP.md"
        index.write_text("# Fixture local skill index\n", encoding="utf-8")
        index_route = "Repository knowledge index (host-authored, if present): WORKTREE/" + index.name
        observed: list[str] = []
        improved: list[str] = []

        for target in LOCAL_SKILL_INDEX_STAGES:
            with self.subTest(stage=target):
                state = self.state()
                while navigator.current_stage(state) != target:
                    stage = navigator.current_stage(state)
                    extra: dict[str, object] = {}
                    if stage == "plan":
                        extra["work_items"] = [{"id": "W1", "title": "Fixture item"}]
                    state, _action_id = self.complete_stage(state, **extra)

                producer, producer_packet = self.cold_packet(state)
                self.assertEqual(navigator.current_stage(producer), target)
                self.assertTrue(index.is_file())
                guide_count = int(target in LOCAL_SKILL_ROUTE_STAGES)
                self.assertEqual(producer_packet.count(LOCAL_SKILL_GUIDE_ROUTE), guide_count, producer_packet)
                self.assertEqual(producer_packet.count(index_route), 1, producer_packet)

                pending, _action = self.produce(producer)
                observed.append(target)
                # The single item's carry-forward is the last item's, which parks its Improve child.
                if target not in prompts.PLANNING_REVIEW_STAGES and target != "carry-forward":
                    self.assertIsNone(pending["active_improve"])
                    continue
                recovered_pending, pending_packet = self.cold_packet(pending)
                self.assertIsNotNone(recovered_pending["active_improve"])
                self.assertEqual(navigator.current_stage(recovered_pending), target)
                self.assertEqual(pending_packet.count(LOCAL_SKILL_GUIDE_ROUTE), guide_count, pending_packet)
                self.assertEqual(pending_packet.count(index_route), 1, pending_packet)
                improved.append(target)

        self.assertEqual(tuple(observed), LOCAL_SKILL_INDEX_STAGES)
        self.assertEqual(improved, ["step-plan", "carry-forward"])

    def test_the_step_plan_packet_asks_each_step_for_its_skills(self) -> None:
        """skill_na and the two skill stages are gone (8-stage loop, 2026-10-10): each step names its skills."""
        state = self.state()
        while navigator.current_stage(state) != "step-plan":
            extra: dict[str, object] = {}
            if navigator.current_stage(state) == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Fixture item"}]
            state, _action_id = self.complete_stage(state, **extra)
        _recovered, packet = self.cold_packet(state)
        flat = normalized(packet)
        self.assertNotIn("skill_na", flat)
        for clause in ("`skills`: reread the host's skills and the repository's skill index",
                       "for each with a concrete use in the step"):
            self.assertIn(clause, flat)
        # Packet re-cut: the implement duty (item 2) is where the listed skills are used; there is no "prints these" line.
        self.assertIn("Use each listed step skill for its purpose", normalized(prompts.prompt("implement")))

    def test_coding_guide_is_selective_in_cold_producer_and_improve_packets(self) -> None:
        """Route locators, not every card body; retain the same owner on recovery."""
        state = self.state()
        observed = []
        improved = []
        while state["status"] != "done":
            stage = navigator.current_stage(state)
            recovered, packet = self.cold_packet(state)
            expected_count = int(stage in CODING_GUIDE_STAGES)
            self.assertEqual(packet.count(CODING_GUIDE_ROUTE), expected_count)
            self.assertNotIn("google.script.run", packet)
            self.assertNotIn("set -euo pipefail", packet)
            if stage in CODING_GUIDE_STAGES:
                observed.append(stage)
            if stage in CODING_GUIDE_STAGES and stage in prompts.PLANNING_REVIEW_STAGES:
                waiting, action = self.pending_improve(recovered)
                pending, child_packet = self.cold_packet(waiting)
                self.assertEqual(child_packet.count(CODING_GUIDE_ROUTE), 1)
                self.assertIn("Current action: Improve the completed " + stage, child_packet)
                self.assertIn(action["id"], child_packet)
                self.assertEqual(navigator.current_stage(pending), stage)
                self.assertEqual(pending["active_improve"], waiting["active_improve"])
                # Bind only synthetic identity to test the separate bound-child
                # render path; no skill or model is executed by this fixture.
                child = pending["active_improve"]
                child.update({
                    "version": 1,
                    "contract_marker": "ShipLoop standalone Improve binding: " + child["binding_id"],
                    "skill": {
                        "skill_card": str(self.repo / "improve/SKILL.md"),
                        "runtime_card": str(self.repo / "until-loop/ADAPTER.md"),
                        "runtime_cli": str(self.repo / "until-loop/scripts/until_loop_ephemeral.py"),
                        "skill_version": "synthetic",
                        "runtime_version": "synthetic",
                    },
                })
                navigator.validate(pending)
                bound, bound_packet = self.cold_packet(pending)
                self.assertEqual(bound["active_improve"], pending["active_improve"])
                self.assertEqual(bound_packet.count(CODING_GUIDE_ROUTE), 1)
                self.assertIn("selected practice/platform locators", normalized(bound_packet))
                improved.append(stage)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            state, _ = self.complete_stage(state, **extra)
        self.assertEqual(tuple(observed), CODING_GUIDE_STAGES)
        self.assertEqual(improved, ["step-plan"])

    def test_coding_reference_links_survive_package_relocation(self) -> None:
        """A packaged selector and its cards must work outside this checkout."""
        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        new_files = ["coding-guidance.md", "coding-practices.md"] + [
            "platforms/" + name + ".md"
            for name in ("ui", "apps-script", "salesforce", "python", "bash")
        ]
        selector = (relocated / "coding-guidance.md").read_text(encoding="utf-8")
        for card in new_files[1:]:
            self.assertIn(card, selector)
        for filename in new_files:
            page = relocated / filename
            body = page.read_text(encoding="utf-8")
            self.assertNotIn("/Users/", body)
            self.assertNotIn("shiploop-coding-guidance-experiment-plan", body)
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", body):
                if link.startswith(("https://", "http://")):
                    continue
                with self.subTest(page=filename, link=link):
                    path, _, anchor = link.partition("#")
                    destination = (page.parent / path).resolve() if path else page
                    self.assertTrue(destination.is_relative_to(relocated), link)
                    self.assertTrue(destination.is_file(), link)
                    if anchor:
                        headings = {
                            heading_anchor(match.group(2)) for match in re.finditer(
                                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                                destination.read_text(encoding="utf-8"),
                            )
                        }
                        self.assertIn(anchor, headings)

    def test_the_salesforce_card_names_the_reporter_shiploop_reads_and_the_red_na_route(self) -> None:
        """An org-run Apex test: the reporter the reader can use, and why a new test cannot fail on the base (the unread route)."""
        card = " ".join((REFERENCES / "platforms" / "salesforce.md").read_text(encoding="utf-8").split())
        for phrase in ("with a reporter it can read", "--result-format tap", "an `ok` or `not ok` line per test",
                       "put the outcome word after the test name", "refused as unread",
                       "cannot fail unless the command deploys the tree first", "`red_na`"):
            self.assertIn(phrase, card)

    def test_consumer_access_is_probed_read_only_at_prepare_and_again_at_release_check(self) -> None:
        """Packet review 2026-10-17 (F-7, X-1) and the implement-step plan's access row: the consumer's entry route and
        access prerequisites are established at prepare, not found at release-verify; release-check reruns the same
        read-only probe; a gap stays open with its owner and nothing is granted.  The platform card holds the probe."""
        prepare = " ".join(prompts.DUTIES["prepare"].split())
        for phrase in ("The consumer's access", "the entry route the plan gives them", "Check it read-only",
                       "the probe the target's platform guide names", "## Access and accounts",
                       "stays open there with its owner", "Create no grant"):
            self.assertIn(phrase, prepare)
        check = " ".join(prompts.DUTIES["release-check"].split())
        for phrase in ("Rerun prepare's read-only probe", "beside the dry run's", "create no grant"):
            self.assertIn(phrase, check)
        card = " ".join((REFERENCES / "platforms" / "salesforce.md").read_text(encoding="utf-8").split())
        for phrase in ("## Consumer entry access (read-only probe)", "At prepare, name the consumer user",
                       "FROM PermissionSetAssignment WHERE AssigneeId", "At release-check, rerun both",
                       "FROM PermissionSetTabSetting WHERE Name = '<TabApiName>'", "grant nothing"):
            self.assertIn(phrase, card)

    def test_accepted_coding_plan_can_survive_later_test_decisions_without_new_fields(self) -> None:
        """Exercise host-authored evidence handoff, not automatic model compliance."""
        state = self.state()
        plan_ref = "docs/item-plan.md#accepted-decisions"
        card_ref = str(REFERENCES / "platforms/python.md")
        plan_action = ""
        latest_decision = ""
        while navigator.current_stage(state) != "implement":
            stage = navigator.current_stage(state)
            extra = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic Python change"}]
            if stage == "step-plan":
                extra["evidence_refs"] = ["draft://not-accepted"]
                state, plan_action = self.complete_stage_with_final(
                    state, result(stage, evidence_refs=[plan_ref, card_ref]), **extra
                )
            else:
                if stage in {"test-spec", "test-author"}:
                    # A host follows the handoff instruction using ordinary fields.
                    extra["summary"] = "Retain accepted decisions; refine only test cases."
                    extra["evidence_refs"] = [plan_ref, card_ref, "tests/cases.py"]
                state, action_id = self.complete_stage(state, **extra)
                if stage in {"test-spec", "test-author"}:
                    latest_decision = action_id
            state = self.save_reload(state)
        _, packet = self.cold_packet(state)
        # 2026-10-11 dedupe: the decision and the step plan are listed once, under "Results this
        # stage builds on"; their evidence references are read from those result records.
        self.assertIn("RUN/results/" + latest_decision + ".md", packet)
        self.assertIn("RUN/results/" + plan_action + ".md", packet)
        self.assertNotIn("test-decision source action", packet)
        self.assertNotIn("draft://not-accepted", packet)
        self.assertEqual(state["accepted"][plan_action]["evidence_refs"], [plan_ref, card_ref])

    def test_next_item_reopens_repo_index_without_inheriting_prior_skill_selection(self) -> None:
        """The generic item context keeps selections scoped to their owner.

        This is synthetic navigation and packet recovery.  It deliberately does
        not parse the index or a product skill: the host still decides whether a
        current task fits either one.
        """
        index = self.repo / "SHIPLOOP.md"
        selected_card = self.repo / "skills/release-evidence-triage/SKILL.md"
        index_ref = str(index) + "#local-skills"
        w1_selection = (
            "W1 selected local skill: " + str(selected_card)
            + "; effective input contract: docs/release-contract.md#v1; "
            + "revalidate when the contract moves."
        )
        w2_context = (
            "W2 start by reopening the current repository index " + index_ref
            + "; no prior skill selection applies until task fit is reassessed."
        )
        index.write_text(
            "# Fixture repository index\n\n## Local skills\n\n"
            "- [Release evidence](skills/release-evidence-triage/SKILL.md)\n",
            encoding="utf-8",
        )
        selected_card.parent.mkdir(parents=True)
        selected_card.write_text("# Fixture local skill\n", encoding="utf-8")
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _action_id = self.complete_stage(state)
        state, plan_action = self.complete_stage(
            state,
            evidence_refs=[index_ref],
            work_items=[
                {"id": "W1", "title": "Assess release evidence", "context": w1_selection},
                {"id": "W2", "title": "Reassess another boundary", "context": w2_context},
            ],
        )
        state = self.save_reload(state)
        self.assertEqual(state["accepted"][plan_action]["evidence_refs"], [index_ref])

        while navigator.current_stage(state) != "step-plan":
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        first_item, first_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(first_item), "W1")
        self.assertIn("Work item context: " + w1_selection, first_packet)
        self.assertIn("Repository knowledge index (host-authored, if present): WORKTREE/" + index.name, first_packet)

        while not (
            navigator.current_stage(state) == "step-plan"
            and navigator._current_work_item(state) == "W2"
        ):
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        second_item, second_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(second_item), "W2")
        self.assertIn("Work item context: " + w2_context, second_packet)
        self.assertIn("Repository knowledge index (host-authored, if present): WORKTREE/" + index.name, second_packet)
        self.assertNotIn(str(selected_card), second_packet)
        self.assertNotIn(w1_selection, second_packet)

    def test_ui_ownership_and_failed_readiness_survive_to_a_blocked_step_plan(self) -> None:
        """Synthetic host judgments test routing and blocking, not model quality."""
        locator = str(REFERENCES / "behavioral-requirements.md#allocate-ui-decisions-to-their-planning-owner")
        docs = self.repo / "docs"
        docs.mkdir()
        design = docs / "ui.md"
        design.write_text("# UI premises\n\nPreserve components, draft interaction and navy tokens.\n")
        readiness = docs / "readiness.md"
        readiness.write_text("# Current target\n\nStorage unavailable. Host owner must resolve it before draft work.\n")
        sources = [str(design) + "#ui-premises", str(readiness) + "#current-target"]
        context = "Draft item depends on host-owned storage readiness; " + "; ".join(sources)
        state = self.state()
        observed = []
        while navigator.current_stage(state) != "step-plan":
            stage = navigator.current_stage(state)
            # Packet re-cut: only plan (and step-plan below) cite the UI planning ownership guide.
            if stage in {"plan"}:
                state, packet = self.cold_packet(state)
                self.assertIn(locator, packet)
                observed.append(stage)
            extra = {}
            if stage == "plan":
                extra = {"evidence_refs": sources,
                         "work_items": [{"id": "W1", "title": "Recover drafts", "context": context}]}
            state, _ = self.complete_stage(state, **extra)
        state, packet = self.cold_packet(state)
        self.assertEqual(observed, ["plan"])
        self.assertIn(locator, packet)
        self.assertIn(context, packet)
        action = dict(navigator.current_action(state))
        blocked = {"outcome": "blocked", "awaiting": PLAN_HOST_WAIT,
                   "summary": "Host storage prerequisite is unavailable; supplier decision pending.",
                   "evidence_refs": sources}
        # Improve starts only on a done result (run-insights N5): a blocked step-plan is accepted as it stands, so the
        # failed readiness is in the blocked run's packet itself, with the UI sources the result cited.
        stopped = navigator.apply(state, action["id"], blocked)
        self.assertIsNone(stopped["active_improve"])
        self.assertEqual(stopped["accepted"][action["id"]]["evidence_refs"], sources)
        stopped, stopped_packet = self.cold_packet(stopped)
        self.assertEqual(stopped["status"], "blocked")
        self.assertEqual(navigator.current_stage(stopped), "step-plan")
        self.assertNotIn("W1", stopped["completed_work_items"])
        self.assertIn("Host storage prerequisite", stopped_packet)
        self.assertIn("Blocked, waiting on an outside service:", stopped_packet)

    def test_ui_supersession_handoff_keeps_replacement_current_after_cold_recovery(self) -> None:
        """A reviewed plan can replace a UI premise without erasing its seed evidence."""
        original_locator = "docs/ui-plan.md#original-premise"
        replacement_locator = "docs/ui-review.md#accepted-replacement"
        original_context = (
            "Original UI premise: use the original storage order from " + original_locator
        )
        replacement_context = (
            "Reviewed replacement: " + replacement_locator
            + "; precedence: this reviewed replacement supersedes the original storage order."
        )
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _ = self.complete_stage(state)

        action = dict(navigator.current_action(state))
        waiting = navigator.apply(
            state,
            action["id"],
            result(
                "plan",
                evidence_refs=[original_locator],
                work_items=[{"id": "W1", "title": "Recover drafts", "context": original_context}],
            ),
        )
        waiting, _review_packet = self.cold_packet(waiting)
        final_plan = result(
            "plan",
            summary="Improve accepted a reviewed UI replacement with explicit precedence.",
            evidence_refs=[replacement_locator],
            work_items=[{"id": "W1", "title": "Recover drafts", "context": replacement_context}],
        )
        state = navigator.finish_improve(waiting, action["id"], receipt("plan"), final_plan)
        self.assertEqual(
            state["improve_results"][action["id"]]["seed_result"]["evidence_refs"],
            [original_locator],
        )
        self.assertEqual(state["accepted"][action["id"]]["evidence_refs"], [replacement_locator])
        self.assertEqual(
            state["improve_results"][action["id"]]["seed_result"]["work_items"][0]["context"],
            original_context,
        )

        state, replacement_packet = self.cold_packet(state)
        self.assertIn(replacement_locator, replacement_packet)
        self.assertIn("reviewed UI replacement with explicit precedence", replacement_packet)
        self.assertNotIn(original_locator, replacement_packet)
        self.assertEqual(navigator.current_stage(state), "prepare")
        state, _ = self.complete_stage(state)
        state, cold_packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "step-plan")
        self.assertIn("Work item context: " + replacement_context, cold_packet)
        self.assertIn(replacement_locator, cold_packet)
        self.assertNotIn(original_context, cold_packet)
        self.assertIn(
            "Carry reviewed replacement locators and their precedence through the existing handoff when these decisions change.",
            normalized(prompts.improve_prompt("step-plan")),
        )

    def test_cold_step_plan_keeps_compact_context_and_evidence_locators(self) -> None:
        context = (
            "Convention source: docs/client.md#requests; decision: reuse the existing "
            "client; rationale: it owns retries; revalidate if the client version changes."
        )
        plan_evidence = "docs/client.md#requests"
        state = self.state()
        plan_action = ""
        while navigator.current_stage(state) != "step-plan":
            stage = navigator.current_stage(state)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra = {
                    "evidence_refs": [plan_evidence],
                    "work_items": [{"id": "W1", "title": "Use existing client", "context": context}],
                }
            state, action_id = self.complete_stage(state, **extra)
            if stage == "plan":
                plan_action = action_id

        navigator.save(self.run, state)
        before = (self.run / "state.md").read_bytes()
        recovered = store.read_record(self.run / "state.md")
        packet = render_with_guides(None, self.run, recovered)

        self.assertEqual((self.run / "state.md").read_bytes(), before)
        self.assertEqual(recovered["work_items"][0]["context"], context)
        self.assertEqual(recovered["accepted"][plan_action]["evidence_refs"], [plan_evidence])
        self.assertIn("Work item context: " + context, packet)
        # Packet re-cut: step-plan duty 1 reopens the item's `context` (no FEATURE/plan.md since consumer contract 4b).
        self.assertIn("Reopen its `context` and recheck each condition.", normalized(packet))
        for label, locator in prompts.STAGE_REFERENCES["step-plan"]:
            self.assertIn(label + ": " + str(REFERENCES / locator), packet)

        improve_packet = normalized(prompts.improve_prompt("step-plan"))
        self.assertIn("relevant work-item `context`, parent `evidence_refs`", improve_packet)
        self.assertIn("packet-selected reference locators", improve_packet)
        self.assertIn("compact current locator, decision, rationale", improve_packet)

    def test_cold_packets_keep_the_latest_done_root_test_strategy(self) -> None:
        """Strategy locators survive later evidence without reading it into packets."""
        item_context = (
            "Current item: retain the accepted fixture setup decision; revalidate it "
            "against the changed boundary before reusing it."
        )
        strategy_ref = "docs/testing.md#accepted-strategy"
        hidden_tail = "UNTRUSTED-STRATEGY-TAIL-MUST-NOT-BE-RENDERED"
        long_ref = "untrusted://strategy/" + ("x" * 2600) + hidden_tail
        checkpoints = {"step-plan", "test-spec", "test", "system-test-author"}
        state = self.state()
        strategy_action = ""
        decision_action: str | None = None
        decision_ref = ""
        rejected_actions: list[str] = []
        observed: set[str] = set()

        def assert_test_sources(packet: str, *, inner: bool) -> None:
            # 2026-10-11 dedupe: a source listed under "Results this stage builds on" is not printed
            # again, so the strategy and the decision are located by that one list; their evidence
            # references are read from the result records.
            self.assertIn("test-strategy stage result: RUN/results/" + strategy_action + ".md", packet)
            self.assertNotIn("Run-wide test strategy source action:", packet)
            self.assertNotIn("Run-wide test strategy source (untrusted", packet)
            strategy_record = (self.run / "results" / (strategy_action + ".md")).read_text(encoding="utf-8")
            self.assertIn(strategy_ref, strategy_record)
            self.assertNotIn(hidden_tail, packet)
            self.assertNotIn("Consume relevant current work-item context with these sources.", packet)
            if decision_action is None:
                self.assertNotIn("test-decision source action:", packet)
            elif not inner:
                # U17 (row VR-4): system-test-author lists each completed item's records in force by locator.
                self.assertNotIn("test-decision source action:", packet)
                self.assertIn(" result: RUN/results/" + decision_action + ".md", packet)
            else:
                self.assertNotIn("Current item test-decision source action:", packet)
                self.assertNotIn("Current item test-decision source (untrusted", packet)
                self.assertIn("RUN/results/" + decision_action + ".md", packet)
                self.assertIn(decision_ref, (self.run / "results" / (decision_action + ".md")).read_text(encoding="utf-8"))
            if inner:
                self.assertIn("Work item context: " + item_context, packet)
            else:
                self.assertNotIn("Work item context:", packet)
                self.assertNotIn(item_context, packet)

        while True:
            stage = navigator.current_stage(state)
            if stage == "test-strategy":
                # A blocked strategy is accepted history and stops the run; it is never the strategy a packet cites.
                # (repeat, the other non-done outcome this loop once rejected, is retired.)
                state, action_id = self.complete_stage(
                    state,
                    outcome="blocked",
                    evidence_refs=["unrelated://test-strategy-blocked"],
                    awaiting=STRATEGY_HOST_WAIT,
                )
                rejected_actions.append(action_id)
                state = self.save_reload(state)
                self.assertEqual(state["status"], "blocked")
                state = navigator.control(state, "resume", observed="The test-runner host answers its status check.")
                state = self.save_reload(state)
                state, strategy_action = self.complete_stage(
                    state,
                    evidence_refs=[strategy_ref, long_ref],
                )
                state = self.save_reload(state)
                self.assertTrue((self.run / "results" / (strategy_action + ".md")).is_file())
                continue

            if stage in checkpoints:
                state = self.save_reload(state)
                before = (self.run / "state.md").read_bytes()
                recovered = store.read_record(self.run / "state.md")
                if stage == "test-spec":
                    waiting, action = self.pending_improve(
                        recovered, evidence_refs=["unrelated://pending-improve"],
                    )
                    navigator.save(self.run, waiting)
                    pending_before = (self.run / "state.md").read_bytes()
                    pending = store.read_record(self.run / "state.md")
                    packet = self.packet_with_handoff(pending, guarded=True)
                    self.assertEqual((self.run / "state.md").read_bytes(), pending_before)
                    self.assertIn("Current action: Improve the completed test-spec result.", packet)
                    assert_test_sources(packet, inner=True)
                    observed.add(stage)
                    observed.add("pending Improve")
                    state = navigator.finish_improve(pending, action["id"], receipt(stage))
                    state = self.save_reload(state)
                    decision_action = action["id"]
                    decision_ref = "unrelated://pending-improve"
                    continue

                with patch.object(Path, "read_text", new=_knowledge_reads_only()):
                    packet = render_with_guides(None, self.run, recovered)
                self.assertEqual((self.run / "state.md").read_bytes(), before)
                assert_test_sources(packet, inner=stage != "system-test-author")
                observed.add(stage)
                if stage == "system-test-author":
                    break

            extra: dict[str, object] = {"evidence_refs": ["unrelated://" + stage]}
            if stage == "plan":
                extra["work_items"] = [
                    {"id": "W1", "title": "Synthetic item", "context": item_context}
                ]
            state, action_id = self.complete_stage(state, **extra)
            state = self.save_reload(state)
            if stage in prompts.TEST_DECISION_STAGES:
                decision_action = action_id
                decision_ref = "unrelated://" + stage

        self.assertEqual(observed, checkpoints | {"pending Improve"})
        for action_id in rejected_actions:
            self.assertNotIn("accepted." + action_id, packet)
            self.assertNotIn(str(self.run / "results" / (action_id + ".md")), packet)

    def test_current_item_test_decision_source_is_revised_and_item_scoped(self) -> None:
        """Only the current item's latest accepted decision is retained in a packet."""
        contexts = {
            "W1": "W1 context: retain its isolated fixture decision.",
            "W2": "W2 context: use its separate compatibility fixture.",
        }
        strategy_ref = "docs/testing.md#run-wide-strategy"
        changed_step_plan_ref = "docs/testing.md#revised-step-plan"
        draft_step_plan_ref = "untrusted://draft-step-plan"
        author_ref = "docs/testing.md#authored-case"
        test_spec_blocked_ref = "untrusted://test-spec-blocked"
        w2_ref = "docs/testing.md#w2-decision"
        state = self.state()
        strategy_action = ""

        def assert_sources(packet: str, action_id: str, reference: str, *,
                           printed: bool = False, strategy_printed: bool = False) -> None:
            # 2026-10-11 dedupe: a source the packet lists under "Results this stage builds on" is
            # not printed again, so the strategy is always located by that list, and the decision
            # either by that list (its evidence references are read from the result record) or, when
            # the stage does not read it, by one printed block carrying the references.
            if strategy_printed:
                self.assertIn("Run-wide test strategy source (untrusted host report; revalidate relevance before use): "
                              + "RUN/results/" + strategy_action + ".md" + " (action "
                              + strategy_action + "; state.md accepted." + strategy_action + ")", packet)
                self.assertIn(strategy_ref, packet)
            else:
                self.assertIn("test-strategy stage result: RUN/results/" + strategy_action + ".md", packet)
                self.assertNotIn("Run-wide test strategy source action:", packet)
            record = self.run / "results" / (action_id + ".md")
            self.assertIn(reference, record.read_text(encoding="utf-8"))
            if printed:
                # Packet re-cut: one line names the source, its result and its state entry (it was four).
                self.assertIn(
                    "Current item test-decision source (untrusted host report; revalidate relevance before use): "
                    + "RUN/results/" + action_id + ".md" + " (action " + action_id + "; state.md accepted." + action_id + ")",
                    packet,
                )
                self.assertIn(reference, packet)
            else:
                self.assertIn("RUN/results/" + action_id + ".md", packet)
                self.assertNotIn("Current item test-decision source action:", packet)

        while navigator.current_stage(state) != "plan":
            stage = navigator.current_stage(state)
            state, action_id = self.complete_stage(
                state,
                evidence_refs=[strategy_ref if stage == "test-strategy" else "unrelated://" + stage],
            )
            state = self.save_reload(state)
            if stage == "test-strategy":
                strategy_action = action_id
        state, _plan_action = self.complete_stage(
            state,
            work_items=[
                {"id": "W1", "title": "First item", "context": contexts["W1"]},
                {"id": "W2", "title": "Second item", "context": contexts["W2"]},
            ],
            evidence_refs=["unrelated://plan"],
        )
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "prepare")
        state, _prepare_action = self.complete_stage(state, evidence_refs=["unrelated://prepare"])
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "step-plan")

        final_step_plan = result(
            "step-plan",
            summary="Improve revised the W1 test decision.",
            evidence_refs=[changed_step_plan_ref],
        )
        state, step_plan_action = self.complete_stage_with_final(
            state,
            final_step_plan,
            evidence_refs=[draft_step_plan_ref],
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        assert_sources(packet, step_plan_action, changed_step_plan_ref)
        self.assertNotIn(draft_step_plan_ref, packet)
        self.assertIn("Work item context: " + contexts["W1"], packet)

        # A blocked test-spec result is not a test decision.  Improve starts only on a done result (run-insights N5), so
        # the blocked result is accepted as it stands: no Improve child holds it pending (repeat, the other non-done
        # inner outcome this once covered, is retired).
        blocked_action = dict(navigator.current_action(state))["id"]
        state, _blocked = self.produce(
            state, outcome="blocked", awaiting=SPEC_ANSWER_WAIT, evidence_refs=[test_spec_blocked_ref]
        )
        self.assertIsNone(state["active_improve"])
        self.assertEqual(state["status"], "blocked")
        self.assertIn(blocked_action, state["accepted"])
        self.assertNotIn(blocked_action, state["improve_results"])
        state, packet = self.cold_packet(state)
        self.assertIn("Blocked, waiting on the user:", packet)
        # The blocked packet prints its sources (it has no "Results this stage builds on" list): the step plan is still
        # the item's decision source, not the blocked test-spec result.
        assert_sources(packet, step_plan_action, changed_step_plan_ref, printed=True, strategy_printed=True)
        self.assertNotIn("Current item test-decision source action: " + blocked_action, packet)
        self.assertNotIn("RUN/results/" + blocked_action + ".md", packet)
        state = navigator.control(state, "resume", answer="Use the isolated fixture.")
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        assert_sources(packet, step_plan_action, changed_step_plan_ref)
        self.assertNotIn("Current item test-decision source action: " + blocked_action, packet)
        self.assertNotIn("RUN/results/" + blocked_action + ".md", packet)

        state, test_spec_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#test-spec"]
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "validate-existing")
        assert_sources(packet, test_spec_action, "docs/testing.md#test-spec", printed=True, strategy_printed=True)

        state, _validate_action = self.complete_stage(
            state, evidence_refs=["unrelated://validate-existing"]
        )
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "implement")
        assert_sources(packet, test_spec_action, "docs/testing.md#test-spec", strategy_printed=True)

        while navigator.current_stage(state) != "test":
            stage = navigator.current_stage(state)
            state, _action_id = self.complete_stage(
                state, evidence_refs=["unrelated://" + stage]
            )
            state = self.save_reload(state)
        state, packet = self.cold_packet(state)
        assert_sources(packet, test_spec_action, "docs/testing.md#test-spec")

        # test-author, test-refine and regression are one test stage now: its result is the decision source.
        state, test_action = self.complete_stage(state, evidence_refs=[author_ref])
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "document")
        assert_sources(packet, test_action, author_ref, strategy_printed=True)

        while not (
            navigator.current_stage(state) == "step-plan"
            and navigator._current_work_item(state) == "W2"
        ):
            stage = navigator.current_stage(state)
            state, _action_id = self.complete_stage(
                state, evidence_refs=["unrelated://" + stage]
            )
            state = self.save_reload(state)
        state, packet = self.cold_packet(state)
        self.assertIn("test-strategy stage result: RUN/results/" + strategy_action + ".md", packet)
        self.assertIn("Work item context: " + contexts["W2"], packet)
        self.assertNotIn(
            "Current item test-decision source "
            "(untrusted host report; revalidate relevance before use):",
            packet,
        )
        self.assertNotIn(changed_step_plan_ref, packet)
        self.assertNotIn(author_ref, packet)

        state, w2_action = self.complete_stage(state, evidence_refs=[w2_ref])
        state, packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        assert_sources(packet, w2_action, w2_ref)
        self.assertNotIn(changed_step_plan_ref, packet)
        self.assertNotIn(author_ref, packet)

    def test_reusable_test_facilities_route_and_recover_without_new_state(self) -> None:
        """Facility locators are ordinary cold-context records, never execution proof."""
        guide = (REFERENCES / "repeatable-test-suites.md").read_text(encoding="utf-8")
        guide_normalized = normalized(guide)
        for clause in (
            "reuse and define test facilities",
            "selected skill and MCP capability references",
            "reuse, configure or extend",
            "missing facility",
            "definition locator",
            "before dependent checks",
            "repository test documentation",
            "repository index",
        ):
            self.assertIn(clause.lower(), guide_normalized.lower())

        for stage in prompts.STAGES:
            routed = ("Reusable test facilities", "repeatable-test-suites.md#reuse-and-define-test-facilities") in prompts.STAGE_REFERENCES[stage]
            # Packet re-cut: carry-forward records facility locators but defines none, so it cites no guide label.
            self.assertEqual(routed, stage in TEST_FACILITY_STAGES and stage != "carry-forward", stage)
        self.assertIsInstance(prompts.TEST_FACILITY_HANDOFF, str)
        facility_handoff = normalized(prompts.TEST_FACILITY_HANDOFF)
        for clause in (
            "selected skill and MCP references",
            "reuse, configure or extend",
            "missing facility",
            "definition locator",
            "Readiness is not test execution",
            "within its scope, before the checks that depend on it",
        ):
            self.assertIn(clause, facility_handoff)
        # Packet re-cut (2026-10-11): TEST_FACILITY_HANDOFF is no longer printed; each stage's own duty carries the
        # point once, in its own words, and cites the guide.
        for stage in TEST_FACILITY_STAGES:
            text = normalized(prompts.prompt(stage))
            with self.subTest(stage=stage):
                self.assertNotIn("Test facilities (Reusable test facilities): reuse, configure or extend", text)
                if stage == "carry-forward":
                    self.assertIn("each test facility's locator, interface, readiness or gap, owner, revalidation condition", text)
                else:
                    self.assertIn("Reusable test facilities", text)
                    # reuse before defining a new one: "the smallest missing" facility, or plan's "before planning a
                    # new one"; test says "first ... build a missing facility within this item".
                    self.assertTrue(any(cue in text for cue in
                                        ("smallest missing", "before planning a new one", "missing facility",
                                         "name the smallest facility", "each new facility's locator",
                                         "the smallest facility")), text)
                self.assertIn(prompts.TEST_FACILITY_HANDOFF, prompts.improve_prompt(stage))
                # No producer packet tells its Improve child anything in advance.
                self.assertNotIn("Improve child's context/notes", text)
        # test-red and regression are folded into test (8-stage loop, 2026-10-10): it reuses facilities first.
        self.assertIn(
            "Reuse existing harness, helpers and fixtures first (Reusable test facilities)",
            normalized(prompts.prompt("test")),
        )

        skill_ref = "docs/testing.md#local-framework-skill-v2"
        mcp_ref = "docs/testing.md#required-mcp-operation-missing-helper"
        context = (
            "Facility: local framework skill via " + skill_ref
            + "; required MCP helper is planned, readiness unresolved; revalidate version."
        )
        state = self.state()
        strategy_action = ""
        plan_action = ""
        author_action = ""
        while navigator.current_stage(state) != "test":
            stage = navigator.current_stage(state)
            extra: dict[str, object] = {"evidence_refs": ["synthetic://" + stage]}
            if stage == "test-strategy":
                extra["evidence_refs"] = [skill_ref, mcp_ref]
            elif stage == "plan":
                extra.update({
                    "evidence_refs": [skill_ref, mcp_ref],
                    "work_items": [{"id": "W1", "title": "Facility item", "context": context}],
                })
            state, action = self.complete_stage(state, **extra)
            if stage == "test-strategy":
                strategy_action = action
            if stage == "plan":
                plan_action = action
        state, author_packet = self.cold_packet(state)
        self.assertIn(REUSABLE_TEST_FACILITY_ROUTE, author_packet)
        state, author_action = self.complete_stage(
            state,
            summary="Required MCP helper remains planned; readiness is not test execution.",
            evidence_refs=[skill_ref, mcp_ref],
        )
        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(skill_ref, packet)
        self.assertIn(mcp_ref, packet)
        self.assertIn("Work item context: " + context, packet)
        self.assertIn("Run-wide test strategy source (untrusted host report; revalidate relevance before use): ", packet)
        self.assertIn("(action " + strategy_action + "; state.md accepted." + strategy_action + ")", packet)
        # The document stage reads the authored decision (listed once under "Results this stage
        # builds on", its references in the result record) but not the strategy (printed here).
        self.assertIn("RUN/results/" + author_action + ".md", packet)
        self.assertNotIn("Current item test-decision source action:", packet)
        self.assertIn("Required MCP helper remains planned; readiness is not test execution.", packet)
        for action in (strategy_action, plan_action, author_action):
            self.assertIn(action, state["accepted"])
        self.assertEqual(set(state).intersection({"test_facilities", "facility_definitions"}), set())
        self.assertIn("untrusted locators; not read by the navigator", packet)
        self.assertEqual(
            state["accepted"][author_action]["summary"],
            "Required MCP helper remains planned; readiness is not test execution.",
        )

    def test_outer_test_handshake_recovers_add_work_aware_sources_cold(self) -> None:
        """The packet routes existing records; it does not certify their contents."""
        label = "OUTER test-planning handshake"
        locator = "repeatable-test-suites.md#outer-test-planning-handshake"
        outer_sources = (
            "latest done system-test-author and release-plan records",
            "most recent accepted add-work",
            "pending and blocked results are not plan authority",
        )

        # The shared contract must reach each root-owned OUTER producer and its
        # standalone Improve handoff without adding a Navigator state field.
        self.assertIsInstance(prompts.OUTER_TEST_HANDOFF, str)
        system_author = normalized(prompts.prompt("system-test-author"))
        for clause in (
            "The records in force are the ones listed under \"Results this stage builds on\"",
            "infer no whole-product coverage from the last transition",
            "candidate and boundaries, selected cases and oracles",
            "A post-release case is owned by release-verify and never waived",
        ):
            self.assertIn(clause, system_author)
        # U17 (row VR-4): the packet lists each completed item's records, so the duty no longer sends the model to search.
        self.assertNotIn("latest done test-decision record for each relevant completed item", system_author)
        release_plan = normalized(prompts.prompt("release-plan"))
        for clause in (
            "Revalidate the integrated test plan for the release target",
            "pre and post check owners, commands or case selectors",
            "execution versus target locations, remote test-definition revision",
        ):
            self.assertIn(clause, release_plan)
        system_test = normalized(prompts.prompt("system-test"))
        self.assertIn("Name the plan you run: the latest done system-test-author record", system_test)
        self.assertIn("remote framework availability", system_test)
        for stage in prompts.OUTER:
            with self.subTest(stage=stage):
                self.assertIn((label, locator), prompts.STAGE_REFERENCES[stage])
                packet = normalized(prompts.prompt(stage))
                improve_packet = normalized(prompts.improve_prompt(stage))
                # Packet re-cut (2026-10-11): OUTER_TEST_HANDOFF is no longer printed in a producer packet; each
                # stage's duty names the handshake and, where it consumes a plan, the "latest done ... record(s)
                # after the most recent/last accepted add-work" in its own words.  The shared text stays whole in the
                # Improve handoff (improve_prompt), where all three source phrases are still asserted.
                self.assertIn(label, packet)
                self.assertNotIn(prompts.OUTER_TEST_HANDOFF.split("\n")[0], packet)
                if stage != "system-test-author":
                    self.assertRegex(packet, r"(most recent|last) accepted\s+add-work")
                for source in outer_sources:
                    self.assertIn(source, improve_packet)

        strategy_ref = "docs/testing.md#strategy"
        decisions = {
            "W1": "docs/testing.md#w1-refined",
            "W2": "docs/testing.md#w2-regression",
            "W3": "docs/testing.md#w3-corrective",
        }
        state = self.state()
        decision_actions: dict[str, str] = {}
        while navigator.current_stage(state) != "plan":
            stage = navigator.current_stage(state)
            state, _action = self.complete_stage(
                state,
                evidence_refs=[strategy_ref if stage == "test-strategy" else "unrelated://" + stage],
            )
        state, _plan = self.complete_stage(
            state,
            evidence_refs=["docs/plan.md#items"],
            work_items=[
                {"id": "W1", "title": "First boundary", "context": "W1 isolated fixture."},
                {"id": "W2", "title": "Second boundary", "context": "W2 compatibility fixture."},
            ],
        )
        state = self.save_reload(state)

        # Complete W1/W2 while retaining their latest local test-decision action.
        while navigator.current_stage(state) != "system-test-author":
            stage = navigator.current_stage(state)
            owner = navigator._current_work_item(state)
            refs = ["unrelated://" + stage]
            if owner in decisions and stage == "test":
                refs = [decisions[owner]]
            state, action = self.complete_stage(state, evidence_refs=refs)
            state = self.save_reload(state)
            if owner in decisions and stage == "test":
                decision_actions[owner] = action

        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), packet)
        # system-test-author's duty 1 (U17, row VR-4): the records in force are listed per completed item, in the block
        # it names.
        self.assertIn("The records in force are the ones listed under \"Results this stage builds on\"", packet)
        current = planning_revision.current_actions(state)
        for owner in ("W1", "W2"):
            for read in ("step-plan", "test-spec", "test"):
                row = "- " + owner + " " + read + " result: RUN/results/" + current[(owner, read)] + ".md"
                self.assertIn(row, packet)
                self.assertGreater(packet.index(row), packet.index("Results this stage builds on"))
            self.assertEqual(current[(owner, "test")], decision_actions[owner])
        # Neither current-item context nor an item-local projection leaks into
        # root-owned outer planning. The handshake directs a bounded history lookup.
        self.assertNotIn("W1 isolated fixture.", packet)
        self.assertNotIn("W2 compatibility fixture.", packet)
        for action in decision_actions.values():
            self.assertTrue((self.run / "results" / (action + ".md")).is_file())
            self.assertIn(action, state["accepted"])

        state, system_author_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#integrated-system-plan"]
        )
        state = self.save_reload(state)
        state, _system_test_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#system-execution"]
        )
        state = self.save_reload(state)
        state, _acceptance_action = self.complete_stage(
            state, evidence_refs=["docs/testing.md#acceptance"]
        )
        state = self.save_reload(state)
        release_plan_action = dict(navigator.current_action(state))["id"]
        release_plan_draft = "untrusted://release-plan-pending-draft"
        waiting = navigator.apply(
            state,
            release_plan_action,
            result("release-plan", evidence_refs=[release_plan_draft]),
        )
        navigator.save(self.run, waiting)
        pending = store.read_record(self.run / "state.md")
        selected_skill = standalone_improve.resolve_skill(str(IMPROVE_CARD))
        bound_pending = dict(pending)
        bound_pending["active_improve"] = standalone_improve.binding(
            pending,
            release_plan_action,
            "release-plan",
            pending["active_improve"]["seed_result"],
            selected_skill,
            improve_action=pending["active_improve"]["improve_action"],
        )
        navigator.save(self.run, bound_pending)
        pending = store.read_record(self.run / "state.md")
        pending_bytes = (self.run / "state.md").read_bytes()
        # The Improve packet is two instructions; the handoff file holds the rest (packet re-cut R3).
        pending_packet = normalized(render_with_guides(None, self.run, pending) + "\n"
                                    + handoff_with_guides(None, self.run, pending))
        self.assertEqual((self.run / "state.md").read_bytes(), pending_bytes)
        self.assertEqual(pending["active_improve"]["action_id"], release_plan_action)
        self.assertEqual(
            pending["active_improve"]["seed_result"]["evidence_refs"],
            [release_plan_draft],
        )
        self.assertNotIn(release_plan_action, pending["accepted"])
        self.assertFalse(any(entry["action"] == release_plan_action for entry in pending["history"]))
        self.assertIn("The reviewed result stays pending until this Improve stage's complete imports the review.",
                      pending_packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), pending_packet)
        self.assertIn("latest done system-test-author and release-plan records", pending_packet)
        self.assertIn(system_author_action, pending["accepted"])

        release_plan_final = "docs/release.md#revalidated-target-and-checks"
        state = navigator.finish_improve(
            pending,
            release_plan_action,
            receipt("release-plan"),
            result("release-plan", evidence_refs=[release_plan_final]),
        )
        state = self.save_reload(state)
        self.assertEqual(state["accepted"][release_plan_action]["evidence_refs"], [release_plan_final])
        self.assertNotIn(release_plan_draft, state["accepted"][release_plan_action]["evidence_refs"])
        self.assertEqual(
            [entry for entry in state["history"] if entry["action"] == release_plan_action][0]["outcome"],
            "done",
        )
        self.assertEqual(navigator.current_stage(state), "release-check")

        # An outer corrective add-work is accepted history, then returns through a
        # new INNER item. Its predecessor records remain durable, but are no
        # longer presented as current outer-plan authority.
        add_work_result = result(
            "release-check",
            outcome="add-work",
            summary="A changed target needs a corrective compatibility item.",
            evidence_refs=["docs/release.md#add-work-target-change"],
            work_items=[
                {"id": "W3", "title": "Correct target compatibility", "context": "W3 new target fixture."}
            ],
        )
        add_work_action = dict(navigator.current_action(state))["id"]
        state = navigator.apply(state, add_work_action, add_work_result)
        self.assertIsNone(state["active_improve"])
        state = self.save_reload(state)
        self.assertEqual(navigator.current_stage(state), "step-plan")
        self.assertEqual(navigator._current_work_item(state), "W3")

        while navigator.current_stage(state) != "system-test-author":
            stage = navigator.current_stage(state)
            owner = navigator._current_work_item(state)
            refs = ["unrelated://" + stage]
            if owner == "W3" and stage == "test":
                refs = [decisions["W3"]]
            state, action = self.complete_stage(state, evidence_refs=refs)
            state = self.save_reload(state)
            if owner == "W3" and stage == "test":
                decision_actions["W3"] = action

        state, packet = self.cold_packet(state)
        packet = normalized(packet)
        self.assertIn(label + ": " + str(REFERENCES / locator), packet)
        self.assertIn("The records in force are the ones listed under \"Results this stage builds on\"", packet)
        self.assertIn("- W3 test result: RUN/results/" + decision_actions["W3"] + ".md", packet)
        self.assertNotIn("W3 new target fixture.", packet)
        # 2026-10-11 dedupe: the trailing "If this action depends on earlier accepted context..."
        # sentence is gone; the lists of sources and the "Results this stage builds on" block carry it.
        self.assertIn("Last accepted transition", packet)
        self.assertNotIn("If this action depends on earlier accepted context", packet)
        # The original records remain immutable/reachable in accepted state and
        # result files, while the recovery instructions mark them historical.
        for action in (system_author_action, release_plan_action, add_work_action):
            self.assertIn(action, state["accepted"])
            self.assertTrue((self.run / "results" / (action + ".md")).is_file())
        self.assertEqual(state["accepted"][add_work_action]["outcome"], "add-work")
        self.assertTrue(any(
            entry["action"] == add_work_action and entry["outcome"] == "add-work"
            for entry in state["history"]
        ))

    def test_the_system_test_author_defines_check_and_says_what_focused_needs(self) -> None:
        """SPEC S-3, S-10: the stage that records system commands names the suite for a command that is not a runner.

        A shell pipeline recorded as suite focused was refused at system-test ("could not read how many tests it
        ran") and the recording stage was the only place to fix it, so the recording stage must define check.
        """
        duties = normalized(prompts.prompt("system-test-author"))
        for clause in (
            "a non-runner (shell pipeline, grep, curl probe) is `check`, judged by exit code, no ids or min_tests",
            "`focused` and `regression` suit runners whose output ShipLoop can count",
        ):
            self.assertIn(clause, duties)
        # The suites are named once, before the definition that tells them apart.
        self.assertLess(duties.index("suite `focused`, `regression` or `check`"),
                        duties.index("a non-runner (shell pipeline, grep, curl probe) is `check`"))

    def test_a_person_only_case_with_no_host_route_is_an_open_item_not_a_block(self) -> None:
        """a13, SPEC S-14: system-test never routes a person-only case to blocked.

        The packet and the stage-readiness reference must agree (S-3): the case is
        an open item owned by a person and due at handoff, reported unverified.
        """
        system_test = normalized(prompts.prompt("system-test"))
        for clause in (
            "A required case only a person can run",
            "no route on this host per the discovery and test-strategy records",
            "does not block this result",
            "Record it as an open item in `assumptions`: case ID, who does what, what they report, "
            "owner (a person), due stage (handoff, or the stage whose external effect it gates) as `consumer`",
            "Submit done once every other due check and ShipLoop's rerun pass",
            "handoff reports it unverified, never as a pass",
            "Report blocked with `awaiting` only when a later stage takes an external, "
            "hard-to-reverse effect the case gates, or nothing else can proceed",
            "An enabled delivery contract keeps its own obligation phases",
        ):
            self.assertIn(clause, system_test)
        # The route cannot widen into a way to skip a check this host can run.
        for guard in (
            "Substitute no planned case or local mock for a required system observation",
            "A recorded system command that fails here is no open item: ShipLoop refuses done while it fails",
            "A local pass replaces no blocked or unrun required remote check",
        ):
            self.assertIn(guard, system_test)
        # Absence: the route is this stage's (release-verify words its own), and it stays
        # generic (S-8): a browser appears only as the example, never a named tool or product.
        for stage in prompts.STAGES:
            if stage != "system-test":
                self.assertNotIn("does not block this result",
                                 normalized(prompts.prompt(stage)), stage)
        start = system_test.index("A required case only a person can run")
        paragraph = system_test[start:system_test.index("keeps its own obligation phases.", start)]
        for term in ("playwright", "selenium", "chrome", "safari", "battleship"):
            self.assertNotIn(term, paragraph.lower())

        reference = normalized((REFERENCES / "testing-and-documentation.md").read_text(encoding="utf-8"))
        section = reference[reference.index("## Stage readiness and completion"):reference.index("## Test cases")]
        closing = section[section.index("Completion is phase-specific."):]
        self.assertIn("A required case already due but failed, blocked or not run prevents declaring "
                      "that boundary complete.", closing)
        self.assertIn(
            "Do not postpone an already-due check simply to advance. A required case that only a "
            "person can run, where the discovery and test-strategy records show this host has no "
            "route to it, is not such a check: it is an open item owned by that person and due at "
            "handoff (or the stage whose external effect it gates), reported unverified, and it "
            "does not prevent declaring the boundary complete. For an enabled delivery contract, "
            "preserve its fixed obligation phases and correction rules",
            closing,
        )
        handoff = normalized(prompts.prompt("handoff"))
        self.assertIn("`summary` lists every open item still unverified", handoff)
        self.assertIn("each with who does what and what they report back", handoff)

    def test_state_assessment_is_routed_to_planning_and_its_improve_handoffs(self) -> None:
        assessment = "requirements-definition.md#state-and-data-change-assessment"
        reconciliation = "requirements-definition.md#initial-plan-reconciliation"
        stages = {"spec", "test-strategy", "plan", "step-plan", "carry-forward", "release-plan"}
        for stage in prompts.STAGES:
            locators = {locator for _label, locator in prompts.STAGE_REFERENCES[stage]}
            with self.subTest(stage=stage):
                self.assertEqual(assessment in locators, stage in stages)
                self.assertEqual(reconciliation in locators, stage == "plan")
                if stage in stages:
                    self.assertIn("State and data assessment", prompts.improve_prompt(stage))
        self.assertIn("Initial-plan reconciliation", prompts.prompt("plan"))
        self.assertIn("State and data assessment", prompts.prompt("spec"))
        # This is guidance within existing stages, not another runtime owner.
        self.assertFalse(any("assessment" in stage or "reconciliation" in stage for stage in prompts.STAGES))

    def test_synthetic_planning_fixtures_have_executable_baselines(self) -> None:
        """Fixture health is not evidence that a model produced an adequate plan."""
        fixtures = ROOT / "test" / "experiments" / "shiploop_state_planning"
        commands = {
            "memory-utility": ["-m", "unittest", "test_minute_tally.py"],
            "crm-board": ["verify_board.py"],
            "import-projection": ["-m", "unittest", "test_imports.py"],
        }
        for case, args in commands.items():
            with self.subTest(case=case):
                root = fixtures / case
                self.assertTrue((root / "request.md").read_text().strip())
                self.assertTrue((root / "frozen-rubric.md").read_text().strip())
                self.assertFalse((root / "repo" / "frozen-rubric.md").exists())
                checked = subprocess.run(
                    [sys.executable, "-B", *args], cwd=root / "repo",
                    text=True, capture_output=True, timeout=10,
                )
                self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)

    def test_cold_initial_plan_preserves_state_obligations_through_improve(self) -> None:
        state = self.state()
        while navigator.current_stage(state) != "plan":
            state, _ = self.complete_stage(state)
        action = dict(navigator.current_action(state))
        refs = ["docs/architecture.md#access", "docs/spec.md#staff-board", "test/access.py#wrong-user"]
        context = (
            "Intended consumer: staff; deploy operator is separate. "
            "Access proof and wrong-user check: docs/spec.md#staff-board; "
            "test/access.py#wrong-user. Revalidate target before verification."
        )
        state = navigator.apply(state, action["id"], result(
            "plan", evidence_refs=refs,
            work_items=[{"id": "ACCESS", "title": "Establish intended consumer access", "context": context}],
        ))
        navigator.save(self.run, state)
        recovered = store.read_record(self.run / "state.md")
        packet = self.packet_with_handoff(recovered)
        self.assertEqual(navigator.current_stage(recovered), "plan")
        self.assertEqual(navigator.current_action(recovered)["id"], action["id"])
        self.assertEqual(recovered["active_improve"]["seed_result"]["evidence_refs"], refs)
        self.assertIn("Initial-plan reconciliation", packet)
        self.assertIn("State and data assessment", packet)
        # Synthetic review receipt exercises transport only, not semantic review.
        recovered = navigator.finish_improve(recovered, action["id"], receipt("plan"))
        while navigator.current_stage(recovered) != "step-plan":
            recovered, _ = self.complete_stage(recovered)
        navigator.save(self.run, recovered)
        cold = store.read_record(self.run / "state.md")
        self.assertEqual(cold["work_items"][0]["context"], context)
        self.assertEqual(cold["accepted"][action["id"]]["evidence_refs"], refs)
        self.assertIn("Work item context: " + context, render_with_guides(None, self.run, cold))

    def test_improve_and_source_return_guidance_keep_the_existing_boundary(self) -> None:
        card = IMPROVE_CARD.read_text(encoding="utf-8")
        self.assertIn("## ShipLoop whole-skill subcall", card)
        self.assertIn("When this skill is invoked with the argument `ShipLoop Improve: <handoff path>`", card)
        self.assertIn("it plays the role of\n\"the ShipLoop packet\"", card)
        self.assertIn("parent-only stopped-child reconciliation callback", normalized(card))
        self.assertIn("no other stopped child advances the parent", normalized(card))
        self.assertIn("standalone whole-skill subcall", card)

        # Commit policy is owned by the selected Improve card, not repeated
        # in every stage's handoff. Native experiments test execution of it.
        improve = normalized(card + STANDALONE_ROUTE.read_text(encoding="utf-8"))
        for clause in (
            "commit authorized scoped changes in the bound candidate worktree",
            "never include runtime receipts or unrelated inherited staging",
            "no-change review gets an honest host record",
            "explicit no-commit request",
            "from an existing invocation, remains binding",
            "retain the commit SHA in its handoff",
        ):
            self.assertIn(clause, improve)

        discovery = normalized(prompts.prompt("discovery"))
        prepare = normalized(prompts.prompt("prepare"))
        self.assertIn("whether the source-branch return triggers CI, a deploy or a publication", discovery)
        self.assertIn("source-return trigger", prepare)
        self.assertIn("Never return early, deploy, or bypass the final-handoff return guard", prepare)

    def test_improve_retains_coding_and_release_capabilities_with_stage_authority(self) -> None:
        card = normalized(IMPROVE_CARD.read_text(encoding="utf-8"))
        self.assertIn("execution-capable coding agent", card)
        self.assertIn("tools, MCP interactions and skills", card)
        self.assertIn("perform authorized deployments", card)
        self.assertIn("consequential issues the initiating context did not anticipate", card)
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                improve = normalized(prompts.improve_prompt(stage))
                self.assertIn("Invoke the selected actual Improve skill", improve)
                self.assertNotIn("changed product or requirements files", improve)
        for stage in RELEASE_OPERATION_STAGES:
            with self.subTest(release=stage):
                improve = normalized(prompts.improve_prompt(stage))
                self.assertIn("Do not repeat unchanged release effects merely to advance the review streak", improve)
                self.assertNotIn("Improve does not initiate or replay release effects", improve)
                # One rule for every stage that reads Release operation guidance (SPEC S-3; environment-lifecycle.md
                # #release-operation-ownership): a stage-scoped Improve assesses and records, never executes or replays
                # a release effect.  No Improve child runs at release itself, so no text lets one perform it (the
                # release-plan Improve packet said it "may perform deployments": packet review 2026-10-10, P-imp-1).
                self.assertIn("does not execute or replay a release effect", improve)
                self.assertNotIn("may perform deployments", improve)
                self.assertNotIn("already authorized for the current task and stage", improve)
        import shiploop_stage_spec as spec
        self.assertIsNone(spec.stage("release").improve)  # the premise: release starts no Improve child
        planning = normalized(prompts.improve_prompt("plan"))
        self.assertNotRegex(planning, r"[Bb]ackchain")  # an Improve review never mentions Backchain (owner, 2026-10-11)
        discovery = normalized(prompts.improve_prompt("discovery"))
        self.assertIn("may not edit product source", discovery)

    def test_discovery_investigation_route_recovers_from_relocated_package(self) -> None:
        """Relocated packets transport the selected locator; they do not prove model use."""
        expected = [(
            DISCOVERY_INVESTIGATION_GUIDANCE_LABEL,
            DISCOVERY_INVESTIGATION_GUIDE + "#" + DISCOVERY_INVESTIGATION_ANCHOR,
        )]
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (label, locator)
                    for label, locator in prompts.STAGE_REFERENCES[stage]
                    if label == DISCOVERY_INVESTIGATION_GUIDANCE_LABEL
                ]
                self.assertEqual(entries, expected if stage in DISCOVERY_INVESTIGATION_STAGES else [])
        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        copied_guide = relocated / DISCOVERY_INVESTIGATION_GUIDE
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(
                r"(?m)^(#{1,6})\s+(.+?)\s*$", copied_guide.read_text(encoding="utf-8")
            )
        }
        self.assertIn(DISCOVERY_INVESTIGATION_ANCHOR, headings)
        core = type("RelocatedCore", (), {"PACKAGE_ROOT": relocated.parent})()
        relocated_route = (
            DISCOVERY_INVESTIGATION_GUIDANCE_LABEL
            + ": "
            + str(relocated / (DISCOVERY_INVESTIGATION_GUIDE + "#" + DISCOVERY_INVESTIGATION_ANCHOR))
        )
        state = self.state()
        observed: list[str] = []

        while navigator.current_stage(state) != "spec":
            stage = navigator.current_stage(state)
            if stage not in DISCOVERY_INVESTIGATION_STAGES:
                state, _action_id = self.complete_stage(state)
                continue

            navigator.save(self.run, state)
            before = (self.run / "state.md").read_bytes()
            recovered = store.read_record(self.run / "state.md")
            packet = render_with_guides(core, self.run, recovered)
            self.assertEqual((self.run / "state.md").read_bytes(), before)
            self.assertEqual(packet.count(relocated_route), 1, packet)
            self.assertNotIn(str(REFERENCES), packet)

            # Discovery stages never start an Improve child.
            state, _action = self.produce(recovered)
            self.assertIsNone(state["active_improve"])
            observed.append(stage)

        self.assertEqual(tuple(observed), DISCOVERY_INVESTIGATION_STAGES)

    def _assert_relocated_discovery_route(
        self, *, label: str, guide: str, anchor: str, stages: tuple[str, ...]
    ) -> None:
        """Check a package-relative discovery route across recovered producer packets."""
        expected = [(label, guide + "#" + anchor)]
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (entry_label, locator)
                    for entry_label, locator in prompts.STAGE_REFERENCES[stage]
                    if entry_label == label
                ]
                self.assertEqual(
                    entries,
                    expected if stage in stages else [],
                )

        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        copied_guide = relocated / guide
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(
                r"(?m)^(#{1,6})\s+(.+?)\s*$", copied_guide.read_text(encoding="utf-8")
            )
        }
        self.assertIn(anchor, headings)
        core = type("RelocatedCore", (), {"PACKAGE_ROOT": relocated.parent})()
        relocated_route = label + ": " + str(relocated / (guide + "#" + anchor))
        state = self.state()
        observed: list[str] = []

        while navigator.current_stage(state) != "spec":
            stage = navigator.current_stage(state)
            if stage not in stages:
                state, _action_id = self.complete_stage(state)
                continue

            navigator.save(self.run, state)
            before = (self.run / "state.md").read_bytes()
            recovered = store.read_record(self.run / "state.md")
            self.assertEqual(recovered["improve_skill"], "")
            self.assertIsNone(recovered["active_improve"])
            packet = render_with_guides(core, self.run, recovered)
            self.assertEqual((self.run / "state.md").read_bytes(), before)
            self.assertEqual(packet.count(relocated_route), 1, packet)
            self.assertNotIn(str(REFERENCES), packet)

            # Discovery stages never start an Improve child.
            state, _action = self.produce(recovered)
            self.assertIsNone(state["active_improve"])
            observed.append(stage)

        self.assertEqual(tuple(observed), stages)

    def test_connected_knowledge_discovery_route_recovers_from_relocated_package(self) -> None:
        """Relocated packets transport the selected locator; they do not prove live access."""
        self._assert_relocated_discovery_route(
            label=CONNECTED_KNOWLEDGE_DISCOVERY_LABEL,
            guide=CONNECTED_KNOWLEDGE_DISCOVERY_GUIDE,
            anchor=CONNECTED_KNOWLEDGE_DISCOVERY_ANCHOR,
            stages=CONNECTED_KNOWLEDGE_DISCOVERY_STAGES,
        )

    def test_discovery_evidence_handoff_route_recovers_from_relocated_package(self) -> None:
        """A recovered producer packet preserves the selected handoff locator."""
        self._assert_relocated_discovery_route(
            label=DISCOVERY_EVIDENCE_HANDOFF_LABEL,
            guide=DISCOVERY_EVIDENCE_HANDOFF_GUIDE,
            anchor=DISCOVERY_EVIDENCE_HANDOFF_ANCHOR,
            stages=DISCOVERY_EVIDENCE_HANDOFF_STAGES,
        )

    def test_service_discovery_stage_routes_are_exact_and_selective(self) -> None:
        """Keep the conditional guide's routes independent of the prompt catalog."""
        observed: list[str] = []
        for stage in prompts.STAGES:
            with self.subTest(stage=stage):
                entries = [
                    (label, locator)
                    for label, locator in prompts.STAGE_REFERENCES[stage]
                    if label == SERVICE_DISCOVERY_GUIDANCE_LABEL
                ]
                anchor = SERVICE_DISCOVERY_STAGE_ANCHORS.get(stage)
                if anchor is None:
                    self.assertEqual(entries, [])
                else:
                    self.assertEqual(
                        entries,
                        [(SERVICE_DISCOVERY_GUIDANCE_LABEL, SERVICE_DISCOVERY_GUIDE + "#" + anchor)],
                    )
                    observed.append(stage)
        self.assertEqual(tuple(observed), tuple(SERVICE_DISCOVERY_STAGE_ANCHORS))


    def test_service_discovery_routes_survive_cold_producer_and_improve_packets(self) -> None:
        """Current-stage routing survives recovery without replaying earlier guide refs."""
        index = self.repo / "SHIPLOOP.md"
        index.write_text("# Fixture decision index\n", encoding="utf-8")
        index_route = "Repository knowledge index (host-authored, if present): WORKTREE/" + index.name
        routes = tuple(dict.fromkeys(SERVICE_DISCOVERY_ROUTES.values()))
        observed: list[str] = []
        improved: list[str] = []
        state = self.state()

        def assert_packet(stage: str, packet: str) -> None:
            expected = SERVICE_DISCOVERY_ROUTES.get(stage)
            self.assertEqual(packet.count(index_route), 1, packet)
            for route in routes:
                with self.subTest(stage=stage, route=route):
                    self.assertEqual(packet.count(route), int(route == expected), packet)

        while state["status"] != "done":
            stage = navigator.current_stage(state)
            producer, producer_packet = self.cold_packet(state)
            self.assertEqual(navigator.current_stage(producer), stage)
            assert_packet(stage, producer_packet)

            if stage in SERVICE_DISCOVERY_ROUTES:
                observed.append(stage)
            extra: dict[str, object] = {}
            if stage == "plan":
                extra["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            waiting, action = self.produce(producer, **extra)
            if waiting["active_improve"] is None:
                state = waiting
                continue
            pending, pending_packet = self.cold_packet(waiting)
            self.assertEqual(navigator.current_stage(pending), stage)
            assert_packet(stage, pending_packet)
            if stage in SERVICE_DISCOVERY_ROUTES:
                improved.append(stage)
            state = navigator.finish_improve(pending, action["id"], receipt(stage))

        self.assertEqual(tuple(observed), tuple(SERVICE_DISCOVERY_STAGE_ANCHORS))
        # implement's Improve child reviews every accepted step (owner decision 2026-10-10).
        self.assertEqual(improved, ["spec", "test-strategy", "plan", "step-plan", "implement"])


    def test_service_discovery_guide_sections_and_links_survive_package_relocation(self) -> None:
        """The direct guide stays portable with its stable section anchors."""
        guide = REFERENCES / SERVICE_DISCOVERY_GUIDE
        self.assertTrue(guide.is_file(), guide)
        if not guide.is_file():
            return
        body = guide.read_text(encoding="utf-8")
        headings = {
            heading_anchor(match.group(2))
            for match in re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", body)
        }
        for anchor in SERVICE_DISCOVERY_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(anchor, headings)

        relocated = (self.repo / "copied-package" / "references").resolve()
        shutil.copytree(REFERENCES, relocated)
        copied_guide = relocated / SERVICE_DISCOVERY_GUIDE
        copied_body = copied_guide.read_text(encoding="utf-8")
        self.assertNotIn("/Users/", copied_body)
        for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)", copied_body):
            if link.startswith(("https://", "http://")):
                continue
            with self.subTest(link=link):
                path, _, anchor = link.partition("#")
                destination = (copied_guide.parent / path).resolve() if path else copied_guide
                self.assertTrue(destination.is_relative_to(relocated), link)
                self.assertTrue(destination.is_file(), link)
                if anchor:
                    destination_headings = {
                        heading_anchor(match.group(2))
                        for match in re.finditer(
                            r"(?m)^(#{1,6})\s+(.+?)\s*$",
                            destination.read_text(encoding="utf-8"),
                        )
                    }
                    self.assertIn(anchor, destination_headings)


    def test_service_discovery_context_and_final_improve_handoff_are_item_scoped(self) -> None:
        """Carry final service decisions through one item without replaying them to the next."""
        index = self.repo / "SHIPLOOP.md"
        decision = self.repo / "docs" / "decisions" / "customer-review.md"
        decision.parent.mkdir(parents=True)
        index.write_text(
            "# Fixture decision index\n\n## Customer review\n\n"
            "- [Accepted remote-service decision](docs/decisions/customer-review.md#accepted)\n",
            encoding="utf-8",
        )
        decision.write_text("# Customer review\n\n## Accepted\n", encoding="utf-8")
        index_ref = str(index) + "#customer-review"
        final_plan_ref = str(decision) + "#accepted"
        final_step_ref = str(decision) + "#implementation-handoff"
        plan_seed_ref = "untrusted://shared-cache-seed"
        step_seed_ref = "untrusted://draft-service-handoff"
        seed_context = "W1 seed: share customer cache before verifying authorization."
        final_context = (
            "W1 remote service: reopen " + index_ref + " and " + final_plan_ref
            + "; preserve the remote schema delta, gate each cached read on current "
            "authorization, use durable record rereads after asynchronous work, and reuse "
            "the existing audit owner unless coverage is insufficient."
        )
        local_context = (
            "W2 local change: reopen " + index_ref
            + " and reassess its own scope; no customer-service decision carries over."
        )
        index_route = "Repository knowledge index (host-authored, if present): WORKTREE/" + index.name
        state = self.state()

        while navigator.current_stage(state) != "plan":
            state, _action_id = self.complete_stage(state)
        final_plan = result(
            "plan",
            evidence_refs=[final_plan_ref],
            work_items=[
                {"id": "W1", "title": "Harden customer service", "context": final_context},
                {"id": "W2", "title": "Make local title change", "context": local_context},
            ],
        )
        state, plan_action = self.complete_stage_with_final(
            state,
            final_plan,
            evidence_refs=[plan_seed_ref],
            work_items=[{"id": "W1", "title": "Seed plan", "context": seed_context}],
        )
        state = self.save_reload(state)
        self.assertEqual(state["accepted"][plan_action]["evidence_refs"], [final_plan_ref])
        self.assertEqual(state["work_items"][0]["context"], final_context)
        self.assertNotIn(plan_seed_ref, state["accepted"][plan_action]["evidence_refs"])
        self.assertNotEqual(state["work_items"][0]["context"], seed_context)

        while navigator.current_stage(state) != "step-plan":
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        first_item, first_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(first_item), "W1")
        self.assertEqual(first_packet.count(index_route), 1, first_packet)
        self.assertEqual(first_packet.count(SERVICE_DISCOVERY_ROUTES["step-plan"]), 1, first_packet)
        self.assertIn("Work item context: " + final_context, first_packet)
        self.assertIn(final_plan_ref, first_packet)
        self.assertNotIn(seed_context, first_packet)
        self.assertNotIn(plan_seed_ref, first_packet)

        final_step = result(
            "step-plan",
            summary="Improve retained the final service handoff.",
            evidence_refs=[final_step_ref],
        )
        state, step_action = self.complete_stage_with_final(
            first_item,
            final_step,
            evidence_refs=[step_seed_ref],
        )
        state, test_spec_packet = self.cold_packet(state)
        self.assertEqual(navigator.current_stage(state), "test-spec")
        self.assertEqual(state["accepted"][step_action]["evidence_refs"], [final_step_ref])
        self.assertIn("Work item context: " + final_context, test_spec_packet)
        # 2026-10-11 dedupe: the accepted step plan is listed once under "Results this stage builds
        # on"; its final references are read from that record, never the draft's.
        self.assertIn("W1 step-plan result: RUN/results/" + step_action + ".md", test_spec_packet)
        self.assertNotIn("Current item test-decision source action:", test_spec_packet)
        step_record = (self.run / "results" / (step_action + ".md")).read_text(encoding="utf-8")
        self.assertIn(final_step_ref, step_record)
        self.assertNotIn(step_seed_ref, step_record)
        self.assertNotIn(step_seed_ref, test_spec_packet)
        self.assertNotIn(plan_seed_ref, test_spec_packet)

        while not (
            navigator.current_stage(state) == "step-plan"
            and navigator._current_work_item(state) == "W2"
        ):
            state, _action_id = self.complete_stage(state)
            state = self.save_reload(state)
        second_item, second_packet = self.cold_packet(state)
        self.assertEqual(navigator._current_work_item(second_item), "W2")
        self.assertEqual(second_packet.count(index_route), 1, second_packet)
        self.assertEqual(second_packet.count(SERVICE_DISCOVERY_ROUTES["step-plan"]), 1, second_packet)
        self.assertIn("Work item context: " + local_context, second_packet)
        self.assertNotIn(final_context, second_packet)
        self.assertNotIn(final_plan_ref, second_packet)
        self.assertNotIn(final_step_ref, second_packet)
        self.assertNotIn(step_seed_ref, second_packet)




class SettledFactTests(unittest.TestCase):
    """The Battleship runs lost hours to facts the plan left open: the module format with no package.json (a missing-module
    escape) and a default `node --test` that needed the host browser. The planning duties now state them."""

    def duty(self, stage: str) -> str:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_prompts as prompts
        return " ".join(prompts.DUTIES[stage].split())

    def test_plan_states_each_items_module_format_and_loadable_seam(self) -> None:
        text = self.duty("plan")
        self.assertIn("module format", text)
        self.assertIn("loadable seam", text)

    def test_system_test_author_marks_host_dependent_rows(self) -> None:
        text = self.duty("system-test-author")
        self.assertIn('"host_dependent": true', text)
        self.assertIn("regression", text)

    def test_test_strategy_keeps_host_dependent_cases_out_of_the_default_suite_command(self) -> None:
        text = self.duty("test-strategy")
        # Packet re-cut: item 11 says "a case that needs a host tool" (the old "host-dependent" label is the system
        # stages' `host_dependent` row flag).
        self.assertIn("A case needing a host tool", text)
        self.assertIn("probe", text)
        self.assertIn("default test command", text)
        # Live finding (Grok 2026-10-07): `Chrome --version` passed as the probe, then the page never loaded.
        self.assertIn("not reading a version", text)
        self.assertIn("access gap", text)

    def test_test_strategy_probes_a_host_tool_against_a_stand_in_because_the_product_does_not_exist_yet(self) -> None:
        """Batch 1009 P4 (round 1, Grok `none` run): the strategy's browser probe was a curl to the product's address
        (connection refused), a server that cannot exist before the product does, and it concluded "no browser"; the
        real access gap surfaced about 40 minutes later at system-test-author and cost 21 minutes of Chrome flag
        iteration.  A probe has to be answerable now, so it runs against a page the stage writes itself."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_prompts as prompts
        text = self.duty("test-strategy")
        for phrase in (
            "Before the product exists, probe a stand-in",
            "a one-line page in RUN/scratch",
            "opened by `file:` URL or a throwaway static server you stop",
            "its title read back",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)
        # The earlier obligations stay: the probe is the case's first step, a failed probe is a recorded access gap,
        # and the case keeps its own opt-in command.
        for kept in ("probe it now by doing the case's first step, not reading a version",
                     "Record only a failed probe as an access gap under ## Real-boundary checks with the requirement "
                     "left unobserved",
                     "Give the case its own opt-in command or flag"):
            with self.subTest(kept=kept):
                self.assertIn(kept, text)
        # and a host reads it in the packet it is given, under either delegation
        for delegation in (prompts.INLINE, prompts.ASK_AGENT):
            with self.subTest(delegation=delegation):
                packet = " ".join(prompts.prompt("test-strategy", delegation=delegation).split())
                self.assertEqual(packet.count("probe a stand-in"), 1)
        # The sentence is conditional: a run on an existing product that is already running does not meet it as a fact.
        self.assertNotIn("The product does not exist yet", text)


class ConsumerCheckLocationTests(unittest.TestCase):
    """Batch 1008, B3: release-verify's consumer checks run in a clean copy of the returned result when a return is
    recorded.  Each stage that has to know it restates its own part (the main tenet: context may be cleared between
    any two stages); the script-computed packet line says where they run this time, so the duties do not repeat it."""

    @staticmethod
    def duty(stage: str) -> str:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_prompts as prompts
        return " ".join(prompts.DUTIES[stage].split())

    def test_release_plan_says_where_the_checks_will_run_and_how_to_write_them(self) -> None:
        text = self.duty("release-plan")
        self.assertIn("clean copy of the returned result", text)
        self.assertIn("in the work area, and says so", text)
        self.assertIn("Write paths relative to the starting directory", text)
        self.assertNotIn("relative to the checkout", text, "the user's checkout is not where the command starts")
        self.assertIn("what a fresh consumer needs", text)
        self.assertIn("never write into the user's checkout", text)

    def test_release_verify_says_how_a_defect_is_fixed_and_what_may_touch_the_checkout(self) -> None:
        text = self.duty("release-verify")
        self.assertIn("Isolated run: this stage cannot return", text)
        self.assertIn("through `add-work`", text)
        self.assertIn("Write nothing inside the user's checkout", text)
        self.assertIn("stale", text)

    def test_the_copy_semantics_are_not_added_to_the_other_two_statements_in_that_packet(self) -> None:
        """GUARD (passes on the unchanged tree): said once per packet. The stage row and the duty keep only the sentence
        they always had; the script-computed rerun block is the one place that says where the commands run."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        self.assertEqual(spec.STAGE_SPEC["release-verify"].tools,
                         "On done, ShipLoop runs every consumer check release-plan recorded.")
        self.assertNotIn("clean copy", self.duty("release-verify"))

    def test_handoff_reports_where_release_verify_ran_from_the_line_its_packet_carries(self) -> None:
        text = self.duty("handoff")
        self.assertIn("Consumer checks (release-verify)", text)
        self.assertIn("or that none ran", text)
        self.assertIn("did not observe the user's checkout", text)

    def test_the_skill_card_and_the_workspace_lifecycle_card_say_the_same(self) -> None:
        skill = " ".join((REFERENCES / "test-loop.md").read_text(encoding="utf-8").split())  # moved from the card by U22
        self.assertIn("clean copy of the result the workspace return delivered", skill)
        self.assertIn("`consumer-check`", skill)
        lifecycle = " ".join((REFERENCES / "workspace-lifecycle.md").read_text(encoding="utf-8").split())
        self.assertIn("### Which checkout release-verify observes", lifecycle)
        for phrase in ("`consumer-check`", "clean copy of the returned result", "never the user's checkout",
                       "no Git history", "absolute path"):
            self.assertIn(phrase, lifecycle)
        follow_up = lifecycle[lifecycle.index("### Follow-up return"):]
        self.assertIn("At `release-verify` the stage cannot return", follow_up[:follow_up.index("## Recovery and limits")])

    JOURNAL = ROOT / "docs" / "shiploop-batch-1007-plan-2026-10-07.md"
    RECOUNT = ROOT / "docs" / "experiments" / "batch-1008-b3-20261008"

    def test_the_journal_lists_what_the_live_run_must_still_show(self) -> None:
        """Hermetic fixtures prove the mechanism, not the models' habits: the journal names each live check as open."""
        text = " ".join(self.JOURNAL.read_text(encoding="utf-8").split())
        built = text[text.index("## B3 built 2026-10-08"):]
        opened = built[built.index("**Open, with status.**"):built.index("**Owner decisions this needs.**")]
        # the recorded consumer commands are relative, so the copy is where they run (5 of 10 recorded runs named the source)
        self.assertIn("recorded release-verify commands use relative paths", opened)
        self.assertIn("names the source or work-area path", opened)
        self.assertIn("5 of the 10", opened)
        # the user's checkout is untouched and the stage hand-off completes
        self.assertIn("empty `git status --porcelain --untracked-files=all` in the source", opened)
        self.assertIn("handoff", opened)
        # the second return kind has no live run: validated another way, with the limit and the next step recorded
        self.assertIn("validated another way", opened)
        self.assertIn("working-tree-return", opened)
        self.assertIn("Named next step", opened)

    def test_the_receipt_recount_the_journal_cites_is_in_the_repository(self) -> None:
        text = self.JOURNAL.read_text(encoding="utf-8")
        self.assertIn("docs/experiments/batch-1008-b3-20261008/receipt-recount.json", text)
        recount = json.loads((self.RECOUNT / "receipt-recount.json").read_text(encoding="utf-8"))
        summary, runs = recount["summary"], recount["runs"]
        self.assertEqual(summary["runs_with_a_return_receipt"], len(runs))
        self.assertEqual(summary["receipt_kinds"], {"fast-forward-merge": len(runs)})
        self.assertEqual(summary["runs_whose_consumer_checks_name_the_source_path"],
                         sum(1 for run in runs if run["commands_naming_source_path"]))
        self.assertEqual(summary["runs_whose_every_release_verify_record_ran_in_the_work_area"], len(runs))
        self.assertTrue((self.RECOUNT / "recount.py").is_file())


class CaseEndStateTests(unittest.TestCase):
    """Owner rule (2026-10-08): a test is authored and executed, and a case completes only when it is validated, re-validated
    another way, or declared unachievable. A case written but not run, or recorded `not run`, is not an end state."""

    STAGES = ("test", "system-test-author", "system-test")

    def test_the_stage_rows_state_the_three_end_states(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        for stage in self.STAGES:
            with self.subTest(stage):
                text = " ".join((spec.stage(stage).test or "").split())
                self.assertIn("validated", text)
                self.assertIn("another way", text)
                self.assertIn("unachievable", text)
                self.assertIn("not an end state", text)

    # The outcomes a case is routed through; done is how any result ends, not where a case goes.
    ROUTES = ("blocked", "send-back", "add-work")

    @staticmethod
    def sentence(stage: str) -> str:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        text = " ".join((spec.stage(stage).test or "").split())
        return text[text.index("Every case ends"):]

    def test_the_case_end_states_are_printed_by_exactly_these_stages_from_one_function(self) -> None:
        """S-12: one function builds the sentence from a stage's own row, so no stage gets another stage's text."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        carrying = tuple(name for name in spec.STAGES if "Every case ends" in (spec.stage(name).test or ""))
        self.assertEqual(carrying, self.STAGES)
        for stage in self.STAGES:
            with self.subTest(stage):
                self.assertEqual(self.sentence(stage), " ".join(spec.case_end_states(spec.stage(stage)).split()))

    def test_each_sentence_names_exactly_the_routes_its_stage_accepts(self) -> None:
        """B2 and correctness #4/#7 of the 2026-10-10 packet review: the sentence was one text, edited by a string
        replace for inner stages, so test-green and regression were told to record an open item and continue (no gate
        of theirs accepts that) and the replace broke silently when the text moved.  Every outcome the sentence names
        is one the stage accepts, and every routing outcome the stage accepts is named."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        for stage in self.STAGES:
            row = spec.stage(stage)
            sentence = self.sentence(stage)
            named = {word for word in spec.OUTCOMES if re.search(r"\b" + word + r"\b", sentence)}
            with self.subTest(stage):
                self.assertLessEqual(named, set(row.outcomes), sentence)
                self.assertEqual(named & set(self.ROUTES), set(row.outcomes) & set(self.ROUTES), sentence)
                self.assertIn("only when nothing else can proceed", sentence)

    def test_an_unachievable_case_is_an_open_item_outside_the_item_and_send_back_inside_it(self) -> None:
        """P-sta-2, SPEC S-14: both Grok BLOCKED runs stopped on a case the host could not run (TC-16 needed a browser),
        while the packet said to record an open item and continue.  That route belongs to the outer test stages; an
        inner stage's case goes back to the step plan (send-back), which its gate accepts."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        for stage in self.STAGES:
            sentence = self.sentence(stage)
            with self.subTest(stage):
                if spec.stage(stage).phase == "outer":
                    self.assertIn("record it as an open item in the result's `assumptions`, with the stage it is due at "
                                  "as its consumer, and continue", sentence)
                    self.assertIn("provided its command is not one ShipLoop reruns, since every rerun command must pass",
                                  sentence)
                    # An unachievable case stays an open item; send-back (S1.5) is only for a case wrong as planned,
                    # and only where the stage runs another stage's plan.
                    if "send-back" in spec.stage(stage).outcomes:
                        self.assertIn("report send-back when the case as planned is itself wrong, so "
                                      + spec.OUTER_SEND_BACK_TO[stage] + " amends it", sentence)
                    else:
                        self.assertNotIn("send-back", sentence)
                else:
                    self.assertIn("report send-back so the step plan reroutes the case", sentence)
                    self.assertNotIn("open item", sentence)
                    self.assertNotIn("add-work", sentence)
        duty = normalized(prompts.DUTIES["system-test-author"])
        for clause in (
            "A case that cannot run here (a browser or account this host cannot reach) is unachievable",
            "Leave its command out of `system_commands`",
            "Record it as an open item in `assumptions`: `assumption` = case ID and the requirement left unverified; "
            "`check` = who does what and reports what; `owner`; `reason` it cannot run here; `consumer` = the due "
            "stage (handoff, or the stage whose external effect it gates)",
            "Report blocked only when nothing else can proceed",
        ):
            self.assertIn(clause, duty)
        self.assertNotIn("blocked_by", duty)   # retired: a wait is `awaiting`, and only when nothing else can proceed
        self.assertNotIn("a route that fails when run", duty)

    def test_system_test_promises_no_done_past_a_failing_recorded_command(self) -> None:
        """B1 of the 2026-10-10 packet review (probe_system_test.py): the system-test duty said a route that fails when
        the case is run is an open item and the result is done, but that case's command is in system_commands and
        ShipLoop's rerun refuses done while it fails.  The widening is gone; a case run here is reported, not recorded."""
        paragraph = normalized(prompts.DUTIES["system-test"])
        self.assertNotIn("the route fails when the case is run", paragraph)
        self.assertNotIn("page never loads", paragraph)
        self.assertIn("Run any open item system-test-author recorded that this stage can now run, reporting each in the "
                      "summary (not recorded evidence: ShipLoop's rerun covers only recorded system commands)", paragraph)
        self.assertIn("A recorded system command that fails here is no open item", paragraph)

    def test_the_system_test_author_runs_each_command_once_while_authoring(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_prompts as prompts
        text = " ".join(prompts.DUTIES["system-test-author"].split())
        self.assertIn("run each system command once", text.lower())
        self.assertIn("unachievable", text)


class CarriedOpenItemTests(unittest.TestCase):
    """SPEC S-6: a stage told to carry in what an earlier stage recorded reads that stage's result."""

    def test_product_acceptance_reads_every_stage_whose_open_items_it_carries_in(self) -> None:
        """N3 of the 2026-10-10 packet review: the duty named system-test-author, the row's reads did not."""
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        duty = normalized(prompts.DUTIES["product-acceptance"])
        carried = re.search(r"Carry in the open items earlier stages recorded \(([^)]*)\)", duty)
        self.assertIsNotNone(carried)
        for name in carried.group(1).split(", "):
            with self.subTest(name):
                self.assertIn(name, spec.stage("product-acceptance").reads)


class UnattendedWordingTests(unittest.TestCase):
    """SPEC S-14: a stage row asks for nothing an unattended run cannot do, and one packet never contradicts itself."""

    def test_the_prelude_rows_ask_for_a_default_or_an_open_item_and_none_for_a_person_or_a_suite_that_may_not_exist(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        rows = {name: " ".join(spec.stage(name).done_when) for name in ("intake", "discovery", "research")}
        self.assertNotIn("put to the user", rows["research"])
        self.assertIn("recorded as an open item with who can grant it", rows["research"])
        self.assertNotIn("the user now", rows["intake"])
        self.assertIn("a recorded default", rows["intake"])
        self.assertIn("none exists and that is recorded as missing coverage", rows["discovery"])

    def test_the_integrate_guidance_leaves_the_commit_to_shiploop_and_binds_no_chain_inline(self) -> None:
        for route in ("inline", "ask-agent"):
            with self.subTest(route=route):
                text = normalized(prompts.prompt("verify", delegation=route))  # integrate folded into verify
                self.assertNotIn("assemble or commit", text)  # the stage row says ShipLoop commits; the duty does not ask
                self.assertEqual("bound a chain" in text, route == "ask-agent")  # a chain exists only when delegation is ask-agent

    def test_the_improve_packet_never_calls_its_own_review_independent(self) -> None:
        # The same packet says the trivial passes are self-passes, not independent reviewers.
        for stage in ("spec", "plan", "step-plan", "carry-forward"):
            with self.subTest(stage=stage):
                self.assertNotIn("independent broader review", normalized(prompts.improve_prompt(stage)))


PROCEDURES = json.loads((ROOT / "test/fixtures/procedure-validity/procedures.json").read_text(encoding="utf-8"))


class _ReferenceStore:
    """The fixture's R-1, written from its text alone: the independent oracle a procedure is replayed against."""

    def __init__(self) -> None:
        self.values: dict[str, object] = {}
        self.revision = 0

    def apply(self, name: str, key: str, *value: object) -> dict[str, object]:
        """Every field any observer could show after the action: the API's value, revision and error, the page's
        status line and enabled controls."""
        found: dict[str, object] = {}
        if name == "create" and key not in self.values:
            self.values[key] = value[0]
            self.revision += 1
        elif name in ("get", "update", "delete") and key not in self.values:
            found["error"] = "NotFound"
        elif name == "get":
            found["value"] = self.values[key]
        elif name == "update":
            self.values[key] = value[0]
            self.revision += 1
            found["value"] = value[0]
        elif name == "delete":
            del self.values[key]
            self.revision += 1
        else:
            raise AssertionError("R-1 does not say what " + name + " does here")
        found.update(revision=self.revision, status=str(len(self.values)) + " keys",
                     controls=["create"] + (["update", "delete"] if self.values else []))
        return found


def replay(procedure: dict, observers: dict) -> int | None:
    """The index of the first step that cannot happen as written (the store refuses an action the step expects to
    succeed, the step expects a field its observer cannot show, or the observed value differs), else None."""
    store = _ReferenceStore()
    visible = observers[procedure["observer"]]
    for index, step in enumerate(procedure["steps"]):
        observed = store.apply(*step["action"])
        expected = step["expect"]
        if any(field not in visible for field in expected):
            return index
        if "error" in observed and "error" not in expected:
            return index
        if any(observed.get(field) != value for field, value in expected.items()):
            return index
    return None


class ProcedureFixtureTests(unittest.TestCase):
    """T25 of the implement-step fix plan (unit W2-C): three generic procedure faults, each in an automated case and an
    opt-in architecture check.  What is checked here is the deterministic part: each fault exists where the fixture says
    (replayed against an independent reference model, or run), each fixed form holds, the six-field shape gate accepts
    the faulty case (so only a review can find the fault), and the review text that owns each fault is the one every
    planning review prints.  Whether a model reviewer reading that text asks for the revision is a live qualification
    (a reviewer pilot), not something an offline fixture can prove."""

    def fault(self, ident: str) -> dict:
        return next(row for row in PROCEDURES["faults"] if row["id"] == ident)

    def test_each_replayed_fault_shows_at_its_step_and_its_fixed_form_holds(self) -> None:
        for ident in ("impossible-transition", "invisible-observation"):
            row = self.fault(ident)
            with self.subTest(fault=ident):
                self.assertEqual(replay(row["procedure"], PROCEDURES["observers"]), row["fault_at"])
                self.assertIsNone(replay(row["fixed"], PROCEDURES["observers"]))
        # The invisible observation states a true value: the API shows revision 2 there; only the page cannot.
        unseen = self.fault("invisible-observation")["procedure"]
        self.assertIsNone(replay(dict(unseen, observer="api"), PROCEDURES["observers"]))
        # The intended refusal survives the fix as its own failure case, not as a weakened product.
        self.assertEqual(self.fault("impossible-transition")["fixed"]["steps"][-1]["expect"], {"error": "NotFound"})

    def test_the_guarded_command_exits_zero_having_run_nothing_and_the_unguarded_one_fails_honestly(self) -> None:
        row = self.fault("existence-guarded-pass")
        with tempfile.TemporaryDirectory(prefix="shiploop-procedure-") as temp:
            tree = Path(temp)
            runner = tree / "run-tests"
            runner.write_text("#!/bin/sh\n: > ran\ntest -e build/app\n", encoding="utf-8")
            runner.chmod(0o755)

            def run(command: str) -> tuple[int, bool]:
                (tree / "ran").unlink(missing_ok=True)
                done = subprocess.run(["sh", "-c", command], cwd=tree, capture_output=True, text=True)
                return done.returncode, (tree / "ran").exists()

            self.assertFalse((tree / row["procedure"]["absent"]).exists())
            self.assertEqual(run(row["procedure"]["command"]), (0, False))   # exit 0, and the tests never ran
            code, ran = run(row["fixed"]["command"])
            self.assertNotEqual(code, 0)
            self.assertTrue(ran)
            (tree / "build").mkdir()
            (tree / "build/app").write_text("built\n", encoding="utf-8")
            self.assertEqual(run(row["fixed"]["command"]), (0, True))       # once the artifact exists both agree
        self.assertEqual(row["automated"]["command"], row["procedure"]["command"])
        self.assertIn("`" + row["procedure"]["command"] + "`", row["architecture"])

    def test_the_six_field_gate_accepts_each_faulty_case_and_refuses_a_procedure_key(self) -> None:
        import shiploop_expectations as expectations
        rows = [row["automated"] for row in PROCEDURES["faults"] if "oracle" in row["automated"]]
        self.assertEqual(len(rows), 2)
        self.assertEqual([sorted(row) for row in rows], [sorted(expectations.TEST_CASE_KEYS)] * 2)
        self.assertEqual(expectations.normalise_test_cases(rows), rows)      # the shape is fine: the fault is meaning
        with self.assertRaises(expectations.ExpectationError) as caught:
            expectations.normalise_test_cases([dict(rows[0], procedure={"start": "empty store"})])
        self.assertIn("needs exactly id, criterion, requirement, oracle, red, green", str(caught.exception))
        for row in PROCEDURES["faults"]:
            with self.subTest(fault=row["id"]):
                # The opt-in form is an architecture check with its own ID, never a focused case row.
                self.assertTrue(row["architecture"].startswith("### RB-"))
                self.assertNotIn(row["architecture"].split()[1], [case["id"] for case in rows])

    def test_the_review_text_that_owns_each_fault_is_in_the_planning_focus_and_the_guide(self) -> None:
        focus = normalized(prompts.PLANNING_REVIEW_FOCUS)
        guide = normalized((REFERENCES / "testing-and-documentation.md").read_text(encoding="utf-8"))
        walk = normalized(prompts.PROCEDURE_WALK)
        owners = {
            "impossible-transition": "can each action occur in the state the preceding actions leave",
            "invisible-observation": "can the chosen observer see the expected result",
            "existence-guarded-pass": "run it once and record the exit code and the cases it executes",
        }
        self.assertIn(walk, focus)
        for ident, phrase in owners.items():
            with self.subTest(fault=ident):
                self.assertIn(phrase, focus)
        for phrase in ("**Procedure validity.**", "an update after a delete expected to succeed",
                       "internal state asserted through an interface that cannot show it",
                       "`test ! -e <file> || <run the tests>`", "that exits 0 having run nothing",
                       "A stand-in probe proves a capability, not the procedure"):
            with self.subTest(guide=phrase):
                self.assertIn(phrase, guide)


class UnverifiedWordingTests(unittest.TestCase):
    """Product-acceptance states the three end states of a request outcome and where an unobserved one is listed."""

    def test_the_row_and_the_duty_name_the_list_and_the_three_end_states(self) -> None:
        sys.path.insert(0, str(SCRIPTS))
        import shiploop_stage_spec as spec
        done = normalized(" ".join(spec.stage("product-acceptance").done_when))
        self.assertIn("listed in unverified with its reason, owner and due stage", done)
        duty = normalized(prompts.DUTIES["product-acceptance"])
        for phrase in ("observed by an executed check", "observed another way", "unachievable here or not yet due",
                       "listed in `unverified`", "while the run continues", "Carry in the open items earlier stages recorded",
                       "has no end state"):
            self.assertIn(phrase, duty)
        self.assertNotIn("blocked_by", duty)  # S-14: a person-only outcome does not stop the run (blocked_by is retired)

    def test_the_skill_card_and_the_system_test_reference_say_what_the_gate_refuses_and_where_it_prints(self) -> None:
        # S-3: the card agrees with the script. The four faults are the ones the stage's Checked-by line names.
        skill = normalized((REFERENCES / "test-loop.md").read_text(encoding="utf-8"))  # moved from the card by U22
        for phrase in ("a done `product-acceptance` lists it in `unverified`",
                       "(outcome, reason, check, owner, due stage)", "`[]` says every outcome was observed",
                       "ShipLoop refuses a missing list, an incomplete or placeholder entry and a due stage that is "
                       "not a later stage", "it cannot judge that the list is complete",
                       "prints each entry at its due stage and the whole list at `handoff` and in the report"):
            self.assertIn(phrase, skill)
        reference = normalized((REFERENCES / "system-tests.md").read_text(encoding="utf-8"))
        self.assertIn("listed in its `unverified` result with the stage that reports it", reference)


if __name__ == "__main__":
    unittest.main(verbosity=2)
