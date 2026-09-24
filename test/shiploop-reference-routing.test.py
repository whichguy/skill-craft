#!/usr/bin/env python3
"""Regression tests for ShipLoop's real reference routing."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
CLI = SCRIPTS / "shiploop"
REF_DIR = SCRIPTS.parent / "references"
IMPROVE_CARD = ROOT / "skills" / "improve" / "SKILL.md"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import shiploop_navigator as navigator  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402


NORMATIVE_GUIDE_ROOTS = (
    Path("SKILL.md"),
    Path("README.md"),
    Path("references/project-knowledge.md"),
    Path("references/requirements-definition.md"),
    Path("references/navigator.md"),
    Path("references/backchain-planning.md"),
    Path("references/testing-and-documentation.md"),
    Path("references/repeatable-test-suites.md"),
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
CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
# A package-relative file name as guides spell it, optionally repo-qualified.
PACKAGE_FILE_NAME_RE = re.compile(
    r"(?<![\w./-])(?:skills/shiploop/)?"
    r"((?:references/[\w./-]+?\.(?:md|json))|(?:scripts/[\w.-]+\.py))(?![\w.-])"
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

    def test_every_v3_v4_packet_locator_resolves_to_a_package_reference_heading(self) -> None:
        """Every reference locator a navigator packet prints names a real file and heading."""
        reference_dir = REF_DIR.resolve()
        locator = re.compile(re.escape(str(reference_dir))
                             + r"/([\w./-]+?\.(?:md|json))(?:#([\w-]+))?")
        selected = standalone.resolve_skill(str(IMPROVE_CARD))
        packets: list[str] = []
        with tempfile.TemporaryDirectory(prefix="shiploop-locator-walk-") as raw:
            repo = Path(raw).resolve() / "repo"
            run = Path(raw).resolve() / "run"
            repo.mkdir()
            run.mkdir()
            for delegation in ("inline", "ask-agent"):
                state = navigator.new_state(str(repo), "Walk every packet locator.",
                                            delegation=delegation)
                for command in ("pause", "halt"):
                    packets.append(navigator.render(
                        None, run, navigator.control(state, command, "Synthetic stop.")))
                while state["status"] == "active":
                    stage = navigator.current_stage(state)
                    action = navigator.current_action(state)["id"]
                    packets.append(navigator.render(None, run, state))
                    payload = {"outcome": "done", "summary": "Synthetic " + stage + "."}
                    if stage == "plan":
                        payload["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
                    state = navigator.apply(state, action, payload)
                    child = state.get("active_improve")
                    if child is None:
                        continue
                    packets.append(navigator.render(None, run, state))
                    bound = dict(state, active_improve=standalone.binding(
                        state, action, child["stage"], child["seed_result"], selected))
                    packets.append(navigator.render(None, run, bound))
                    state = navigator.finish_improve(
                        state, action, {"summary": "Synthetic receipt; no review claim."})
                packets.append(navigator.render(None, run, state))
        seen = {(match.group(1), match.group(2)) for packet in packets
                for match in locator.finditer(packet)}
        for relative, anchor in sorted(seen, key=lambda item: (item[0], item[1] or "")):
            with self.subTest(reference=relative, anchor=anchor):
                if anchor:
                    self.assert_reference_resolves(reference_dir / relative, anchor)
                else:
                    self.assertTrue((reference_dir / relative).is_file(), relative)
        # Locators hard-coded outside the stage catalog are part of the walk.
        for expected in (
            ("navigator.md", "sdlc-responsibilities"),
            ("research-loop.md", "early-access-readiness"),
            ("research-loop.md", "recursive-discovery-and-experiments"),
            ("research-loop.md", "navigator-execution-mode-adapter"),
            ("execution-planning.md", "initial-repository-baseline"),
            ("improve-context.md", "default-route-the-parent-runs-improve-delegation-inline"),
            ("planning-experiments.md", None),
        ):
            self.assertIn(expected, seen)

    def test_normative_guides_name_only_existing_package_files(self) -> None:
        """Linked or backticked package file names must not outlive their files.

        A name missing from ShipLoop may still belong to a skill package this
        repository carries (for example Until Loop's runtime) or to the
        repository's own scripts; a deleted ShipLoop file exists nowhere.
        """
        package = SCRIPTS.parent.resolve()
        guides = [package / "SKILL.md", package / "README.md",
                  *sorted((package / "commands").glob("*.md")),
                  *sorted((package / "references").rglob("*.md"))]

        def exists(name: str) -> bool:
            candidates = [package / name, ROOT / name,
                          *ROOT.glob("skills/*/" + name), *ROOT.glob("skills/*/runtime/*/" + name),
                          *ROOT.glob("bundles/*/skills/*/" + name)]
            return any(candidate.is_file() for candidate in candidates)

        missing: list[str] = []
        for guide in guides:
            relative_guide = guide.relative_to(package)
            for line_number, line in active_markdown_lines(guide.read_text(encoding="utf-8")):
                targets = [match.group("target").strip("<>") for match in MARKDOWN_LINK_RE.finditer(line)]
                for target in targets:
                    parsed = urlsplit(target)
                    path = unquote(parsed.path)
                    if (parsed.scheme or parsed.netloc or not path
                            or Path(path).suffix.lower() not in (".md", ".json", ".py")):
                        continue
                    destination = (guide.parent / path).resolve()
                    try:
                        inside = destination.relative_to(package)
                    except ValueError:
                        continue
                    if (not any(part in HISTORICAL_ARTIFACT_DIRECTORIES for part in inside.parts)
                            and not destination.is_file()):
                        missing.append(f"{relative_guide}:{line_number} links {target}")
                for span in targets + CODE_SPAN_RE.findall(line):
                    for match in PACKAGE_FILE_NAME_RE.finditer(span):
                        if not exists(match.group(1)):
                            missing.append(f"{relative_guide}:{line_number} names {match.group(1)}")
        self.assertEqual(missing, [])

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
