#!/usr/bin/env python3
"""The Improve router, the ShipLoop route and the standalone route (ShipLoop efficiency plan, unit U18).

* skills/improve/SKILL.md is a router within a journaled byte bound; the five standalone sections moved whole to
  references/standalone-route.md; what a ShipLoop child needs from the four old sources is in the ShipLoop route: since
  2026-10-24 a core under 10,000 bytes (references/shiploop-route.md, what every child reads at every Improve stage) and five
  case files the core names with the case that opens them (live run 4 read the 47 KB route whole at each of 13 stages).
* test/improve_route_ledger.json has a row for every obligation block of those files, and every row is anchored: a block that
  gains no row, a head or route phrase that vanishes, a row with no phrase and no reason, fails here; a row whose phrase
  stands only in the long form names the core phrase that carries it for a normal pass (or why a pass needs nothing more).
* The core names every case file with its condition, each case file says when to read it, and what the core leaves to the
  handoff (the commit message rules, the notes file, the scratch directory) is in every handoff.
* The handoff ShipLoop writes opens with what a cleared child needs (the read-tool sentence, CHILD, ROUTE, the one command)
  inside 2,000 characters, and holds the focus, the commit command and the callback inside 4,500 (the real CLI path
  is 96 characters; the walk's is 8, so the bound is tested with 88 characters reserved per command).
* The review inputs that left the handoff are the route's, word for word.
"""

from pathlib import Path
import json
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "shiploop" / "scripts"
IMPROVE = ROOT / "skills" / "improve"
ROUTER = IMPROVE / "SKILL.md"
STANDALONE = IMPROVE / "references" / "standalone-route.md"
ROUTE = IMPROVE / "references" / "shiploop-route.md"
POLICY = IMPROVE / "references" / "review-policy.md"
EVIDENCE = IMPROVE / "references" / "callback-evidence.md"
ADAPTER = IMPROVE / "runtime" / "until-loop" / "ADAPTER.md"
LEDGER = ROOT / "test" / "improve_route_ledger.json"
LONG_FORM = IMPROVE / "references" / "shiploop-route-rules.md"
RECOVERY = IMPROVE / "references" / "shiploop-route-recovery.md"
ASK_AGENT_ROUTE = IMPROVE / "references" / "shiploop-route-ask-agent.md"
INPUTS = IMPROVE / "references" / "shiploop-review-inputs.md"
CORE_LIMIT = 10_000             # the core every ShipLoop child reads per Improve stage (2026-10-24)
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "test"))
from shiploop_improve_route import CASE_FILES, ROUTE_FILES, route_text  # noqa: E402
import shiploop_navigator as nav  # noqa: E402
import shiploop_prompts as prompts  # noqa: E402
import shiploop_standalone_improve as standalone  # noqa: E402

PILOT_A_BYTES = 22_000          # plan U18 exit 3: the implement handoff against pilot A's 22 KB
READ_LIMIT = 2_000              # plan U18 exit 2: the first 2,000 characters are self-sufficient
FOCUS_LIMIT = 4_500             # ... the focus ends, and the commit and complete lines sit, inside the first 4,500
# The walk prints short paths; a real install prints these lengths (the E2E render uses the same: run dir 83, CLI 96).
RUN_LENGTH, WORKTREE_LENGTH, ROUTE_LENGTH, CLI_LENGTH = 83, 95, 105, 96
KINDS = ("spec", "test-strategy", "plan", "step-plan", "test-spec", "implement", "carry-forward")   # plan U18 exit 2

FILES = {"router": ROUTER, "standalone": STANDALONE, "policy": POLICY, "evidence": EVIDENCE, "adapter": ADAPTER}


def flat(text: str) -> str:
    return " ".join(text.split())


def at_install_lengths(text: str, run: Path, repo: Path) -> str:
    """``text`` with the walk's run directory, worktree, route file and CLI written at the lengths of a normal install, so a
    position measured here is the position in a real run whatever directory this checkout and its temp files stand in."""
    def padded(prefix: str, length: int) -> str:
        return prefix[:1] + "x" * (length - 1)
    text = text.replace(str(ROUTE), padded(str(ROUTE), ROUTE_LENGTH))
    text = text.replace(str(repo), padded(str(repo), WORKTREE_LENGTH))
    text = text.replace(str(run), padded(str(run), RUN_LENGTH))
    return text.replace("python3 shiploop ", "python3 " + padded("/cli", CLI_LENGTH) + " ")


def blocks(text: str) -> list[str]:
    """The obligation blocks of a markdown file: paragraphs and list items, a code fence whole, headings left out."""
    found: list[str] = []
    current: str | None = None
    fenced = False
    for line in text.split("\n"):
        if line.startswith("```"):
            if current is not None and not fenced:
                found.append(current)
                current = None
            fenced = not fenced
            if fenced:
                current = line.strip()
            else:
                found.append((current or "") + " " + line.strip())
                current = None
            continue
        if fenced:
            current = (current or "") + " " + line.strip()
            continue
        if re.match(r"#{1,3} .+", line):
            if current is not None:
                found.append(current)
                current = None
            continue
        if not line.strip():
            if current is not None:
                found.append(current)
                current = None
            continue
        if re.match(r"(- |\d+\. |\* )", line) and current is not None:
            found.append(current)
            current = None
        current = line.strip() if current is None else current + " " + line.strip()
    if current is not None:
        found.append(current)
    return found


def head(text: str, words: int = 5) -> str:
    return " ".join(text.split()[:words])


def slug(heading: str) -> str:
    """The GitHub anchor of a heading."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    return {slug(m.group(2)) for m in re.finditer(r"(?m)^(#{1,6}) (.+?)\s*$", path.read_text(encoding="utf-8"))}


class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
        cls.route = flat(route_text())                      # the core and every case file
        cls.core = flat(ROUTE.read_text(encoding="utf-8"))
        cls.long_form = flat(LONG_FORM.read_text(encoding="utf-8"))

    def test_the_router_and_the_route_stay_within_their_journaled_bounds(self):
        bounds = self.ledger["bounds"]
        self.assertLessEqual(len(ROUTER.read_bytes()), bounds["router_bytes"])
        self.assertLessEqual(len(ROUTE.read_bytes()), bounds["route_bytes"])
        # The core is what every Improve stage reads: its bound never rises past the plan's 10,000 bytes.
        self.assertLessEqual(bounds["route_bytes"], CORE_LIMIT)
        self.assertLessEqual(sum(len(path.read_bytes()) for path in ROUTE_FILES), bounds["route_set_bytes"])
        # A bound is set from the measured text, so it cannot drift far above it unjournaled.
        self.assertLessEqual(bounds["router_bytes"] - bounds["router_measured"], 500)
        self.assertLessEqual(bounds["route_bytes"] - bounds["route_measured"], 500)
        self.assertLessEqual(bounds["route_set_bytes"] - bounds["route_set_measured"], 500)
        self.assertTrue(bounds["why"])

    def test_every_block_of_the_five_files_has_a_row_and_every_row_a_block(self):
        rows = self.ledger["rows"]
        self.assertEqual(len({row["id"] for row in rows}), len(rows), "row ids are unique")
        by_file: dict[str, dict[str, str]] = {}
        for row in rows:
            by_file.setdefault(row["file"], {})
            self.assertNotIn(row["head"], by_file[row["file"]], row["id"])
            by_file[row["file"]][row["head"]] = row["id"]
        for name, path in FILES.items():
            relative = str(path.relative_to(ROOT))
            heads = [head(block) for block in blocks(path.read_text(encoding="utf-8"))]
            self.assertEqual(len(set(heads)), len(heads), f"{relative}: two blocks open with the same five words")
            for h in heads:
                self.assertIn(h, by_file.get(relative, {}), f"{relative}: a block opening '{h}' has no ledger row")
            for h, rid in by_file.get(relative, {}).items():
                self.assertIn(h, heads, f"row {rid} names a block of {relative} that is gone ('{h}')")

    def test_every_row_is_in_the_router_carried_by_the_route_or_explains_itself(self):
        for row in self.ledger["rows"]:
            with self.subTest(row=row["id"]):
                in_router = row["file"] == str(ROUTER.relative_to(ROOT)) and not row.get("route") and not row.get("reason")
                if in_router:
                    continue
                if row.get("route"):
                    self.assertIn(flat(row["route"]), self.route, row["id"])
                else:
                    self.assertGreaterEqual(len(row.get("reason", "")), 20, row["id"])

    def test_an_obligation_only_the_long_form_states_is_carried_by_the_core(self):
        # The core is all a normal pass reads besides the handoff: a rule whose route phrase stands only in the long form
        # names the core phrase that states it, or why a normal pass needs nothing more.  A case file's rows need neither:
        # the core names the case that opens their file (CoreTests).
        carried = 0
        for row in self.ledger["rows"]:
            with self.subTest(row=row["id"]):
                if row.get("core"):
                    self.assertIn(flat(row["core"]), self.core, row["id"])
                    carried += 1
                phrase = flat(row.get("route") or "")
                if phrase and phrase in self.long_form and phrase not in self.core:
                    self.assertTrue(row.get("core") or len(row.get("long_form_only", "")) >= 20,
                                    row["id"] + ": its phrase stands only in the long form")
                elif not row.get("core"):
                    self.assertNotIn("long_form_only", row, row["id"])
        self.assertGreater(carried, 60)

    def test_the_old_card_sections_are_all_accounted_for(self):
        # SKILL.md before the split had 46 blocks (S01-S46): they stand in the router or the standalone route.
        old = [row for row in self.ledger["rows"] if row["id"].startswith("S")]
        self.assertEqual(len(old), 46)
        where = {row["file"] for row in old}
        self.assertEqual(where, {str(ROUTER.relative_to(ROOT)), str(STANDALONE.relative_to(ROOT))})
        for row in self.ledger["rows"]:
            if row["id"][0] in "RCA":
                self.assertIn(row["file"], {str(POLICY.relative_to(ROOT)), str(EVIDENCE.relative_to(ROOT)), str(ADAPTER.relative_to(ROOT))})


class RouterTests(unittest.TestCase):
    def test_the_router_routes_both_ways_and_names_the_read_tool(self):
        text = ROUTER.read_text(encoding="utf-8")
        self.assertIn("(references/shiploop-route.md)", text)
        self.assertIn("(references/standalone-route.md)", text)
        self.assertIn("## ShipLoop whole-skill subcall", text)
        self.assertIn("read that handoff file with a file-reading tool, not cat", text)
        # the five standalone sections are no longer in the router, and all are in the standalone route
        for heading in ("Standalone owner binding", "Continue after context loss", "Completion summary",
                        "Preview before execution when requested", "Execution handoff"):
            self.assertNotIn("## " + heading, text)
            self.assertIn("## " + heading, STANDALONE.read_text(encoding="utf-8"))

    def test_a_standalone_improve_reaches_every_standalone_section_through_the_router(self):
        router = ROUTER.read_text(encoding="utf-8")
        link = re.search(r"\[the standalone route\]\((references/standalone-route\.md)\)", router)
        self.assertIsNotNone(link)
        self.assertTrue((ROUTER.parent / link.group(1)).is_file())
        self.assertIn("in full before interpreting or executing", router)
        standalone_text = STANDALONE.read_text(encoding="utf-8")
        self.assertIn("Read the shared policy in full before interpreting or executing this skill.", standalone_text)
        self.assertIn("[the ShipLoop route](shiploop-route.md)", standalone_text)

    def test_every_markdown_anchor_into_the_split_files_resolves(self):
        files = [ROUTER, STANDALONE, *ROUTE_FILES, POLICY, EVIDENCE, IMPROVE / "README.md",
                 ROOT / "docs" / "improve-research.md"]
        checked = 0
        for path in files:
            for match in re.finditer(r"\]\(([^)\s]+?)(?:#([^)\s]+))?\)", path.read_text(encoding="utf-8")):
                target, anchor = match.group(1), match.group(2)
                if target.startswith(("http:", "https:", "mailto:")):
                    continue
                resolved = path if target == "" else (path.parent / target).resolve()
                if resolved not in {ROUTER, STANDALONE, *ROUTE_FILES, POLICY, EVIDENCE}:
                    continue          # only the files this split touched: other documents' anchors are not this test's
                if anchor and resolved.suffix == ".md":
                    self.assertIn(anchor, anchors(resolved), f"{path.relative_to(ROOT)} -> {target}#{anchor}")
                    checked += 1
        self.assertGreater(checked, 6)

    def test_the_route_anchors_the_navigator_prints_exist(self):
        printed = set(re.findall(r"ROUTE#([a-z][a-z_-]*[a-z])", (SCRIPTS / "shiploop_navigator.py").read_text(encoding="utf-8")))
        self.assertTrue(printed)
        self.assertLessEqual(printed, anchors(ROUTE))


class CoreTests(unittest.TestCase):
    """The core (2026-10-24): small, and it names each case file with the case that opens it."""

    def test_the_core_names_every_case_file_with_its_condition_and_each_says_when_to_read_it(self):
        core = ROUTE.read_text(encoding="utf-8")
        self.assertLessEqual(len(core.encode()), CORE_LIMIT)
        cases = core[core.index("## Cases: read only when"):]
        for path in CASE_FILES:
            with self.subTest(case=path.name):
                if path == LONG_FORM:
                    # the long form is named beside the rules it extends, for a question a rule leaves
                    self.assertIn("[long form](shiploop-route-rules.md)", core)
                    self.assertIn("only for a question a rule here leaves", flat(core))
                else:
                    self.assertRegex(cases, r"(?m)^- \[[^]]+\]\(" + re.escape(path.name) + r"\)[^\n]*:")
                text = path.read_text(encoding="utf-8")
                opening = flat(text.split("\n## ", 1)[0])
                self.assertIn("(shiploop-route.md", opening)              # it links back to the core
                self.assertRegex(opening, r"[Rr]ead (this file only when|a section only when)"
                                 r"|[Oo]pen a section below only when|[Aa] normal pass does not open this file")

    def test_a_normal_pass_needs_no_case_file(self):
        # What every pass does, from the receipt to the return, stands in the core itself.
        core = flat(ROUTE.read_text(encoding="utf-8"))
        for needed in ("the last seven reachable Git commit messages in full", "`self-review (inline default)`",
                       "Read `CHILD/packet.json`; never write it", "run its `next_argv` once", "`improve-pass`",
                       "`CHILD/reviews/review-<n>.md`", "`checks.md` first", "`improve-commit`", "never `git commit`",
                       "`classification`: `trivial` only for", "`exit`: `satisfied` only after checking every exit clause",
                       "`## Handoff`:", "**Current learnings**", "Never fabricate a record to submit `trivial`",
                       "run the handoff's callback (`complete`) only after the runtime returned `complete`",
                       "Omit `final_result` when the step result is unchanged", "Maintained requirements",
                       "changes no product code"):
            self.assertIn(flat(needed), core, needed)
        # and it sends a plain compaction back to its own first step, not to the recovery file
        self.assertIn("After a plain compaction, step 1 is the recovery.", core)


class RouteContentTests(unittest.TestCase):
    def test_the_review_inputs_are_the_prompts_fixed_text_word_for_word(self):
        inputs = flat(INPUTS.read_text(encoding="utf-8"))
        # the inline wording is the file's; the ask-agent wording is its note.  The file puts each paragraph under the
        # heading of its condition, so a paragraph, not the whole text, is the unit kept word for word.
        tail = prompts.IMPROVE_REVIEW_INPUTS_TAIL
        for delegated, inline in prompts._INLINE_IMPROVE_REPLACEMENTS:
            tail = tail.replace(delegated, inline)
        paragraphs = [part for text in (prompts.IMPROVE_REVIEW_INPUTS_HEAD, tail) for part in text.split("\n\n")
                      if part.strip()]
        self.assertEqual(len(paragraphs), 10)
        for paragraph in paragraphs:
            self.assertIn(flat(paragraph), inputs, paragraph[:60])
        self.assertIn("dispatch step's task/ready/done contract remains the sole assignment", inputs)
        # and improve_prompt is still the composition of the opening, the scope, those two texts and the stage's paragraphs
        for stage in prompts.STAGES:
            for delegation in (prompts.INLINE, prompts.ASK_AGENT):
                with self.subTest(stage=stage, delegation=delegation):
                    full = prompts.improve_prompt(stage, delegation=delegation)
                    own = prompts.improve_stage_prompt(stage, delegation=delegation)
                    self.assertTrue(own.startswith("Invoke the selected actual Improve skill for "))
                    for paragraph in own.split("\n\n")[1:]:
                        self.assertIn(paragraph.strip(), full)
                    self.assertNotIn(flat(prompts.IMPROVE_REVIEW_INPUTS_TAIL[:200]), flat(own))
                    self.assertLess(len(own), len(full) // 2)

    def test_the_handoff_texts_that_moved_here_are_in_the_route(self):
        # verbatim prefixes of both routes, from the constants that used to print them in every handoff: the inline one in
        # the recovery file, the ask-agent one in its own file
        self.assertIn(flat(prompts.INLINE_IMPROVE_CONTEXT.strip()), flat(RECOVERY.read_text(encoding="utf-8")))
        self.assertIn(flat(prompts.IMPROVE_INNER_CONTEXT.strip()), flat(ASK_AGENT_ROUTE.read_text(encoding="utf-8")))


class HandoffTests(unittest.TestCase):
    """The seven handoff kinds of the plan (and the two outer stages), on both routes."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="improve-route-walk-")
        repo = Path(cls.temp.name).resolve() / "repo"
        repo.mkdir()
        cls.selected = standalone.resolve_skill(str(ROUTER))
        cls.walks = {route: cls.walk(repo, route) for route in (prompts.INLINE, prompts.ASK_AGENT)}
        cls.runs = {route: Path(repo).parent / ("run-" + route) for route in cls.walks}
        cls.repo = repo
        cls.sized = {route: {stage: at_install_lengths(text, cls.runs[route], repo) for stage, text in handoffs.items()}
                     for route, handoffs in cls.walks.items()}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @classmethod
    def walk(cls, repo: Path, delegation: str) -> dict[str, str]:
        state = nav.new_state(str(repo), "Synthetic route walk.", delegation=delegation)
        run = Path(repo).parent / ("run-" + delegation)
        run.mkdir()
        handoffs: dict[str, str] = {}
        while state["status"] == "active":
            stage = nav.current_stage(state)
            action = nav.current_action(state)["id"]
            result = {"outcome": "done", "summary": "Synthetic " + stage + " declaration."}
            if stage == "plan":
                result["work_items"] = [{"id": "W1", "title": "Synthetic item"}]
            if stage == "step-plan" and delegation == prompts.ASK_AGENT:
                # one ask-agent implement action builds every step, so its review focus names them: the longest focus there is
                result.update(steps=[{"id": "S1", "task": "Make change one.", "paths": ["a.py"]},
                                     {"id": "S2", "task": "Make change two.", "paths": ["pkg/b.py"]}],
                              paths=["a.py", "pkg/b.py"])
            state = nav.apply(state, action, result)
            child = state.get("active_improve")
            if child is not None:
                state["active_improve"] = standalone.binding(state, action, child["stage"], child["seed_result"],
                                                             cls.selected, improve_action=child["improve_action"])
                receipt = standalone.receipt_path(state["active_improve"])
                receipt.parent.mkdir(parents=True, exist_ok=True)
                receipt.write_text("{}", encoding="utf-8")
                handoffs[stage] = nav.improve_handoff_text(None, run, state)
                state["active_improve"] = child
                state = nav.finish_improve(state, action, {"summary": "Synthetic receipt; no review claim."})
        return handoffs

    def test_the_seven_kinds_are_all_rendered(self):
        for route, handoffs in self.walks.items():
            self.assertTrue(set(KINDS) <= set(handoffs), (route, sorted(handoffs)))

    def test_the_first_2000_characters_hold_the_read_sentence_child_route_and_the_one_command(self):
        for route, handoffs in self.sized.items():
            for stage, text in handoffs.items():
                with self.subTest(route=route, stage=stage):
                    first = text[:READ_LIMIT]
                    self.assertIn(nav.IMPROVE_READ_SENTENCE, first)
                    self.assertIn("a shell cuts a long file", first)
                    child_dir = re.search(r"(?m)^CHILD = (\S+) · ROUTE = (\S+) · Route: (\S+)$", first)
                    self.assertIsNotNone(child_dir, first)
                    self.assertEqual(child_dir.group(3), route)
                    self.assertTrue(Path(self.walks[route][stage].split(" · ROUTE = ")[1].split(" · ")[0]).is_file())
                    self.assertTrue(self.walks[route][stage].split(" · ROUTE = ")[1].split(" · ")[0].endswith("references/shiploop-route.md"))
                    self.assertRegex(Path(re.search(r"(?m)^CHILD = (\S+)", self.walks[route][stage]).group(1)).name,
                                     r"^" + re.escape(stage) + r"-[0-9a-f]{8}$")
                    self.assertRegex(first, r" complete --run-dir=")                         # the one command to finish
                    self.assertIn("Open ROUTE once per context", first)                    # when a cleared child opens the route
                    self.assertIn("this file leaves them out", first)

    def test_the_focus_ends_and_the_commit_and_complete_lines_sit_inside_the_first_4500(self):
        for route, handoffs in self.sized.items():
            for stage, text in handoffs.items():
                with self.subTest(route=route, stage=stage):
                    focus = text.index("## What this review looks for")
                    commit = text.index("## Commit")
                    self.assertGreater(focus, text.index("Open ROUTE once per context"))   # the focus follows the top block
                    self.assertLess(commit, FOCUS_LIMIT)                                    # the focus ends before char 4,500
                    commit_end = text.index("\n", text.index("improve-commit", commit))
                    self.assertLess(commit_end, FOCUS_LIMIT)                                # the improve-commit line ends inside it
                    complete = text.index(" complete --run-dir=")
                    self.assertLess(complete, READ_LIMIT)
                    self.assertLess(text.index("\n", complete), FOCUS_LIMIT)
                    # the focus is the stage's own, and Code craft stays verbatim beside the action
                    body = text[focus:commit]
                    if stage == "carry-forward":
                        self.assertIn(prompts.END_REVIEW_FOCUS_HEAD.strip(), body)
                    elif stage == "implement":
                        self.assertIn("Implementation step review focus.", body)
                    else:
                        self.assertIn(prompts.PLANNING_REVIEW_FOCUS.strip(), body)
                    if stage in ("implement", "carry-forward"):
                        self.assertIn("## Code craft\n" + prompts.CODE_CRAFT.rstrip(), text)

    def test_what_is_the_same_in_every_review_left_the_handoff_for_the_route(self):
        for route, handoffs in self.walks.items():
            for stage, text in handoffs.items():
                with self.subTest(route=route, stage=stage):
                    self.assertNotIn(flat(prompts.IMPROVE_REVIEW_INPUTS_HEAD[:160]), flat(text))
                    for moved in ("Delegation: inline.", "Keep the invoking parent alive", "Parent assignment preparation",
                                  "Binding inputs: before dispatch", "Completion deletes the child's temporary state",
                                  "Terminal recovery uses the retained raw packet", "The prior result and relevant accepted",
                                  "Do not register all scratch output"):
                        self.assertNotIn(moved, text)
                    # what stays beside the action: the per-run facts and the exact commands
                    for kept in ("Selected Improve skill: ", "Child workspace: ", "Optional, for later steps: lessons in",
                                 "Pause parent without losing child: python3 shiploop pause --run-dir=",
                                 "--restart-stopped"):
                        self.assertIn(kept, text)
                    # The request whole where the reviewed stage quotes it (owner decision D2, 2026-10-17), else its file.
                    whole = stage in nav.REQUEST_WHOLE_STAGES
                    self.assertEqual("Original request (preserve user scope" in text, whole)
                    self.assertEqual(nav.REQUEST_POINTER in text, not whole)

    def test_what_the_core_leaves_to_the_handoff_is_in_every_handoff(self):
        # The core says the commit message rules are in the handoff (plan stage: parent-return.md, which its start writes).
        for route, handoffs in self.walks.items():
            for stage, text in handoffs.items():
                with self.subTest(route=route, stage=stage):
                    if stage == "plan":
                        self.assertIn("run the improve-commit command in CHILD/parent-return.md; its message rules are "
                                      "there", text)
                    else:
                        self.assertIn("`Key learnings: <what this iteration taught", text)
                        self.assertIn("`Learned-from: <commit id> <what it contributed>`", text)
                        self.assertIn("`Remote change: <system alias>", text)
                    self.assertIn("Optional, for later steps: lessons in", text)       # complete --notes
                    self.assertIn("Scratch directory (your temporary files, not /tmp)", text)
                    self.assertIn("short core has every pass's rules", text)       # the top line says what ROUTE is

    def test_the_implement_handoff_is_within_pilot_a(self):
        for route, handoffs in self.walks.items():
            with self.subTest(route=route):
                self.assertLessEqual(len(handoffs["implement"].encode()), PILOT_A_BYTES)
                self.assertLess(len(handoffs["implement"]), 0.7 * 33_329)       # was 33,329 on the same walk (inline)

    def test_the_ask_agent_walk_reviews_the_aggregate_steps(self):
        text = self.walks[prompts.ASK_AGENT]["implement"]
        self.assertIn("steps S1 to S2", text)               # so the bounds above hold for the longest focus
        self.assertNotIn("steps S1 to S2", self.walks[prompts.INLINE]["implement"])

    def test_the_review_directory_is_short_and_per_action(self):
        # the Improve packet prints the handoff path; the child directory in it is the stage and 8 characters
        for route, handoffs in self.walks.items():
            for stage, text in handoffs.items():
                child_dir = re.search(r"(?m)^CHILD = (\S+)", text).group(1)
                self.assertLess(len(Path(child_dir).name), 32, child_dir)     # system-test-author-502306e5 is the longest
                self.assertEqual(Path(child_dir).parent.name, ".shiploop-improve", child_dir)
        names = {re.search(r"(?m)^CHILD = (\S+)", text).group(1) for handoffs in self.walks.values() for text in handoffs.values()}
        self.assertEqual(len(names), 18, "nine handoffs on each route, no two sharing a child directory")


if __name__ == "__main__":
    unittest.main()
