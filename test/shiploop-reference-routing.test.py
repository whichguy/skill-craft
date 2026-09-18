#!/usr/bin/env python3
"""Regression tests for ShipLoop's real reference routing."""

from __future__ import annotations

import copy
from pathlib import Path
import re
import runpy
import shutil
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
REF_DIR = SCRIPTS.parent / "references"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_packets as packets  # noqa: E402
import shiploop_protocol as protocol  # noqa: E402


READ_ONLY = ": read only "
OPTIONAL_REFERENCE = "Reference (optional; "
NORMATIVE_GUIDE_ROOTS = (
    Path("SKILL.md"),
    Path("README.md"),
    Path("references/project-knowledge.md"),
    Path("references/requirements-definition.md"),
    Path("references/navigator.md"),
    Path("references/backchain-planning.md"),
    Path("references/testing-and-documentation.md"),
)
HISTORICAL_ARTIFACT_DIRECTORIES = frozenset({".shiploop", "experiments", "reports"})
FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$")
HTML_ID_RE = re.compile(
    r"<[^>]+\bid\s*=\s*(?:\"(?P<double>[^\"]+)\"|'(?P<single>[^']+)'|(?P<bare>[^\s>]+))",
    re.IGNORECASE,
)
MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[[^\]\n]+\]\(\s*(?P<target><[^>\n]+>|[^)\s]+)"
    r"(?:\s+['\"][^)]*['\"])?\s*\)"
)


def heading_anchor(text: str) -> str:
    """Match GitHub-style anchors from rendered Markdown heading text."""
    value = text.strip().lower()
    value = re.sub(r"\s+#+\s*$", "", value)
    value = re.sub(r"!?\[([^\]]*)\]\([^)]+\)", r"\1", value)
    value = re.sub(r"<[^>]*>", "", value)
    value = re.sub(r"\\([\\`*{}\[\]()#+\-.!_>])", r"\1", value)
    value = re.sub(r"[^\w\s-]", "", value)
    return re.sub(r"\s", "-", value).strip("-")


def active_markdown_lines(text: str) -> list[tuple[int, str]]:
    """Return Markdown lines outside fenced examples, which do not create links."""
    lines: list[tuple[int, str]] = []
    fence: str | None = None
    for number, line in enumerate(text.splitlines(), start=1):
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is None:
            lines.append((number, line))
    return lines


def markdown_heading_anchors(path: Path) -> set[str]:
    """Build heading IDs plus explicit HTML anchor aliases in one guide."""
    occurrences: dict[str, int] = {}
    anchors: set[str] = set()
    for _number, line in active_markdown_lines(path.read_text(encoding="utf-8")):
        for explicit_anchor in HTML_ID_RE.finditer(line):
            anchors.add(next(value for value in explicit_anchor.groups() if value is not None))
        match = HEADING_RE.match(line)
        if not match:
            continue
        base = heading_anchor(match.group(2))
        occurrence = occurrences.get(base, 0)
        occurrences[base] = occurrence + 1
        anchors.add(base if occurrence == 0 else f"{base}-{occurrence}")
    return anchors


class ReferenceRoutingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.core = SimpleNamespace(
            VERSION="test",
            PACKAGE_ROOT=SCRIPTS.parent,
            REF_DIR=REF_DIR,
            __file__=str(CLI),
        )

    def assert_reference_resolves(self, path: Path, anchor: str) -> None:
        """Check an emitted package filename and anchor against the actual Markdown."""
        self.assertTrue(path.is_file(), f"reference file is absent: {path}")
        self.assertFalse(path.is_symlink(), f"reference file must be package-owned: {path}")
        try:
            path.resolve().relative_to(REF_DIR.resolve())
        except ValueError as exc:
            self.fail(f"reference escapes package references: {path} ({exc})")
        headings = markdown_heading_anchors(path)
        self.assertIn(anchor, headings, f"missing #{anchor} heading in {path}")

    def local_markdown_links(self, source: Path) -> list[tuple[int, str, str, str]]:
        """Extract active package-local Markdown-document links from one guide."""
        links: list[tuple[int, str, str, str]] = []
        for line_number, line in active_markdown_lines(source.read_text(encoding="utf-8")):
            for match in MARKDOWN_LINK_RE.finditer(line):
                raw_target = match.group("target").strip()
                if raw_target.startswith("<") and raw_target.endswith(">"):
                    raw_target = raw_target[1:-1]
                parsed = urlsplit(raw_target)
                if parsed.scheme or parsed.netloc:
                    continue
                relative_path = unquote(parsed.path)
                fragment = unquote(parsed.fragment)
                if relative_path and Path(relative_path).suffix.lower() != ".md":
                    continue
                if relative_path or fragment:
                    links.append((line_number, raw_target, relative_path, fragment))
        return links

    def assert_normative_markdown_graph(self, package_root: Path) -> set[Path]:
        """Walk the bounded package-owned guide graph and validate each destination."""
        package_root = package_root.resolve()
        pending = [package_root / relative for relative in NORMATIVE_GUIDE_ROOTS]
        visited: set[Path] = set()

        while pending:
            source = pending.pop().resolve()
            if source in visited:
                continue
            relative_source = source.relative_to(package_root)
            self.assertTrue(
                source.is_file(),
                f"normative ShipLoop guide is absent: {relative_source}",
            )
            visited.add(source)

            for line_number, raw_target, raw_path, fragment in self.local_markdown_links(source):
                destination = (source.parent / raw_path).resolve() if raw_path else source
                with self.subTest(
                    source=f"{relative_source}:{line_number}",
                    target=raw_target,
                ):
                    try:
                        relative_destination = destination.relative_to(package_root)
                    except ValueError as exc:
                        self.fail(
                            "local Markdown link escapes ShipLoop package: "
                            f"{relative_source}:{line_number} -> {raw_target} ({exc})"
                        )
                    if any(
                        directory in HISTORICAL_ARTIFACT_DIRECTORIES
                        for directory in relative_destination.parts
                    ):
                        continue
                    self.assertTrue(
                        destination.is_file(),
                        "local Markdown destination is absent: "
                        f"{relative_source}:{line_number} -> {relative_destination}",
                    )
                    if fragment:
                        self.assertIn(
                            fragment,
                            markdown_heading_anchors(destination),
                            "local Markdown fragment is absent: "
                            f"{relative_source}:{line_number} -> "
                            f"{relative_destination}#{fragment}",
                        )
                    if destination not in visited:
                        pending.append(destination)

        return {path.relative_to(package_root) for path in visited}

    def guidance_references(self, stage: str) -> list[tuple[Path, str, str]]:
        """Parse both direct and shared-``Guidance directory`` packet forms."""
        shared_directory: Path | None = None
        references: list[tuple[Path, str, str]] = []
        lines = packets._guidance_lines(self.core, stage, vars(protocol))
        for line in lines:
            if line.startswith("Guidance directory: "):
                raw_directory = line.removeprefix("Guidance directory: ").split(" (", 1)[0]
                shared_directory = Path(raw_directory)
                self.assertEqual(shared_directory.resolve(), REF_DIR.resolve())
                continue
            if READ_ONLY not in line:
                continue
            _label, rendered = line.split(READ_ONLY, 1)
            parts = [part.strip() for part in rendered.split(",")]
            first_path, separator, first_anchor = parts[0].partition("#")
            self.assertEqual(separator, "#", f"guidance lacks an anchor: {line}")
            candidate = Path(first_path)
            if not candidate.is_absolute():
                self.assertIsNotNone(
                    shared_directory,
                    f"relative guidance needs an announced directory: {line}",
                )
                assert shared_directory is not None
                candidate = shared_directory / candidate
            anchors = [first_anchor]
            for continuation in parts[1:]:
                self.assertTrue(
                    continuation.startswith("#"),
                    f"guidance continuation is not an anchor: {line}",
                )
                anchors.append(continuation.removeprefix("#"))
            for anchor in anchors:
                self.assertTrue(anchor, f"guidance has an empty anchor: {line}")
                references.append((candidate, anchor, line))
        return references

    def optional_reference(self, lines: list[str]) -> tuple[Path, str]:
        line = next((line for line in lines if line.startswith(OPTIONAL_REFERENCE)), None)
        self.assertIsNotNone(line, f"missing optional reference in: {lines}")
        assert line is not None
        path_and_anchor = line.split(": ", 1)[1]
        raw_path, separator, anchor = path_and_anchor.rpartition("#")
        self.assertEqual(separator, "#", f"optional reference lacks an anchor: {line}")
        self.assertTrue(raw_path, f"optional reference lacks a path: {line}")
        self.assertTrue(anchor, f"optional reference lacks an anchor: {line}")
        return Path(raw_path), anchor

    def assert_optional_reference(self, lines: list[str], filename: str, anchor: str) -> None:
        path, actual_anchor = self.optional_reference(lines)
        self.assertEqual(path, REF_DIR / filename)
        self.assertEqual(actual_anchor, anchor)
        self.assert_reference_resolves(path, actual_anchor)

    def test_every_prompt_stage_routes_to_existing_package_reference_heading(self) -> None:
        for stage in protocol.PROMPTS:
            with self.subTest(stage=stage):
                references = self.guidance_references(stage)
                self.assertTrue(
                    references,
                    f"{stage} must select at least one package reference",
                )
                for path, anchor, _line in references:
                    self.assert_reference_resolves(path, anchor)

    def test_every_prompt_stage_routes_to_maintained_requirements_handoffs(self) -> None:
        expected = (
            REF_DIR / "project-knowledge.md",
            "reference-handoffs-and-destinations",
        )
        for stage in protocol.PROMPTS:
            with self.subTest(stage=stage):
                selected = {
                    (path, anchor)
                    for path, anchor, _line in self.guidance_references(stage)
                }
                self.assertIn(
                    expected,
                    selected,
                    f"{stage} must route maintained-requirements handoffs",
                )
                self.assert_reference_resolves(*expected)

    def test_merge_and_coverage_are_the_only_activity_specific_routes(self) -> None:
        routes = {
            stage: self.guidance_references(stage) for stage in protocol.PROMPTS
        }
        expected = {
            "merge": (REF_DIR / "activities" / "implement.md", "merge-and-recovery"),
            "coverage": (REF_DIR / "activities" / "residual.md", "coverage"),
        }
        for stage, target in expected.items():
            with self.subTest(required_stage=stage):
                selected = {(path, anchor) for path, anchor, _line in routes[stage]}
                self.assertIn(target, selected)
                self.assertTrue(
                    any(
                        READ_ONLY in line and path == target[0] and anchor == target[1]
                        for path, anchor, line in routes[stage]
                    ),
                    f"{stage} must retain the packet's read only reference form",
                )
                self.assert_reference_resolves(*target)

        targets = set(expected.values())
        for stage, references in routes.items():
            if stage in expected:
                continue
            with self.subTest(unrelated_stage=stage):
                selected = {(path, anchor) for path, anchor, _line in references}
                self.assertFalse(
                    selected & targets,
                    f"{stage} must not inherit merge/coverage activity routing",
                )

    def test_safe_orientation_uses_real_optional_references_without_reading_state(self) -> None:
        cases = (
            ("done", "certified completion", "report.md", "content-and-boundaries"),
            ("done", "report certification is incomplete", "report.md", "content-and-boundaries"),
            ("halted", "halted unfinished", "report.md", "content-and-boundaries"),
            ("schedule", "waiting to allocate a dependency-ready step", "turn-packet.md", "action-use"),
            ("preflight", "paused before completion", "turn-packet.md", "action-use"),
            ("unknown", "blocked before assignment", "turn-packet.md", "action-use"),
        )
        for stage, note, filename, anchor in cases:
            with self.subTest(stage=stage, note=note):
                state = {
                    "phase": "damaged",
                    "stage": stage,
                    "prompt": "Restore a bounded ShipLoop fixture.",
                }
                before = copy.deepcopy(state)
                with patch.object(
                    Path,
                    "read_text",
                    side_effect=AssertionError("safe orientation must not read damaged state"),
                ):
                    lines = packets._safe_orientation_lines(
                        self.core,
                        Path("/missing/damaged-run"),
                        state,
                        "current-action",
                        state_note=note,
                    )
                self.assertEqual(state, before)
                self.assert_optional_reference(lines, filename, anchor)
                self.assertNotIn("Call this when done:", "\n".join(lines))

    def test_new_activity_guides_have_resolvable_local_links(self) -> None:
        for filename in ("activities/implement.md", "activities/residual.md"):
            guide = REF_DIR / filename
            for target in re.findall(r"\]\(([^)]+)\)", guide.read_text(encoding="utf-8")):
                if "://" in target:
                    continue
                with self.subTest(guide=filename, target=target):
                    relative, _, anchor = target.partition("#")
                    destination = (guide.parent / relative).resolve() if relative else guide
                    destination.relative_to(SCRIPTS.parent.resolve())
                    self.assertTrue(destination.is_file(), target)
                    if anchor:
                        headings = {
                            heading_anchor(match.group(2))
                            for match in re.finditer(
                                r"(?m)^(#{1,6})\s+(.+?)\s*$",
                                destination.read_text(encoding="utf-8"),
                            )
                        }
                        self.assertIn(anchor, headings, target)

    def test_maintained_requirements_guides_keep_package_local_links_when_relocated(self) -> None:
        source_graph = self.assert_normative_markdown_graph(SCRIPTS.parent)
        with tempfile.TemporaryDirectory(prefix="shiploop-reference-graph-") as raw:
            relocated_package = Path(raw) / "relocated" / "shiploop"
            shutil.copytree(SCRIPTS.parent, relocated_package)
            relocated_graph = self.assert_normative_markdown_graph(relocated_package)
        self.assertEqual(source_graph, relocated_graph)

    def test_normative_markdown_graph_rejects_missing_links_and_keeps_explicit_aliases(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-reference-graph-fixture-") as raw:
            package_root = Path(raw) / "shiploop"
            references = package_root / "references"
            references.mkdir(parents=True)
            readme = package_root / "README.md"
            readme.write_text(
                "# Root\n\n"
                '<a id="legacy-alias"></a>\n\n'
                "[alias](#legacy-alias)\n"
                "[formatted](#p1--frame)\n\n"
                "## P1 — Frame\n\n"
                "[child](references/child.md#child)\n",
                encoding="utf-8",
            )
            (references / "child.md").write_text("# Child\n", encoding="utf-8")

            with patch.object(
                sys.modules[__name__],
                "NORMATIVE_GUIDE_ROOTS",
                (Path("README.md"),),
            ):
                self.assertEqual(
                    self.assert_normative_markdown_graph(package_root),
                    {Path("README.md"), Path("references/child.md")},
                )

                readme.write_text(
                    "# Root\n[missing](references/missing.md)\n",
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    AssertionError,
                    r"local Markdown destination is absent: README\.md:2 -> references/missing\.md",
                ):
                    ReferenceRoutingTests().assert_normative_markdown_graph(package_root)

                readme.write_text("# Root\n[missing](#absent)\n", encoding="utf-8")
                with self.assertRaisesRegex(
                    AssertionError,
                    r"local Markdown fragment is absent: README\.md:2 -> README\.md#absent",
                ):
                    ReferenceRoutingTests().assert_normative_markdown_graph(package_root)

    def test_damaged_packets_and_supporting_responses_remain_non_advancing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="shiploop-reference-routing-") as raw:
            run_dir = Path(raw) / ".shiploop"
            state = {
                "phase": "implement",
                "stage": "review",
                "revision": 3,
                "action": {"id": "review-damaged"},
                "prompt": "Inspect the bounded fixture.",
                "paused": "durable context is damaged",
            }
            before = copy.deepcopy(state)
            calls: list[str] = []

            def repo_for(_root, _state):
                calls.append("repo_for")
                return "/unavailable-worktree"

            with (
                patch.object(
                    packets,
                    "_step_info",
                    side_effect=AssertionError("paused packet must not read step context"),
                ),
                patch.object(
                    Path,
                    "read_text",
                    side_effect=AssertionError("paused packet must not read damaged files"),
                ),
            ):
                packet = packets.render(
                    self.core,
                    run_dir,
                    state,
                    {"repo_for": repo_for},
                )
            self.assertEqual(calls, ["repo_for"])
            self.assertEqual(state, before)
            self.assertIn("No completion callback is valid while paused.", packet)
            self.assertNotIn("Call this when done:", packet)
            self.assert_optional_reference(
                packet.splitlines(), "turn-packet.md", "action-use"
            )

        supporting = protocol.supporting_response_lines(
            self.core,
            Path("/missing/damaged-run"),
            {
                "phase": "implement",
                "stage": "review",
                "action": {"id": "review-damaged"},
            },
            response="Git history evidence",
            scope="the requested Git-history page",
        )
        self.assert_optional_reference(
            list(supporting), "turn-packet.md", "action-use"
        )
        self.assertIn(
            "does not assign a new action or advance the workflow",
            "\n".join(supporting),
        )
        self.assertNotIn("Call this when done:", "\n".join(supporting))

        fixture_class = runpy.run_path(
            str(ROOT / "test" / "shiploop-packets.test.py")
        )["PacketTests"]
        fixture = fixture_class()
        fixture.setUp()
        self.addCleanup(fixture.tearDown)
        fixture.cli(
            "init",
            "--repo",
            str(fixture.repo),
            "--run-dir",
            str(fixture.run_dir),
            "--prompt=Inspect a bounded fixture.",
        )
        state_before = (fixture.run_dir / "state.md").read_bytes()
        context = fixture.cli("context", "--section", "prompt").stdout
        self.assert_optional_reference(
            context.splitlines(), "turn-packet.md", "action-use"
        )
        self.assertIn("does not assign a new action", context)
        self.assertEqual((fixture.run_dir / "state.md").read_bytes(), state_before)

        action_id = fixture.state()["action"]["id"]
        rejected = fixture.cli(
            "done",
            "--action",
            action_id,
            "--result",
            fixture.result("invalid-preflight.md", {"summary": "Baseline omitted."}),
            code=2,
        )
        self.assert_optional_reference(
            rejected.stderr.splitlines(), "turn-packet.md", "action-use"
        )
        self.assertNotIn("Call this when done:", rejected.stderr)
        self.assertEqual((fixture.run_dir / "state.md").read_bytes(), state_before)


if __name__ == "__main__":
    unittest.main(verbosity=2)
