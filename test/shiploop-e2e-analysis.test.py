"""ShipLoop E2E tests grouped by responsibility."""
from __future__ import annotations

import importlib as _component_importlib
import pathlib as _component_pathlib
import sys as _component_sys

_component_test_dir = str(_component_pathlib.Path(__file__).resolve().parent)
if _component_test_dir not in _component_sys.path:
    _component_sys.path.insert(0, _component_test_dir)
_support = _component_importlib.import_module("shiploop-e2e-support")
globals().update({name: value for name, value in vars(_support).items()
                  if not name.startswith("__") and name not in {"_tests_from_namespace", "_tests_from_modules"}})


def load_tests(loader, standard_tests, pattern):
    return _support._tests_from_namespace(loader, __name__, globals(), pattern)




class ImproveReviewsMetricTest(unittest.TestCase):
    def test_counts_review_passes_per_child_and_the_time_they_span(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            one = Path(temp) / "worktree" / ".shiploop-improve" / "nav-a" / "nav-1" / "reviews"
            two = Path(temp) / "worktree" / ".shiploop-improve" / "nav-a" / "nav-2" / "reviews"
            for reviews, count in ((one, 3), (two, 1)):
                reviews.mkdir(parents=True)
                for n in range(1, count + 1):
                    note = reviews / f"review-{n}.md"
                    note.write_text("x" * 10)
                    os.utime(note, (1000 + 60 * n, 1000 + 60 * n))
            got = metrics.improve_reviews(run_dir)
            self.assertEqual((got["children"], got["passes"], got["max_passes"]), (2, 4, 3))
            self.assertEqual([(c["passes"], c["seconds"], c["bytes"]) for c in got["per_child"]],
                             [(3, 120.0, 30), (1, 0.0, 10)])

    def test_a_review_folder_one_level_down_is_read_as_the_runs_write_it(self):
        """Runs 3, 4 and 5 keep .shiploop-improve/<stage>-<id>/reviews; the reader saw 0 children until 2026-10-25."""
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            for child, count in (("spec-1d6d2aa8", 3), ("implement-0d7e1c02", 2)):
                reviews = Path(temp) / "worktree" / ".shiploop-improve" / child / "reviews"
                reviews.mkdir(parents=True)
                for n in range(1, count + 1):
                    (reviews / f"review-{n}.md").write_text("x")
            got = metrics.improve_reviews(run_dir)
            self.assertEqual((got["children"], got["passes"], got["max_passes"]), (2, 5, 3))

    def test_a_result_only_edit_counts_as_an_edited_review_and_a_one_pass_review_is_timed_from_its_bind(self):
        """Advisors panel 2026-10-25: a test spec's result lies outside the tree, so a tree-only count read 0 of 9 test-spec
        reviews as edited (5 of 9 had edited their result); and a one-pass review measured first note to last note: 0 s."""
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            (run_dir / "improve").mkdir(parents=True)
            bind = run_dir / "improve" / "nav-aaaa1111-bind.md"
            bind.write_text("bind")
            reviews = Path(temp) / "worktree" / ".shiploop-improve" / "test-spec-aaaa1111" / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "review-1.md").write_text("x")
            (reviews / "pass-1.json").write_text(json.dumps({"changed": False, "result_changed": True, "edited": True,
                                                             "lines": 6}))
            os.utime(bind, (1000, 1000))
            os.utime(reviews / "review-1.md", (1046, 1046))
            older = Path(temp) / "worktree" / ".shiploop-improve" / "step-plan-bbbb2222" / "reviews"
            older.mkdir(parents=True)
            (older / "review-1.md").write_text("x")
            (older / "pass-1.json").write_text(json.dumps({"changed": False}))  # a run before result tracking
            got = metrics.improve_reviews(run_dir)
            child = {c["child"]: c for c in got["per_child"]}
            self.assertEqual((child["test-spec-aaaa1111"]["edited"], child["test-spec-aaaa1111"]["edited_basis"]),
                             (True, "tree and result"))
            self.assertEqual((child["test-spec-aaaa1111"]["seconds"], child["test-spec-aaaa1111"]["review_seconds"]),
                             (0.0, 46.0))
            self.assertEqual((child["step-plan-bbbb2222"]["edited"], child["step-plan-bbbb2222"]["edited_basis"]),
                             (False, "tree only"))
            self.assertEqual(got["edited_children"], 1)
            # Each pass's size in lines (the convergence gate's measure); a run before passes had a size has none.
            self.assertEqual((child["test-spec-aaaa1111"]["lines"], child["step-plan-bbbb2222"]["lines"]), ([6], None))

    def test_direct_run_reads_its_recorded_repo_not_an_unrelated_sibling_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "shiploop-run"
            run_dir.mkdir()
            repo = root / "work"
            (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": str(repo)}) + '\n```\n')
            direct = repo / ".shiploop-improve" / "carry-forward-aaaa1111" / "reviews"
            decoy = root / "worktree" / ".shiploop-improve" / "unrelated-bbbb2222" / "reviews"
            previous = repo / ".shiploop-improve" / "previous-cccc3333" / "reviews"
            (run_dir / "improve").mkdir()
            (run_dir / "improve" / "nav-aaaa1111-bind.md").write_text("this run's child")
            for folder in (direct, decoy, previous):
                folder.mkdir(parents=True)
                (folder / "review-1.md").write_text("review")
            (direct / "review-2.md").write_text("review")
            (direct / "pass-1.json").write_text(json.dumps({"edited": True, "changed": False, "result_changed": True}))
            got = metrics.improve_reviews(run_dir)
            self.assertEqual((got["children"], got["passes"], got["edited_children"]), (1, 2, 1))
            self.assertEqual(got["per_child"][0]["child"], "carry-forward-aaaa1111")
            self.assertEqual(got["per_child"][0]["edited_basis"], "tree and result")

    def test_recorded_missing_repo_cannot_fall_back_to_an_unrelated_worktree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": str(root / "gone")}) + '\n```\n')
            reviews = root / "worktree" / ".shiploop-improve" / "decoy" / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "review-1.md").write_text("not this run")
            got = metrics.improve_reviews(run_dir)
            self.assertIsNone(got["passes"])
            self.assertTrue(got["unmeasured"])

    def test_a_review_folder_requires_an_unambiguous_exact_writer_id(self):
        for variant in ("full-action-id", "short-suffix", "duplicate-folder", "duplicate-binding"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                run_dir = root / "run"
                (run_dir / "improve").mkdir(parents=True)
                repo = root / "work"
                (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": str(repo)}) + '\n```\n')
                (run_dir / "improve" / ("nav-" + "a" * 24 + "aaaa1111-bind.md")).write_text("current binding")
                child = "decoy-1111" if variant == "short-suffix" else "spec-aaaa1111"
                reviews = repo / ".shiploop-improve" / child / "reviews"
                reviews.mkdir(parents=True)
                (reviews / "review-1.md").write_text("review")
                if variant == "duplicate-folder":
                    older = repo / ".shiploop-improve" / "old-run" / "spec-aaaa1111" / "reviews"
                    older.mkdir(parents=True)
                    (older / "review-1.md").write_text("ambiguous review")
                if variant == "duplicate-binding":
                    (run_dir / "improve" / ("nav-" + "b" * 24 + "aaaa1111-bind.md")).write_text("another binding")
                got = metrics.improve_reviews(run_dir)
                if variant == "full-action-id":
                    self.assertEqual((got["children"], got["passes"]), (1, 1))
                else:
                    self.assertIsNone(got["passes"])
                    self.assertTrue(got["unmeasured"])

    def test_invalid_recorded_repo_is_unknown_not_relative_to_the_evaluator_cwd(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp) / "run"
            run_dir.mkdir()
            for repo in ("relative/path", "", 42, None, "/bad\0path"):
                with self.subTest(repo=repo):
                    (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": repo}) + '\n```\n')
                    got = metrics.improve_reviews(run_dir)
                    self.assertIsNone(got["passes"])
                    self.assertTrue(got["unmeasured"])

    def test_missing_review_evidence_is_unknown_not_zero(self):
        self.assertIsNone(metrics.improve_reviews(None)["passes"])
        with tempfile.TemporaryDirectory() as temp:
            got = metrics.improve_reviews(Path(temp) / "run")
            for field in ("children", "passes", "edited_children", "max_passes"):
                self.assertIsNone(got[field])
            self.assertTrue(got["unmeasured"])

    def test_an_observed_empty_review_root_is_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "worktree" / ".shiploop-improve").mkdir(parents=True)
            got = metrics.improve_reviews(root / "run")
            self.assertEqual((got["children"], got["passes"], got["max_passes"]), (0, 0, 0))
            self.assertFalse(got.get("unmeasured"))

    def test_bound_children_with_missing_notes_do_not_look_like_a_complete_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            (run_dir / "improve").mkdir(parents=True)
            repo = root / "work"
            reviews = repo / ".shiploop-improve" / "spec-aaaa1111" / "reviews"
            reviews.mkdir(parents=True)
            (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": str(repo)}) + '\n```\n')
            (run_dir / "improve" / "nav-aaaa1111-bind.md").write_text("first child")
            (run_dir / "improve" / "nav-bbbb2222-bind.md").write_text("second child")
            for have_one_note in (False, True):
                with self.subTest(have_one_note=have_one_note):
                    if have_one_note:
                        (reviews / "review-1.md").write_text("first child's review")
                    got = metrics.improve_reviews(run_dir)
                    self.assertIsNone(got["passes"])
                    self.assertTrue(got["unmeasured"])

    def test_recorded_repo_reviews_without_bindings_cannot_be_attributed_to_this_run(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_dir.mkdir()
            repo = root / "work"
            reviews = repo / ".shiploop-improve" / "previous-aaaa1111" / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "review-1.md").write_text("previous run's review")
            (run_dir / "state.md").write_text('```shiploop-state\n' + json.dumps({"repo": str(repo)}) + '\n```\n')
            got = metrics.improve_reviews(run_dir)
            self.assertIsNone(got["passes"])
            self.assertTrue(got["unmeasured"])

    def test_legacy_bound_child_with_missing_notes_is_also_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            (run_dir / "improve").mkdir(parents=True)
            (run_dir / "improve" / "nav-aaaa1111-bind.md").write_text("recorded child")
            (root / "worktree" / ".shiploop-improve").mkdir(parents=True)
            got = metrics.improve_reviews(run_dir)
            self.assertIsNone(got["passes"])
            self.assertTrue(got["unmeasured"])

    def test_unreadable_bindings_do_not_look_like_no_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            binds = root / "run" / "improve"
            binds.mkdir(parents=True)
            (root / "worktree" / ".shiploop-improve").mkdir(parents=True)
            original = Path.iterdir

            def read(path):
                if path == binds:
                    raise PermissionError("fixture unreadable bindings")
                return original(path)

            with mock.patch.object(Path, "iterdir", read):
                got = metrics.improve_reviews(root / "run")
            self.assertIsNone(got["passes"])
            self.assertIn("unreadable", got["unmeasured"])

    def test_unreadable_review_root_is_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reviews = root / "worktree" / ".shiploop-improve"
            reviews.mkdir(parents=True)
            original = Path.iterdir

            def read(path):
                if path == reviews:
                    raise PermissionError("fixture unreadable review root")
                return original(path)

            with mock.patch.object(Path, "iterdir", read):
                got = metrics.improve_reviews(root / "run")
            self.assertIsNone(got["passes"])
            self.assertIn("unreadable", got["unmeasured"])

    def test_unreadable_state_is_unknown_not_a_collector_crash(self):
        with mock.patch.object(metrics, "engine_state", side_effect=PermissionError("fixture unreadable state")):
            got = metrics.improve_reviews(Path("/fixture/run"))
        self.assertIsNone(got["passes"])
        self.assertIn("unreadable", got["unmeasured"])

    def test_malformed_existing_state_does_not_authorize_the_legacy_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_dir.mkdir()
            (run_dir / "state.md").write_text('```shiploop-state\n{broken\n```\n')
            reviews = root / "worktree" / ".shiploop-improve" / "decoy" / "reviews"
            reviews.mkdir(parents=True)
            (reviews / "review-1.md").write_text("not this run")
            got = metrics.improve_reviews(run_dir)
            self.assertIsNone(got["passes"])
            self.assertTrue(got["unmeasured"])

    def test_summary_reports_missing_review_measurement(self):
        data = dict(shiploop_failures=[], model_glue=[], asked_user=[], sessions=[], cost_usd=0.0,
                    unmeasured={}, improve_children=0, improve_reviews=metrics.improve_reviews(None),
                    script_verifications={"passed": 0, "records": 0}, turns=0, stages=[])
        self.assertIn("review passes not measured", metrics.summary_lines(data)[0])


class ExpectationTest(HarnessCase):
    """Every expectation names its source; a failing run gets a filled mismatch record."""

    def test_every_case_names_the_source_of_its_expectations(self):
        cases = json.loads(run.CASES.read_text())
        for name, case in cases.items():
            self.assertTrue(case.get("checks_source"), name)
            for block in ("chain", "budget"):
                if block in case:
                    self.assertTrue(case[block].get("source"), f"{name}.{block}")
            if "retention" in case:
                self.assertTrue(case.get("retention_source"), name)

    def test_a_failing_run_records_expected_beside_observed_in_mismatch_md(self):
        code, result = self.invoke("claude", "nothing")
        self.assertEqual(code, 1)
        self.assertEqual(result["expectations"]["checks"], json.loads(run.CASES.read_text())["hello"]["checks_source"])
        mismatch = (Path(result["output"]) / "mismatch.md").read_text()
        for section in ("## Expected", "## Observed", "## Triage", "## Decision", "## Verified by"):
            self.assertIn(section, mismatch)
        self.assertIn("**shiploop**: ShipLoop reaches done", mismatch)
        self.assertIn("(source: the request", mismatch)
        self.assertRegex(mismatch, r"\*\*check\*\*: exit [0-9]+(: .+)?\n")  # the failing check's exit and last output line

    def test_a_passing_run_writes_no_mismatch(self):
        code, result = self.invoke("claude", "done")
        self.assertEqual(code, 0, result)
        self.assertFalse((Path(result["output"]) / "mismatch.md").exists())

    def test_run_deadlines_count_active_time_and_strptime_is_loaded_at_start(self):
        """Run 5 (2026-10-24/25): a 10 h sleep spent the 5 h wall-clock cap after 3.8 h of work, and a mid-run
        interpreter swap removed the lazily imported _strptime. Deadlines read time.monotonic, which stops during
        sleep, in run.py and slice.py alike. With no --timeout and no case default the deadline is infinite.
        _strptime is imported at start.

        A case may now declare its own `timeout` in seconds (2026-11-04): every one of chess-salesforce's 124 saved
        runs was killed at a hand-typed 4-hour cap rather than finishing, so a platform case whose work outlives the
        usual cap says so once in cases.json. An explicit --timeout still wins, which is what keeps a caller in
        control; only the fallback changed.
        """
        source = (ROOT / "test" / "shiploop_e2e" / "run.py").read_text(encoding="utf-8")
        for name in ("run.py", "slice.py"):
            text = (ROOT / "test" / "shiploop_e2e" / name).read_text(encoding="utf-8")
            wall = [line.strip() for line in text.splitlines() if "deadline" in line and "time.time()" in line]
            self.assertEqual(wall, [], name)
        # The monotonic clock is the point; the cap's source is the case, then the flag, then unbounded.
        self.assertIn("deadline = time.monotonic() + cap", source)
        self.assertIn('cap = args.timeout or (catalog().get(args.case, {}) if args.case else {}).get("timeout") '
                      'or float("inf")', source)
        self.assertIn('deadline = time.monotonic() + (args.timeout or float("inf"))', 
                      (ROOT / "test" / "shiploop_e2e" / "slice.py").read_text(encoding="utf-8"))
        self.assertRegex(source, r"(?m)^import _strptime\b")
        self.assertIn("_strptime", sys.modules)  # importing run loaded it

    def test_a_platform_case_declares_its_own_timeout_and_the_flag_still_wins(self):
        """chess-salesforce ran to a hand-typed 4-hour cap with ShipLoop still active at test-spec, and all 124 of its
        saved runs were killed rather than finished (2026-10-18 and after). A case whose work outlives the usual cap
        says so once in cases.json; a caller can still override it.
        """
        cases = run.catalog()
        for case in ("chess-salesforce", "battleship-salesforce", "battleship-salesforce-ui",
                     "gym-membership-salesforce"):
            with self.subTest(case=case):
                self.assertEqual(cases[case].get("timeout"), 8 * 3600,
                                 "a hosted-platform case declares 8 hours")
        self.assertIsNone(cases["hello"].get("timeout"), "an ordinary case stays uncapped")

        # Resolution: the flag wins, then the case, then unbounded.
        def cap(case, flag):
            args = types.SimpleNamespace(timeout=flag, case=case)
            return args.timeout or (run.catalog().get(args.case, {}) if args.case else {}).get("timeout") \
                or float("inf")
        self.assertEqual(cap("chess-salesforce", None), 8 * 3600)
        self.assertEqual(cap("chess-salesforce", 600), 600, "an explicit --timeout wins")
        self.assertEqual(cap("hello", None), float("inf"))

    def test_budget_is_should_level_and_read_from_the_run_timeline(self):
        run_dir = self.tmp / "run"
        run_dir.mkdir()
        (run_dir / "timeline.json").write_text(json.dumps({
            "started": "2026-10-03T10:00:00Z",
            "accepted": {"a": "2026-10-03T10:05:00Z", "b": "2026-10-03T10:21:30Z"}}))
        budget = {"seeded_minutes": 30, "source": "one session"}
        met = run.budget_facts(budget, True, str(run_dir))
        self.assertEqual((met["level"], met["observed_minutes"], met["pass"]), ("should", 21.5, True))
        over = run.budget_facts({"seeded_minutes": 20, "source": "x"}, True, str(run_dir))
        self.assertFalse(over["pass"])
        self.assertIsNone(run.budget_facts(budget, False, str(run_dir)))  # only seeded runs carry a budget
        interrupted = run.budget_facts(budget, True, str(run_dir), interrupted=True)
        self.assertEqual((interrupted["applies"], interrupted["pass"], interrupted["observed_minutes"]), (False, None, 21.5))


class ReviewParsingTest(unittest.TestCase):
    def test_actionable_keeps_only_material_premise_preserving_findings(self):
        verdict = {
            "learnings": [{"title": "a", "severity": "material", "preserves_premise": True},
                          {"title": "b", "severity": "minor", "preserves_premise": True}],
            "optimizations": [{"title": "c", "severity": "material", "preserves_premise": False}],
            "missing_considerations": [{"title": "d", "severity": "material", "preserves_premise": True}],
        }
        self.assertEqual([(f["title"], f["category"]) for f in review.actionable(verdict)],
                         [("a", "learnings"), ("d", "missing_considerations")])

    def test_last_json_object_prefers_the_final_fenced_block(self):
        text = 'Notes {"x": 1}\n```json\n{"outcome": "old"}\n```\nthen\n```json\n{"outcome": "new"}\n```'
        self.assertEqual(hosts.last_json_object(text), {"outcome": "new"})
        self.assertEqual(hosts.last_json_object('prefix {"a": {"b": 2}} tail'), {"a": {"b": 2}})
        self.assertIsNone(hosts.last_json_object("no json here"))

    def test_final_text_is_grok_text_after_its_last_tool_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            events = Path(tmp) / "events.jsonl"
            events.write_text("\n".join(json.dumps(e) for e in (
                {"type": "text", "data": "thinking aloud"},
                {"type": "tool_call", "toolName": "read_file", "rawInput": {}},
                {"type": "text", "data": "final "}, {"type": "text", "data": "answer"})))
            self.assertEqual(hosts.final_text(events), "final answer")

    def test_reviewer_prompt_states_the_premise_and_the_three_questions(self):
        prompt = review.reviewer_prompt(Path("/tmp/run"), Path("/tmp/skill"))
        # The standing spec is the premise, loaded from the one file, with clause IDs to cite.
        self.assertIn("**S-1 Scripts own the graph and the state.**", prompt)
        self.assertIn("**S-7 Packets are small where they are printed", prompt)
        self.assertIn("Cite its clause IDs", prompt)
        for key in review.CATEGORIES:
            self.assertIn(key, prompt)
        for key in review.HARNESS_QUESTIONS:
            self.assertIn(key, prompt)
        rendered = review.render_markdown({"harness": {"learning_retention": {"answer": "Keep it", "proposals": ["p1"]}}})
        self.assertIn("**Learning retention:** Keep it", rendered)
        self.assertIn("**Evaluation criteria:** not answered", rendered)


class FakeReviewer:
    """The reviewer host of the audit control: every call returns the next (process status, final text) pair."""
    model, effort = "offline-probe", "high"

    def __init__(self, replies: list):
        self.replies = list(replies)
        self.text = ""

    def env(self, home):
        return {"HOME": str(home)}

    def argv(self, **kwargs):
        return ["offline-probe", "-s", "danger-full-access"]

    def translator(self):
        return None

    def run_agent(self, argv, cwd, env, events_path, stderr_path, timeout, translate=None):
        status, self.text = self.replies.pop(0)
        Path(events_path).write_text("")
        Path(stderr_path).write_text("")
        return {"status": status, "returncode": {"exited": 0, "failed": 1}.get(status), "elapsed_seconds": 0}

    def patches(self):
        return (mock.patch.object(review.hosts, "host", return_value=self),
                mock.patch.object(review.hosts, "run_agent", side_effect=self.run_agent),
                mock.patch.object(review.hosts, "final_text", side_effect=lambda path: self.text))


class ReviewValidityTest(unittest.TestCase):
    UNUSABLE = (("failed", "", "failed"),
                ("exited", '```json\n{"learnings": []}\n```', "invalid"),
                ("exited", "I looked at the run and it was fine.", "invalid"),
                ("timeout", "", "timed_out"),
                ("failed", VALID_EMPTY_REVIEW, "failed"))

    def review(self, status: str, text: str) -> tuple[dict, int]:
        fake = FakeReviewer([(status, text)])
        with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
            for patch in fake.patches():
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            run_dir = Path(tmp) / "run"
            run_dir.mkdir()
            code = review.main([str(run_dir), "--host", "grok", "--no-prior-learnings"])
            return json.loads((run_dir / "review.json").read_text()), code

    def test_an_unusable_review_is_never_clean_and_keeps_its_own_outcome(self):
        for status, text, outcome in self.UNUSABLE:
            with self.subTest(status=status, text=text[:30]):
                verdict, code = self.review(status, text)
                self.assertEqual(verdict["validity"]["status"], outcome)
                self.assertTrue(verdict["validity"]["reason"])
                self.assertFalse(review.counts_as_clean(verdict))
                self.assertEqual(verdict["actionable"], [])
                self.assertEqual(code, 1)

    def test_a_legacy_review_remains_readable_without_discovery_qualification(self):
        verdict, code = self.review("exited", VALID_EMPTY_REVIEW)
        self.assertEqual(verdict["validity"], {"status": "valid", "reason": None})
        self.assertFalse(review.counts_as_clean(verdict))
        self.assertEqual(code, 0)


class ReviewSourceTest(unittest.TestCase):
    """The 2026-10-16 E2E audit: review.py run directly gave the reviewer this checkout's skills/shiploop and called it "the
    ShipLoop skill source that ran", whatever the run had actually installed."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()
        self.run_dir = self.tmp / "run"
        self.run_dir.mkdir()

    def plugin(self, name: str) -> Path:
        root = self.tmp / name
        (root / "skills" / "shiploop").mkdir(parents=True)
        (root / "skills" / "shiploop" / "SKILL.md").write_text("---\nname: shiploop\n---\n")
        return root

    def launch(self, file: str, plugin_dir: Path) -> None:
        (self.run_dir / file).write_text(json.dumps({"case": "hello", "host": "grok", "plugin_dir": str(plugin_dir)}))

    def prompt(self, *extra: str) -> tuple[str, str, dict]:
        shutil.rmtree(self.run_dir / "review", ignore_errors=True)  # one review per run directory
        fake = FakeReviewer([("exited", VALID_EMPTY_REVIEW)])
        seen = {}
        fake.argv = lambda **kwargs: seen.update(kwargs) or ["offline-probe"]
        printed = io.StringIO()
        with contextlib.ExitStack() as stack:
            for patch in fake.patches():
                stack.enter_context(patch)
            stack.enter_context(contextlib.redirect_stdout(printed))
            review.main([str(self.run_dir), "--host", "grok", "--no-prior-learnings", *extra])
        return seen["prompt"], printed.getvalue(), json.loads((self.run_dir / "review.json").read_text())

    def test_the_reviewer_is_given_the_source_the_runs_own_launch_record_names(self):
        built = self.plugin("build")
        self.launch("invocation.json", built)
        prompt, _, verdict = self.prompt()
        self.assertIn(f"The ShipLoop skill source that ran: {built / 'skills' / 'shiploop'}", prompt)
        self.assertNotIn(str(ROOT / "skills" / "shiploop"), prompt)
        self.assertEqual(verdict["skill_source"]["basis"], "the run's launch records")

    def test_a_run_whose_records_name_no_source_says_so_instead_of_calling_this_checkout_the_source_that_ran(self):
        prompt, printed, verdict = self.prompt()
        self.assertNotIn("source that ran", prompt)
        self.assertIn("Source mismatch", prompt)
        self.assertIn(str(ROOT / "skills" / "shiploop"), prompt)
        self.assertIn("source mismatch:", printed)
        self.assertEqual(verdict["skill_source"]["basis"], "mismatch")
        gone = self.tmp / "deleted-build"
        self.launch("invocation.json", gone)  # recorded, but no longer on disk
        prompt, printed, _ = self.prompt()
        self.assertIn("Source mismatch", prompt)
        self.assertIn(str(gone), printed)

    def test_launches_on_different_plugins_name_each_source(self):
        first, second = self.plugin("first"), self.plugin("second")
        self.launch("invocation.json", first)
        self.launch("invocation-resume-codex-1792200000.json", second)
        prompt, _, verdict = self.prompt()
        self.assertIn(str(first / "skills" / "shiploop"), prompt)
        self.assertIn(str(second / "skills" / "shiploop"), prompt)
        self.assertEqual(len(verdict["skill_source"]["roots"]), 2)

    def test_an_explicit_skill_root_is_the_callers_statement_and_is_kept(self):
        worktree = self.plugin("worktree")
        self.launch("invocation.json", self.plugin("build"))
        prompt, _, verdict = self.prompt("--skill-root", str(worktree / "skills" / "shiploop"))
        self.assertIn(f"The ShipLoop skill source that ran: {worktree / 'skills' / 'shiploop'}", prompt)
        self.assertEqual(verdict["skill_source"]["basis"], "given by the caller")


class IterateConvergenceTest(unittest.TestCase):
    """iterate.main end to end with the host, the build and the run faked: only the review's validity varies."""

    def iterate(self, replies: list, iterations: int, host: tuple = ("--host", "grok"), launched: list | None = None,
                late_change=False, receipt: dict | None = None) -> str:
        """``host`` is the --host argument (empty: the default); ``launched`` collects each run's argv."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        repo = tmp / "repo"
        (repo / "test" / "shiploop_e2e").mkdir(parents=True)
        (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").write_text("# ShipLoop E2E learnings\n")
        (repo / "skills" / "shiploop").mkdir(parents=True)
        source = repo / "skills" / "shiploop" / "SKILL.md"
        source.write_text("tested ShipLoop source")
        for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"],
                    ["config", "user.email", "t@example.invalid"], ["add", "test"], ["commit", "-q", "-m", "base"]):
            subprocess.run(["git", "-C", str(repo), *cmd], check=True)
        real_run = subprocess.run

        def no_build(argv, *a, **kw):
            if any(str(part).endswith("build-packages.py") for part in argv):
                return subprocess.CompletedProcess(argv, 0)
            return real_run(argv, *a, **kw)

        def passing_run(argv):
            if launched is not None:
                launched.append(list(argv))
            out = Path(argv[argv.index("--output") + 1])
            out.mkdir(parents=True)
            (out / "result.json").write_text(json.dumps({
                "pass": True, "host": "grok", "model": "m", "effort": "medium",
                "process": {"status": "exited", "returncode": 0, "elapsed_seconds": 1},
                "cli": {"num_turns": 1, "cost_usd": None}, "shiploop": {"status": "done", "stage": "done", "report_html": True},
                "checks": [], "invoked": {"pass": True}, "plugin": {"pass": True}}))
            return 0

        def independent_judge(run_dir, verdict, **kwargs):
            return {"review_sha256": iterate.judge.review_sha256(run_dir, verdict), "assessments": [],
                    "validity": {"status": "valid", "reason": None},
                    "process": {"status": "exited", "returncode": 0}}

        fake = FakeReviewer(replies)
        record = iterate.record_learnings
        def record_then_change(*args):
            recorded = record(*args)
            if late_change:
                source.write_text("source changed after its last E2E run")
            return recorded
        with contextlib.ExitStack() as stack:
            for patch in fake.patches():
                stack.enter_context(patch)
            stack.enter_context(mock.patch.object(iterate, "new_worktree", return_value=(repo, "auto/test")))
            stack.enter_context(mock.patch.object(iterate.subprocess, "run", side_effect=no_build))
            stack.enter_context(mock.patch.object(iterate.runner, "main", side_effect=passing_run))
            stack.enter_context(mock.patch.object(iterate.judge, "judge", side_effect=independent_judge))
            stack.enter_context(mock.patch.object(iterate, "record_learnings", side_effect=record_then_change))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            iterate.main([*host, "--iterations", str(iterations), "--output", str(tmp / "out")])
        if receipt is not None:
            receipt.update(json.loads((tmp / "out" / "iteration-result.json").read_text()))
        return (tmp / "out" / "LEARNINGS.md").read_text()

    def test_the_default_subject_is_codex_with_separate_review_roles(self):
        launched: list = []
        self.iterate([("exited", VALID_EMPTY_REVIEW)] * 2, 2, host=(), launched=launched)
        self.assertTrue(launched)
        for argv in launched:
            self.assertEqual(argv[argv.index("--host") + 1], "codex")
            self.assertNotIn("--backend", argv)

    def test_unusable_reviews_of_passing_runs_never_converge(self):
        journal = self.iterate([("failed", ""), ("exited", '```json\n{"learnings": []}\n```'), ("timeout", "")], 3)
        self.assertNotIn("clean review", journal)
        self.assertNotIn("two consecutive clean reviews", journal)
        self.assertIn("reached --iterations 3", journal)
        for outcome in ("failed", "invalid", "timed_out"):
            self.assertIn(f"- review {outcome}:", journal)

    def test_legacy_empty_reviews_do_not_claim_discovery_qualified_convergence(self):
        journal = self.iterate([("exited", VALID_EMPTY_REVIEW)] * 3, 3)
        self.assertNotIn("two scoped passing assessments", journal)
        self.assertIn("reached --iterations 3", journal)

    def test_two_v2_empty_reviews_with_fresh_judgments_close_only_the_scoped_assessment(self):
        payload = json.loads(VALID_EMPTY_REVIEW.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        payload.update(version=2, discoveries=[])
        response = "```json\n" + json.dumps(payload) + "\n```"
        journal = self.iterate([("exited", response)] * 2, 3)
        self.assertIn("two scoped passing assessments; no claim of exhausted learning", journal)

    def test_a_late_source_change_cannot_inherit_the_last_tested_artifact_status(self):
        receipt = {}
        self.iterate([("exited", VALID_EMPTY_REVIEW)], 1, late_change=True, receipt=receipt)
        self.assertEqual(receipt["qualification"], "unevaluated")
        self.assertNotEqual(receipt["tested_source_sha256"], receipt["final_source_sha256"])
        self.assertFalse(receipt["learning_exhausted"])

    def test_an_unchanged_exploration_artifact_still_needs_comparative_qualification(self):
        receipt = {}
        self.iterate([("exited", VALID_EMPTY_REVIEW)], 1, receipt=receipt)
        self.assertEqual(receipt["qualification"], "comparison_required")

    def test_an_unusable_review_between_two_clean_ones_resets_the_streak(self):
        journal = self.iterate([("exited", VALID_EMPTY_REVIEW), ("failed", ""), ("exited", VALID_EMPTY_REVIEW)], 3)
        self.assertNotIn("clean review (streak 2)", journal)
        self.assertIn("reached --iterations 3", journal)


class FakeImprover(FakeReviewer):
    """The reviewer replies in turn; a call whose working directory is the improver's worktree runs `act(worktree, events)`."""

    def __init__(self, replies: list, worktree: Path, act):
        super().__init__(replies)
        self.worktree, self.act, self.seen = worktree, act, {}

    def env(self, home, git_config=None):  # the improver passes the user's git config too
        return {"HOME": str(home)}

    def run_agent(self, argv, cwd, env, events_path, stderr_path, timeout, translate=None):
        if Path(cwd) != self.worktree:
            return super().run_agent(argv, cwd, env, events_path, stderr_path, timeout, translate)
        Path(events_path).write_text("")
        Path(stderr_path).write_text("")
        self.seen["files"] = sorted(path.relative_to(cwd).as_posix() for path in Path(cwd).rglob("*.py")
                                    if ".git" not in path.parts)
        self.seen["status"] = subprocess.run(["git", "-C", str(cwd), "status", "--porcelain"], capture_output=True,
                                             text=True, check=True).stdout
        self.act(Path(cwd), Path(events_path))
        return {"status": "exited", "returncode": 0, "elapsed_seconds": 0}


class IterateBoundaryTest(unittest.TestCase):
    """The evaluator boundary in iterate.py (SPEC "The promotion contract", build step 3, R13 of the final verdict). Astra's
    done signal: a candidate cannot modify grader inputs or read protected holdout instances, and the hashes stay unchanged."""

    HELD_OUT = ["test/fixtures/quality/reference_checkers.py", "test/shiploop_e2e/checks/checkers_accept.py"]

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        # The checkout that grades the runs: its harness code, its checks and its catalog.
        self.harness = self.tmp / "grader" / "test" / "shiploop_e2e"
        (self.harness / "checks").mkdir(parents=True)
        (self.harness / "run.py").write_text("# the harness\n")
        (self.harness / "checks" / "checkers_accept.py").write_text("CHECKS = {}\n")
        acceptance = {"module": "checkers_accept", "calibration": [self.HELD_OUT[0]], "start": "node server.js", "checks": []}
        (self.harness / "cases.json").write_text(json.dumps({"checkers": {"prompt": "p", "quality": {"acceptance": acceptance}}}))
        (self.harness / "suites.json").write_text('{"fixture":{"cases":["checkers"]}}')
        (self.harness / "SPEC.md").write_text("# Fixture specification\n")
        for module in ("scorecard.py", "boundary.py", "metrics.py", "delivery.py", "environment.py", "runrecord.py"):
            (self.harness / module).write_text("# frozen dependency\n")
        # The improver's worktree, with the same held-out files committed.
        self.repo = self.tmp / "worktree"
        for path, text in ((self.HELD_OUT[1], "CHECKS = {}\n"), (self.HELD_OUT[0], "# a correct implementation\n"),
                           ("skills/shiploop/SKILL.md", "# ShipLoop\n"), ("test/shiploop_e2e/LEARNINGS.md", "# learnings\n")):
            (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / path).write_text(text)
        for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"], ["config", "user.email", "t@example.invalid"],
                    ["add", "."], ["commit", "-q", "-m", "base"]):
            subprocess.run(["git", "-C", str(self.repo), *cmd], check=True)

    def git(self, *args: str) -> str:
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True).stdout

    def commit(self, worktree: Path, *paths: str) -> None:
        for path in paths:
            (worktree / path).parent.mkdir(parents=True, exist_ok=True)
            (worktree / path).write_text("changed\n")
        subprocess.run(["git", "-C", str(worktree), "add", *paths], check=True)
        subprocess.run(["git", "-C", str(worktree), "commit", "-q", "-m", "improve"], check=True)

    def grading(self):
        return (mock.patch.object(iterate, "HERE", self.harness), mock.patch.object(iterate.runner, "CASES", self.harness / "cases.json"))

    def improve(self, act) -> tuple[dict, dict]:
        fake = FakeImprover([], self.repo, act)
        args = iterate.argparse.Namespace(case="checkers", host="grok", model=None, effort=None, permission_mode="auto",
                                          improve_max_turns=None, max_budget_usd=None, improve_timeout=10)
        with contextlib.ExitStack() as stack:
            for patch in (*fake.patches(), *self.grading()):
                stack.enter_context(patch)
            change = iterate.improve(self.repo, [], self.tmp / f"stage-{len(list(self.tmp.glob('stage-*')))}", args)
        return change, fake.seen

    def test_a_candidate_change_keeps_the_boundary_and_never_sees_the_held_out_files(self):
        before = {path: (self.repo / path).read_bytes() for path in self.HELD_OUT}
        change, seen = self.improve(lambda worktree, events: self.commit(worktree, "skills/shiploop/SKILL.md",
                                                                         "test/shiploop-lint.test.py"))
        self.assertFalse(set(self.HELD_OUT) & set(seen["files"]), "withheld while the improver worked")
        self.assertEqual(seen["status"], "", "withholding is not an uncommitted change")
        self.assertEqual(change["withheld"], self.HELD_OUT)
        self.assertEqual({path: (self.repo / path).read_bytes() for path in self.HELD_OUT}, before, "restored as they were")
        self.assertEqual(self.git("status", "--porcelain"), "")
        self.assertFalse([line for line in self.git("ls-files", "-v").splitlines() if line.startswith("S ")],
                         "no skip-worktree flag is left behind")
        self.assertEqual((change["out_of_scope"], change["held_out_named"], change["grading"]["changed"]), ([], 0, []))
        self.assertEqual(change["grading"]["before"], change["grading"]["after"], "the hashes stay unchanged")
        self.assertIsNone(iterate.boundary_crossing(change))

    def test_a_change_to_what_grades_the_runs_crosses_the_boundary(self):
        for target, group in (("checks/checkers_accept.py", "oracle"), ("run.py", "evaluator"), ("cases.json", "case")):
            with self.subTest(target=target):
                self.setUp()

                def tamper(worktree, events, target=target):
                    path = self.harness / target
                    if target == "cases.json":
                        cases = json.loads(path.read_text())
                        cases["checkers"]["quality"]["acceptance"]["checks"] = [{"id": "easier"}]
                        path.write_text(json.dumps(cases))
                    else:
                        path.write_text(path.read_text() + "# weakened\n")
                change, _ = self.improve(tamper)
                self.assertEqual(change["grading"]["changed"], [group])
                self.assertIn(f"the improver changed what grades the runs ({group} digest",
                              iterate.boundary_crossing(change))

    def test_a_tool_call_that_names_a_held_out_file_crosses_the_boundary(self):
        # The SPEC is in the improver's prompt and names these files, so prose that names one proves nothing: only calls count.
        prose = {"type": "assistant", "message": {"content": [{"type": "text", "text": f"The SPEC withholds {self.HELD_OUT[0]}."}]}}
        change, _ = self.improve(lambda worktree, events: events.write_text(json.dumps(prose) + "\n"))
        self.assertEqual(change["held_out_named"], 0)
        self.assertIsNone(iterate.boundary_crossing(change))

        def peek(worktree, events):
            events.write_text(json.dumps(prose) + "\n" + json.dumps(
                {"type": "tool_call", "toolName": "bash", "rawInput": {"command": f"git show HEAD:{self.HELD_OUT[0]}"}}) + "\n")
        change, _ = self.improve(peek)
        self.assertEqual(change["held_out_named"], 1)
        self.assertIn("tool calls name a held-out file 1 time(s)", iterate.boundary_crossing(change))
        change, _ = self.improve(lambda worktree, events: events.unlink())
        self.assertIsNone(change["held_out_named"])
        self.assertIn("cannot be ruled out", iterate.boundary_crossing(change))

    def test_the_harness_its_suites_the_runner_and_the_catalog_are_out_of_scope(self):
        change, _ = self.improve(lambda worktree, events: self.commit(
            worktree, "test/shiploop_e2e/run.py", "test/shiploop-e2e.test.py", SUITE_CATALOG, "test/run-all.sh",
            "test/shiploop-lint.test.py", "test/shiploop_example_support.py", "changes/shiploop/x.md"))
        self.assertEqual(sorted(change["out_of_scope"]), ["test/run-all.sh", "test/shiploop-e2e.test.py",
                                                          "test/shiploop_e2e/run.py", SUITE_CATALOG])

    def test_the_loop_stops_and_journals_when_the_improver_changes_what_grades(self):
        def tamper(worktree, events):
            (self.harness / "checks" / "checkers_accept.py").write_text("CHECKS = {}  # weakened\n")
            self.commit(worktree, "skills/shiploop/SKILL.md")
        real_run = subprocess.run

        def no_build(argv, *a, **kw):
            return (subprocess.CompletedProcess(argv, 0) if any(str(part).endswith("build-packages.py") for part in argv)
                    else real_run(argv, *a, **kw))

        def passing_run(argv):
            out = Path(argv[argv.index("--output") + 1])
            out.mkdir(parents=True)
            (out / "result.json").write_text(json.dumps({
                "pass": True, "host": "grok", "model": "m", "effort": "medium",
                "process": {"status": "exited", "returncode": 0, "elapsed_seconds": 1},
                "cli": {"num_turns": 1, "cost_usd": None}, "shiploop": {"status": "done", "stage": "done", "report_html": True},
                "checks": [], "invoked": {"pass": True}, "plugin": {"pass": True},
                "boundary": {"evaluator": "e" * 12, "oracle": "o" * 12, "case": "c" * 12}, "versions": {"plugin_sha256": "p" * 12}}))
            return 0

        discovery = {"id": "script-repair", "title": "Improve the script", "target": "shiploop",
                     "mission_anchor": {"clause_id": "S-1", "relationship": "supports", "challenge": "Keep scripts authoritative"},
                     "materiality": "material", "confidence": "high", "implementation_eligible": True,
                     "proposed_disposition": "implement", "files": ["skills/shiploop/SKILL.md"],
                     "proposal": "Repair the script generically", "potential_impact": "Restore durable navigation",
                     "alternatives": ["The observed behaviour could be case-specific"],
                     "next_experiment": "Rerun the navigation probe",
                     "evidence": [{"reference": "result.json", "observation": "Navigation repeated",
                                   "interpretation": "The script needs a generic repair"}]}
        reply = json.dumps({"version": 2, "outcome": "A repair is warranted", "learnings": [],
                            "missing_considerations": [], "optimizations": [], "harness": {},
                            "discoveries": [discovery]})
        fake = FakeImprover([("exited", reply)] * 3, self.repo, tamper)

        def independent_judge(run_dir, verdict, **kwargs):
            identity = iterate.judge.review_sha256(run_dir, verdict)
            process = {"status": "exited", "returncode": 0}
            report = {"review_sha256": identity, "assessments": [{"id": "script-repair", "status": "supported",
                      "disposition": "implement", "reason": "The trace supports the repair", "evidence": ["result.json"]}]}
            return {**report, "process": process,
                    "validity": iterate.judge.validity(report, process, verdict, identity)}
        with contextlib.ExitStack() as stack:
            for patch in (*fake.patches(), *self.grading()):
                stack.enter_context(patch)
            stack.enter_context(mock.patch.object(iterate, "new_worktree", return_value=(self.repo, "auto/test")))
            stack.enter_context(mock.patch.object(iterate.subprocess, "run", side_effect=no_build))
            stack.enter_context(mock.patch.object(iterate.runner, "main", side_effect=passing_run))
            stack.enter_context(mock.patch.object(iterate.judge, "judge", side_effect=independent_judge))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            iterate.main(["--case", "checkers", "--host", "grok", "--iterations", "3", "--output", str(self.tmp / "out")])
        journal = (self.tmp / "out" / "LEARNINGS.md").read_text()
        self.assertIn(f"- boundary: evaluator {'e' * 12}, oracle {'o' * 12}, case {'c' * 12}, candidate {'p' * 12}", journal)
        self.assertIn("- stopped: the improver changed what grades the runs (oracle digest", journal)
        self.assertNotIn("quick tier:", journal, "nothing graded on the changed oracle")
        self.assertNotIn("## Iteration 2", journal)


class BoundaryTest(unittest.TestCase):
    """test/shiploop_e2e/boundary.py: the digests and the held-out list (build step 3)."""

    def test_candidate_paths(self):
        for path, allowed in (("skills/shiploop/SKILL.md", True), ("changes/shiploop/x.md", True),
                              ("test/shiploop-lint.test.py", True), ("test/shiploop_example_support.py", True),
                              ("test/fixtures/shiploop-keepalive/a", True), ("test/experiments/shiploop_chain/a.py", True),
                              ("test/shiploop_e2e/checks/battleship_game.py", False), ("test/shiploop-e2e-quality.test.py", False),
                              (SUITE_CATALOG, False), ("test/run-all.sh", False), ("skills/improve/SKILL.md", False),
                              ("test/fixtures/quality/reference_checkers.py", False)):
            with self.subTest(path=path):
                self.assertEqual(boundary.candidate_path(path), allowed)

    def test_the_digests_read_bytes_and_ignore_compiled_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            harness = Path(tmp)
            (harness / "checks" / "__pycache__").mkdir(parents=True)
            (harness / "run.py").write_text("x\n")
            (harness / "README.md").write_text("docs are not the evaluator\n")
            (harness / "checks" / "a.py").write_text("y\n")
            first = boundary.fingerprint(harness, {"prompt": "p"})
            (harness / "checks" / "__pycache__" / "a.cpython-313.pyc").write_bytes(b"\0")
            (harness / "README.md").write_text("edited\n")
            self.assertEqual(boundary.fingerprint(harness, {"prompt": "p"}), first)
            (harness / "checks" / "a.py").write_text("z\n")
            self.assertEqual(boundary.changed(first, boundary.fingerprint(harness, {"prompt": "p"})), ["oracle"])
            self.assertEqual(boundary.changed(first, boundary.fingerprint(harness, None)), ["oracle", "case"])
            self.assertEqual(boundary.fingerprint(harness, None)["unmeasured"], {"case": "a custom prompt has no catalog entry"})

    def test_the_held_out_files_are_the_acceptance_modules_and_their_calibration(self):
        # The paths are not read here: this suite runs in the improver's worktree, where they are withheld. That they
        # exist is checked in test/shiploop-e2e-quality.test.py, which no candidate change selects.
        acceptance = {"module": "m_accept", "calibration": ["test/fixtures/quality/ref.py"]}
        self.assertEqual(boundary.held_out_files({"a": {"quality": {"acceptance": acceptance}}, "b": {"prompt": "p"}}),
                         ["test/fixtures/quality/ref.py", "test/shiploop_e2e/checks/m_accept.py"])


class LearningsTest(unittest.TestCase):
    def history_repo(self, directory):
        repo = Path(directory) / "history"
        repo.mkdir()

        def git(*args, message=None):
            return subprocess.run(["git", "-C", str(repo), *args], input=message, check=True,
                                  capture_output=True, text=True).stdout.strip()

        git("init", "-q", "-b", "main")
        git("config", "user.name", "test")
        git("config", "user.email", "test@example.invalid")
        return repo, git

    def test_history_preserves_full_commit_identity_and_empty_learning_bodies(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, git = self.history_repo(tmp)
            messages = ["first lesson\n\nMeasured failure: keep the accepted gate.\n",
                        "second lesson\n\nNo code retained; the candidate increased cost.\n",
                        "third lesson\n\nPrior evidence remains unknown.\n"]
            commits = []
            for message in messages:
                git("commit", "-q", "--allow-empty", "-F", "-", message=message)
                commits.append(git("rev-parse", "HEAD"))

            history = review.last_commit_messages(repo)

            for sha, message in zip(commits, messages):
                self.assertIn("commit " + sha + "\n", history)
                self.assertIn(message.strip(), history)

    def test_candidate_reads_older_record_learning_including_private_candidate_refs(self):
        import cycle

        with tempfile.TemporaryDirectory() as tmp:
            repo, git = self.history_repo(tmp)
            record_id = "LR-history-fixture"
            git("commit", "-q", "--allow-empty", "-m",
                f"unrelated ancient material\n\nLearning-Record: {record_id}-other")
            base = git("rev-parse", "HEAD")
            old = "older retained rejection: avoid the failed catalog lookup"
            git("commit", "-q", "--allow-empty", "-F", "-", message=f"{old}\n\nLearning-Record: {record_id}\n")
            old_sha = git("rev-parse", "HEAD")
            for number in range(4):
                git("commit", "-q", "--allow-empty", "-m", f"later unrelated {number}")
            private = "unadopted candidate rationale: retain its negative learning"
            private_sha = git("commit-tree", base + "^{tree}", "-p", base,
                              message=f"{private}\n\nLearning-Record: {record_id}\n")
            git("update-ref", f"refs/shiploop-loop/fixture/{record_id}", private_sha)

            history = review.last_commit_messages(repo, record_id=record_id)

            self.assertIn("commit " + old_sha + "\n", history)
            self.assertIn("commit " + private_sha + "\n", history)
            self.assertIn(old, history)
            self.assertIn(private, history)
            self.assertNotIn("unrelated ancient material", history)
            self.assertIn("not complete", history.lower())
            record = {"record": record_id, "title": "Preserve prior decisions", "anchor": ["S-1"],
                      "files": [], "proposal": "Use the recorded learning", "next_experiment": "A neutral check"}
            prompt = cycle.one_record_prompt(repo, record, git("rev-parse", "HEAD"), ["hello"],
                                             {"tolerance": 0.1, "attempts": 1})
            self.assertIn(old, prompt)
            self.assertIn(private, prompt)

    def test_substantive_source_and_comparison_history_outlast_terminal_notes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, git = self.history_repo(tmp)
            git("commit", "-q", "--allow-empty", "-m", "unrelated base")
            source = repo / "skills" / "shiploop" / "scripts" / "engine.py"
            source.parent.mkdir(parents=True)
            source.write_text("accepted = True\n")
            git("add", "skills/shiploop/scripts/engine.py")
            git("commit", "-q", "-m", "fix(shiploop): retain source constraint\n\nKeep the accepted source-scope lesson.")
            source_sha = git("rev-parse", "HEAD")
            (repo / "skills" / "shiploop" / "SKILL.md").write_text("version: 2\n")
            git("add", "skills/shiploop/SKILL.md")
            git("commit", "-q", "-m", "release: version metadata\n\nSkill-Craft-Release: shiploop@2")
            git("commit", "-q", "--allow-empty", "-m",
                "test(e2e): qualified cycle for LR-context: PROMOTE, prediction confirmed\n\n"
                "Substantive measured learning remains applicable.")
            comparison_sha = git("rev-parse", "HEAD")
            for number in range(3):
                git("commit", "-q", "--allow-empty", "-m",
                    f"test(e2e): retain cycle outcome for LR-terminal-{number}: NO_CANDIDATE\n\n"
                    "No comparison was completed.")

            history = review.last_commit_messages(repo)

            for sha in (source_sha, comparison_sha):
                self.assertIn("commit " + sha + "\n", history)
            prompt = review.reviewer_prompt(Path("/r"), repo / "skills" / "shiploop", history)
            self.assertIn("Keep the accepted source-scope lesson.", prompt)
            self.assertIn("Substantive measured learning remains applicable.", prompt)

    def test_default_history_marks_quoted_rejected_candidates_as_unadopted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, git = self.history_repo(tmp)
            git("commit", "-q", "--allow-empty", "-m",
                "test(e2e): qualified cycle for LR-rejected: DROP\n\n"
                "Candidate author claimed: fix the archived defect.\n\nDecision DROP: candidate not adopted.")

            history = review.last_commit_messages(repo)

            self.assertIn("Candidate author claimed: fix the archived defect.", history)
            self.assertIn("Decision DROP", history)
            self.assertIn("unadopted", history.lower())
            self.assertIn("explicit disposition", history.lower())

    RESULT = {"host": "grok", "model": "grok-4.7", "effort": "medium", "pass": False,
              "process": {"status": "failed", "returncode": 1, "elapsed_seconds": 12.5},
              "shiploop": {"status": "active", "stage": "regression", "report_html": False},
              "product_at_stop": {"information_only": True, "ran": True, "worktree": "/w", "total": 1, "passed": 1,
                                  "failed": 0, "timed_out": 0,
                                  "engine": {"status": "active", "stage": "regression"},
                                  "checks": [{"command": "node --test", "pass": True, "returncode": 0, "timed_out": False}]},
              "checks": [{"command": "node --test", "pass": False}],
              "cli": {"num_turns": 150, "cost_usd": 10.88,
                      "truncated_outputs": [{"total_bytes": 36000, "shown_chars": 20467, "call": "x"}]}}
    VERDICT = {"outcome": "Capped before return.",
               "learnings": [{"title": "Return earlier", "evidence": "work/ empty", "proposal": "p",
                              "files": ["skills/shiploop/SKILL.md"], "severity": "material",
                              "preserves_premise": True, "premise_note": "script decides"}],
               "optimizations": [{"title": "Let the model pick stages", "severity": "material",
                                  "preserves_premise": False}],
               "harness": {"further_learning": {"answer": "Compare stage costs", "proposals": ["track per stage"]}}}

    def message(self) -> str:
        verdict = dict(self.VERDICT, actionable=review.actionable(self.VERDICT))
        args = iterate.argparse.Namespace(case="battleship")
        return iterate.learnings_message(2, args, "0123456789ab", self.RESULT, verdict, ["aaa1111", "bbb2222"])

    def test_message_details_outcome_findings_and_prior_learnings(self):
        message = self.message()
        self.assertTrue(message.startswith(
            "test(shiploop): record E2E iteration 2 learnings (battleship, grok medium)\n\n"))
        for text in ("150 turns", "stage regression", "product at stop (information only, engine active at regression): 1/1",
                     "host truncated 1 tool outputs", "Evidence: work/ empty", "requires separate disposition",
                     "- apply: Return earlier", "Built on the learnings of aaa1111, bbb2222.",
                     "- further learning: Compare stage costs", "  proposal: track per stage",
                     "- evaluation criteria: not answered"):
            self.assertIn(text, message)
        self.assertTrue(message.rstrip().endswith("<shiploop-e2e@example.invalid>"))

    def test_a_cost_the_host_did_not_report_is_not_printed_as_a_dollar_figure(self):
        args = iterate.argparse.Namespace(case="battleship")
        verdict = dict(self.VERDICT, actionable=review.actionable(self.VERDICT))
        message = iterate.learnings_message(2, args, "0123456789ab", dict(self.RESULT, cli={"num_turns": 2189,
                                                                                            "cost_usd": None}),
                                            verdict, [])
        self.assertIn("2189 turns, cost not reported", message)
        self.assertNotIn("$None", message)
        self.assertIn("150 turns, cost $10.88", self.message())

    def test_record_learnings_appends_and_commits_only_the_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "test" / "shiploop_e2e").mkdir(parents=True)
            (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").write_text("# ShipLoop E2E learnings\n")
            (repo / "untracked.txt").write_text("stay out")
            for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"],
                        ["config", "user.email", "t@example.invalid"], ["add", "test"],
                        ["commit", "-q", "-m", "base"]):
                subprocess.run(["git", "-C", str(repo), *cmd], check=True)
            stage = Path(tmp) / "stage"
            stage.mkdir()
            iterate.record_learnings(repo, self.message(), stage)
            journal = (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
            self.assertIn("## E2E iteration 2 learnings (battleship, grok medium)", journal)
            self.assertNotIn("Co-Authored-By", journal)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md"])
            body = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%B"],
                                  capture_output=True, text=True, check=True).stdout
            self.assertIn("Built on the learnings of aaa1111, bbb2222.", body)

    def test_record_learnings_commits_the_run_review_export_in_the_same_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "test" / "shiploop_e2e").mkdir(parents=True)
            (repo / "test" / "shiploop_e2e" / "LEARNINGS.md").write_text("# ShipLoop E2E learnings\n")
            for cmd in (["init", "-q", "-b", "main"], ["config", "user.name", "t"],
                        ["config", "user.email", "t@example.invalid"], ["add", "test"],
                        ["commit", "-q", "-m", "base"]):
                subprocess.run(["git", "-C", str(repo), *cmd], check=True)
            stage = Path(tmp) / "stage"
            bundle = stage / "run" / "review-export" / "review-export.json"
            bundle.parent.mkdir(parents=True)
            text = json.dumps({"schema": "run-review-export/v2", "docs": {"runs": {"grok-1.0.0-hello-20261004": {}}}})
            bundle.write_text(text)
            iterate.record_learnings(repo, self.message(), stage)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            evidence = "test/shiploop_e2e/evidence/grok-1.0.0-hello-20261004.json"
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md", evidence])
            self.assertEqual((repo / evidence).read_text(), text)
            bundle.write_text("not json")  # an unreadable export never blocks the learnings commit
            iterate.record_learnings(repo, self.message(), stage)
            files = subprocess.run(["git", "-C", str(repo), "show", "--name-only", "--format=", "HEAD"],
                                   capture_output=True, text=True, check=True).stdout.split()
            self.assertEqual(files, ["test/shiploop_e2e/LEARNINGS.md"])

    def test_reviewer_and_improver_prompts_carry_prior_learnings(self):
        prior = "commit abc1234\nRun 1 learned the graph is fixed.\n"
        self.assertIn("Run 1 learned the graph is fixed.", review.reviewer_prompt(Path("/r"), Path("/s"), prior))
        self.assertNotIn("Learnings recorded", review.reviewer_prompt(Path("/r"), Path("/s")))
        self.assertIn("Run 1 learned the graph is fixed.", iterate.improver_prompt(Path("/w"), [], "base", prior))
        improver = iterate.improver_prompt(Path("/w"), [], "base")
        self.assertIn("adversarial evaluation", improver)
        self.assertIn("mitigated and tested / accepted with the clause that asks for it", improver)
        self.assertIn("**Adversarial evaluation first.**", improver)  # the spec, loaded as the premise


class FastPlanningRecordTest(unittest.TestCase):
    """The fast-planning decision keeps its evidence in the repository and its SPEC carve-out.

    Existence checks only: no prose is pinned. The option's name, default and values are
    pinned against the code constants where those exist (test/shiploop-navigator-contract.test.py).
    """

    EVIDENCE = ROOT / "docs" / "experiments" / "shiploop-fast-planning-20261004"

    def test_the_evidence_the_journal_cites_is_in_the_repository(self):
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-fast-planning-20261004/", journal)
        self.assertIn("docs/shiploop-fast-planning-plan-2026-10-04.md", journal)
        for name in ("README.md", "design-final.json", "report-knobs.txt", "report-pass-value-and-cost.txt",
                     "report-planning-prompts.txt", "attack-quality-kiss.json", "attack-engine-correctness.json",
                     "gate_experiment.py", "gate_experiment.out"):
            self.assertTrue((self.EVIDENCE / name).is_file(), name)
        self.assertTrue((ROOT / "docs" / "shiploop-fast-planning-plan-2026-10-04.md").is_file())
        json.loads((self.EVIDENCE / "design-final.json").read_text())

    def test_spec_s10_names_its_carve_outs(self):
        spec = (ROOT / "test" / "shiploop_e2e" / "SPEC.md").read_text()
        s10 = " ".join(spec[spec.index("**S-10 Loops"):spec.index("**S-11")].split())  # the SPEC is hard-wrapped
        self.assertIn("Except for the carve-outs below, there is no iteration cap", s10)
        for heading in ("**S-10 carve-out, owner decision 2026-10-04**", "**S-10 carve-out, owner decision 2026-10-05**"):
            self.assertIn(heading, s10)
        for option in ("--backchain-passes converge", "--backchain-passes none", "backchain_passes",
                       "--planning-review stage", "--planning-review none", "planning_review"):
            self.assertIn(option, s10)

    def test_the_planning_review_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "shiploop-planning-review-20261005"
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-planning-review-20261005/", journal)
        self.assertIn("docs/shiploop-planning-review-plan-2026-10-05.md", journal)
        self.assertTrue((ROOT / "docs" / "shiploop-planning-review-plan-2026-10-05.md").is_file())
        for name in ("README.md", "design-draft.json", "design-final.json", "report-engine.txt",
                     "report-consumers.txt", "report-value.txt", "report-rules-and-wording.txt",
                     "attack-measurement-and-text.json", "attack-engine-correctness.json",
                     "sonnet-plan-review-b1e196d.txt", "e6b-excerpt.md", "probe_judge.py", "probe_judge.out",
                     "passes.py", "passes.out"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("design-draft.json", "design-final.json", "attack-measurement-and-text.json",
                     "attack-engine-correctness.json"):
            json.loads((evidence / name).read_text())

    def test_the_statements_the_planning_review_supersedes_say_so(self):
        for name in ("shiploop-fast-planning-plan-2026-10-04.md", "shiploop-delivery-overhead-plan-2026-09-23.md"):
            text = " ".join((ROOT / "docs" / name).read_text().split())
            self.assertIn("Superseded 2026-10-05", text, name)
            self.assertIn("docs/shiploop-planning-review-plan-2026-10-05.md", text, name)

    def test_the_planning_time_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "shiploop-planning-time-20261005"
        journal = (ROOT / "test" / "shiploop_e2e" / "LEARNINGS.md").read_text()
        self.assertIn("docs/experiments/shiploop-planning-time-20261005/", journal)
        for name in ("README.md", "ledger-account-final.json", "stage-clock.md", "grok-medium-improve-children.json",
                     "run-doc-luna-xhigh-v1210.json", "run-doc-grok-medium-v1210.json"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("ledger-account-final.json", "grok-medium-improve-children.json",
                     "run-doc-luna-xhigh-v1210.json", "run-doc-grok-medium-v1210.json"):
            json.loads((evidence / name).read_text())

    def test_the_doccheck_evidence_and_the_batch_1008_design_audit_are_in_the_repository(self):
        # The DOCCHECK figures were produced by a classifier that was not kept, so this pins presence and shape: the
        # committed output, the audit entries the journal cites, and the dated note that supersedes the ledger's L11.
        journal = (ROOT / "docs" / "shiploop-batch-1008a-journal-2026-10-08.md").read_text()
        audit = ROOT / "docs" / "experiments" / "batch-1008-design-audit-20261008" / "design-audit.json"
        evidence = ROOT / "docs" / "experiments" / "docheck-20261008" / "evidence.json"
        for path in (audit, evidence):
            self.assertIn(str(path.relative_to(ROOT)), journal)
        entries = {row["key"]: row for row in json.loads(audit.read_text())}
        for key in ("DOCCHECK", "REGISTER", "B6", "REVISE"):
            self.assertEqual(sorted(entries[key]), ["audit", "design", "key", "title"], key)
        data = json.loads(evidence.read_text())
        luna = data["luna_xhigh_1210"]
        self.assertEqual(sum(row["scripts"] for row in luna["inline_scripts_by_purpose"]), luna["inline_scripts"])
        for key in ("end_state", "caveats", "superseded_figure"):
            self.assertTrue(data[key], key)
        ledger_readme = ROOT / "docs" / "experiments" / "shiploop-planning-time-20261005" / "README.md"
        self.assertIn("Superseded 2026-10-08: lever L11", ledger_readme.read_text())

    def test_the_ci_audit_evidence_is_in_the_repository(self):
        evidence = ROOT / "docs" / "experiments" / "ci-audit-20261005"
        for name in ("README.md", "ci-audit-final.json", "name-collision-trace.json", "dump_selection.py"):
            self.assertTrue((evidence / name).is_file(), name)
        for name in ("ci-audit-final.json", "name-collision-trace.json"):
            json.loads((evidence / name).read_text())

    def test_the_gate_experiment_output_is_what_the_script_prints(self):
        script = self.EVIDENCE / "gate_experiment.py"
        done = subprocess.run([sys.executable, "-B", str(script)], capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertEqual(done.stdout, (self.EVIDENCE / "gate_experiment.out").read_text())


class ReviewExportTest(HarnessCase):
    def run_printed(self, *extra: str) -> tuple[int, dict, str]:
        os.environ["FAKE_MODE"] = "done"
        out, printed = self.tmp / "out-export", io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "claude", "--backend", "anthropic", "--claude-bin", str(self.fakes["claude"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_an_export_problem_is_printed_and_never_changes_the_verdict(self):
        # The fake run's state has no timeline.json, so the exporter refuses it.
        code, result, printed = self.run_printed()
        self.assertEqual(code, 0, printed)
        self.assertTrue(result["pass"])
        self.assertRegex(printed, r"review export skipped: missing .*timeline\.json")
        raising = self.tmp / "raising.py"
        raising.write_text("def export_run(out):\n    raise RuntimeError('boom')\n")
        with mock.patch.object(run, "REVIEW_EXPORTER", raising):
            shutil.rmtree(self.tmp / "out-export")
            code, result, printed = self.run_printed()
        self.assertEqual((code, result["pass"]), (0, True))
        self.assertIn("review export skipped: boom", printed)

    def test_a_run_with_shiploop_records_is_exported_into_its_output_directory(self):
        out = self.tmp / "graded"
        state_dir = out / ".shiploop-runs" / "work-1" / "run"
        run.store.write_record(state_dir / "state.md", {"status": "done", "stage": "done", "history": [
            {"action": "nav-0123456789abcdef", "stage": "intake", "outcome": "done"}]})
        run.store.write_record(state_dir / "results" / "nav-0123456789abcdef.md",
                           {"action": "nav-0123456789abcdef", "stage": "intake", "result": {"outcome": "done"}})
        (state_dir / "timeline.json").write_text(json.dumps({"started": "2026-10-04T10:00:00Z", "accepted": {
            "nav-0123456789abcdef": "2026-10-04T10:03:00Z"}}))
        (out / "metrics.json").write_text(json.dumps({"shiploop_failures": [], "model_glue": [], "unmeasured": {}}))
        line = run.review_export(out)
        folder = (out / 'review-export').resolve()
        # The exporter also writes the static page (run-review.html, shiploop-run-review 0.1.3): its path is printed after the
        # folder, so a reader of the report finds the page without listing the folder.
        self.assertTrue((folder / "run-review.html").is_file(), "the exporter writes the standalone page beside the bundle")
        self.assertEqual(line, f"review export: {folder}; page {folder / 'run-review.html'}")
        bundle = json.loads((out / "review-export" / "review-export.json").read_text())
        self.assertEqual([s["min"] for s in next(iter(bundle["docs"]["runs"].values()))["stages"]], [3.0])

    def test_preflight_only_never_exports(self):
        with mock.patch.object(run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})), \
                mock.patch.object(run, "review_export") as exporter:
            self.assertEqual(run.main(["--preflight-only", "--host", "claude", "--backend", "anthropic", "--output", str(self.tmp / "pf")]), 0)
        exporter.assert_not_called()


class ReviewAdviseLineTest(unittest.TestCase):
    def test_the_step_after_the_learnings_commit_names_the_advise_mode_and_the_run_directory(self):
        self.assertEqual(iterate.review_line(2, Path("/out/iter-2/run")),
                         "== iteration 2: update the Run Review page: "
                         "/skill-craft:shiploop-run-review advise /out/iter-2/run")


class GradeIdentityTest(unittest.TestCase):
    """The 2026-10-16 E2E audit's state control (docs/experiments/shiploop-e2e-audit-20261016/grading/state-binding-fixture):
    an output folder holding this invocation's active run in work/.shiploop and an unrelated finished run beside it was
    graded from the finished one, a pass nobody earned."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name).resolve()

    def state(self, relative: str, status: str, report: bool = False) -> str:
        folder = self.out / relative
        run.store.write_record(folder / "state.md", {"status": status, "stage": status == "done" and "done" or "implement",
                                                      "revision": 3})
        if report:
            (folder / "report.html").write_text("<html></html>")
        return str(folder)

    def audit_fixture(self) -> tuple[str, str]:
        return self.state("work/.shiploop", "active"), self.state(".shiploop-runs/stale/run", "done", report=True)

    def test_an_active_run_beside_a_stale_finished_one_is_never_graded_from_the_finished_one(self):
        active, stale = self.audit_fixture()
        graded = run.grade_shiploop(self.out)
        self.assertFalse(graded["pass"])
        self.assertNotEqual(graded.get("run_dir"), stale)
        self.assertIn("ambiguous", graded["reason"])
        self.assertEqual(sorted(graded["ambiguous"]), sorted([active, stale]))

    def test_a_run_that_existed_before_the_invocation_started_is_not_a_candidate(self):
        stale = self.state(".shiploop-runs/stale/run", "done", report=True)
        run.record_preexisting_runs(self.out)
        active = self.state("work/.shiploop", "active")
        graded = run.grade_shiploop(self.out)
        self.assertEqual((graded["run_dir"], graded["status"], graded["pass"]), (active, "active", False))
        self.assertNotEqual(graded["run_dir"], stale)

    def test_the_recorded_run_is_graded_and_a_resume_keeps_it_when_another_run_appears(self):
        active = self.state("work/.shiploop", "active")
        self.assertEqual(run.grade_shiploop(self.out)["run_dir"], active)  # the only run: bound now
        self.assertEqual(json.loads((self.out / run.RUN_IDENTITY).read_text())["run_dir"], active)
        self.state(".shiploop-runs/other/run", "done", report=True)
        graded = run.grade_shiploop(self.out)
        self.assertEqual((graded["run_dir"], graded["pass"], graded["identity"]), (active, False, "recorded"))

    def test_several_new_runs_are_resolved_only_by_the_run_the_host_named(self):
        first = self.state(".shiploop-runs/a/run", "done", report=True)
        second = self.state(".shiploop-runs/b/run", "active")
        self.assertIn("ambiguous", run.grade_shiploop(self.out)["reason"])
        command = f'python3 "/x/shiploop" next --run-dir "{second}"'
        (self.out / "events.jsonl").write_text(json.dumps({"type": "tool_call", "rawInput": {"command": command}}) + "\n")
        graded = run.grade_shiploop(self.out)
        self.assertEqual((graded["run_dir"], graded["pass"]), (second, False))
        self.assertNotEqual(graded["run_dir"], first)

    def test_a_new_run_that_reuses_the_path_of_a_copied_one_is_this_invocations(self):
        self.state("work/.shiploop", "done", report=True)
        run.record_preexisting_runs(self.out)
        self.assertIn("every state.md was there before", run.grade_shiploop(self.out)["reason"])
        reused = self.state("work/.shiploop", "active")
        graded = run.grade_shiploop(self.out)
        self.assertEqual((graded["run_dir"], graded["status"], graded["pass"]), (reused, "active", False))

    def test_a_run_in_an_external_workspace_root_beside_work_is_graded(self):
        external = self.state(".shiploop-runs/work-20261016-abc/run", "done", report=True)
        (self.out / "work").mkdir(exist_ok=True)
        graded = run.grade_shiploop(self.out)
        self.assertEqual((graded["run_dir"], graded["pass"]), (external, True))

    def test_a_run_inside_the_repository_is_graded(self):
        inside = self.state("work/.shiploop", "done", report=True)
        self.assertEqual((run.grade_shiploop(self.out)["run_dir"], run.grade_shiploop(self.out)["pass"]), (inside, True))


class MultipleRunsTest(unittest.TestCase):
    """A model that abandons its first ShipLoop run and starts a second leaves two runs in the output folder (brownfield
    bf-ds-r1-ticket-assignment, 2026-10-29: the first paused with a status_reason saying it was replaced, the second live).
    Five readers say which run the folder holds: grade_shiploop (the verdict), metrics.run_dir_of (every measurement that
    reads the run's files), progress.report (the live monitor), status_card.build_e2e (the Live Run Card the owner is fed
    each tick) and packets.find_run_dir (the run flow.build, packets.build and the owner page describe). They share one
    rule, so each case here asks all five: a run is told apart by its revision, which the monitor prints, the card draws
    (the run's trace starts at its revision) and the other three return as the run directory."""

    STAMP = 1_800_000_000  # seconds; the state.md of each run is stamped from here so the newest state change is known

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name).resolve()
        self.written = 0

    def make(self, name: str, status: str, revision: int, *, changed: int | None = None, report: bool = False,
             stage: str | None = None) -> str:
        """One run under .shiploop-runs/<name>/run, its state.md stamped `changed` seconds after STAMP (default: later than
        the runs written before it)."""
        folder = self.out / ".shiploop-runs" / name / "run"
        state = {"status": status, "stage": stage or ("done" if status == "done" else "implement"), "revision": revision}
        if status in ("paused", "blocked", "halted"):
            state["status_reason"] = f"{status} by the test"
        run.store.write_record(folder / "state.md", state)
        # The Live Run Card draws no revision; it draws the run's trace on a time axis that starts at the trace's first row.
        (folder / "trace.jsonl").write_text(json.dumps({"kind": "command", "verb": "workspace", "exit": 0, "ts": float(revision)}) + "\n")
        if report:
            (folder / "report.html").write_text("<html></html>")
        self.written += 1
        stamp = (self.STAMP + (self.written if changed is None else changed)) * 10 ** 9
        os.utime(folder / "state.md", ns=(stamp, stamp))
        return str(folder)

    def readers(self) -> tuple[dict, str | None, int | None, str]:
        """(the graded verdict, the directory run_dir_of returns, the revision the monitor shows, the monitor's text)."""
        graded = run.grade_shiploop(self.out)
        picked = metrics.run_dir_of(self.out)
        text = progress.report(self.out)
        shown = re.search(r"\| \w+, rev (\d+),", text)
        return graded, str(picked) if picked else None, int(shown.group(1)) if shown else None, text

    def card(self) -> tuple[int | None, dict, dict]:
        """(the revision the Live Run Card drew, its model, its meta); None where it drew no run."""
        model, meta = status_card.build_e2e(self.out)
        return (int(model["timeline"]["start"]) if model.get("timeline") else None), model, meta

    def packet_reader(self) -> str | None:
        """What packets.find_run_dir answers: the directory, None, or the message of the exit it makes."""
        try:
            found = packets.find_run_dir(self.out)
        except SystemExit as stopped:
            return str(stopped)
        return str(found) if found else None

    def assert_chosen(self, directory: str, revision: int) -> dict:
        graded, picked, shown, text = self.readers()
        self.assertEqual(graded.get("run_dir"), directory, graded)
        self.assertEqual(picked, directory)
        self.assertEqual(shown, revision, text)
        drawn, _model, meta = self.card()
        self.assertEqual(drawn, revision, meta)
        self.assertFalse(any("ambiguous" in event["text"] for event in meta["events"]), meta)
        self.assertEqual(self.packet_reader(), directory)
        return graded

    def assert_ambiguous(self, *directories: str) -> dict:
        graded, picked, shown, text = self.readers()
        self.assertFalse(graded["pass"])
        self.assertEqual(sorted(graded.get("ambiguous", [])), sorted(directories), graded)
        self.assertIn("ambiguous", graded["reason"])
        self.assertIsNone(picked)
        self.assertIsNone(shown, text)
        self.assertIn(f"ambiguous: {len(directories)} ShipLoop runs", text)
        # The card draws no run, and says why instead of drawing the first one in path order.
        drawn, model, meta = self.card()
        self.assertIsNone(drawn, meta)
        self.assertEqual(model["rows"], [])
        self.assertIn(f"ambiguous: {len(directories)} ShipLoop runs", meta["events"][0]["text"])
        # packets.find_run_dir exits with the same words; flow.build, packets.build and the owner page stop there.
        self.assertIn(f"ambiguous: {len(directories)} ShipLoop runs", self.packet_reader() or "")
        return graded

    # ---- the reported defect

    def test_a_run_the_model_paused_and_replaced_is_not_the_run_while_its_live_successor_is(self):
        first = self.make("work-1", "paused", 1, stage="intake")
        second = self.make("work-2", "active", 5, stage="test-strategy")
        graded = self.assert_chosen(second, 5)
        self.assertEqual((graded["status"], graded["pass"], graded["runs"], graded["other_runs"]), ("active", False, 2, [first]))
        self.assertNotIn("paused", self.readers()[3].split("\n")[0])

    def test_the_choice_follows_the_runs_statuses_so_it_is_not_recorded_as_the_runs_identity(self):
        self.make("work-1", "paused", 1)
        self.make("work-2", "active", 5)
        self.assert_chosen(str(self.out / ".shiploop-runs" / "work-2" / "run"), 5)
        self.assertNotIn("run_dir", run.run_identity(self.out))

    def test_a_live_run_is_preferred_to_a_paused_one_whichever_changed_last(self):
        first = self.make("work-1", "paused", 1, changed=500)
        second = self.make("work-2", "active", 5, changed=100)
        self.assert_chosen(second, 5)
        self.assertNotEqual(second, first)

    def test_a_halted_run_is_set_aside_as_a_paused_one_is(self):
        self.make("work-1", "halted", 1)
        second = self.make("work-2", "active", 5)
        self.assert_chosen(second, 5)

    def test_a_blocked_run_is_still_in_play_beside_a_paused_one(self):
        blocked = self.make("work-1", "blocked", 1, changed=100)
        self.make("work-2", "paused", 5, changed=500)
        self.assert_chosen(blocked, 1)

    def test_the_live_run_is_found_among_several_that_were_set_aside(self):
        first = self.make("work-1", "paused", 1)
        second = self.make("work-2", "halted", 2)
        third = self.make("work-3", "active", 5)
        graded = self.assert_chosen(third, 5)
        self.assertEqual(graded["other_runs"], [first, second])

    # ---- candidates that nothing tells apart

    def test_two_live_runs_stay_ambiguous_and_the_newer_one_is_not_picked(self):
        first = self.make("work-1", "active", 1, changed=100)
        second = self.make("work-2", "active", 5, changed=500)
        graded = self.assert_ambiguous(first, second)
        self.assertEqual(graded["runs"], 2)
        self.assertNotIn("other_runs", graded)

    def test_a_finished_run_beside_an_active_one_stays_ambiguous(self):
        # The 2026-10-16 audit's control: an unrelated finished run is never preferred, and nothing prefers the active one either.
        finished = self.make("work-1", "done", 3, report=True, changed=500)
        active = self.make("work-2", "active", 5, changed=100)
        self.assert_ambiguous(finished, active)

    def test_the_live_runs_that_remain_are_the_only_ones_listed_as_ambiguous(self):
        self.make("work-1", "paused", 1)
        second = self.make("work-2", "active", 5)
        third = self.make("work-3", "active", 7)
        graded = self.assert_ambiguous(second, third)
        self.assertEqual(graded["runs"], 3)
        self.assertIn("2 ShipLoop runs under the output directory that are not paused or halted", graded["reason"])

    def test_the_host_naming_one_of_two_live_runs_resolves_them_in_every_reader(self):
        first = self.make("work-1", "active", 1)
        second = self.make("work-2", "active", 5)
        self.assert_ambiguous(first, second)
        command = f'python3 "/x/shiploop" next --run-dir "{first}"'
        (self.out / "events.jsonl").write_text(json.dumps({"type": "tool_call", "rawInput": {"command": command}}) + "\n")
        graded = self.assert_chosen(first, 1)
        self.assertEqual(graded["other_runs"], [second])

    def test_a_paused_run_the_host_named_does_not_beat_a_live_one_it_did_not(self):
        paused = self.make("work-1", "paused", 1)
        live = self.make("work-2", "active", 5)
        command = f'python3 "/x/shiploop" pause --run-dir "{paused}"'
        (self.out / "events.jsonl").write_text(json.dumps({"type": "tool_call", "rawInput": {"command": command}}) + "\n")
        self.assert_chosen(live, 5)

    def test_a_run_dir_naming_an_unknown_user_does_not_crash_a_reader(self):
        first = self.make("work-1", "active", 1)
        second = self.make("work-2", "active", 5)
        commands = ['python3 "/x/shiploop" next --run-dir "~no_such_user_for_this_test/run"',
                    f'python3 "/x/shiploop" next --run-dir "{first}"']
        (self.out / "events.jsonl").write_text(
            "\n".join(json.dumps({"type": "tool_call", "rawInput": {"command": command}}) for command in commands) + "\n")
        graded = self.assert_chosen(first, 1)
        self.assertEqual(graded["other_runs"], [second])

    # ---- no run is live

    def test_when_every_run_was_set_aside_the_one_changed_last_is_the_run(self):
        first = self.make("work-1", "paused", 1, changed=500)
        second = self.make("work-2", "halted", 5, changed=100)
        graded = self.assert_chosen(first, 1)
        self.assertEqual((graded["status"], graded["other_runs"]), ("paused", [second]))

    def test_set_aside_runs_changed_at_the_same_moment_stay_ambiguous(self):
        first = self.make("work-1", "paused", 1, changed=100)
        second = self.make("work-2", "paused", 5, changed=100)
        self.assert_ambiguous(first, second)

    def test_a_finished_run_beside_a_paused_one_is_the_run_and_its_pass_is_its_own(self):
        finished = self.make("work-1", "done", 3, report=True, changed=100)
        self.make("work-2", "paused", 5, changed=500)
        graded = self.assert_chosen(finished, 3)
        self.assertTrue(graded["pass"])

    # ---- the identity the harness recorded still wins

    def test_a_recorded_run_wins_in_every_reader_even_when_it_is_the_paused_one(self):
        recorded = self.make("work-1", "paused", 1)
        self.make("work-2", "active", 5)
        run.record_run_identity(self.out, run_dir=recorded, basis="seeded by the harness")
        graded = self.assert_chosen(recorded, 1)
        self.assertEqual(graded["identity"], "recorded")

    def test_a_recorded_run_whose_state_is_gone_is_chosen_again_by_the_rule(self):
        gone = self.make("work-1", "paused", 1)
        paused = self.make("work-2", "paused", 2)
        live = self.make("work-3", "active", 7)
        run.record_run_identity(self.out, run_dir=gone, basis="seeded by the harness")
        (Path(gone) / "state.md").unlink()
        graded = self.assert_chosen(live, 7)
        self.assertEqual(graded["other_runs"], [paused])

    def test_runs_that_were_there_before_the_invocation_are_candidates_for_no_reader(self):
        stale = self.make("a-stale", "done", 3, report=True)
        run.record_preexisting_runs(self.out)
        live = self.make("work-2", "active", 5)
        graded = self.assert_chosen(live, 5)
        self.assertNotEqual(graded["run_dir"], stale)

    # ---- state files that are not runs

    def test_a_state_file_nobody_can_read_is_not_a_run(self):
        self.make("work-1", "paused", 1)
        live = self.make("work-2", "active", 5)
        broken = self.out / ".shiploop-runs" / "work-3" / "run" / "state.md"
        broken.parent.mkdir(parents=True)
        broken.write_bytes(b"not a record \xff\xfe")
        graded = self.assert_chosen(live, 5)
        self.assertEqual(graded["runs"], 2)

    def test_one_readable_run_beside_an_unreadable_one_is_the_only_run(self):
        paused = self.make("work-1", "paused", 1)
        broken = self.out / ".shiploop-runs" / "work-2" / "run" / "state.md"
        broken.parent.mkdir(parents=True)
        broken.write_text("# no state fence here\n")
        graded = self.assert_chosen(paused, 1)
        self.assertEqual(graded["identity"], "the only run that was not there before the invocation")
        self.assertNotIn("other_runs", graded)

    # ---- a folder with exactly one run is graded as it always was

    def test_exactly_one_run_grades_with_the_same_keys_in_the_same_order_whatever_its_status(self):
        for status, report in (("paused", False), ("active", False), ("done", True), ("halted", False)):
            with self.subTest(status=status):
                shutil.rmtree(self.out / ".shiploop-runs", ignore_errors=True)
                (self.out / run.RUN_IDENTITY).unlink(missing_ok=True)
                only = self.make("only", status, 4, report=report)
                graded = self.assert_chosen(only, 4)
                self.assertEqual(list(graded), ["pass", "run_dir", "status", "stage", "revision", "report_html", "runs", "identity",
                                                "worktree"])
                self.assertEqual(graded, {"pass": status == "done", "run_dir": only, "status": status,
                                          "stage": "done" if status == "done" else "implement", "revision": 4,
                                          "report_html": report, "runs": 1,
                                          "identity": "the only run that was not there before the invocation", "worktree": None})
                self.assertEqual(run.run_identity(self.out)["run_dir"], only)  # one run: bound at the first grade, as before


class FollowOnTest(HarnessCase):
    def prior_run(self) -> Path:
        prior = self.tmp / "prior"
        work = prior / "work"
        work.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        (work / "prior.txt").write_text("kept\n")
        (work / ".git" / "worktrees" / "stale").mkdir(parents=True)
        (prior / "result.json").write_text(json.dumps({"case": "hello", "pass": True,
                                                        "metrics": {"turns": 40, "cost_usd": 2.5}}))
        return prior

    def test_follow_on_starts_in_a_copy_of_the_earlier_checkout(self):
        prior = self.prior_run()
        code, result = self.invoke("grok", "done", "--continue-from", str(prior), "--prompt", "Add a feature.",
                                   "--check", 'test -f "$PRIOR_WORK/prior.txt" && test -f prior.txt')
        self.assertEqual(code, 0, result)
        self.assertIn("prior.txt", self.seen()["cwd_listing"])
        work = Path(result["output"]) / "work"
        self.assertFalse((work / ".git" / "worktrees").exists())
        self.assertTrue((prior / "work" / ".git" / "worktrees" / "stale").is_dir(), "the earlier run is untouched")
        self.assertEqual(result["follow_on"]["prior_case"], "hello")
        self.assertEqual(result["follow_on"]["prior_turns"], 40)
        self.assertEqual(result["follow_on"]["prior_cost_usd"], 2.5)

    def test_a_follow_on_never_counts_the_run_its_copy_brought_along(self):
        prior = self.prior_run()
        run.store.write_record(prior / "work" / ".shiploop-old" / "state.md", {"status": "done", "stage": "done"})
        (prior / "work" / ".shiploop-old" / "report.html").write_text("<html></html>")
        code, result = self.invoke("grok", "done", "--continue-from", str(prior), "--prompt", "Add a feature.")
        self.assertEqual(code, 0, result)
        identity = json.loads((Path(result["output"]) / run.RUN_IDENTITY).read_text())
        self.assertEqual(list(identity["preexisting"]), [str(Path(result["output"]) / "work" / ".shiploop-old")])
        self.assertEqual(identity["run_dir"], str(Path(result["output"]) / "work" / ".shiploop"))
        self.assertEqual(result["shiploop"]["run_dir"], identity["run_dir"])

    def test_follow_on_case_needs_the_run_it_follows(self):
        with self.assertRaises(SystemExit) as raised:
            self.invoke("grok", "done", "--case", "battleship-scoring")
        self.assertIn("--continue-from", str(raised.exception))

    def test_follow_on_case_checks_regression_feature_and_retention(self):
        cases = json.loads(run.CASES.read_text())
        args = run.parser().parse_args(["--case", "battleship-scoring"])
        name, _, checks, follows = run.load_case(args)
        case = cases[name]
        self.assertEqual(follows, "battleship")
        self.assertEqual(checks, cases["battleship"]["checks"] + case["checks"] + case["retention"])
        self.assertTrue(all("PRIOR_WORK" in check for check in case["retention"]))


class StageAttributionTest(unittest.TestCase):
    """Per-stage attribution reads ShipLoop's own records and never invents timing."""

    def collect(self, accepted: list, *, status: str = "done", stage: str | None = None,
                inner: dict | None = None, events: int = 6) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            stream = [{"type": "usage", "usage": {"input_tokens": 100, "output_tokens": 1}}
                      for _n in range(events)]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            (out / "timeline.jsonl").write_text("\n".join(json.dumps({"line": n, "t": 100.0 + n})
                                                          for n in range(events)) + "\n")
            write_engine_records(run_dir, accepted, status=status, stage=stage, inner=inner)
            return metrics.collect(out, run_dir)

    def test_an_action_without_a_readable_stamp_reports_unavailable_not_zero(self):
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "spec", "done", None)])
        self.assertEqual(m["stages"][1], {"stage": "spec", "outcome": "done", "timing": "unavailable"})
        self.assertIn("seconds", m["stages"][0])

    def test_without_any_runner_timeline_every_stage_is_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            (out / "events.jsonl").write_text(json.dumps(
                {"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}) + "\n")
            write_engine_records(run_dir, [("A1", "intake", "done", 101.0)])
            m = metrics.collect(out, run_dir)
        self.assertEqual(m["stages"], [{"stage": "intake", "outcome": "done", "timing": "unavailable"}])

    def test_the_stage_an_active_run_never_accepted_is_still_attributed(self):
        m = self.collect([("A1", "intake", "done", 101.0)], status="active", stage="spec")
        self.assertEqual([s["stage"] for s in m["stages"]], ["intake", "spec"])
        incomplete = m["stages"][-1]
        self.assertTrue(incomplete["incomplete"])
        self.assertGreater(incomplete["turns"], 0)  # the work after the last acceptance

    def test_an_active_inner_loop_reports_the_items_own_stage(self):
        m = self.collect([("A1", "intake", "done", 101.0)], status="active", stage="inner-loop",
                         inner={"work_index": 0, "work_items": [{"id": "W1", "title": "t"}],
                                "inner_loops": {"W1": {"stage": "implement", "action": None}}})
        self.assertEqual(m["stages"][-1]["stage"], "implement")

    def test_a_finished_run_adds_no_incomplete_row(self):
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "handoff", "done", 102.0)])
        self.assertTrue(all(not s.get("incomplete") for s in m["stages"]))

    def test_a_stage_after_an_unstamped_one_is_not_credited_with_its_time(self):
        """Its window covers both actions, so attributing it all here would overstate it."""
        m = self.collect([("A1", "intake", "done", 101.0), ("A2", "spec", "done", None),
                          ("A3", "plan", "done", 104.0), ("A4", "prepare", "done", 105.0)])
        timing = [(s["stage"], s.get("timing", "measured")) for s in m["stages"]]
        self.assertEqual(timing, [("intake", "measured"), ("spec", "unavailable"),
                                  ("plan", "unavailable"), ("prepare", "measured")])
        # Attribution resumes from the next known boundary, not from before the gap.
        self.assertEqual(m["stages"][3]["seconds"], 1.0)

    def test_both_stamp_precisions_the_engine_writes_are_read(self):
        """The navigator writes second precision; other records use microseconds."""
        self.assertEqual(metrics._epoch("1970-01-01T00:01:41Z"), 101.0)
        self.assertEqual(metrics._epoch("1970-01-01T00:01:41.500000Z"), 101.5)
        self.assertIsNone(metrics._epoch("not a time"))
        self.assertIsNone(metrics._epoch(None))

    def test_a_stage_row_carries_no_output_token_figure(self):
        # A per-event output count is a streaming snapshot (16 to 17 times below the host's own total on two
        # recorded Claude runs): no stage row carries one.
        m = self.collect([("A1", "intake", "done", 103.0), ("A2", "spec", "done", 105.0)])
        self.assertEqual([r["turns"] for r in m["stages"]], [4, 2])
        self.assertTrue(all("output_tokens" not in row for row in m["stages"]), m["stages"])

    def test_the_committed_baseline_keeps_only_comparable_stage_fields(self):
        rows = [{"stage": "spec", "outcome": "done", "seconds": 1.0, "turns": 2,
                 "tool_calls": 3, "output_tokens": 4},
                {"stage": "plan", "outcome": "done", "timing": "unavailable"},
                {"stage": "implement", "outcome": None, "incomplete": True, "seconds": 5.0, "turns": 6,
                 "tool_calls": 7, "output_tokens": 8}]
        kept = run.baseline_stages(rows)
        self.assertEqual(kept[0], {"stage": "spec", "outcome": "done", "seconds": 1.0, "turns": 2})
        # The markers that say a row is not comparable must survive.
        self.assertEqual(kept[1], {"stage": "plan", "outcome": "done", "timing": "unavailable"})
        self.assertTrue(kept[2]["incomplete"])
        self.assertTrue(all("tool_calls" not in r and "output_tokens" not in r for r in kept))
        self.assertIsNone(run.baseline_stages(None))


class BaselineComparabilityTest(unittest.TestCase):
    """SPEC: a baseline compares only with rows from the same host, model and effort."""

    ROWS = [{"case": "hello", "source": "marketplace", "host": "claude", "model": "m", "effort": "high",
             "turns": 1},
            {"case": "hello", "source": "marketplace", "host": "codex", "model": "m", "effort": "high",
             "turns": 2},
            {"case": "hello", "source": "marketplace", "turns": 3}]  # written before the fields existed

    def rows_file(self, tmp: str) -> Path:
        path = Path(tmp) / "baselines.jsonl"
        path.write_text("".join(json.dumps(r) + "\n" for r in self.ROWS))
        return path

    def test_only_the_same_host_model_and_effort_is_a_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.rows_file(tmp)
            same = run.previous_row(path, "hello", "marketplace", "claude", "m", "high")
            other_host = run.previous_row(path, "hello", "marketplace", "codex", "m", "high")
            other_effort = run.previous_row(path, "hello", "marketplace", "claude", "m", "xhigh")
        self.assertEqual(same["turns"], 1)
        self.assertEqual(other_host["turns"], 2)
        self.assertIsNone(other_effort)  # no row ran that effort: nothing to compare with

    def test_a_row_without_the_identity_fields_is_not_used_as_a_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.rows_file(tmp)
            self.assertIsNone(run.previous_row(path, "hello", "marketplace", None, None, "high"))
            # The legacy row names no host/model/effort, so it matches only an all-None request.
            self.assertEqual(run.previous_row(path, "hello", "marketplace")["turns"], 3)

    def test_the_stage_diff_locates_a_regression_and_refuses_to_guess(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 600}, {"stage": "implement", "turns": 5, "seconds": 60}]
        now = [{"stage": "spec", "turns": 40, "seconds": 2400}, {"stage": "implement", "turns": 5, "seconds": 60}]
        lines = run.stage_diff_lines(before, now)
        self.assertIn("spec 10->40", lines[0])
        self.assertNotIn("implement", lines[0])  # unchanged stages are not noise
        self.assertEqual(run.stage_diff_lines(before, [{"stage": "spec", "timing": "unavailable"}]),
                         ["per-stage comparison unavailable (one run has no measured stage timing)"])
        self.assertEqual(run.stage_diff_lines(before, before), ["no per-stage turn difference"])

    def test_a_partial_comparison_says_how_much_it_covers(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 600}]
        now = [{"stage": "spec", "turns": 40, "seconds": 2400},
               {"stage": "plan", "timing": "unavailable"},
               {"stage": "implement", "timing": "unavailable"}]
        lines = run.stage_diff_lines(before, now)
        self.assertIn("covers 1 of 3 stages (2 not comparable, incomplete or unmeasured on a side: "
                      "implement, plan)", lines[0])
        self.assertIn("spec 10->40", lines[1])

    def test_repeated_visits_to_one_stage_are_summed(self):
        before = [{"stage": "implement", "turns": 3, "seconds": 30}]
        now = [{"stage": "implement", "turns": 4, "seconds": 40} for _n in range(3)]
        self.assertIn("implement 3->12", run.stage_diff_lines(before, now)[0])


class PlanningReviewRowTest(unittest.TestCase):
    """A baseline row records the run's planning_review mode, and a run is compared only with a row of its own mode:
    planning minutes, Improve passes and turns are not the same quantity under stage and none."""

    NOTE = "predates the option"

    def earlier(self, **fields) -> dict:
        return {"date": "2026-10-04T10:00:00+0000", "shiploop_version": "0.52.0", **fields}

    def test_the_mode_is_read_from_a_genuine_state_md_as_written_and_is_not_recorded_when_the_key_is_absent(self):
        fixtures = ROOT / "test" / "fixtures" / "run-review"  # `shiploop init --planning-review <mode>` of the plugin's own CLI
        for mode in ("stage", "none"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                (Path(tmp) / "state.md").write_text((fixtures / f"state-{mode}.md").read_text())
                self.assertEqual(metrics.planning_review(metrics.engine_state(Path(tmp))), mode)
        self.assertEqual([metrics.planning_review(s) for s in (
            {"planning_review": "once"}, {"planning_review": 2}, {}, {"planning_review": None}, metrics.engine_state(None))],
            ["once", "2", "not recorded", "not recorded", "not recorded"])

    def test_the_row_carries_the_mode_and_a_row_built_without_one_says_not_recorded(self):
        result = {"case": "hello", "metrics": {}}
        self.assertEqual(run.baseline_row(result, None, None, "none")["planning_review"], "none")
        self.assertEqual(run.baseline_row(result, None, None, "stage")["planning_review"], "stage")
        self.assertEqual(run.baseline_row(result, None, None)["planning_review"], "not recorded")  # no default mode

    def test_a_row_stands_for_the_mode_it_recorded_and_for_stage_only_when_its_plugin_predates_the_option(self):
        self.assertEqual(run.row_planning_review({"planning_review": "none", "plugin_version": "1.22.0"}), ("none", ""))
        self.assertEqual(run.row_planning_review({"planning_review": "once", "plugin_version": "1.21.0"}), ("once", ""))
        for version in ("1.21.0", "1.20.0", "1.9.0", "0.99.9"):  # numbers, not text: 1.9.0 is before 1.22.0
            with self.subTest(version=version):
                mode, why = run.row_planning_review({"plugin_version": version})
                self.assertEqual(mode, "stage")
                self.assertIn(f"plugin {version} {self.NOTE}", why)
        self.assertEqual(run.row_planning_review({"planning_review": None, "plugin_version": "1.20.0"})[0], "stage")
        for version in (None, "", "1.22.0", "1.22.1", "1.100.0", "2.0.0", "1.22", "dev", "1.21.0-rc.1", 121):
            with self.subTest(version=version):
                mode, why = run.row_planning_review({} if version is None else {"plugin_version": version})
                self.assertEqual(mode, "not recorded")
                self.assertTrue(why.startswith("records no mode and "), why)
        self.assertEqual(run.PLANNING_REVIEW_FIRST_RELEASE, "1.22.0")

    def test_the_report_line_names_why_nothing_was_compared_and_the_last_row_of_the_driver(self):
        line = run.planning_review_line
        self.assertEqual(line("none", self.earlier(planning_review="stage")),
                         "  baseline  not compared across planning_review modes (none vs stage); no earlier row of mode none; "
                         "the last row for this driver is 2026-10-04, ShipLoop 0.52.0")
        self.assertIn("(stage vs none); no earlier row of mode stage;", line("stage", self.earlier(planning_review="none")))
        as_stage = line("none", self.earlier(plugin_version="1.21.0"))
        self.assertIn("(none vs stage); no earlier row of mode none;", as_stage)
        self.assertTrue(as_stage.endswith("; it records no mode, read as stage because plugin 1.21.0 predates the option"), as_stage)
        for fields, why in ((self.earlier(), "no plugin_version places it before the option"),
                            (self.earlier(plugin_version="1.22.0"), "plugin 1.22.0 does not predate the option")):
            unknown = line("stage", fields)
            self.assertIn("(stage vs not recorded); no earlier row of mode stage;", unknown)
            self.assertTrue(unknown.endswith("; it records no mode and " + why), unknown)
        # a run that records no mode matches no row, and says that instead of "no earlier row of mode not recorded"
        self.assertIn("(not recorded vs stage); this run records no mode;", line("not recorded", self.earlier(planning_review="stage")))
        both = line("not recorded", self.earlier(planning_review="not recorded"))
        self.assertIn("(not recorded vs not recorded); this run records no mode;", both)
        self.assertNotIn("no earlier row of mode", both)

    DRIVER = {"case": "hello", "source": "marketplace", "host": "claude", "model": "m", "effort": "high"}

    def scan(self, rows: list[dict], mode: str | None, **driver) -> tuple[dict | None, int]:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "baselines.jsonl"
            path.write_text("".join(json.dumps({**self.DRIVER, **row}) + "\n" for row in rows))
            return run.scan_baseline(path, "hello", "marketplace", "claude", "m", "high", mode)

    def test_a_run_is_compared_with_the_last_row_of_its_own_mode_found_past_rows_of_the_other(self):
        stage, none = {"planning_review": "stage"}, {"planning_review": "none"}
        turns = lambda found: found and found["turns"]  # noqa: E731
        self.assertEqual(turns(self.scan([dict(stage, turns=1), dict(none, turns=2)], "stage")[0]), 1)  # not refused as before
        self.assertEqual(turns(self.scan([dict(stage, turns=1), dict(none, turns=2)], "none")[0]), 2)
        rows = [dict(stage, turns=1), dict(none, turns=2), dict(stage, turns=3), dict(none, turns=4)]  # interleaved
        self.assertEqual((turns(self.scan(rows, "none")[0]), turns(self.scan(rows, "stage")[0])), (4, 3))
        self.assertEqual(turns(self.scan(rows[:3], "none")[0]), 2)
        self.assertEqual(self.scan(rows, "stage")[1], 4)  # the count still says how many rows the case and source have
        self.assertEqual(turns(self.scan(rows, None)[0]), 4)  # no mode asked for: the last row of the driver, as before

    def test_no_earlier_row_of_the_runs_mode_finds_nothing_and_an_unrecorded_mode_matches_no_row(self):
        self.assertEqual(self.scan([{"planning_review": "none", "turns": 1}], "stage"), (None, 1))
        self.assertEqual(self.scan([{"planning_review": "stage", "turns": 1}], "once"), (None, 1))
        self.assertEqual(self.scan([{"planning_review": "not recorded", "turns": 1}], "not recorded"), (None, 1))
        self.assertEqual(self.scan([{"turns": 1}], "not recorded"), (None, 1))
        other_driver = [{"planning_review": "stage", "turns": 1, "host": "codex"}]
        self.assertEqual(self.scan(other_driver, "stage"), (None, 1))  # the driver rule is unchanged

    def test_a_row_with_no_mode_is_found_as_stage_only_when_its_plugin_predates_the_option(self):
        none = {"planning_review": "none", "turns": 2}
        old = {"plugin_version": "1.21.0", "turns": 1}
        self.assertEqual(self.scan([old, none], "stage")[0]["turns"], 1)  # the old row is the stage row past the none row
        self.assertEqual(self.scan([old, none], "none")[0]["turns"], 2)
        for fields in ({"turns": 1}, {"turns": 1, "plugin_version": "1.22.0"}, {"turns": 1, "plugin_version": "dev"}):
            self.assertIsNone(self.scan([fields, none], "stage")[0], fields)

    def test_the_version_constant_is_named_once_and_the_readme_says_the_rule(self):
        self.assertEqual(Path(run.__file__).read_text().count('"1.22.0"'), 1)
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("not compared across planning_review modes (<this> vs <previous>)",
                       "compared with the last row of its own mode", "no earlier row of mode <this>",
                       "it stands for `stage` only when its recorded `plugin_version` is below 1.22.0",
                       "reads `not recorded` and is compared with no run", "the run's `planning_review` mode"):
            self.assertIn(phrase, readme)


class TerminationRecordTest(unittest.TestCase):
    """Why a run stopped is the harness's to record, and unknown is kept."""

    def facts(self, engine: dict, resume_stop: str | None, stops: list) -> dict:
        sessions = [{"stop": s} for s in stops]  # one entry per launched session, as run.launch reports it
        return run.termination_facts({"status": "exited", "returncode": 0, "sessions": sessions, "resumes": 0},
                                     engine, resume_stop)

    def test_an_abandoned_run_names_the_stage_it_never_accepted(self):
        engine = {"status": "active", "stage": "inner-loop", "work_index": 0,
                  "work_items": [{"id": "W1"}], "inner_loops": {"W1": {"stage": "test-green"}}}
        facts = self.facts(engine, "resume budget spent (8)", ["end_turn"])
        self.assertEqual(facts["engine_status"], "active")
        self.assertEqual(facts["engine_unaccepted_stage"], "test-green")
        self.assertEqual(facts["resume_stop"], "resume budget spent (8)")

    def test_a_missing_reason_is_unknown_and_never_guessed(self):
        facts = self.facts({}, None, [None])
        self.assertEqual(facts["resume_stop"], "unknown")
        self.assertEqual(facts["session_stops"], ["unknown"])
        self.assertEqual(facts["engine_status"], "unknown")
        self.assertEqual(facts["engine_stage"], "unknown")
        self.assertIsNone(facts["engine_unaccepted_stage"])

    def test_a_finished_run_has_no_unaccepted_stage(self):
        facts = self.facts({"status": "done", "stage": "handoff"}, "ShipLoop run is done", ["end_turn"])
        self.assertIsNone(facts["engine_unaccepted_stage"])
        self.assertEqual(facts["engine_stage"], "handoff")


class MetricsTest(unittest.TestCase):
    def test_turns_failures_and_truncations_are_attributed_to_stages(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "loop" / "run"
            (run_dir / "results").mkdir(parents=True)
            (run_dir / "improve" / "child-1").mkdir(parents=True)
            (run_dir / "improve" / "child-1-bind.md").write_text("# bind\n")  # a real run leaves one per child
            stream = [
                {"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": 10}},
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "python3 x/shiploop complete --run-dir r"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {
                    "exit_code": 2, "output_for_prompt": "SHIPLOOP-RUN run=x rev=1 dir=/r\nerror: result refused"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 2, "truncated": True}},
                {"type": "usage", "usage": {"input_tokens": 3000, "output_tokens": 20}},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "node --test"}},
                {"type": "tool_call_update", "toolCallId": "b", "rawOutput": {"exit_code": 0, "truncated": True}},
                {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "git init -b main"}},
                {"type": "tool_call_update", "toolCallId": "c", "status": "failed", "rawOutput": None, "content": [
                    {"type": "content", "content": {"type": "text",
                                                    "text": "User cancelled the execution for tool `run_terminal_command`"}}]},
                {"type": "tool_call", "toolCallId": "q", "toolName": "ask_user_question",
                 "rawInput": {"question": "Which port?"}},
                {"type": "auto_compact_completed"},
                {"type": "usage", "usage": {"input_tokens": 500, "output_tokens": 5}},
                {"type": "end", "stopReason": "end_turn", "num_turns": 3, "total_cost_usd": 3.0},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            (out / "timeline.jsonl").write_text("\n".join(json.dumps({"line": n, "t": 100.0 + n})
                                                           for n in range(len(stream))) + "\n")
            # Stage boundaries come from ShipLoop's own history and acceptance
            # stamps, joined by action id -- not from result-file mtimes.
            write_engine_records(run_dir, [("A1", "intake", "done", 104.5), ("A2", "spec", "done", 111.5)])
            m = metrics.collect(out, run_dir)
        self.assertEqual(m["turns"], 3)
        self.assertEqual(m["cost_usd"], 3.0)
        self.assertEqual(m["compactions"], 1)
        self.assertEqual(m["truncated_outputs"], 2)
        self.assertEqual(m["script_verifications"],
                         {"records": 0, "passed": 0, "could_not_run": 0, "commands": 0, "red": 0})
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["asked_user"], ["Which port?"])
        self.assertEqual(m["improve_children"], 1)
        self.assertEqual(m["shiploop_failures"], [{"verb": "complete", "exit": 2, "line": "error: result refused"}])
        self.assertEqual([(s["stage"], s["turns"]) for s in m["stages"]], [("intake", 2), ("spec", 1)])
        self.assertEqual([s["outcome"] for s in m["stages"]], ["done", "done"])
        # No cost is apportioned per stage: a share of one total, split by turn
        # count, moves when prices or unrelated work move.
        self.assertTrue(all("cost_share_usd" not in s for s in m["stages"]))

    # What the script prints after any refused callback, as shiploop_protocol.py words it.
    TRAILERS = ("Read the current packet with next; the rejected request did not advance the graph.",
                "The run is still active: fix the result and resubmit in this turn; do not end the turn over a "
                "refused callback.")

    def recorded_failure_line(self, output: str, command: str = "python3 x/shiploop complete --run-dir r",
                              code: int = 2) -> str:
        """The `line` the export keeps for one refused ShipLoop command whose output was ``output``."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [{"type": "tool_call", "toolCallId": "a",
                       "rawInput": {"command": command}},
                      {"type": "tool_call_update", "toolCallId": "a",
                       "rawOutput": {"exit_code": code, "output_for_prompt": output}},
                      {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            failures = metrics.collect(out, None)["shiploop_failures"]
        self.assertEqual(len(failures), 1, failures)
        return failures[0]["line"]

    def test_a_refusal_is_recorded_by_its_own_line_not_by_the_trailers_after_it(self):
        marker = "SHIPLOOP-RUN run=x rev=1 dir=/r\n"
        refusal = "ShipLoop navigator: result requires outcome and summary: the result is missing \"summary\""
        trailers = "\n".join(self.TRAILERS)
        # Before: the trailer says "rejected", so it was recorded and the export could not name the refusal.
        self.assertEqual(self.recorded_failure_line(marker + refusal + "\n" + trailers + "\n"), refusal)
        # The script's other refusal prefix, and the lines its blocked branch adds after it.
        blocked = "ShipLoop blocked: the run directory is not readable"
        after = ("Request failure: no in-memory result, candidate, or rejected artifact is trusted.\n"
                 "Durable cursor recovery: do not infer a next action from this error; follow the recovery packet.\n")
        self.assertEqual(self.recorded_failure_line(blocked + "\n" + after), blocked)
        # A line that already matched before is still recorded first, wherever the prefix line sits.
        self.assertEqual(self.recorded_failure_line("shiploop: error: unrecognized arguments: x\n" + trailers),
                         "shiploop: error: unrecognized arguments: x")

    def test_a_routed_verbs_could_not_run_refusal_is_recorded_by_its_own_line(self):
        # lint, red-check and backchain-check refuse with "ShipLoop <verb> could not run: " (exit 3), which has no failure
        # word: metrics.json kept "line": "" for all 7 lint refusals of the brownfield runs bf-ds-*-09c33b (2026-10-28).
        refusal = "ShipLoop lint could not run: nav-b is not the current action (nav-a)"
        lint = "python3 x/shiploop lint --run-dir=r --action=nav-b"
        self.assertEqual(self.recorded_failure_line("Exit code 3\n" + refusal + "\n", lint, 3), refusal)
        # A refusal line counts whatever exit the host showed: a pipe through tail shows 0.
        self.assertEqual(self.recorded_failure_line(refusal + "\n", lint + " 2>&1 | tail -5", 0), refusal)
        red = "ShipLoop red-check could not run: red-check runs only for the current test action"
        self.assertEqual(self.recorded_failure_line(red + "\n", "python3 x/shiploop red-check --run-dir=r --action=a", 3),
                         red)

    def test_where_only_the_trailers_match_the_export_records_what_it_did_before(self):
        self.assertEqual(self.recorded_failure_line("\n".join(self.TRAILERS) + "\n"), self.TRAILERS[0])
        self.assertEqual(self.recorded_failure_line("nothing here names a failure\n"), "")

    def test_the_trailers_the_export_skips_are_the_ones_the_script_prints(self):
        """The skip list copies the script's fixed text; a reworded trailer must fail here, not hide a refusal."""
        source = " ".join((ROOT / "skills/shiploop/scripts/shiploop_protocol.py").read_text().split())
        for text in (*self.TRAILERS[:1], "The run is still active: fix the result and resubmit in this turn;",
                     "Request failure: no in-memory result", "Durable cursor recovery: ", 'f"ShipLoop navigator: {exc}"',
                     'f"ShipLoop blocked: {exc}"'):
            self.assertIn(text, source)
        for line in self.TRAILERS:
            self.assertRegex(line, metrics.TRAILER_LINE)
        self.assertRegex("ShipLoop navigator: x", metrics.REFUSAL_LINE)

    # What a real Claude result event reports as its usage: nested, and the host's own figure.
    CLAUDE_USAGE = {"input_tokens": 96, "cache_creation_input_tokens": 131587, "cache_read_input_tokens": 5194338,
                    "output_tokens": 28419, "output_tokens_details": {"thinking_tokens": 3450},
                    "server_tool_use": {"web_search_requests": 0, "web_fetch_requests": 0},
                    "cache_creation": {"ephemeral_1h_input_tokens": 131587, "ephemeral_5m_input_tokens": 0},
                    "iterations": [{"input_tokens": 2, "output_tokens": 1109, "type": "message"}],
                    "service_tier": "standard", "speed": "standard", "fallback_credit": None}
    # What the Codex translator's end event carried for a 2189-item session (the recorded Luna battleship run).
    CODEX_USAGE = {"input_tokens": 172611340, "cache_read_input_tokens": 167042304, "output_tokens": 1622714,
                   "reasoning_tokens": 1015804}

    @staticmethod
    def read(events: list[dict]) -> tuple[dict, dict]:
        """metrics.collect and run.summarize_events over the same bare host events."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            return metrics.collect(out), run.summarize_events(out / "events.jsonl")

    def test_unknown_cost_stays_unknown_and_the_hosts_own_usage_is_kept_unsummed(self):
        luna = {"type": "end", "stopReason": "end_turn", "num_turns": 2189, "total_cost_usd": None,
                "usage": self.CODEX_USAGE}
        grok = {"type": "end", "stopReason": "cancelled", "num_turns": 4, "total_cost_usd": 1.0}
        claude = {"type": "result", "subtype": "success", "num_turns": 56, "total_cost_usd": 1.8495976,
                  "usage": self.CLAUDE_USAGE}
        for label, events, want in (
                ("a host that reports no cost", [luna], None),
                ("one session reported a cost and one did not", [grok, luna], None),
                ("every ended session reported", [grok, grok, claude], round(1.0 + 1.0 + 1.8495976, 4)),
                ("no session ended", [{"type": "available_commands", "commands": []}], None)):
            m, cli = self.read(events)
            self.assertEqual((m["cost_usd"], cli.get("cost_usd")), (want, want), label)
        # The host's own usage rides with its session, as written: never summed, never rebuilt.
        m, _ = self.read([luna])
        self.assertEqual(m["sessions"][0]["usage"], self.CODEX_USAGE)
        m, _ = self.read([claude, claude])  # nested usage is kept whole, not added key by key
        self.assertEqual([s["usage"] for s in m["sessions"]], [self.CLAUDE_USAGE, self.CLAUDE_USAGE])
        self.assertIsNone(self.read([grok])[0]["sessions"][0]["usage"])  # none reported: None, not {} or 0
        # One implementation (SPEC S-12): the metrics and the CLI summary both ask metrics.total_cost.
        with mock.patch.object(metrics, "total_cost", return_value=123.0):
            m, cli = self.read([luna])
        self.assertEqual((m["cost_usd"], cli["cost_usd"]), (123.0, 123.0))

    def test_no_token_figure_is_made_from_events_that_do_not_carry_it(self):
        text_only = {"type": "assistant", "message": {"content": [{"type": "text", "text": "x"}]}}
        m, _ = self.read([text_only] * 3)  # Claude messages that report no usage
        self.assertEqual((m["turns"], m["tokens"]["input_peak"]), (3, None))
        # A host's end-of-session total is not a per-call context figure. From build step 8 it is the session's tokens:
        # the output needs no host, the processed total does (Codex counts cache reads inside its input), and this
        # stream has no launch record to name one.
        m, _ = self.read([{"type": "end", "num_turns": 9, "total_cost_usd": None, "usage": self.CODEX_USAGE}])
        self.assertEqual(m["tokens"], {"input_peak": None, "processed": None, "output": self.CODEX_USAGE["output_tokens"]})
        self.assertEqual(m["unmeasured"]["tokens_processed"], metrics.SESSION_HOST_UNKNOWN)
        # A call that reported its context counts; one that did not neither lowers the peak nor invents a 0.
        m, _ = self.read([{"type": "usage", "usage": {"input_tokens": 1000, "cache_read_input_tokens": 500,
                                                      "output_tokens": 7}},
                          {"type": "usage", "usage": {"output_tokens": 9}}, {"type": "usage"},
                          {"type": "usage", "usage": {"input_tokens": 200}}])
        self.assertEqual((m["turns"], m["tokens"]["input_peak"]), (4, 1500))

    def test_a_session_killed_before_it_reported_makes_the_cost_a_lower_bound(self):
        init = {"type": "system", "subtype": "init", "model": "m"}
        result = {"type": "result", "subtype": "success", "num_turns": 5, "total_cost_usd": 1.85}
        opened = {"type": "available_commands", "commands": []}
        end = {"type": "end", "stopReason": "end_turn", "num_turns": 5, "total_cost_usd": None}
        for label, events, want in (
                ("Claude: four sessions began and one reported", [init, init, init, init, result], 3),
                ("Claude: the first was killed, the second finished", [init, init, result], 1),
                ("Codex or Grok: two began and one reported", [opened, opened, end], 1),
                ("Grok: killed before any end", [opened], 1),
                ("every session reported", [init, result, opened, end], 0),
                ("an end with no recorded start is never negative", [result, end], 0),
                ("a Claude system event that is not an init is not a start",
                 [{"type": "system", "subtype": "task_started"}, result], 0)):
            m, _ = self.read(events)
            self.assertEqual(m["unreported_sessions"], want, label)
        m, _ = self.read([init, init, result])
        self.assertEqual(metrics.cost_text(m), "$1.85 (lower bound: 1 session(s) never reported)")
        self.assertIn("cost $1.85 (lower bound: 1 session(s) never reported)", metrics.summary_lines(m)[0])
        whole, _ = self.read([init, result])
        self.assertEqual(metrics.cost_text(whole), "$1.85")
        unknown, _ = self.read([opened, opened, end])  # no figure, so nothing for a lower bound to bound
        self.assertEqual(metrics.cost_text(unknown), "not reported")

    NARRATIVE_BODY = ("#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2588\u2591` **Preparation 1/7**\n\n"
                      "**\u25b6\ufe0f Now** \u2014 **spec**: define behavior\n")

    def packet(self, stage: str, rule: str = "Show the user this narrative exactly as written, as Markdown.",
               body: str | None = None) -> str:
        """A ShipLoop packet print. ``body`` defaults to the one narrative; pass a different one to make two
        emissions distinct, since narrative() now counts one obligation per distinct body (2026-11-03)."""
        return (f"ShipLoop navigator | {stage} | revision 3\nCallback: x\n\n=== ShipLoop narrative ===\n{rule}\n\n"
                f"{self.NARRATIVE_BODY if body is None else body}=== end ShipLoop narrative ===\n")

    def result_record(self, run_dir: Path, name: str, result: dict) -> None:
        body = json.dumps({"action": name, "result": result, "stage": "intake", "workitem": None}, indent=2)
        (run_dir / "results" / f"{name}.md").write_text(f"# ShipLoop navigator result\n\n```shiploop-state\n{body}\n```\n")

    def test_narrative_shown_verbatim_skipped_and_headlines_grok(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            (run_dir / "results").mkdir(parents=True)
            half = len(self.NARRATIVE_BODY) // 2
            stream = [
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop init"}},
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                # Grok repeats an update; one tool call is one emission.
                {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                {"type": "text", "data": "Starting.\n"},
                {"type": "text", "data": self.NARRATIVE_BODY[:half]},
                {"type": "text", "data": self.NARRATIVE_BODY[half:]},
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "shiploop complete"}},
                # A distinct body per stage: narrative() counts one obligation per distinct body (2026-11-03),
                # so identical bodies would collapse and this test would stop testing skip/verbatim per stage.
                {"type": "tool_call_update", "toolCallId": "b", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet(
                    "discovery", body="#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2591\u2591` **Preparation 2/7**\n")}},
                {"type": "text", "data": "Moving on to discovery."},
                {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "c", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet(
                    "research", body="#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2591\u2591` **Preparation 3/7**\n")}},
                {"type": "thought", "data": "thinking"},                                    # ends the message
                {"type": "text", "data": "\U0001f6a2 ShipLoop \u2014 Add a flag\nsomething else"},  # heading only
                # The CLI hook shows this one; the model is not asked to.
                {"type": "tool_call", "toolCallId": "d", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "d", "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet(
                    "spec", rule="The host's status hook already shows the user this narrative; do not repeat it.")}},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            self.result_record(run_dir, "r1", {"outcome": "done", "summary": "s", "headline": "Scope set"})
            self.result_record(run_dir, "r2", {"outcome": "done", "summary": "s"})
            self.result_record(run_dir, "r3", {"outcome": "done", "summary": "Not applicable to this item: x."})
            story = metrics.narrative(out, run_dir)
            report = metrics.summary_lines({**metrics.collect(out, run_dir), "narrative": story})
        self.assertEqual(story, {"emitted": 3, "shown": 2, "verbatim": 1, "skipped": ["discovery"],
                                 "raw_emissions": 3, "repeated": 0, "composed": 3, "results": 2,
                                 "with_headline": 1,
                                 # presence counts of run-level facts in the model's own words, never the prose
                                 "run_level": {"achieved": 0, "phase": 0, "pace": 0}})
        # Each distinct body is one obligation (2026-11-03). The fixture's second `intake` update is the same tool
        # call, which the reader already collapses before counting, so it contributes no repeat either way.
        self.assertEqual(story["emitted"] + story["repeated"], story["raw_emissions"])
        self.assertIn("narrative relayed 2/3 (verbatim 1), not relayed at discovery", report[-1])
        self.assertNotIn("Add a flag", json.dumps(story))

    def test_narrative_reads_claude_tool_results_and_text_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1",
                                                          "content": [{"type": "text", "text": self.packet("intake")}]}]}},
                {"type": "assistant", "message": {"content": [{"type": "text", "text": self.NARRATIVE_BODY.replace("#### ", "")}]}},
                {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t2",
                                                          "content": self.packet(
                                                              "discovery",
                                                              body="#### \U0001f6a2 ShipLoop \u2014 Add a flag\n"
                                                                   "`\u2588\u2591` **Preparation 2/7**\n")}]}},
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            story = metrics.narrative(out)
        self.assertEqual((story["emitted"], story["shown"], story["verbatim"], story["skipped"]),
                         (2, 1, 1, ["discovery"]))
        self.assertEqual((story["results"], story["with_headline"]), (0, 0))

    def test_a_repeated_narrative_body_is_one_obligation_not_one_per_packet(self):
        """A packet's narrative can reach the model more than once; a run that shows it once has met it.

        Measured 2026-11-03 over 102 saved runs: 261 of 2,111 emissions repeated a body already emitted (12%, in
        67% of runs), and one run emitted the identical body 22 times, four of which were scored "skipped" because
        the model showed that block 18 times already. Counting per packet read compliance as 61% when the distinct
        bodies were 69% shown, which is a 9-point understatement of the same behaviour.
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            body = "#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2588\u2591` **Preparation 1/7**\n"
            stream = [
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "a",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake", body=body)}},
                {"type": "text", "data": self.NARRATIVE_BODY},
                # The same narrative reaches three further packets, and the model does not paste it again.
                *[item for call in ("b", "c", "d") for item in (
                    {"type": "tool_call", "toolCallId": call, "rawInput": {"command": "shiploop complete"}},
                    {"type": "tool_call_update", "toolCallId": call,
                     "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake", body=body)}},
                    {"type": "text", "data": "Continuing."})],
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            story = metrics.narrative(out)
        self.assertEqual((story["emitted"], story["shown"], story["skipped"]), (1, 1, []),
                         "one body asked four times and shown once is one met obligation")
        self.assertEqual((story["raw_emissions"], story["repeated"]), (4, 3))
        self.assertEqual(story["emitted"] + story["repeated"], story["raw_emissions"])

    def test_composed_progress_is_counted_beside_the_relayed_block_never_instead_of_it(self):
        """A run can relay few blocks and still update the user constantly: the battleship round of 2026-11-03 relayed
        2 of 6 and wrote 18 progress sentences of its own. Counting only the relay read that as silence, and I reported
        it as one. The reader counts both, so a reader of metrics.json sees the difference.
        """
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "a",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                {"type": "text", "data": "The workspace is empty and Node is available."},   # composed
                {"type": "tool_call", "toolCallId": "b", "rawInput": {"command": "shiploop complete"}},
                {"type": "tool_call_update", "toolCallId": "b",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet(
                     "discovery", body="#### \U0001f6a2 ShipLoop \u2014 Add a flag\n`\u2591\u2591` **Preparation 2/7**\n")}},
                {"type": "text", "data": "The fleet rules are specified."},                   # composed
                {"type": "tool_call", "toolCallId": "bb", "rawInput": {"command": "shiploop check"}},
                {"type": "text", "data": "All eight tests pass."},                            # composed
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            story = metrics.narrative(out)
        self.assertEqual((story["emitted"], story["shown"]), (2, 0), "neither block was relayed")
        self.assertEqual(story["composed"], 3, "three progress sentences of the model's own")
        report = metrics.summary_lines({**metrics.collect(out), "narrative": story})
        self.assertIn("narrative relayed 0/2", report[-1])
        self.assertIn("3 composed progress message(s)", report[-1])

    def test_a_streamed_message_is_one_composed_update_not_one_per_chunk(self):
        """A host streams a reply as many tiny `text` events (median 4 characters: "I'll", " start", " Ship"), so a
        count per event read one message as 7,659 (chess-sf-full-12a23d, 2026-11-04). Its 8,011 chunks are 139 messages,
        and reasoning, bookkeeping and blank chunks interleave inside a message without ending it; a tool call does."""
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = [
                {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "shiploop init"}},
                {"type": "tool_call_update", "toolCallId": "a",
                 "rawOutput": {"exit_code": 0, "output_for_prompt": self.packet("intake")}},
                {"type": "text", "data": "The workspace"},          # one message...
                {"type": "thought", "data": "reasoning"},           # ...interleaved with reasoning...
                {"type": "text", "data": " is empty"},              # ...continues...
                {"type": "usage", "data": ""},                      # ...and bookkeeping...
                {"type": "text", "data": ""},                       # ...and a blank chunk: still one message
                {"type": "text", "data": "."},
                {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "shiploop check"}},
                {"type": "text", "data": "All eight tests pass."},  # a second message
            ]
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            story = metrics.narrative(out)
        self.assertEqual(story["composed"], 2, "two messages, not seven chunks")

    def test_run_without_narrative_reports_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "text", "data": "hi"}) + "\n")
            m = metrics.collect(out)
        self.assertEqual(m["narrative"], {"emitted": 0, "shown": 0, "verbatim": 0, "skipped": [],
                                          "raw_emissions": 0, "repeated": 0, "composed": 0, "results": 0, "with_headline": 0,
                                          "run_level": {"achieved": 0, "phase": 0, "pace": 0}})
        self.assertFalse(any(line.startswith("narrative") for line in metrics.summary_lines(m)))

    def test_glue_is_defined_by_shiploop_paths_and_verbs_not_by_product_tools(self):
        cases = {
            'cd /x/.shiploop-runs/a/worktree && node --test > "/x/.shiploop-runs/a/worktree/out.txt"': [],
            'npm test > report.txt': [],
            'cat > /x/.shiploop-runs/a/run/inbox/r.md <<EOF': [],  # the model's own result file
            'rm -rf "/x/.shiploop-improve"': ["shell write into a ShipLoop-owned path"],
            'mv /x/wt/.shiploop-improve/n/packet.json /x/p.old': ["shell write into a ShipLoop-owned path"],
            'echo x > /x/.shiploop/state.md': ["shell write into a ShipLoop-owned path"],
            'git -C /x/wt commit -F /tmp/m': ["git commit/add by the model"],
            'python3 until_loop.py start --directory /x <<PY\n{"exit_condition": 1}\nPY': ["hand-built loop contract"],
            "python3 - <<'PY'\nd=json.load(open('/x/run/quality/c-contract.json'))\nprint(d['exit_condition'][:500])\nPY": [],
            'python3 /p/shiploop improve-commit --run-dir=/x/run --action=a --message=/x/m.md': [],
            # words inside a heredoc are a document, not commands
            "python3 - << 'PY'\nreport = {'evidence': 'git log shows the commit'}\nPY\n": [],
            'cd /x/wt && WT=/x git -C "$WT" add docs/a.md && git commit -m m': ["git commit/add by the model"],
            'echo "run git commit later"': [],
            # evidence the packets ask the model to record
            'node --test > "/x/.shiploop-runs/a/run/notes/test-green.txt" 2>&1': [],
            'cp /tmp/r.txt /x/wt/.shiploop-improve/n/a/reviews/checks.md': [],
            'echo x > /x/.shiploop-runs/a/run/results/nav-1.md': ["shell write into a ShipLoop-owned path"],
            # a file of the model's own that merely ends like a ShipLoop name
            'python3 /p/shiploop improve-start --action=a --restart-stopped > /tmp/plan-start.json': [],
            'cp /tmp/x.json /x/wt/.shiploop-improve/n/a/start.json': ["shell write into a ShipLoop-owned path"],
            # check output the packet asks the model to record as evidence
            'npm test > /x/.shiploop-runs/a/run/evidence/w1-verify.txt': [],
            # the run's scratch directory is the model's own (P13)
            'python3 -m unittest > /x/.shiploop-runs/a/run/scratch/baseline.txt 2>&1': [],
            # the Improve child's review directory is where P12 asks it to write
            "mkdir -p .shiploop-improve/n/a/reviews": [],
            # the Improve child's own directory (a saved run's model wrote its opening file there; ShipLoop writes it now, and the regrade of a saved run still allows it)
            'mkdir -p "/x/wt/.shiploop-improve/run1/nav-1"': [],
            'rm -rf "/x/wt/.shiploop-improve"': ["shell write into a ShipLoop-owned path"],
            # reading ShipLoop's own contract is not building one
            'python3 -c \'import json; p=json.load(open("/x/run/quality/c-contract.json")); print(p["exit_condition"])\'': [],
            'python3 -c \'import json; json.dump({"exit_condition": 1}, open("/x/c.json", "w"))\'': ["hand-built loop contract"],
            # making the model's own directories is not a write into a ShipLoop-owned path (batch 1003 / 1.16.1 run)
            "mkdir -p '/x/.shiploop-runs/a/run/notes' && cat > '/x/.shiploop-runs/a/run/notes/w1.md' <<'EOF'\nx\nEOF": [],
            "mkdir -p /x/.shiploop-runs/a/run/evidence": [],
            "mkdir -p /x/.shiploop-runs/a/run/scratch": [],
            # a `>` in prose inside a quoted string is not a redirect, and run/scratch is the model's own
            "python3 -c 'import pathlib; pathlib.Path(\"/x/.shiploop-runs/a/run/scratch/r.json\").write_text(\"each > 0 must pass; see /x/.shiploop-runs/a/run/results\")'": [],
            'echo x > "/x/.shiploop-runs/a/run/state.md"': ["shell write into a ShipLoop-owned path"],
            # json.dumps only formats text for printing
            "python3 - <<'PY'\nd=json.load(open('/x/packet.json'))\nprint(json.dumps(d['exit_condition'], indent=2))\nPY": [],
        }
        for command, reasons in cases.items():
            with self.subTest(command=command):
                self.assertEqual(metrics.glue_reasons(command), reasons)

    def test_verifications_come_from_shiploop_records_not_tool_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            (tests / "nav-1-verify1.md").write_text('{"passed": true, "runs": [{"command": "a"}, {"command": "b"}]}')
            (tests / "nav-2-verify1.md").write_text('{"passed": false, "runs": [{"command": "c"}]}')
            (tests / "nav-2-contract.json").write_text("{}")
            self.assertEqual(metrics.verifications(Path(tmp) / "run"),
                             {"records": 2, "passed": 1, "could_not_run": 0, "commands": 3, "red": 0})

    def test_a_verify_record_that_lists_its_request_counts_only_what_ran(self):
        """A record carrying both a `commands` array (the request) and a `runs` array (what executed) held each command
        twice, so counting `"command":` occurrences read 374 recorded commands as 523 over the saved runs and made this
        reader disagree with fidelity.validation on 89 of 90 runs (found 2026-11-03; 149 of 374 records carry both)."""
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            (tests / "nav-1-verify1.md").write_text(json.dumps({
                "schema": "shiploop-test-loop/v1", "passed": True,
                "commands": [{"command": "a", "suite": "focused"}, {"command": "b", "suite": "regression"}],
                "runs": [{"command": "a", "suite": "focused", "exit": 0}, {"command": "b", "suite": "regression", "exit": 0}],
            }))
            found = metrics.verifications(Path(tmp) / "run")
        self.assertEqual(found["commands"], 2, "the two that ran, not the two requested plus the two that ran")
        self.assertEqual(found["records"], 1)
        self.assertEqual(found["passed"], 1)

    def test_a_verify_record_with_no_runs_array_counts_no_executed_command(self):
        """A record that only lists its request ran nothing this reader can see; it must not claim commands ran."""
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            (tests / "nav-1-verify1.md").write_text('{"passed": false, "commands": [{"command": "a"}]}')
            (tests / "nav-2-verify1.md").write_text("not json at all")
            found = metrics.verifications(Path(tmp) / "run")
        self.assertEqual((found["records"], found["commands"]), (2, 0))

    def test_progress_reports_only_what_is_new_and_never_a_run_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in (
                {"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                {"type": "text", "data": "SHIPLOOP-RUN run=x rev=1 dir=/r"})) + "\n")
            first = progress.report(out)
            second = progress.report(out)
        self.assertIn("turns 1", first)
        self.assertNotIn("SHIPLOOP-RUN", first + second)
        self.assertIn("no run state yet", second)

    def test_progress_says_peak_context_n_a_when_no_call_reported_its_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in (
                {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},) * 2))
            text = progress.report(out)
        self.assertIn("turns 2, peak context n/a", text)


class GateCountsTest(unittest.TestCase):
    """metrics.gate_counts (owner's per-gate fired/caught measurement): classify each ShipLoop refusal by
    GATE_SIGNATURES, and tell whether the same action id's complete was later accepted."""

    def test_nomenclature_counts_each_retired_term_in_shiploop_output(self) -> None:
        """S-16's record: a retired glossary term in a printed packet or a refusal is counted with its first line;
        the glossary is read from the checkout and named by digest; an unreadable glossary is unmeasured."""
        tools = metrics.ToolLog()
        tools.replies.append({"event": 4, "packet": False,
                              "text": "ShipLoop navigator | test-strategy | revision 3\nName an expected-RED control.\n"})
        tools.replies.append({"event": 9, "packet": True, "text": "ShipLoop navigator | prepare | revision 4\nNothing.\n"})
        tools.failure_events.append({"event": 12, "line": "ShipLoop navigator: blocked_by is retired: ..."})
        record = metrics.nomenclature(tools)
        self.assertEqual(record["texts_scanned"], 3)
        self.assertEqual(len(record["glossary_sha256"]), 64)
        self.assertEqual(record["retired"]["expected-RED (a baseline repair)"],
                         {"use": "expected failure", "texts": 1,
                          "first": {"event": 4, "line": "Name an expected-RED control."}})
        self.assertEqual(record["retired"]["blocked_by"]["first"]["event"], 12)
        self.assertEqual(metrics.nomenclature_text(record), "blocked_by 1, expected-RED (a baseline repair) 1")
        self.assertIn("Retired terms in ShipLoop's output: ",
                      " ".join(metrics.summary_lines(dict(self.collect([]), nomenclature=record))))
        with tempfile.TemporaryDirectory() as temp:
            self.assertIn("unmeasured", metrics.nomenclature(tools, Path(temp) / "missing.md"))
        self.assertEqual(metrics.nomenclature(metrics.ToolLog())["retired"], {})

    def test_each_test_layer_refusal_classifies_under_its_own_gate(self) -> None:
        """The F1 rows read the gates' own refusal text: built here by the gate functions, never typed."""
        spec = importlib.util.spec_from_file_location(
            "shiploop_test_layers_for_metrics", ROOT / "skills/shiploop/scripts/shiploop_test_layers.py")
        layers = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(layers)
        row = {"code": "board", "layer": "unit", "harness": "jest", "status": "available", "reason": "runner"}
        command = {"command": "grep -q Board src/board.js", "criteria": ["C1"]}
        faults = {
            "test_layers": [lambda: layers.check_rows([row, row]), lambda: layers.check_rows([dict(row, layer="e2e")]),
                            lambda: layers.check_rows([dict(row, status="unverified")]),
                            lambda: layers.canonical_rows([{"code": "x"}])],
            "confirm": [lambda: layers.check_confirms([{"id": "C1"}], [row], []),
                        lambda: layers.check_confirms([{"id": "C1", "confirm": "inspected", "code": "board",
                                                        "layer": "unit"}], [row], []),
                        lambda: layers.check_confirms([{"id": "C1", "confirm": "executed"}], [row], [command])],
            "harness_runs": [lambda: layers.check_harness_runs([dict(row, status="prerequisite")], [])],
            "targets": [lambda: layers.canonical_targets([{"target": "org", "keeps_state": "yes",
                                                           "base_state_route": "n/a"}])],
        }
        for gate, calls in faults.items():
            for call in calls:
                with self.subTest(gate=gate), self.assertRaises(layers.LayerError) as caught:
                    call()
                self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + str(caught.exception)), gate,
                                 str(caught.exception))

    def test_the_focused_guard_and_command_target_refusals_classify_under_their_gates(self) -> None:
        """F2's guard and F3's target refusals, built by the navigator's own gates, never typed."""
        sys.path.append(str(ROOT / "skills/shiploop/scripts"))
        import shiploop_navigator as navigator
        guarded = {"outcome": "done", "test_commands": [{"command": "test -f a.js && node --test", "suite": "focused"}]}
        with self.assertRaises(navigator.NavigatorError) as caught:
            navigator._check_focused_guards("step-plan", guarded)
        self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + str(caught.exception)), "focused_guard")
        org = {"target": "org", "keeps_state": "yes", "base_state_route": "a clean org"}
        state = {"history": [{"action": "ts1", "stage": "test-strategy", "workitem": None, "outcome": "done"}],
                 "accepted": {"ts1": {"outcome": "done", "targets": [org]}}}
        with mock.patch.object(navigator, "_test_strategy_layers", return_value=([], [org])), \
                mock.patch.object(navigator, "_test_strategy_result", return_value={}):
            for command in ({"command": "npm test", "suite": "focused", "target": "the org"},):
                plan = {"outcome": "done", "summary": "s", "test_commands": [command]}
                with self.subTest(command=command), self.assertRaises(navigator.NavigatorError) as caught:
                    navigator._check_submitted_layers(state, "step-plan", plan)
                self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + str(caught.exception)), "targets",
                                 str(caught.exception))

    def test_the_improve_regression_test_refusal_classifies_under_its_own_gate(self) -> None:
        """F5's refusal, built by the navigator's own gate, never typed."""
        sys.path.append(str(ROOT / "skills/shiploop/scripts"))
        import shiploop_navigator as navigator
        with tempfile.TemporaryDirectory() as temp:
            text = navigator._regression_refusal(Path(temp), {"stage": "carry-forward"}, "fix\n\nKey learnings: none\n",
                                                 ["src/calc.py"], Path(temp) / "commit-message.md", "CMD")
        self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + text), "improve_regression_test", text)

    def test_each_primary_requirement_refusal_classifies_under_its_own_gate(self) -> None:
        """The F6 rows, and F3's plan coverage (2026-10-28), read the gates' own refusal text: built here by the gate
        functions, never typed."""
        scripts = str(ROOT / "skills/shiploop/scripts")
        sys.path.append(scripts)
        self.addCleanup(sys.path.remove, scripts)
        import shiploop_navigator as navigator
        import shiploop_primary as primary
        import shiploop_unverified as unverified
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "docs/shiploop").mkdir(parents=True)
            (repo / "docs/shiploop/spec.md").write_text("## Requirements\n\n- R-1: Play.\n", encoding="utf-8")
            done = {"outcome": "done", "summary": "s"}
            row = {"outcome": "o", "requirement": "R-1", "reason": "r", "lower_layer_check": "TC-9", "settle": "s",
                   "owner": "the user", "due_stage": "handoff"}
            state = {"repo": str(repo), "work_items": [],
                     "history": [{"action": "sp", "stage": "spec", "workitem": None, "outcome": "done"}],
                     "accepted": {"sp": dict(done, primary=["R-1"])}}
            faults = {
                "primary": [lambda: primary.check_spec(repo, "spec", done),
                            lambda: primary.check_spec(repo, "spec", dict(done, primary=["R-9"])),
                            lambda: primary.check_spec(repo, "spec", dict(done, primary=[primary.PLACEHOLDER])),
                            lambda: primary.canonical("R-1")],
                "unverified_requirement": [
                    lambda: primary.check_unverified(repo, state, "product-acceptance",
                                                     dict(done, unverified=[dict(row, requirement="R-9")])),
                    lambda: unverified.check_submitted("product-acceptance",
                                                       dict(done, unverified=[dict(row, requirement="R-1 and R-2")]))],
                "lower_layer_check": [lambda: primary.check_unverified(repo, state, "product-acceptance",
                                                                       dict(done, unverified=[row]))],
                # F3 (2026-10-28): the plan's queue leaves R-1 out of every follows, or follows an ID with no entry.
                "primary_coverage": [
                    lambda: primary.check_queue(state, "plan", dict(done, work_items=[{"id": "W1", "title": "t"}])),
                    lambda: primary.check_queue(dict(state, work_index=0), "carry-forward",
                                                dict(done, work_items=[{"id": "W2", "title": "t"}])),
                    lambda: primary.check_queue(state, "plan", dict(done, work_items=[
                        {"id": "W1", "title": "t", "follows": ["R-1", "R-9"]}])),
                    lambda: navigator._normalise_work_items([{"id": "W1", "title": "t", "follows": "R-1"}],
                                                            allow_empty=False)],
            }
            for gate, calls in faults.items():
                for call in calls:
                    with self.subTest(gate=gate), self.assertRaises(ValueError) as caught:
                        call()
                    self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + str(caught.exception)), gate,
                                     str(caught.exception))

    def test_the_restate_and_small_pass_refusals_classify_under_their_gates(self) -> None:
        """The unverified restatement's refusals and the Improve convergence gate's, built by their gates, never typed."""
        scripts = str(ROOT / "skills/shiploop/scripts")
        sys.path.append(scripts)
        self.addCleanup(sys.path.remove, scripts)
        import shiploop_navigator as navigator
        import shiploop_unverified as unverified
        row = {"outcome": "o", "requirement": "R-1", "reason": "r", "lower_layer_check": "TC-1", "settle": "s",
               "owner": "the user", "due_stage": "handoff"}
        early = dict(row, outcome="o2", due_stage="release-check")
        state = {"history": [{"action": "pa", "stage": "product-acceptance", "workitem": None, "outcome": "done"}],
                 "accepted": {"pa": {"outcome": "done", "unverified": [row, early]}}}
        done = {"outcome": "done", "summary": "s"}
        for result in (done, dict(done, unverified=[early]), dict(done, unverified=[row, early])):
            with self.subTest(result=result), self.assertRaises(unverified.UnverifiedError) as caught:
                unverified.check_restated(state, "release-check", result)
            self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + str(caught.exception)), "unverified_restate",
                             str(caught.exception))
        text = navigator._small_pass_refusal(5, [2, 2, 2], "test-spec", Path("/r/review-5.md"), "CMD")
        self.assertEqual(metrics.refusal_gate("ShipLoop navigator: " + text), "improve_small_passes", text)

    SPEC_WRITEBACK = ("ShipLoop navigator: Restore /r/docs/shiploop/spec.md to what HEAD holds plus this "
                      "step's acceptance lines")

    def collect(self, stream: list[dict]) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text("\n".join(json.dumps(e) for e in stream) + "\n")
            (out / "timeline.jsonl").write_text("\n".join(json.dumps({"line": n, "t": 100.0 + n})
                                                           for n in range(len(stream))) + "\n")
            return metrics.collect(out, None)

    def test_two_refusals_of_one_gate_one_caught_one_not_plus_an_unknown_refusal(self):
        def call(call_id: str, action: str) -> dict:
            return {"type": "tool_call", "toolCallId": call_id,
                    "rawInput": {"command": f"python3 x/shiploop complete --run-dir r --action={action}"}}

        def refuse(call_id: str, line: str) -> dict:
            return {"type": "tool_call_update", "toolCallId": call_id,
                    "rawOutput": {"exit_code": 2, "output_for_prompt": line}}

        stream = [
            call("a1", "nav-AAA"), refuse("a1", self.SPEC_WRITEBACK),              # fires spec_writeback
            call("a2", "nav-AAA"),                                                 # same action, retried
            {"type": "tool_call_update", "toolCallId": "a2",
             "rawOutput": {"exit_code": 0, "output_for_prompt": "ShipLoop navigator | plan | revision 1"}},
            call("b1", "nav-BBB"), refuse("b1", self.SPEC_WRITEBACK),              # fires spec_writeback, never caught
            call("c1", "nav-CCC"), refuse("c1", "ShipLoop navigator: a brand-new refusal no row covers yet"),
            {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0},
        ]
        m = self.collect(stream)
        self.assertEqual(len(m["shiploop_failures"]), 3)
        self.assertEqual(m["gate_counts"], {"spec_writeback": {"fired": 2, "caught": 1}, "other": {"fired": 1, "caught": 0}})

    def test_an_unreadable_action_id_catches_on_the_next_complete_of_any_action(self):
        stream = [
            {"type": "tool_call", "toolCallId": "a1", "rawInput": {"command": "python3 x/shiploop complete --run-dir r"}},
            {"type": "tool_call_update", "toolCallId": "a1",
             "rawOutput": {"exit_code": 2, "output_for_prompt": self.SPEC_WRITEBACK}},
            {"type": "tool_call", "toolCallId": "a2", "rawInput": {"command": "python3 x/shiploop complete --run-dir r --action=nav-ZZZ"}},
            {"type": "tool_call_update", "toolCallId": "a2",
             "rawOutput": {"exit_code": 0, "output_for_prompt": "ShipLoop navigator | plan | revision 1"}},
            {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0},
        ]
        m = self.collect(stream)
        self.assertEqual(m["gate_counts"], {"spec_writeback": {"fired": 1, "caught": 1}})

    def test_summary_lines_shows_gate_counts_only_when_there_are_any(self):
        self.assertEqual(metrics.gate_counts_text({"spec_writeback": {"fired": 2, "caught": 1},
                                                   "other": {"fired": 1, "caught": 0}}),
                         "spec_writeback 2 (caught 1), other 1")
        self.assertNotIn("ShipLoop gates", "\n".join(metrics.summary_lines(
            dict(shiploop_failures=[], gate_counts={}, model_glue=[], asked_user=[], sessions=[], cost_usd=0.0,
                 unmeasured={}, improve_children=0, improve_reviews={}, script_verifications={
                     "passed": 0, "records": 0, "could_not_run": 0, "red": 0}, turns=0, stages=[]))))


class FanoutGradeTest(unittest.TestCase):
    """The live fan-out/fan-in check is graded from stamps and dispatcher state, never by the model."""

    def grade(self, stamps: dict, complete: bool = True, handles: bool = True) -> dict:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dispatch = root / "dispatch.js"
            dispatch.write_text("process.stdout.write(JSON.stringify({complete: %s}))" % str(complete).lower())
            run_dir, marks = root / "run", root / "stamps"
            run_dir.mkdir()
            marks.mkdir()
            attempts = {f"att-{s}": {"step": s, "handle": "h" if handles else None,
                                     **({} if handles else {"executor": {"kind": "main-context"}})} for s in "ABJ"}
            (run_dir / "plan-dispatcher-state.json").write_text(json.dumps({
                "steps": {s: {"current_attempt": f"att-{s}"} for s in "ABJ"}, "attempts": attempts}))
            for step, (start, end) in stamps.items():
                (marks / f"{step}.json").write_text(json.dumps({"step": step, "start": start, "end": end}))
            return fanout.grade(dispatch, run_dir, marks)

    def test_parallel_fan_out_then_fan_in_passes(self):
        result = self.grade({"A": (0, 30), "B": (1, 31), "J": (32, 62)})
        self.assertTrue(result["pass"], result)
        self.assertTrue(result["fan_out_parallel"])
        self.assertEqual(result["fan_out_overlap_seconds"], 29.0)
        self.assertEqual(result["runner"], {"A": "native", "B": "native", "J": "native"})

    def test_sequential_steps_pass_the_order_but_report_no_fan_out(self):
        result = self.grade({"A": (0, 30), "B": (30, 60), "J": (61, 90)}, handles=False)
        self.assertTrue(result["pass"], result)
        self.assertFalse(result["fan_out_parallel"])
        self.assertEqual(result["runner"]["A"], "main-context")

    def test_join_before_both_suppliers_end_fails(self):
        result = self.grade({"A": (0, 30), "B": (1, 45), "J": (40, 70)})
        self.assertFalse(result["fan_in_order"])
        self.assertFalse(result["pass"])

    def test_incomplete_run_fails(self):
        result = self.grade({"A": (0, 30), "B": (1, 31)}, complete=False)
        self.assertFalse(result["pass"])
        self.assertFalse(result["complete"])


class HostCoverageTest(unittest.TestCase):
    """A counter the host's events cannot show is unmeasured, never a zero that passes a comparison."""

    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def test_a_host_with_no_per_call_usage_has_no_stage_turns_not_zero_turns(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED)
        self.assertIn("stage_turns", m["unmeasured"])
        self.assertNotIn("model_glue", m["unmeasured"])  # Codex's tool calls are parsed
        self.assertEqual([r["seconds"] for r in m["stages"]], [5.0, 8.0])  # time is still measured
        for row in m["stages"]:
            self.assertIsNone(row["turns"])
            self.assertGreater(row["tool_calls"], 0)
        self.assertEqual(m["turns"], 12)  # the session's own total is still reported
        self.assertEqual(m["tokens"]["input_peak"], None)  # no output figure is built from events
        self.assertIsNone(m["cost_usd"], "a host that reports no cost has an unknown cost, not $0")
        kept = run.baseline_stages(m["stages"])
        self.assertEqual(kept[0], {"stage": "intake", "outcome": "done", "seconds": 5.0, "turns": None})

    def test_the_stage_a_codex_run_never_accepted_is_attributed_from_its_events(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED[:1], status="active", stage="spec")
        incomplete = [r for r in m["stages"] if r.get("incomplete")]
        self.assertEqual([r["stage"] for r in incomplete], ["spec"])
        self.assertGreater(incomplete[0]["seconds"], 0)
        self.assertGreater(incomplete[0]["tool_calls"], 0)
        self.assertIsNone(incomplete[0]["turns"])

    def test_a_claude_stream_measures_its_tool_calls_and_leaves_the_grok_only_counters_unmeasured(self):
        stream = claude_stream(["git add -A && git commit -m x", "shiploop complete --run-dir r"] * 3)
        m = collect_stream(stream, self.ACCEPTED)
        for name in ("cancelled_tool_calls", "knowledge_reads", "compactions", "truncated_outputs"):
            self.assertIn(name, m["unmeasured"], name)
        for name in ("model_glue", "shiploop_failures", "tmp_writes", "stage_tool_calls"):
            self.assertNotIn(name, m["unmeasured"], name)
        self.assertNotIn("stage_turns", m["unmeasured"])
        self.assertEqual(len(m["model_glue"]), 3, "three git commands by the model")
        self.assertEqual(m["shiploop_failures"], [], "'error: refused' is no ShipLoop refusal line and carries no exit code")
        self.assertEqual([(r["tool_calls"], r["turns"] is not None) for r in m["stages"]], [(3, True), (3, True)])
        self.assertEqual(m["tokens"]["input_peak"], 10)
        self.assertEqual(metrics.count(m, "model_glue"), 3)
        self.assertEqual(metrics.count({"unmeasured": {}, "model_glue": [1, 2]}, "model_glue"), 2)
        first = metrics.summary_lines(m)[0]
        self.assertIn("model glue 3", first)
        self.assertIn("ShipLoop command failures 0", first)
        self.assertIn("cancelled tool calls not measured", first)

    def test_a_grok_shaped_stream_measures_every_counter(self):
        stream = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}},
                  {"type": "tool_call", "toolCallId": "a", "rawInput": {"command": "git add -A"}}] * 4
        # Every counter: the detectors read Grok's events. (A context window is a figure Grok never reports, and nothing in
        # its events marks a session start, so the count of sessions that never reported is unmeasured too.)
        self.assertEqual(set(collect_stream(stream, self.ACCEPTED)["unmeasured"]),
                         {"window_tokens", "unreported_sessions", "tokens_processed", "tokens_output"})  # its end has no usage

    def test_the_baseline_row_carries_unmeasured_counters_as_null_with_their_names(self):
        result = {"case": "hello", "metrics": {"turns": 5, "cost_usd": None, "model_glue": None,
                                               "shiploop_failures": None, "stages": [],
                                               "unmeasured": {"model_glue": "why", "shiploop_failures": "why"}}}
        row = run.baseline_row(result, None, None)
        self.assertIsNone(row["model_glue"])
        self.assertIsNone(row["shiploop_failures"])
        self.assertEqual(row["unmeasured"], ["model_glue", "shiploop_failures"])
        self.assertEqual(run.baseline_row({"case": "hello", "metrics": {}}, None, None)["unmeasured"], [])

    def test_the_costliest_stages_rank_by_minutes_when_the_host_reports_no_turns(self):
        rows = [{"stage": "intake", "seconds": 60.0, "turns": None}, {"stage": "plan", "seconds": 6000.0, "turns": None},
                {"stage": "spec", "seconds": 600.0, "turns": None}]
        m = {"turns": 9, "cost_usd": None, "sessions": [], "compactions": 0, "truncated_outputs": 0,
             "cancelled_tool_calls": [], "shiploop_failures": [], "model_glue": [], "asked_user": [],
             "improve_children": 0, "script_verifications": {"passed": 0, "records": 0}, "stages": rows,
             "unmeasured": {"stage_turns": "x"}}
        costly = metrics.summary_lines(m)[-1]
        self.assertTrue(costly.startswith("costliest stages: plan 100.0m, spec 10.0m, intake 1.0m"), costly)
        self.assertIn("this host reports no per-stage turns", costly)
        self.assertIn("cost not reported", metrics.summary_lines(m)[0])

    def test_progress_prints_minutes_and_the_inner_loop_stage_for_a_host_without_turns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            stream = codex_stream(12)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
            (out / "timeline.jsonl").write_text("".join(
                json.dumps({"line": n, "t": 100.0 + 30 * n}) + "\n" for n in range(len(stream))))
            write_engine_records(run_dir, [("A1", "intake", "done", 190.0)], status="active", stage="inner-loop",
                                 inner={"work_index": 0, "work_items": [{"id": "W1"}],
                                        "inner_loops": {"W1": {"stage": "implement"}}})
            text = progress.report(out)
        self.assertIn("accepted: intake 1.5m", text)
        # The stage still being worked has a row that moves with every poll: it is not listed as accepted.
        self.assertNotIn("implement", next(line for line in text.splitlines() if "accepted:" in line))
        self.assertNotIn("intake 0t", text)
        self.assertIn("peak context n/a", text)
        # The in-progress stage is the item's own, not the navigator's pseudo-label.
        self.assertIn("stage implement", text)
        self.assertNotIn("stage inner-loop", text)


class StageDiffTest(unittest.TestCase):
    """A stage row that is incomplete or unmeasured is never compared as a whole measurement."""

    def test_an_incomplete_row_on_either_side_is_not_compared_as_a_stage(self):
        cut = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "implement", "incomplete": True,
                                                              "turns": 5, "seconds": 30}]
        whole = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "implement", "turns": 50, "seconds": 600}]
        for before, now in ((cut, whole), (whole, cut)):
            text = "\n".join(run.stage_diff_lines(before, now))
            self.assertNotIn("implement 5->50", text)
            self.assertNotIn("implement 50->5", text)
            self.assertIn("covers 1 of 2 stages (1 not comparable", text)
            self.assertIn("implement", text.split("not comparable")[1])
            self.assertNotIn("only now", text)
            self.assertNotIn("only before", text)

    def test_a_stage_unmeasured_on_the_baseline_is_not_reported_as_new(self):
        before = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "plan", "timing": "unavailable"}]
        now = [{"stage": "spec", "turns": 10, "seconds": 60}, {"stage": "plan", "turns": 8, "seconds": 90}]
        text = "\n".join(run.stage_diff_lines(before, now))
        self.assertNotIn("only now", text)
        self.assertIn("covers 1 of 2 stages", text)  # coverage is stated for the baseline side too
        reverse = "\n".join(run.stage_diff_lines(now, before))
        self.assertNotIn("only before", reverse)
        self.assertIn("covers 1 of 2 stages", reverse)

    def test_a_stage_with_one_unmeasured_visit_is_not_summed_as_if_whole(self):
        spec = {"stage": "spec", "turns": 1, "seconds": 6}
        before = [spec, {"stage": "implement", "turns": 5, "seconds": 60}, {"stage": "implement", "timing": "unavailable"}]
        now = [spec, {"stage": "implement", "turns": 5, "seconds": 60}, {"stage": "implement", "turns": 9, "seconds": 90}]
        text = "\n".join(run.stage_diff_lines(before, now))
        self.assertNotIn("implement 5->14", text)
        self.assertIn("1 not comparable", text)
        self.assertEqual(run.stage_diff_lines([{"stage": "implement", "timing": "unavailable"}], now),
                         ["per-stage comparison unavailable (one run has no measured stage timing)"])

    def test_a_true_one_sided_stage_is_still_reported_with_its_coverage(self):
        before = [{"stage": "spec", "turns": 1, "seconds": 6}, {"stage": "plan", "turns": 1, "seconds": 6}]
        now = [{"stage": "spec", "turns": 1, "seconds": 6}, {"stage": "implement", "turns": 1, "seconds": 6}]
        lines = run.stage_diff_lines(before, now)
        self.assertEqual(lines[0], "per-stage comparison covers 1 of 3 stages")
        self.assertIn("only now: implement", lines)
        self.assertIn("only before: plan", lines)

    def test_a_host_with_no_stage_turns_is_compared_by_minutes_not_called_unchanged(self):
        before = [{"stage": "plan", "turns": None, "seconds": 6000}, {"stage": "spec", "turns": None, "seconds": 600}]
        now = [{"stage": "plan", "turns": None, "seconds": 36000}, {"stage": "spec", "turns": None, "seconds": 600}]
        lines = run.stage_diff_lines(before, now)
        self.assertEqual(lines, ["stage minutes (this host reports no per-stage turns): plan 100->600"])
        self.assertEqual(run.stage_diff_lines(before, before), ["no per-stage minute difference (turns not measured)"])
        mixed = run.stage_diff_lines(before, [{"stage": "plan", "turns": 4, "seconds": 36000},
                                              {"stage": "spec", "turns": 2, "seconds": 600}])
        self.assertEqual(len(mixed), 1)
        self.assertTrue(mixed[0].startswith("stage minutes"), mixed)  # a turn count on one side only is no comparison

    def test_short_stages_show_their_seconds_not_a_rounded_minute(self):
        lines = run.stage_diff_lines([{"stage": "spec", "turns": 3, "seconds": 30}],
                                     [{"stage": "spec", "turns": 4, "seconds": 40}])
        self.assertEqual(lines, ["stage turns: spec 3->4 (0.5->0.7m)"])


class ReportedCostThroughMainTest(PrintedCase):
    """What run.main prints for cost: unknown stays unknown, and a killed session makes a lower bound."""

    def line(self, printed: str, prefix: str) -> str:
        return next(ln for ln in printed.splitlines() if ln.startswith(prefix))

    def test_a_host_that_reports_no_cost_says_so_in_the_report_and_never_prints_zero(self):
        code, result, printed = self.invoke_printed("codex", "done")
        self.assertEqual(code, 0, result)
        self.assertIsNone(self.last_row()["cost_usd"])
        process = self.line(printed, "  process")
        self.assertIn("cost=not reported", process)
        self.assertNotIn("$0", process)
        self.assertIn("cost not reported", self.line(printed, "  metrics   turns"))


class CommittedVerdictTest(PrintedCase):
    """`committed` means the product is in HEAD, not that HEAD differs from a start that had no commit.

    On a fresh run ShipLoop's first act is an empty baseline commit, so HEAD always differs from "no commit".
    Known limit, not guarded: any file counts as product, so a future ShipLoop that returned only knowledge
    files (docs/shiploop/) to the source checkout before the product would pass early."""

    def repo(self) -> Path:
        repo = self.tmp / "source"
        repo.mkdir()
        self.git(repo, "init", "-q")
        return repo

    def git(self, repo: Path, *args: str) -> str:
        done = subprocess.run(["git", "-C", str(repo), "-c", "user.name=T", "-c", "user.email=t@example.invalid",
                               "-c", "commit.gpgsign=false", *args], check=True, capture_output=True, text=True)
        return done.stdout.strip()

    def verdict(self, repo: Path, start_head: str | None = None) -> dict:
        return run.committed_facts(run.knowledge_facts(repo), start_head)

    def test_a_repository_holding_only_the_empty_baseline_commit_has_no_product(self):
        repo = self.repo()
        self.git(repo, "commit", "-q", "--allow-empty", "-m", "Empty baseline for the first ShipLoop run")
        got = self.verdict(repo)
        self.assertEqual((got["pass"], got["head_files"]), (False, 0))
        self.assertTrue(got["head"], "HEAD exists and differs from a start with no commit: only the files say no")

    def test_one_committed_file_is_product(self):
        repo = self.repo()
        (repo / "hello.py").write_text("print('hi')\n")
        self.git(repo, "add", "--", "hello.py")
        self.git(repo, "commit", "-q", "-m", "product")
        got = self.verdict(repo)
        self.assertEqual((got["pass"], got["head_files"], got["uncommitted"]), (True, 1, []))

    def test_head_must_still_move_past_the_start_and_leave_no_product_path_uncommitted(self):
        repo = self.repo()
        (repo / "hello.py").write_text("print('hi')\n")
        self.git(repo, "add", "--", "hello.py")
        self.git(repo, "commit", "-q", "-m", "product")
        head = self.git(repo, "rev-parse", "HEAD")
        self.assertFalse(self.verdict(repo, start_head=head)["pass"], "HEAD never moved past where the run started")
        (repo / "extra.py").write_text("x = 1\n")
        got = self.verdict(repo)
        self.assertFalse(got["pass"], "a product path is left untracked")
        self.assertEqual((got["head_files"], got["uncommitted"]), (1, ["extra.py"]))

    def test_a_run_that_returned_nothing_fails_committed_in_the_result_the_row_and_the_report(self):
        fake = self.tmp / "claude-empty-baseline"
        fake.write_text(FAKE_CLAUDE_EMPTY_BASELINE)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        out = self.tmp / "out-empty-baseline"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--host", "claude", "--backend", "anthropic", "--claude-bin", str(fake), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines),
                             "--prompt", "make hello", "--check", "true"])
        result = json.loads((out / "result.json").read_text())
        # Everything else is right: ShipLoop is done, the plugin loaded, the check passes. Only the product is absent.
        self.assertTrue(result["shiploop"]["pass"], result["shiploop"])
        self.assertTrue(result["plugin"]["pass"] and result["invoked"]["pass"], result)
        self.assertTrue(all(c["pass"] for c in result["checks"]), result["checks"])
        self.assertEqual(code, 1, "a run that returned no file to the source checkout is not a pass")
        self.assertFalse(result["pass"])
        self.assertEqual((result["committed"]["pass"], result["committed"]["head_files"]), (False, 0))
        self.assertFalse(self.last_row()["verdicts"]["committed"])
        self.assertIn("0 files in HEAD", next(ln for ln in printed.getvalue().splitlines()
                                              if ln.startswith("  committed")))
        mismatch = (out / "mismatch.md").read_text()
        self.assertIn("**committed**", mismatch)
        self.assertIn("files in HEAD", mismatch)


class RegradeRecordTest(PrintedCase):
    """--resume-run on a finished run starts no host, so it restates the run's own record and invents none.

    The plugin verdict, the process block and the host, model and effort come from what the run recorded; a
    regrade that relabels a run, invents a clean exit or grades a Grok or Codex plugin from Claude's events
    replaces a finished result with a different one although nothing about the run changed."""

    HOSTS = ("claude", "grok", "codex")
    CLI = "python3 /x/skills/shiploop/scripts/shiploop next"

    def setUp(self):
        super().setUp()
        # A real host's events name the installed ShipLoop CLI by path, which is how a regrade sees that the skill
        # was invoked. The shared fakes print the bare command, so these tests use copies that print the path.
        for host in ("claude", "grok"):
            script = self.fakes[host]
            script.write_text(script.read_text().replace('"command": "shiploop next"', f'"command": "{self.CLI}"'))
            self.assertIn(self.CLI, script.read_text())

    def regrade(self, out: Path, *extra: str) -> tuple[dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main([*extra, "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                      "--baseline", str(self.baselines)])
        return json.loads((out / "result.json").read_text()), printed.getvalue()

    def finish_out_of_band(self, out: Path) -> None:
        shutil.rmtree(out / "work" / ".shiploop", ignore_errors=True)
        (out / "work" / ".shiploop").mkdir()
        (out / "work" / ".shiploop" / "report.html").write_text("<html></html>")
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "done"})

    def test_a_regrade_of_a_finished_run_keeps_its_passing_result_on_every_host(self):
        for host in self.HOSTS:
            with self.subTest(host=host):
                code, first, _ = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, first)
                result, _ = self.regrade(Path(first["output"]), "--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]))
                self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "process")})
                self.assertTrue(result["process"]["regraded"])
                for key in ("host", "model", "effort", "plugin"):
                    self.assertEqual(result[key], first[key], key)
                # what the host did is what the original run observed, not a clean exit made up for the regrade
                self.assertEqual({k: v for k, v in result["process"].items() if k != "regraded"}, first["process"])

    def test_a_regrade_never_turns_a_failed_host_into_a_pass(self):
        wrapper = self.tmp / "claude-exits-3"  # the run finishes, then the host exits non-zero
        wrapper.write_text(f'#!/bin/sh\n"{self.fakes["claude"]}" "$@"\nexit 3\n')
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "out-exit-3"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--host", "claude", "--backend", "anthropic", "--claude-bin", str(wrapper), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        first = json.loads((out / "result.json").read_text())
        self.assertEqual((code, first["pass"], first["shiploop"]["pass"]), (1, False, True))
        self.assertEqual((first["process"]["status"], first["process"]["returncode"]), ("failed", 3))
        result, printed = self.regrade(out)
        self.assertFalse(result["pass"], "a regrade cannot turn a failed host into a pass")
        self.assertEqual((result["process"]["status"], result["process"]["returncode"], result["process"]["pass"]),
                         ("failed", 3, False))
        self.assertEqual(result["process"]["sessions"], first["process"]["sessions"])
        self.assertEqual(result["process"]["elapsed_seconds"], first["process"]["elapsed_seconds"])
        self.assertEqual((result["termination"]["process_status"], result["termination"]["returncode"]), ("failed", 3))
        self.assertIn("process   FAIL", printed)
        self.assertIn("failed rc=3", (out / "mismatch.md").read_text())

    def test_a_regrade_with_no_record_of_a_host_exit_says_so_and_leaves_that_verdict_out(self):
        code, first, _ = self.invoke_printed("grok", "done")
        out = Path(first["output"])
        (out / "result.json").unlink()  # the harness died with its host: nothing recorded the exit
        result, printed = self.regrade(out)
        self.assertEqual((result["process"]["status"], result["process"]["returncode"], result["process"]["pass"]),
                         ("not observed", None, None))
        self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "committed", "checks")})
        self.assertIn("process   n/a   no host ran: regraded from what is on disk", printed)
        self.assertFalse((out / "mismatch.md").exists(), "an unobserved exit is not a failure")

    def test_a_regrade_keeps_the_host_model_and_effort_the_run_recorded_whatever_the_command_line_says(self):
        code, first, _ = self.invoke_printed("grok", "done")
        result, printed = self.regrade(Path(first["output"]), "--host", "codex", "--codex-bin", str(self.fakes["codex"]),
                                       "--model", "gpt-6-sol", "--effort", "xhigh")
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (first["host"], first["model"], first["effort"]))
        self.assertEqual((first["host"], first["effort"]), ("grok", "medium"))
        self.assertTrue(result["pass"], {k: result[k] for k in ("invoked", "plugin", "process")})
        self.assertIn("ignoring --host codex, --model gpt-6-sol, --effort xhigh", printed)

    def test_a_run_resumed_on_another_host_is_regraded_as_that_host_with_its_plugin_and_versions(self):
        code, stopped, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(stopped["output"])
        os.environ["FAKE_MODE"] = "nothing"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        resumed = json.loads((out / "result.json").read_text())
        self.assertEqual((resumed["host"], resumed["resumed_run"]["from_host"]), ("codex", "grok"))
        self.finish_out_of_band(out)
        result, _ = self.regrade(out)  # no --host: the invocation.json host is grok, the run's own record says codex
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (resumed["host"], resumed["model"], resumed["effort"]))
        self.assertEqual(result["plugin"], resumed["plugin"])
        self.assertEqual({k: v for k, v in result["versions"].items() if k != "regraded"}, resumed["versions"])
        self.assertTrue(result["process"]["regraded"])


class BaselineAbsentTest(PrintedCase):
    def test_rows_that_name_no_host_say_nothing_was_compared_instead_of_printing_nothing(self):
        self.baselines.write_text(json.dumps({"case": "hello", "source": "checkout", "turns": 3}) + "\n")
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertIn("baseline  nothing compared: 1 earlier row(s) for hello, none recorded with grok/", printed)
        self.assertEqual(run.scan_baseline(self.baselines, "hello", "checkout", "grok", "m", "e")[1], 2)

    def test_a_resumed_run_says_it_is_not_a_baseline(self):
        code, stopped, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", stopped["output"],
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertIn("baseline  nothing compared: a resumed or seeded run is not a baseline", printed.getvalue())

    def test_the_host_flag_is_seen_only_when_it_was_given(self):
        self.assertFalse(run.host_given([]))
        self.assertTrue(run.host_given(["--host", "claude"]))
        self.assertTrue(run.host_given(["--case", "hello", "--host=codex"]))


class PlanningReviewBaselineThroughMainTest(PrintedCase):
    """The committed row and the printed report as run.main writes them, for runs of the same and of different
    planning_review modes. The fake host's state.md records the mode named by FAKE_PLANNING_REVIEW ("absent": none)."""

    def run_with(self, mode: str) -> tuple[dict, str]:
        os.environ["FAKE_PLANNING_REVIEW"] = mode
        self.addCleanup(os.environ.pop, "FAKE_PLANNING_REVIEW", None)
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        return self.last_row(), printed

    def earlier_row(self, **changes) -> None:
        """Make the last committed row the only one, with `changes` (None removes a key): the row the next run compares with."""
        row = self.last_row()
        for key, value in changes.items():
            row.pop(key, None) if value is None else row.__setitem__(key, value)
        self.baselines.write_text(json.dumps(row) + "\n")

    def test_the_row_records_the_mode_the_runs_state_named_and_not_recorded_when_it_named_none(self):
        self.assertEqual([self.run_with(mode)[0]["planning_review"] for mode in ("none", "stage", "absent")],
                         ["none", "stage", "not recorded"])

    def test_a_second_run_of_the_same_mode_is_compared_and_the_report_names_the_mode(self):
        self.run_with("none")
        _, printed = self.run_with("none")
        self.assertRegex(printed, r"  baseline  vs \d{4}-\d\d-\d\d \(ShipLoop .*, same grok/.*, planning_review none\): turns ")
        self.assertIn("            ", printed.split("planning_review none): turns ")[1])  # the stage lines follow
        self.assertNotIn("not compared across", printed)
        self.assertNotIn("records no mode", printed)  # it recorded one: no rule was used

    def number_rows(self, *turns: int) -> None:
        """Give each committed row a distinctive `turns`, so the printed `turns <earlier> -> <now>` names the row compared with."""
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual(len(rows), len(turns))
        self.baselines.write_text("".join(json.dumps(dict(row, turns=n)) + "\n" for row, n in zip(rows, turns)))

    def test_a_run_with_only_rows_of_the_other_mode_compares_nothing_and_says_there_is_no_earlier_row_of_its_mode(self):
        for first, second in (("stage", "none"), ("none", "stage")):
            with self.subTest(first=first, second=second):
                self.baselines.unlink(missing_ok=True)
                self.run_with(first)
                _, printed = self.run_with(second)
                self.assertIn(f"  baseline  not compared across planning_review modes ({second} vs {first}); "
                              f"no earlier row of mode {second}; the last row for this driver is ", printed)
                self.assertNotIn("baseline  vs", printed)
                self.assertNotRegex(printed, r"turns \S+ -> |stage turns|per-stage")  # nothing below the line is compared
        self.assertEqual(len(self.baselines.read_text().splitlines()), 2)  # the run still writes its own row

    def test_a_run_is_compared_with_the_last_row_of_its_own_mode_not_refused_because_the_last_row_has_the_other(self):
        self.run_with("stage")
        _, printed = self.run_with("none")  # the only earlier row is a stage row: nothing to compare
        self.assertIn("no earlier row of mode none", printed)
        self.number_rows(11, 22)
        _, printed = self.run_with("stage")  # [stage, none] then stage: the stage row, found past the none row
        self.assertIn("planning_review stage): turns 11 -> ", printed)
        self.assertNotIn("not compared across", printed)

    def test_two_modes_interleaved_each_pick_their_own_last_row(self):
        for mode in ("stage", "none", "stage", "none"):
            self.run_with(mode)
        self.number_rows(111, 222, 333, 444)
        _, printed = self.run_with("none")
        self.assertIn("planning_review none): turns 444 -> ", printed)
        self.number_rows(111, 222, 333, 444, 555)
        _, printed = self.run_with("stage")
        self.assertIn("planning_review stage): turns 333 -> ", printed)
        self.assertNotIn("not compared across", printed)

    def test_an_earlier_row_with_no_mode_compares_as_stage_only_when_its_plugin_predates_the_option(self):
        self.run_with("stage")
        self.earlier_row(planning_review=None, plugin_version="1.21.0")
        _, printed = self.run_with("stage")
        self.assertIn("planning_review stage): turns ", printed)
        self.assertIn("            the earlier row records no mode, read as stage because plugin 1.21.0 predates the option", printed)
        self.earlier_row(planning_review=None, plugin_version="1.21.0")
        _, printed = self.run_with("none")
        self.assertIn("  baseline  not compared across planning_review modes (none vs stage); no earlier row of mode none; ", printed)
        self.assertIn("; it records no mode, read as stage because plugin 1.21.0 predates the option", printed)
        for version in (None, "1.22.0"):  # no plugin_version, and a release that has the option but wrote no field
            self.earlier_row(planning_review=None, plugin_version=version)
            _, printed = self.run_with("stage")
            self.assertIn("modes (stage vs not recorded); no earlier row of mode stage; ", printed, version)
            self.assertNotIn("baseline  vs", printed, version)

    def test_an_old_row_still_serves_as_the_stage_row_after_a_none_run_has_been_recorded_after_it(self):
        self.run_with("stage")
        self.earlier_row(planning_review=None, plugin_version="1.21.0", turns=555)
        _, printed = self.run_with("none")
        self.assertIn("(none vs stage); no earlier row of mode none; ", printed)
        _, printed = self.run_with("stage")  # [old row, none row] then stage: the old row, read as stage
        self.assertIn("planning_review stage): turns 555 -> ", printed)
        self.assertIn("            the earlier row records no mode, read as stage because plugin 1.21.0 predates the option", printed)

    def test_a_run_whose_state_named_no_mode_is_compared_with_no_row(self):
        self.run_with("stage")
        _, printed = self.run_with("absent")
        self.assertIn("modes (not recorded vs stage); this run records no mode; the last row for this driver is ", printed)
        _, printed = self.run_with("absent")  # two unrecorded modes are not known to match
        self.assertIn("modes (not recorded vs not recorded); this run records no mode; ", printed)
        self.assertNotIn("baseline  vs", printed)


class AttributionEdgeTest(unittest.TestCase):
    """Edge cases of per-stage attribution: seeded stages, an empty history, an unstamped action, a block."""

    USAGE = [{"type": "usage", "usage": {"input_tokens": 10, "output_tokens": 1}} for _n in range(12)]

    def test_a_stage_the_harness_seeded_has_no_timing_and_does_not_bill_the_host_start_up(self):
        # Seeded stages are accepted before the host's first event (t = 100.0).
        m = collect_stream(self.USAGE, [("S1", "intake", "done", 95.0), ("S2", "spec", "done", 96.0),
                                        ("A3", "plan", "done", 110.0)])
        self.assertEqual([(r["stage"], r.get("timing")) for r in m["stages"]],
                         [("intake", "unavailable"), ("spec", "unavailable"), ("plan", None)])
        self.assertEqual(m["stages"][2]["seconds"], 10.0)  # from the first host event, not from the seed
        self.assertGreater(m["stages"][2]["turns"], 0)
        self.assertTrue(all(r.get("seconds", 0) >= 0 for r in m["stages"]))

    def test_a_run_that_stopped_before_its_first_acceptance_still_names_its_stage(self):
        m = collect_stream(self.USAGE, [], status="active", stage="intake")
        self.assertEqual([(r["stage"], r.get("incomplete")) for r in m["stages"]], [("intake", True)])
        self.assertGreater(m["stages"][0]["turns"], 0)
        self.assertGreater(m["stages"][0]["seconds"], 0)

    def test_an_incomplete_row_after_an_unstamped_acceptance_is_unavailable_not_overstated(self):
        m = collect_stream(self.USAGE, [("A1", "intake", "done", 101.0), ("A2", "spec", "done", None)],
                           status="active", stage="plan")
        self.assertEqual(m["stages"][-1], {"stage": "plan", "outcome": None, "incomplete": True,
                                           "timing": "unavailable"})

    def test_without_a_runner_timeline_the_unaccepted_stage_is_still_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps(self.USAGE[0]) + "\n")
            write_engine_records(out / "run", [("A1", "intake", "done", 101.0)], status="active", stage="spec")
            m = metrics.collect(out, out / "run")
        self.assertEqual([(r["stage"], r.get("incomplete")) for r in m["stages"]],
                         [("intake", None), ("spec", True)])
        self.assertTrue(all(r["timing"] == "unavailable" for r in m["stages"]))

    def test_a_stage_the_engine_accepted_as_blocked_was_not_left_unaccepted(self):
        accepted = [("A1", "intake", "done", 101.0), ("A2", "system-test", "blocked", 104.0)]
        m = collect_stream(self.USAGE, accepted, status="blocked", stage="system-test")
        self.assertFalse(any(r.get("incomplete") for r in m["stages"]))
        engine = {"status": "blocked", "stage": "system-test", "status_reason": "user: a person must look\n at it",
                  "history": [{"stage": "system-test", "outcome": "blocked", "action": "A2"}]}
        t = run.termination_facts({"status": "exited", "returncode": 0, "sessions": [{"stop": "end_turn"}],
                                   "resumes": 0}, engine, "ShipLoop run is blocked")
        self.assertIsNone(t["engine_unaccepted_stage"])
        self.assertEqual((t["engine_stage"], t["engine_status_reason"]), ("system-test", "user: a person must look at it"))
        line = run.stopped_line(t)
        self.assertIn("engine blocked at system-test (user: a person must look at it)", line)
        self.assertNotIn("never accepted", line)

    def test_a_blocked_run_whose_current_stage_was_not_the_blocked_one_still_has_an_unaccepted_stage(self):
        engine = {"status": "blocked", "stage": "plan",
                  "history": [{"stage": "spec", "outcome": "blocked", "action": "A2"}]}
        self.assertEqual(metrics.pending_stage(engine), "plan")

    def test_a_halted_run_names_the_item_s_own_stage(self):
        engine = {"status": "halted", "stage": "inner-loop", "work_index": 0, "work_items": [{"id": "W1"}],
                  "inner_loops": {"W1": {"stage": "test-green"}}, "status_reason": "halted by the user"}
        t = run.termination_facts({"status": "exited", "returncode": 0, "sessions": [{}], "resumes": 0},
                                  engine, "ShipLoop run is halted")
        self.assertEqual((t["engine_stage"], t["engine_unaccepted_stage"]), ("test-green", "test-green"))
        self.assertIn("engine halted with test-green never accepted (halted by the user)", run.stopped_line(t))


class CouldNotRunCountTest(unittest.TestCase):
    """A test attempt that reached no verdict is counted and shown, because it is an environment problem."""

    def records(self, tmp: str) -> Path:
        tests = Path(tmp) / "run" / "tests"
        tests.mkdir(parents=True)
        (tests / "nav-1-verify1.md").write_text('{"passed": false, "disposition": "could-not-run", '
                                                '"runs": [{"command": "a", "status": "timeout"}]}')
        (tests / "nav-1-verify2.md").write_text('{"passed": true, "runs": [{"command": "a"}]}')
        (tests / "nav-2-verify1.md").write_text('{"passed": false, "runs": [{"command": "b"}]}')
        return Path(tmp) / "run"

    def test_could_not_run_records_are_counted_apart_from_failures_and_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(metrics.verifications(self.records(tmp)),
                             {"records": 3, "passed": 1, "could_not_run": 1, "commands": 3, "red": 0})

    def test_the_report_and_the_progress_line_show_the_could_not_run_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = self.records(tmp)
            out = Path(tmp)
            (out / "events.jsonl").write_text(json.dumps({"type": "usage", "usage": {"input_tokens": 1}}) + "\n")
            write_engine_records(run_dir, [("A1", "intake", "done", 101.0)])
            m = metrics.collect(out, run_dir)
            self.assertIn("script verifications 1/3 passed (1 could not run)", metrics.summary_lines(m)[0])
            self.assertIn("1 could not run", progress.report(out))


class RedRecordCountTest(unittest.TestCase):
    """A record that passed because its commands ran red is counted apart from the green passes (r1 Battleship: 2 of the
    10 passed records). The count reads what ran (a run whose status is `red`), not what the record expected."""

    def verify(self, records: dict) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "run" / "tests"
            tests.mkdir(parents=True)
            for name, record in records.items():
                (tests / f"{record['action']}-verify1.md").write_text(run.store.dumps(record, "ShipLoop test-loop verification"))
            return metrics.verifications(Path(tmp) / "run")

    def test_records_whose_commands_ran_red_are_counted_apart_from_green_passes(self):
        records = json.loads((TOOL_BLOCKS / "verify-records.json").read_text())
        self.assertEqual(self.verify(records), {"records": 3, "passed": 3, "could_not_run": 0, "commands": 5, "red": 2})
        # The test-author probe accepts red or passed (`expect: a test ran`): one that ran green is a green pass.
        probe = json.loads(json.dumps(records))
        for each in probe["test-author"]["runs"]:
            each["status"], each["exit"] = "passed", 0
        self.assertEqual(self.verify(probe)["red"], 1)

    def test_the_report_names_the_red_records_without_calling_them_expected(self):
        m = collect_stream(codex_stream(1), [])
        m["script_verifications"] = {"records": 10, "passed": 10, "could_not_run": 0, "commands": 20, "red": 2}
        line = metrics.summary_lines(m)[0]
        self.assertIn("script verifications 10/10 passed (2 ran red)", line)
        m["script_verifications"] = {"records": 10, "passed": 9, "could_not_run": 1, "commands": 20, "red": 0}
        self.assertIn("script verifications 9/10 passed (1 could not run)", metrics.summary_lines(m)[0])
        self.assertNotIn("ran red", metrics.summary_lines(m)[0])
        self.assertNotIn("expected", metrics.summary_lines(m)[0])


class RetentionIdCountTest(unittest.TestCase):
    """The scoring case's retention check counts requirement ids the way the engine does (plan R7).

    The check is the catalog's own shell command, run through `run.run_checks`, and the engine's
    `_REQUIREMENT_ID` is the oracle: a spec form the engine accepts must not fail a correct run.
    """

    # A spec records its ids in any of these forms; the engine reads an id anywhere on a line.
    FORMS = {
        "heading": "## R-1 Fire\n## R-2 Board\n",  # the one form the earlier line-start pattern also read
        "bullet": "- R-1 Fire\n- R-2 Board\n",
        "bold bullet": "- **R-1** Fire\n- **R-2** Board\n",
        "table row": "| R-1 | Fire |\n| R-2 | Board |\n",
        "mixed line": "Requirements: R-1 R-1a R-2\n",  # R-1a is not an id: BSD `grep -ow` reads 1 of the 2 here
    }
    NEW = "R-3 Accuracy\nEvery fire returns shots, hits and accuracy.\n"

    @staticmethod
    def retention_check() -> str:
        retention = json.loads(run.CASES.read_text())["battleship-scoring"]["retention"]
        found = [command for command in retention if "ids()" in command]
        assert len(found) == 1, "the requirement-id retention check moved: update this test"
        return found[0]

    @staticmethod
    def earlier_ids(result: dict) -> int:
        """The count the check printed (BSD `wc -l` pads it with spaces, so read it as a number)."""
        found = re.search(r"earlier ids:\s*(\d+);", result["output"])
        assert found, "the check no longer prints its id count: " + result["output"]
        return int(found.group(1))

    def verdict(self, prior_spec: str, current_spec: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            prior, work = Path(tmp) / "prior", Path(tmp) / "work"
            for root, text in ((prior, prior_spec), (work, current_spec)):
                (root / "docs" / "shiploop").mkdir(parents=True)
                (root / "docs" / "shiploop" / "spec.md").write_text(text)
            return run.run_checks(work, [self.retention_check()], env={"PRIOR_WORK": str(prior)})[0]

    def test_a_correct_spec_passes_in_every_form_and_the_count_is_the_engines(self):
        for name, form in self.FORMS.items():
            with self.subTest(form=name):
                engine = run.knowledge_home._REQUIREMENT_ID.findall(form)
                self.assertEqual(len(set(engine)), 2, "the form must hold two ids for the engine")
                result = self.verdict(form, form + self.NEW)
                self.assertTrue(result["pass"], result["output"])
                self.assertEqual(self.earlier_ids(result), 2, "the engine's count, not a pattern's: " + result["output"])

    def test_a_dropped_id_fails_in_every_form_and_is_named(self):
        for name, form in self.FORMS.items():
            with self.subTest(form=name):
                kept = form.replace("R-2", "R-9") if name != "mixed line" else "Requirements: R-1 R-1a R-9\n"
                result = self.verdict(form, kept + self.NEW)
                self.assertFalse(result["pass"], "a dropped earlier id must still fail: " + result["output"])
                self.assertIn("missing: R-2", result["output"])

    def test_a_spec_with_no_ids_still_fails_because_nothing_was_retained(self):
        result = self.verdict("Fire and board.\n", "Fire and board.\n" + self.NEW)
        self.assertFalse(result["pass"], result["output"])
        self.assertEqual(self.earlier_ids(result), 0)

    def test_the_catalog_pattern_is_written_verbatim_and_matches_the_engine_regex(self):
        # Drift guard: the engine's `\b(R-\d+)\b` is the oracle, so a change to either side fails here.
        found = re.search(r"grep -oE '([^']*)' \"\$1/docs/shiploop/spec\.md\"", self.retention_check())
        self.assertIsNotNone(found, "ids() no longer reads the spec with one `grep -oE '<pattern>'`")
        pattern = found.group(1)
        self.assertEqual(pattern, r"\bR-[0-9]+\b", "verbatim, with a real backslash (JSON-escaped in the catalog)")
        samples = ("R-1 R-1a R-2\n", "XR-3 R-4_ R-5\n", "[R-6] (R-7).\n", "R-8R-9\n", "R-10.2 R-007\n",
                   "| R-11 | x |\n- **R-12** y\n## R-13 z\n", "r-1 R- R-x R-\n", "no ids here\n")
        for text in samples:
            with self.subTest(text=text):
                from_grep = subprocess.run(["grep", "-oE", pattern], input=text, capture_output=True,
                                           text=True).stdout.split()
                self.assertEqual(sorted(set(from_grep)),
                                 sorted(set(run.knowledge_home._REQUIREMENT_ID.findall(text))))


class RolloutContextTest(unittest.TestCase):
    """The Codex rollout reader: what counts as a call, a compaction and the main thread's peak (R15)."""

    WINDOWS = [[999, 1015], [1015, 1035], [1035, 1055], [1055, 1100], None]

    def read(self, files: list[list[str]], windows=None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for number, lines in enumerate(files):
                write_rollout(out, f"{number}", lines)
            return rollouts.rollout_context(out, self.WINDOWS if windows is None else windows)

    def test_a_compaction_request_is_not_a_call_and_never_the_peak(self):
        got = self.read(two_thread_rollouts())
        # 6 root calls; the 8 root usage records minus the two compaction requests, and the repeated token_count
        # neither adds a call nor changes the peak. The requests' 9500 and 8000 are heavier than any call.
        self.assertEqual((got["calls"], got["peak"], got["peakPct"], got["window"]), (6, 9000, 90.0, 10000))
        self.assertEqual(got["compactions"], 2)

    def test_sub_agent_threads_are_reported_apart_from_the_main_thread(self):
        got = self.read(two_thread_rollouts())
        # The sub-agent's own compaction counts for it; the inherited copy of its parent's does not count at all.
        self.assertEqual(got["subagents"], {"calls": 3, "peak": 7000, "compactions": 1})
        self.assertEqual(got["window"], 10000, "the sub-agent's 20000 window is not the main thread's")

    def test_each_stage_window_gets_its_own_calls_peak_and_compactions(self):
        got = self.read(two_thread_rollouts())
        self.assertEqual(got["perStage"], [
            {"calls": 2, "peak": 2000, "peakPct": 20.0, "compactions": 0},  # the call at the window's end counts
            {"calls": 1, "peak": 9000, "peakPct": 90.0, "compactions": 1},  # and not again in the next window
            {"calls": 2, "peak": 4000, "peakPct": 40.0, "compactions": 0},
            {"calls": 1, "peak": 1500, "peakPct": 15.0, "compactions": 1},
            None])  # a stage with no window has no figures, not zeros
        self.assertEqual(sum(w["calls"] for w in got["perStage"] if w), got["calls"])

    def test_a_call_outside_every_window_is_in_the_headline_only(self):
        got = self.read(two_thread_rollouts(), [[999, 1015]])
        self.assertEqual(got["calls"], 6)
        self.assertEqual(got["perStage"], [{"calls": 2, "peak": 2000, "peakPct": 20.0, "compactions": 0}])

    def test_no_rollout_is_unmeasured_with_its_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rollouts.rollout_context(Path(tmp), []), {"unmeasured": rollouts.NO_ROLLOUTS})
            (Path(tmp) / "home" / ".codex" / "sessions").mkdir(parents=True)  # a home with no rollout in it
            self.assertEqual(rollouts.rollout_context(Path(tmp), []), {"unmeasured": rollouts.NO_ROLLOUTS})
        self.assertIn("rollout-*.jsonl", rollouts.NO_ROLLOUTS)

    def test_rollouts_with_no_main_thread_call_are_unmeasured_not_zero_calls(self):
        sub_only = [rollout_line("session_meta", 1000, {"id": "sub"}), *thread_calls("sub", "root", 20000, SUB_THREAD)]
        self.assertEqual(self.read([sub_only]), {"unmeasured": rollouts.NO_CALLS})
        self.assertEqual(self.read([[rollout_line("session_meta", 1000, {"id": "root"})]]),
                         {"unmeasured": rollouts.NO_CALLS})

    def test_a_window_nobody_reported_is_none_and_gives_no_percentage(self):
        root = [usage_line(1000, "root", "root", "r1", 4000), usage_line(1001, "root", "root", "r2", 5000)]
        got = self.read([root], [[999, 1100]])
        self.assertEqual((got["window"], got["calls"], got["peak"], got["peakPct"]), (None, 2, 5000, None))
        self.assertEqual(got["perStage"], [{"calls": 2, "peak": 5000, "peakPct": None, "compactions": 0}])

    def test_a_resumed_session_is_another_root_thread_whose_calls_and_compactions_add_up(self):
        first = [usage_line(1000, "a", "a", "a1", 1000), *thread_calls("a", "a", 10000, [(1001, "aq", 6000, True)])]
        second = thread_calls("b", "b", 10000, [(2000, "b1", 3000, False), (2001, "bq", 7000, True),
                                               (2002, "b2", 2500, False)])
        got = self.read([first, second], [])
        self.assertEqual((got["calls"], got["peak"], got["compactions"]), (3, 3000, 2))
        self.assertEqual(got["subagents"], {"calls": 0, "peak": None, "compactions": 0})


class MixedHostTurnsTest(unittest.TestCase):
    """Live finding (round 2, Grok resume): a run's events.jsonl can hold turn rows of two shapes, those with a `call`
    key (Claude's assistant messages) and those without (Grok's usage events); per_stage crashed on the mix, after the
    host had finished, so the run got no metrics and no review export."""

    def test_per_stage_counts_the_rows_that_carry_a_call_and_ignores_the_rest(self):
        accepted = [{"stage": "a", "outcome": "done", "t": 105.0}, {"stage": "b", "outcome": "done", "t": 112.0}]
        stamps = {n: 100.0 + n for n in range(21)}
        turns = [{"t": 101.5, "input": 10, "call": True}, {"t": 102.0, "input": 20},
                 {"t": 103.0, "input": 30, "call": False}, {"t": 106.0, "input": 40, "call": True}]
        rows = metrics.per_stage(accepted, turns, {}, stamps, None, context_window=100)
        self.assertEqual([r["context"]["calls"] for r in rows], [1, 1])
        self.assertEqual([r["context"]["peak"] for r in rows], [30, 40])
        self.assertEqual([r["turns"] for r in rows], [3, 1])


class StageWindowsTest(unittest.TestCase):
    """The windows per_stage already derived are one implementation the rollout reader shares."""

    def test_windows_line_up_with_the_stage_rows_and_none_marks_unavailable_timing(self):
        accepted = [{"stage": "seeded", "outcome": "done", "t": 90.0},     # before the host's first event
                    {"stage": "a", "outcome": "done", "t": 105.0},
                    {"stage": "no-stamp", "outcome": "done", "t": None},
                    {"stage": "after-gap", "outcome": "done", "t": 112.0},  # its lower boundary is unknown
                    {"stage": "b", "outcome": "revise", "t": 118.0}]
        stamps = {n: 100.0 + n for n in range(21)}
        windows = metrics.stage_windows(accepted, stamps, "open")
        rows = metrics.per_stage(accepted, [{"t": 101.5, "input": 1}, {"t": 114.0, "input": 1}], {}, stamps, "open")
        self.assertEqual(len(windows), len(rows))
        self.assertEqual([w is None for w in windows], [r.get("timing") == "unavailable" for r in rows])
        self.assertEqual(windows, [None, (99.0, 105.0, 100.0), None, None, (112.0, 118.0, 112.0),
                                   (118.0, 120.0, 118.0)])
        for window, row in zip(windows, rows):
            if window:
                self.assertEqual(row["seconds"], round(window[1] - window[2], 1))
        self.assertEqual(metrics.stage_windows(accepted, {}, "open"), [None] * 6)
        self.assertEqual(metrics.stage_windows([], stamps, None), [])


class CodexRolloutMetricsTest(unittest.TestCase):
    """metrics.collect on a Codex run reads calls, window, peak and compactions from its rollouts, and says
    why when they are absent; the other counters Codex cannot show stay unmeasured."""

    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def rollouts(self) -> list[list[str]]:
        root = thread_calls("root", "root", 10000, [(101, "r1", 1000, False), (104.5, "r2", 3000, False),
                                                    (108, "rq", 3500, True), (110, "r3", 2000, False),
                                                    (120, "r4", 500, False)])  # after the last acceptance
        sub = thread_calls("sub", "root", 20000, [(102, "s1", 9000, False)])
        return [root, sub]

    def test_a_codex_run_with_rollouts_has_calls_window_peak_and_compactions(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED, rollout_files=self.rollouts())
        self.assertEqual((m["model_calls"], m["window_tokens"], m["compactions"]), (4, 10000, 1))
        self.assertEqual(m["tokens"]["input_peak"], 3000)
        for name in ("model_calls", "window_tokens", "compactions"):
            self.assertNotIn(name, m["unmeasured"], name)
        # What the Codex stream still cannot show stays unmeasured: the four stage and detector counters, and the processed
        # tokens, since this stream names no host and Codex counts its cache reads inside its input (build step 8).
        self.assertEqual(set(m["unmeasured"]), {"stage_turns", "truncated_outputs", "cancelled_tool_calls",
                                                "knowledge_reads", "tokens_processed"})
        self.assertEqual([r["context"] for r in m["stages"]], [
            {"calls": 2, "peak": 3000, "peakPct": 30.0, "compactions": 0},
            {"calls": 1, "peak": 2000, "peakPct": 20.0, "compactions": 1}])
        self.assertTrue(all(r["turns"] is None for r in m["stages"]), "stage turns stay unmeasured")
        self.assertIn("compactions 1,", metrics.summary_lines(m)[0])

    def test_a_codex_run_without_rollouts_names_them_as_the_reason(self):
        m = collect_stream(codex_stream(12), self.ACCEPTED)
        self.assertEqual((m["model_calls"], m["window_tokens"], m["compactions"]), (None, None, None))
        self.assertEqual(m["tokens"]["input_peak"], None)
        for name in ("model_calls", "window_tokens", "compactions"):
            self.assertIn(name, m["unmeasured"], name)
        self.assertIn(rollouts.NO_ROLLOUTS, m["unmeasured"]["model_calls"])
        self.assertIn(rollouts.NO_ROLLOUTS, m["unmeasured"]["window_tokens"])
        self.assertTrue(all("context" not in r for r in m["stages"]))
        self.assertEqual(len(m["unmeasured"]), 8)  # the five Codex had, the two new figures, and the processed tokens

    def test_rollouts_are_not_read_when_the_host_reported_per_call_usage(self):
        # A Grok or Claude stream measures its own calls; a stray rollout beside it does not change them.
        stream = [{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}] * 2
        m = collect_stream(stream, self.ACCEPTED, rollout_files=self.rollouts())
        self.assertEqual((m["model_calls"], m["compactions"]), (2, 0), "Grok's own events: no compaction event")
        # The stage rows carry the stream's own calls (batch 1011: a Grok usage event is a model call, and a stage with no
        # event has no context); none of the rollouts' figures (calls 2 peak 3000 / calls 1 peak 2000) reach them.
        self.assertEqual(m["stages"][0]["context"], {"calls": 2, "peak": 1, "peakPct": None})
        self.assertNotIn("context", m["stages"][1])

    def test_rollouts_that_hold_no_call_are_unmeasured_with_the_reason(self):
        m = collect_stream(codex_stream(3), self.ACCEPTED, rollout_files=[[rollout_line("session_meta", 1, {})]])
        self.assertIsNone(m["model_calls"])
        self.assertIn(rollouts.NO_CALLS, m["unmeasured"]["model_calls"])


class ModelCallsAndWindowTest(unittest.TestCase):
    """A model call is a Claude message, not an event: `turns` keeps counting events (baselines.jsonl stores that
    definition and run.py compares it across runs), and a window the host did not report is unknown, not 0."""

    @staticmethod
    def message(message_id, text="x"):
        message = {"usage": {"input_tokens": 10}, "content": [{"type": "text", "text": text}]}
        if message_id is not None:
            message["id"] = message_id
        return {"type": "assistant", "message": message}

    @staticmethod
    def result(*windows, num_turns=1):
        return {"type": "result", "subtype": "success", "num_turns": num_turns, "total_cost_usd": 1.0,
                "modelUsage": {f"model-{n}": {"contextWindow": w, "inputTokens": 5}
                               for n, w in enumerate(windows)}}

    def test_three_events_of_one_message_are_one_call_and_three_turns(self):
        m = collect_stream([self.message("m1")] * 3, [])
        self.assertEqual((m["model_calls"], m["turns"]), (1, 3))
        self.assertNotIn("model_calls", m["unmeasured"])

    def test_events_without_an_id_count_one_each_and_a_repeated_id_counts_once(self):
        stream = [self.message("m1"), self.message("m1"), self.message("m2"), self.message(None),
                  self.message(None), self.message(""), self.message("m1")]
        m = collect_stream(stream, [])
        self.assertEqual((m["model_calls"], m["turns"]), (5, 7))  # m1, m2, two with no id, one empty id

    def test_the_window_comes_from_the_result_event(self):
        m = collect_stream([self.message("m1"), self.result(1000000)], [])
        self.assertEqual(m["window_tokens"], 1000000)
        self.assertNotIn("window_tokens", m["unmeasured"])
        # Two sessions of one run that agree on it are one window.
        m = collect_stream([self.message("m1"), self.result(1000000), self.message("m2"), self.result(1000000)], [])
        self.assertEqual(m["window_tokens"], 1000000)

    def test_a_window_nobody_reported_or_that_disagrees_is_null_with_its_reason(self):
        for label, stream in (("no result event", [self.message("m1")]),
                              ("a result without modelUsage", [self.message("m1"),
                                                               {"type": "result", "subtype": "success"}]),
                              ("a bool or zero window", [self.message("m1"), self.result(True, 0)]),
                              ("two models with different windows", [self.message("m1"), self.result(200000, 1000000)])):
            with self.subTest(label):
                m = collect_stream(stream, [])
                self.assertIsNone(m["window_tokens"])
                self.assertIn("context window", m["unmeasured"]["window_tokens"])
                self.assertEqual(m["model_calls"], 1, "the window being unknown does not hide the calls")

    def test_a_grok_stream_counts_its_usage_events_and_has_no_window(self):
        m = collect_stream([{"type": "usage", "usage": {"input_tokens": 1, "output_tokens": 1}}] * 4, [])
        self.assertEqual((m["model_calls"], m["turns"]), (4, 4))
        self.assertIsNone(m["window_tokens"])
        # Grok marks no session start, and this stream's end event carries no usage
        self.assertEqual(set(m["unmeasured"]), {"window_tokens", "unreported_sessions", "tokens_processed", "tokens_output"})

    def test_a_host_with_no_per_call_usage_has_no_call_count_not_zero_calls(self):
        m = collect_stream(codex_stream(3), [])
        self.assertIsNone(m["model_calls"])
        self.assertIsNone(m["window_tokens"])
        self.assertIn("per-call usage", m["unmeasured"]["model_calls"])
        self.assertEqual(m["turns"], 3, "the session's own total is still reported")


class HostSignalCountersTest(unittest.TestCase):
    """Counters read only from Grok's event shapes are unmeasured on every other host (review 2: compactions,
    truncated_outputs, cancelled_tool_calls, knowledge_reads), never a 0 or a look-alike that reads as a measurement."""

    GROK_ONLY = ("compactions", "truncated_outputs", "cancelled_tool_calls", "knowledge_reads")
    ACCEPTED = [("A1", "intake", "done", 105.0), ("A2", "spec", "done", 113.0)]

    def codex(self) -> dict:
        items = [codex_command(0), codex_command(1, "node --test", "ℹ tests 3\nℹ fail 1\nℹ cancelled 0\n", 1),
                 {"id": "item_2", "type": "file_change", "status": "completed",
                  "changes": [{"path": "/w/docs/shiploop/spec.md", "kind": "update"}]}]
        return collect_stream(codex_session(items), self.ACCEPTED)

    def test_a_codex_failing_test_run_is_not_a_host_refusal_and_a_write_is_not_a_read(self):
        m = self.codex()
        for name in self.GROK_ONLY:
            self.assertIn(name, m["unmeasured"], name)
        self.assertEqual(m["cancelled_tool_calls"], [], "'cancelled 0' in a node --test summary is not a refusal")
        self.assertEqual(m["knowledge_reads"], [], "Codex's file_change is a write, listed as a read")
        self.assertIsNone(m["compactions"])
        self.assertIsNone(m["truncated_outputs"])
        self.assertIsNone(metrics.count(m, "cancelled_tool_calls"))
        self.assertNotIn("model_glue", m["unmeasured"], "Codex's tool calls are still read")
        first = metrics.summary_lines(m)[0]
        for text in ("compactions not measured", "truncated outputs not measured", "cancelled tool calls not measured"):
            self.assertIn(text, first)

    def test_a_claude_run_cannot_show_them_either_with_or_without_tool_calls(self):
        compact = {"type": "system", "subtype": "compact_boundary", "compact_metadata": {"trigger": "auto"}}
        read = {"type": "assistant", "message": {"usage": {"input_tokens": 5}, "content": [
            {"type": "tool_use", "id": "r1", "name": "Read", "input": {"file_path": "/w/docs/shiploop/spec.md"}}]}}
        text_only = {"type": "assistant", "message": {"usage": {"input_tokens": 5},
                                                      "content": [{"type": "text", "text": "hello"}]}}
        for label, stream in (("tool calls", [compact, read, *claude_stream(["ls"])]),
                              ("text only", [text_only, {"type": "result", "subtype": "success", "num_turns": 1}])):
            with self.subTest(label):
                m = collect_stream(stream, self.ACCEPTED)
                for name in self.GROK_ONLY:
                    self.assertIn(name, m["unmeasured"], name)
                self.assertIsNone(m["compactions"])
                self.assertIsNone(m["truncated_outputs"])
                self.assertIn("compactions not measured", metrics.summary_lines(m)[0])

    def test_a_grok_stream_still_counts_each_one(self):
        stream = [
            {"type": "usage", "usage": {"input_tokens": 1000, "output_tokens": 10}},
            {"type": "tool_call", "toolCallId": "a", "toolName": "read_file",
             "rawInput": {"target_file": "/w/docs/shiploop/spec.md"}},
            {"type": "tool_call_update", "toolCallId": "a", "rawOutput": {"exit_code": 0, "truncated": True}},
            {"type": "tool_call", "toolCallId": "c", "rawInput": {"command": "git init -b main"}},
            {"type": "tool_call_update", "toolCallId": "c", "status": "failed", "rawOutput": None, "content": [
                {"type": "content", "content": {"type": "text",
                                                "text": "User cancelled the execution for tool `run_terminal_command`"}}]},
            {"type": "auto_compact_completed"},
            {"type": "end", "stopReason": "end_turn", "num_turns": 1, "total_cost_usd": 1.0}]
        m = collect_stream(stream, self.ACCEPTED)
        self.assertEqual(set(m["unmeasured"]), {"window_tokens", "unreported_sessions", "tokens_processed", "tokens_output"},
                         "every detector reads a Grok stream; its events mark no session start; its end has no usage")
        self.assertEqual((m["compactions"], m["truncated_outputs"]), (1, 1))
        self.assertEqual(m["cancelled_tool_calls"], ["git init -b main"])
        self.assertEqual(m["knowledge_reads"], ["docs/shiploop/spec.md"])
        first = metrics.summary_lines(m)[0]
        self.assertIn("compactions 1, truncated outputs 1, cancelled tool calls 1", first)


class HostSignalCountersThroughMainTest(PrintedCase):
    """result.json, the baseline row and the printed line carry null, not 0, for what the host cannot show."""

    def test_claude_and_codex_runs_commit_null_for_the_grok_only_counters(self):
        for host in ("claude", "codex"):
            with self.subTest(host):
                code, result, printed = self.invoke_printed(host, "done")
                self.assertEqual(code, 0, result)
                row = self.last_row()
                for name in HostSignalCountersTest.GROK_ONLY:
                    self.assertIn(name, result["metrics"]["unmeasured"], name)
                for name in ("compactions", "truncated_outputs", "cancelled_tool_calls"):
                    self.assertIsNone(result["metrics"][name], name)
                    self.assertIsNone(row[name], name)
                self.assertIn("compactions not measured", printed)
                self.assertIn("truncated outputs not measured", printed)


class ModelCallsThroughMainTest(PrintedCase):
    """result.json carries the two figures beside the other whole-run scalars; the baseline row does not
    (they are not comparison keys: the row's turns keep the events-based definition)."""

    def test_result_json_carries_calls_and_window_and_the_baseline_row_does_not(self):
        code, result, _ = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["metrics"]["model_calls"], 1)  # the fake's one assistant event
        self.assertIsNone(result["metrics"]["window_tokens"])  # its result event reports no modelUsage
        self.assertIn("window_tokens", result["metrics"]["unmeasured"])
        row = self.last_row()
        for name in ("model_calls", "window_tokens"):
            self.assertNotIn(name, row)
        self.assertIn("window_tokens", row["unmeasured"])
        code, result, _ = self.invoke_printed("codex", "done")
        self.assertIsNone(result["metrics"]["model_calls"])
        self.assertIn("model_calls", result["metrics"]["unmeasured"])
        self.assertIn("rollout", result["metrics"]["unmeasured"]["model_calls"])
        self.assertIn("compactions", result["metrics"]["unmeasured"])

    def test_a_codex_run_whose_home_holds_rollouts_reports_them_in_every_record(self):
        os.environ["FAKE_ROLLOUT"] = "1"
        self.addCleanup(os.environ.pop, "FAKE_ROLLOUT", None)
        code, result, _ = self.invoke_printed("codex", "done")
        self.assertEqual(code, 0, result)
        m = result["metrics"]
        self.assertEqual((m["model_calls"], m["compactions"]), (2, 0))  # 0 is a measurement: the rollouts exist
        self.assertIsNone(m["window_tokens"])  # no token_count record reported one
        self.assertIn("model_context_window", m["unmeasured"]["window_tokens"])
        for name in ("model_calls", "compactions"):
            self.assertNotIn(name, m["unmeasured"], name)
        self.assertEqual(json.loads((Path(result["output"]) / "metrics.json").read_text())["tokens"]["input_peak"],
                         2000)
        row = self.last_row()
        self.assertEqual(row["compactions"], 0)
        self.assertNotIn("compactions", row["unmeasured"])


class UnknownTurnsTest(unittest.TestCase):
    """A session that never reported its turns leaves the whole-run turns unknown, as it does the cost (review 2)."""

    ACCEPTED = [("A1", "intake", "done", 105.0)]

    def killed(self) -> list[dict]:
        return codex_session([codex_command(n) for n in range(30)], end=False, thread="t1")

    def test_a_codex_session_killed_before_its_end_event_has_no_turn_count(self):
        m = collect_stream(self.killed(), self.ACCEPTED, status="active", stage="spec")
        self.assertIsNone(m["turns"], "30 tool calls and no end event: the host reported no turn count")
        self.assertEqual((m["sessions"], m["unreported_sessions"]), ([], 1))
        self.assertIsNone(m["cost_usd"])
        self.assertIn("turns not reported", metrics.summary_lines(m)[0])
        self.assertEqual(metrics.turns_text(m), "not reported")

    def test_a_killed_session_beside_an_ended_one_makes_the_turns_a_lower_bound(self):
        stream = self.killed() + codex_session([codex_command(n) for n in range(3)], thread="t2")
        m = collect_stream(stream, self.ACCEPTED)
        self.assertEqual(m["turns"], 3)
        self.assertEqual(m["unreported_sessions"], 1)
        self.assertIn("turns 3 (lower bound)", metrics.summary_lines(m)[0])

    def test_an_ended_session_is_a_plain_number_and_a_reported_zero_is_a_measurement(self):
        m = collect_stream(codex_session([codex_command(n) for n in range(4)]), self.ACCEPTED)
        self.assertEqual(m["turns"], 4)
        self.assertNotIn("lower bound", metrics.summary_lines(m)[0].split("cost")[0])
        zero = collect_stream([{"type": "end", "stopReason": "end_turn", "num_turns": 0}], [])
        self.assertEqual(zero["turns"], 0)
        self.assertEqual(metrics.turns_text(zero), "0")

    def test_progress_says_the_turns_are_unknown_and_survives_the_null_counters(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            stream = self.killed()
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
            text = progress.report(out)
            again = progress.report(out)  # the memo it wrote must read back
        self.assertIn("turns not reported", text)
        self.assertNotIn("turns 0", text)
        self.assertIn("not measured on this host", text)
        self.assertNotIn("not measured on this host", again, "said once per run, not on every poll")


class CliSummaryRecordTest(PrintedCase):
    """result.json's `cli` agrees with `termination` and the metrics: the same stop reason, and no turn count that
    nobody reported turned into 0 (review 2: summarize_events)."""

    def test_a_claude_api_error_is_an_error_in_the_cli_record_too(self):
        code, result, printed = self.invoke_printed("claude", "api-error")
        stops = result["termination"]["session_stops"]
        self.assertTrue(stops[0].startswith("error: api_error"), stops)
        self.assertEqual(result["cli"]["stop"], stops[0])
        self.assertEqual([s["stop"] for s in result["cli"]["sessions"]], stops)

    def test_a_normal_stop_and_a_failed_codex_turn(self):
        code, result, printed = self.invoke_printed("claude", "done")
        self.assertEqual((result["cli"]["stop"], result["cli"]["sessions"][0]["stop"]), ("success", "success"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(json.dumps({"type": "end", "stopReason": "error", "num_turns": 2,
                                        "error": "You've hit your usage limit.\nTry later"}) + "\n")
            seen = run.summarize_events(path)
        self.assertEqual(seen["stop"], "error: You've hit your usage limit. Try later")
        self.assertEqual(seen["sessions"][0]["stop"], seen["stop"])

    def test_the_cli_summary_does_not_turn_a_missing_turn_count_into_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(json.dumps({"type": "end", "stopReason": "end_turn", "total_cost_usd": None}) + "\n")
            seen = run.summarize_events(path)
        self.assertIsNone(seen["num_turns"])
        self.assertIsNone(seen["cost_usd"])


class ContextTokensTest(unittest.TestCase):
    """A call's context is its input, its cache reads and its cache writes, where the host reports them."""

    CLAUDE_USAGE = {"input_tokens": 3, "cache_creation_input_tokens": 90000, "cache_read_input_tokens": 10000,
                    "output_tokens": 50}

    def test_a_cache_write_is_context(self):
        self.assertEqual(metrics.context_tokens(self.CLAUDE_USAGE), 100003)
        self.assertEqual(metrics.context_tokens({"input_tokens": 3, "cache_read_input_tokens": 10000}), 10003)
        self.assertEqual(metrics.context_tokens({"cache_creation_input_tokens": 7}), 7)

    def test_a_call_with_no_figure_has_no_context(self):
        for usage in (None, {}, {"output_tokens": 5}, {"input_tokens": None}, {"input_tokens": True}):
            self.assertIsNone(metrics.context_tokens(usage), usage)

    def test_the_run_peak_counts_the_cache_write_and_a_stream_without_usage_has_none(self):
        def message(n: int, usage: dict) -> dict:
            return {"type": "assistant", "message": {"id": f"m{n}", "usage": usage,
                                                     "content": [{"type": "text", "text": "x"}]}}
        quiet = {"input_tokens": 3, "cache_read_input_tokens": 50000, "cache_creation_input_tokens": 0}
        stream = [message(0, quiet), message(1, self.CLAUDE_USAGE), message(2, quiet)]
        self.assertEqual(collect_stream(stream, [])["tokens"]["input_peak"], 100003)
        self.assertEqual(collect_stream([{"type": "assistant", "message": {"content": []}}], [])["tokens"]["input_peak"],
                         None)
        self.assertEqual(collect_stream(codex_stream(3), [])["tokens"]["input_peak"], None)


class GradeOnlyTest(PrintedCase):
    """--resume-run <dir> --grade-only: records from what is on disk, no host, for a run whose harness was killed."""

    def killed_harness_run(self) -> Path:
        code, result, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(result["output"])
        for name in ("result.json", "metrics.json"):  # a task kill gives the harness no chance to write them
            (out / name).unlink()
        shutil.rmtree(out / "review-export", ignore_errors=True)
        self.log.unlink()
        return out

    def grade_only(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "review_export", return_value="review export: fake") as exporter:
            code = run.main([*extra, "--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        self.exporter = exporter
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_an_active_run_whose_harness_was_killed_is_graded_without_a_host(self):
        out = self.killed_harness_run()
        recorded = json.loads((out / "invocation.json").read_text())
        rows = self.baselines.read_text() if self.baselines.exists() else ""
        code, result, printed = self.grade_only(out)
        self.assertEqual(code, 1, "an unfinished run is not a pass")
        self.assertFalse(self.log.exists(), "no host process was started")
        self.assertTrue((out / "metrics.json").is_file())
        self.exporter.assert_called_once()
        self.assertTrue(result["process"]["regraded"])
        self.assertEqual(result["shiploop"]["status"], "active")
        self.assertEqual((result["host"], result["model"], result["effort"]),
                         (recorded["host"], recorded["model"], recorded["effort"]))
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"], t["engine_unaccepted_stage"]),
                         (run.NOT_OBSERVED, "active", "test-refine"))
        self.assertEqual(self.baselines.read_text() if self.baselines.exists() else "", rows,
                         "a grade-only writes no baseline row")
        self.assertIn("no host ran (regraded); engine active", printed)

    def test_a_regrade_names_a_refusal_whose_exit_the_host_did_not_show(self):
        # A Claude refusal behind `| head` has no exit; the printed line says so, and does not print "exit None".
        out = self.killed_harness_run()
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in recorded_calls("refusal-behind-head")))
        code, result, printed = self.grade_only(out)
        line = next(ln for ln in printed.splitlines() if ln.startswith("  failed    shiploop"))
        self.assertTrue(line.startswith("  failed    shiploop complete exit not shown: ShipLoop navigator: evidence_refs cite"), line)
        self.assertNotIn("exit None", printed)

    def test_a_regrade_prints_no_resume_command_because_its_flags_are_not_the_runs(self):
        # The grading invocation's --timeout is the default (10800 s, above any task limit); presenting it as the exact
        # command that continues the run would send a resume to be killed with no records.
        out = self.killed_harness_run()
        code, result, printed = self.grade_only(out)
        self.assertEqual(result["shiploop"]["status"], "active")
        self.assertNotIn("--resume-run", printed)
        self.assertNotRegex(printed, r"--timeout \d+")
        line = next(ln for ln in printed.splitlines() if ln.startswith("  resume"))
        self.assertIn("printed when the run started", line)
        self.assertIn("--timeout below the launcher's limit", line)

    def test_a_paused_run_is_graded_under_the_flag_and_refused_without_it(self):
        out = self.killed_harness_run()
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md", {"status": "paused", "stage": "spec",
                                                                        "status_reason": "paused for a person"})
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, "needs an active, blocked or finished"):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin)])
        code, result, _ = self.grade_only(out)
        self.assertEqual(result["shiploop"]["status"], "paused")
        self.assertFalse(self.log.exists())

    def test_the_flag_needs_a_run_to_grade_and_a_run_with_no_state_is_still_refused(self):
        with self.assertRaisesRegex(SystemExit, "--grade-only needs --resume-run"):
            run.main(["--grade-only", "--host", "grok", "--output", str(self.tmp / "never")])
        self.assertFalse((self.tmp / "never").exists())
        code, result, _ = self.invoke_printed("grok", "nothing", "--max-resumes", "0")
        out = Path(result["output"])
        with self.assertRaisesRegex(SystemExit, "needs an active, blocked or finished"):
            run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin)])


class UnfinishedRunBaselineTest(PrintedCase):
    """No baseline row for a run whose engine is still active when the harness ends."""

    def setUp(self):
        super().setUp()
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)  # a deadline is noticed on the next poll
        patched.start()
        self.addCleanup(patched.stop)

    def test_a_run_left_active_by_a_spent_resume_budget_writes_no_row(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "1")
        self.assertEqual(result["termination"]["engine_status"], "active")
        self.assertFalse(self.baselines.exists())
        self.assertIn("baseline  nothing compared: the run is not finished (its engine is still active)", printed)
        self.assertEqual(printed.count("--resume-run"), 2, "the start line and the end line carry the command")

    def test_a_deadline_ends_with_the_records_leaves_the_run_resumable_and_writes_no_row(self):
        # The README's recipe for a task with a limit: --timeout below it, so the harness finalizes.
        code, result, printed = self.invoke_printed("grok", "hang-active", "--timeout", "2")
        out = Path(result["output"])
        self.assertEqual(code, 1)
        self.assertTrue((out / "metrics.json").is_file())
        self.assertRegex(printed, r"review export")
        t = result["termination"]
        self.assertEqual((t["process_status"], t["resume_stop"], t["engine_status"]),
                         ("timeout", "run deadline spent", "active"))
        self.assertFalse(self.baselines.exists(), "the first segment of a long run is not a baseline")

    def test_a_finished_run_still_writes_its_row(self):
        code, result, _ = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0)
        self.assertEqual(len(self.baselines.read_text().splitlines()), 1)

    def test_a_host_killed_at_the_deadline_before_any_engine_state_writes_no_row(self):
        # The audit's reproduction: the existing `hang` fake, --timeout 3, engine status unknown. It appended a row with
        # process status timeout, which scan_baseline then offered as the last comparable row.
        code, result, printed = self.invoke_printed("grok", "hang", "--timeout", "3")
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"]), ("timeout", "unknown"))
        self.assertFalse(self.baselines.exists(), "a host the deadline killed is not a finished run")
        self.assertIn("baseline  nothing compared: the run is not finished (the harness ended the host: timeout; "
                      "engine unknown), so it is not a baseline", printed)
        self.assertEqual(printed.count("--resume-run"), 1,
                         "a run with no engine state is refused by --resume-run, so only the start line carries a command")

    def test_a_later_run_is_not_compared_with_the_killed_one(self):
        self.invoke_printed("grok", "hang", "--timeout", "3")
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        self.assertIn("baseline  nothing compared: no earlier row for hello", printed)

    def test_a_host_that_ends_by_itself_with_no_engine_state_still_writes_its_row(self):
        # Its own exit is the ending the row records, unlike a deadline or a stop the harness imposed.
        code, result, _ = self.invoke_printed("grok", "nothing")
        self.assertEqual((result["termination"]["engine_status"], result["termination"]["process_status"]),
                         ("unknown", "exited"))
        self.assertEqual(len(self.baselines.read_text().splitlines()), 1)


class PlanningBlockCase(unittest.TestCase):
    """metrics.collect's `planning` block, built from files a run left behind."""

    def planning(self, rows=PLANNING_ROWS, *, stream=None, started=1030.0, improve=None, binds=None, **kw) -> dict:
        inner = {} if improve is None else {"improve_results": improve}
        m = collect_stream(grok_usage(3) if stream is None else stream, rows, status="active", first_event=1000.0,
                           started=started, inner=inner, binds=binds, **kw)
        return m["planning"]


class PlanningClockTest(PlanningBlockCase):
    def test_the_window_runs_from_the_engine_start_to_the_first_done_test_spec(self):
        plan = self.planning(improve={})
        self.assertEqual(plan["window"], {"closed": True, "through": "test-spec", "seconds": 370.0,
                                          "host_seconds": 400.0, "before_engine_seconds": 30.0})
        self.assertEqual([(r["stage"], r["outcome"], r["seconds"]) for r in plan["stages"]],
                         [("intake", "done", 130.0), ("spec", "done", 90.0), ("test-spec", "done", 150.0)])
        self.assertEqual(plan["unmeasured"].get("window"), None)

    def test_a_revised_test_spec_does_not_close_the_window(self):
        rows = [("a-intake", "intake", "done", 1160), ("a-ts1", "test-spec", "revise", 1300),
                ("a-ts2", "test-spec", "done", 1500)]
        plan = self.planning(rows, improve={})
        self.assertEqual((plan["window"]["closed"], plan["window"]["seconds"]), (True, 470.0))
        self.assertEqual([r["outcome"] for r in plan["stages"]], ["done", "revise", "done"])

    def test_a_run_that_never_reached_test_spec_is_open_and_says_through_which_stage(self):
        plan = self.planning(PLANNING_ROWS[:2], improve={})
        self.assertEqual(plan["window"], {"closed": False, "through": "spec", "seconds": 220.0,
                                          "host_seconds": 250.0, "before_engine_seconds": 30.0})
        self.assertGreater(plan["window"]["seconds"], 0, "an open window is never reported as 0")

    def test_a_run_with_no_accepted_stage_has_no_window_and_says_why(self):
        plan = self.planning([], improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("no stage has been accepted", plan["unmeasured"]["window"])

    def test_an_unstamped_stage_inside_the_window_leaves_its_own_seconds_unknown_not_the_window_shorter(self):
        rows = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", None), ("a-ts", "test-spec", "done", 1400)]
        plan = self.planning(rows, improve={})
        self.assertEqual(plan["window"]["seconds"], 370.0, "the window needs only the start and the end stamp")
        self.assertEqual([r["seconds"] for r in plan["stages"]], [130.0, None, None])

    def test_a_seeded_run_has_no_planning_window(self):
        # The harness recorded the early stages itself, before the host's first event (1000).
        rows = [("a-intake", "intake", "done", 900), ("a-ts", "test-spec", "done", 1400)]
        plan = self.planning(rows, improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("before the host", plan["unmeasured"]["window"])

    def test_a_recreated_timeline_reads_as_unmeasured_never_as_a_zero_window(self):
        # The engine gives every historical action one stamp when it recreates a lost timeline.json.
        rows = [("a-intake", "intake", "done", 1160), ("a-spec", "spec", "done", 1160), ("a-ts", "test-spec", "done", 1160)]
        plan = self.planning(rows, started=1160.0, improve={})
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("one stamp", plan["unmeasured"]["window"])

    def test_a_recreated_timeline_with_one_accepted_row_is_unmeasured_not_a_measured_zero(self):
        # One accepted row whose stamp equals the start: not a duration, and an open window is never 0.
        plan = self.planning([("a-intake", "intake", "done", 1160)], started=1160.0, improve={})
        self.assertFalse(plan["window"]["closed"])
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIsNone(plan["window"]["host_seconds"])
        self.assertIn("one stamp", plan["unmeasured"]["window"])
        closed = self.planning([("a-ts", "test-spec", "done", 1160)], started=1160.0, improve={})
        self.assertIsNone(closed["window"]["seconds"])
        self.assertIn("one stamp", closed["unmeasured"]["window"])

    def test_a_timeline_with_no_start_is_unmeasured(self):
        plan = self.planning(improve={}, started=False)
        self.assertIsNone(plan["window"]["seconds"])
        self.assertIn("no start time", plan["unmeasured"]["window"])

    def test_the_host_clock_is_unknown_without_the_runner_timeline_and_the_engine_clock_stands(self):
        plan = self.planning(improve={}, timed=False)
        self.assertEqual((plan["window"]["seconds"], plan["window"]["host_seconds"], plan["window"]["before_engine_seconds"]),
                         (370.0, None, None))
        self.assertIn("runner", plan["unmeasured"]["host_seconds"])


class PlanningImproveSplitTest(PlanningBlockCase):
    def test_improve_seconds_run_from_the_bind_file_to_the_accept_for_an_action_with_an_improve_result(self):
        plan = self.planning(improve={"a-spec": {"summary": "reviewed"}}, binds={"a-spec": 1190.4})
        self.assertEqual([(r["stage"], r["improve_seconds"]) for r in plan["stages"]],
                         [("intake", 0.0), ("spec", 59.6), ("test-spec", 0.0)])
        self.assertEqual(plan["improve"], {"children": 1, "seconds": 59.6})

    def test_producer_seconds_plus_improve_seconds_equal_the_window(self):
        plan = self.planning(improve={"a-spec": {}, "a-ts": {}}, binds={"a-spec": 1190.0, "a-ts": 1300.0})
        self.assertEqual(plan["improve"], {"children": 2, "seconds": 160.0})
        self.assertEqual(plan["producer_seconds"] + plan["improve"]["seconds"], plan["window"]["seconds"])

    def test_a_none_run_has_a_measured_zero_improve_share_in_the_window(self):
        plan = self.planning(improve={})
        self.assertEqual(plan["improve"], {"children": 0, "seconds": 0.0})
        self.assertEqual(plan["producer_seconds"], plan["window"]["seconds"])

    def test_an_improve_result_with_no_bind_file_makes_improve_unknown_not_zero(self):
        plan = self.planning(improve={"a-spec": {}})
        self.assertEqual(plan["improve"], {"children": 1, "seconds": None})
        self.assertIsNone(plan["producer_seconds"])
        self.assertEqual(plan["window"]["seconds"], 370.0)
        self.assertIn("bind", plan["unmeasured"]["improve"])
        self.assertIsNone(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"])

    def test_a_state_with_no_improve_results_makes_improve_unknown(self):
        plan = self.planning()  # no improve_results key in state.md
        self.assertIsNone(plan["improve"])
        self.assertIn("improve_results", plan["unmeasured"]["improve"])

    def test_an_accept_stamp_within_a_second_below_the_bind_time_is_whole_second_truncation_not_a_negative(self):
        # Accept stamps are truncated to whole seconds; the bind file's mtime is fractional. Seen on a real Sonnet run: -0.33 s.
        plan = self.planning(improve={"a-spec": {}}, binds={"a-spec": 1250.9})
        self.assertEqual(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"], 0.0)
        self.assertEqual(plan["improve"]["seconds"], 0.0)

    def test_a_stamp_more_than_a_second_below_the_bind_time_is_unmeasured_and_never_reaches_producer_seconds(self):
        plan = self.planning(improve={"a-spec": {}}, binds={"a-spec": 1253.0})
        self.assertIsNone(next(r for r in plan["stages"] if r["stage"] == "spec")["improve_seconds"])
        self.assertIsNone(plan["improve"]["seconds"])
        self.assertIsNone(plan["producer_seconds"])
        self.assertIn("before", plan["unmeasured"]["improve"])


class PlanningTokensTest(PlanningBlockCase):
    ROWS = [("a-intake", "intake", "done", 1002), ("a-ts", "test-spec", "done", 1005), ("a-impl", "implement", "done", 1008)]

    def test_a_grok_window_sums_the_usage_events_inside_the_host_window_and_names_the_clock(self):
        # Events are stamped 1000 to 1009; the window ends at 1005, so events 0 to 5 are inside it.
        plan = self.planning(self.ROWS, stream=grok_usage(10), started=1001.0, improve={})
        self.assertEqual(plan["tokens"], {"output": 600, "reasoning": 240, "clock": "host", "source": "usage events"})

    def test_a_grok_window_that_covers_the_run_equals_the_sum_of_every_usage_event(self):
        plan = self.planning([("a-ts", "test-spec", "done", 1500)], stream=grok_usage(10), started=1001.0, improve={})
        self.assertEqual((plan["tokens"]["output"], plan["tokens"]["reasoning"]), (1000, 400))

    def test_a_grok_run_with_no_runner_timeline_has_unmeasured_tokens(self):
        plan = self.planning(self.ROWS, stream=grok_usage(10), started=1001.0, improve={}, timed=False)
        self.assertIn("runner", plan["tokens"]["unmeasured"])
        self.assertNotIn("output", plan["tokens"])

    def test_an_open_window_has_no_token_figure(self):
        plan = self.planning(self.ROWS[:1], stream=grok_usage(10), started=1001.0, improve={})
        self.assertIn("open", plan["tokens"]["unmeasured"])

    def test_a_claude_run_has_no_window_tokens_and_says_why(self):
        plan = self.planning(self.ROWS, stream=claude_stream(["echo hi"]), started=1001.0, improve={})
        self.assertIn("snapshot", plan["tokens"]["unmeasured"])

    def rollouts(self) -> list[list[str]]:
        root = [usage_line(1001, "root", "root", "r1", 1000, output=100, reasoning=40),
                usage_line(1010, "root", "root", "r2", 2000, output=200, reasoning=80),
                usage_line(1011, "root", "root", "r2", 2000, output=200, reasoning=80),  # the same response repeated
                usage_line(1020, "root", "root", "rq1", 9000, output=50, reasoning=0),   # a compaction request
                compacted_line(1020.01, "rq1"),
                usage_line(1040, "root", "root", "r3", 3000, output=300, reasoning=100),
                usage_line(1060, "root", "root", "r4", 3500, output=400, reasoning=150)]  # after the window
        sub = [usage_line(1030, "sub", "root", "s1", 5000, output=70, reasoning=30)]
        return [root, sub]

    def test_a_codex_window_counts_each_response_once_includes_compaction_requests_and_reports_sub_agents_apart(self):
        rows = [("a-intake", "intake", "done", 1002), ("a-ts", "test-spec", "done", 1050), ("a-impl", "implement", "done", 1100)]
        plan = self.planning(rows, stream=codex_stream(3), started=1001.0, improve={}, rollout_files=self.rollouts())
        # 100 + 200 + 50 (the compaction request) + 300; r2 once; r4 is after the window; the sub-agent's 70 is beside.
        self.assertEqual(plan["tokens"], {"output": 650, "reasoning": 220, "subagent_output": 70, "clock": "host",
                                          "source": "rollout token_usage_records"})

    def test_a_codex_run_with_no_rollouts_has_unmeasured_tokens(self):
        rows = [("a-ts", "test-spec", "done", 1050)]
        plan = self.planning(rows, stream=codex_stream(3), started=1001.0, improve={})
        self.assertIn("rollout", plan["tokens"]["unmeasured"])


class PlanningPlumbingTest(HarnessCase):
    def test_collect_leaves_the_top_level_unmeasured_map_alone(self):
        m = collect_stream(grok_usage(3), PLANNING_ROWS, status="active", first_event=1000.0, started=False)
        self.assertIn("window", m["planning"]["unmeasured"])
        self.assertFalse([name for name in m["unmeasured"] if "planning" in name], m["unmeasured"])

    def test_a_run_written_by_the_harness_carries_the_planning_block_in_metrics_json(self):
        code, result = self.invoke("grok", "done")
        out = Path(result["output"])
        written = json.loads((out / "metrics.json").read_text())
        self.assertIn("planning", written)
        self.assertEqual(set(written["planning"]), {"window", "stages", "improve", "producer_seconds", "tokens", "unmeasured"})
        self.assertNotIn("planning", result["metrics"], "result.json keeps its explicit subset; metrics.json is the evidence")

    def test_summary_lines_name_the_window_the_improve_share_and_the_tokens_right_after_the_counters(self):
        m = collect_stream(grok_usage(10), [("a-intake", "intake", "done", 1002), ("a-spec", "spec", "done", 1003),
                                            ("a-ts", "test-spec", "done", 1005)],
                           status="active", first_event=1000.0, started=1001.0,
                           inner={"improve_results": {"a-spec": {}}}, binds={"a-spec": 1002.0})
        lines = metrics.summary_lines(m)
        self.assertTrue(lines[0].startswith("turns "))
        self.assertEqual(lines[1], "planning window closed at test-spec: 0.1 min engine / 0.1 min host; Improve 0.0 min in 1 child, "
                                   "other 0.1 min; output tokens 600 (40% reasoning, host clock)")

    def test_summary_lines_say_when_the_window_could_not_be_measured(self):
        m = collect_stream(grok_usage(3), PLANNING_ROWS, status="active", first_event=1000.0, started=False)
        self.assertEqual(metrics.summary_lines(m)[1],
                         "planning window not measured: " + m["planning"]["unmeasured"]["window"])

    def test_progress_prints_the_planning_line_once_when_the_window_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_stream_run(out, grok_usage(10), PLANNING_ROWS[:1], status="active", first_event=1000.0, started=1030.0,
                             inner={"improve_results": {}})
            self.assertNotIn("planning window", progress.report(out))  # still open: nothing to print
            write_stream_run(out, grok_usage(10), PLANNING_ROWS, status="active", first_event=1000.0, started=1030.0,
                             inner={"improve_results": {}})
            first, second = progress.report(out), progress.report(out)
            self.assertIn("planning window closed at test-spec: 6.2 min engine / 6.7 min host", first)
            self.assertNotIn("planning window", second)


class RecordedRunReproductionTest(unittest.TestCase):
    """The planning block reproduces the figures of recorded runs (validated another way: real-run extracts).

    The extracts under docs/experiments/planning-measures-20261008/ hold the accepted rows, stamps, Improve bind times and
    per-call token rows of three recorded planning windows (no run text); `extract.py` rebuilds them from the run folders.
    The expected figures are the ones the 2026-10-05 planning-time account reported (Luna xhigh: window 374.95 min, 203.35
    in Improve children; Grok `none`: 20.5 min on the engine clock, 22.05 on the host's), recomputed on 2026-10-08."""

    EXTRACTS = ROOT / "docs" / "experiments" / "planning-measures-20261008"

    def planning(self, name: str) -> dict:
        data = json.loads((self.EXTRACTS / f"{name}.json").read_text())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_dir = out / "run"
            write_engine_records(run_dir, [(r["action"], r["stage"], r["outcome"], r["t"]) for r in data["rows"]],
                                 status="active", inner={"improve_results": {a: {} for a in data["improve"]}},
                                 started=data["started"])
            for action, mtime in data["improve"].items():
                bind = run_dir / "improve" / f"{action}-bind.md"
                bind.parent.mkdir(parents=True, exist_ok=True)
                bind.write_text("bound\n")
                os.utime(bind, (mtime, mtime))
            first = {"type": "available_commands", "commands": []}
            events, stamps = [first], [data["first_event"]]
            if data["host"] == "grok":
                for t, output, reasoning in data["usage"]:
                    events.append({"type": "usage", "usage": {"output_tokens": output, "reasoning_tokens": reasoning}})
                    stamps.append(t)
            if data["host"] == "claude":
                events.append({"type": "assistant", "message": {"id": "m0", "content": [{"type": "text", "text": "x"}]}})
                stamps.append(data["first_event"] + 1)
            (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            (out / "timeline.jsonl").write_text("".join(json.dumps({"line": n, "t": t}) + "\n" for n, t in enumerate(stamps)))
            if data["host"] == "codex":
                lines = []
                for number, (t, output, reasoning, thread, request) in enumerate(data["rollouts"]):
                    lines.append(usage_line(t, "root" if thread == "main" else "sub", "root", f"r{number}", output + 1000,
                                            output=output, reasoning=reasoning))
                    if request:
                        lines.append(compacted_line(t + 0.01, f"r{number}"))
                write_rollout(out, "0", lines)
            return metrics.collect(out, run_dir)["planning"]

    def test_the_luna_xhigh_extract_reproduces_374_95_203_35_and_171_6_and_the_five_stage_improve_shares(self):
        plan = self.planning("luna-xhigh-1.21.0")
        window = plan["window"]
        self.assertEqual((window["closed"], round(window["seconds"] / 60, 2), round(window["host_seconds"] / 60, 2)),
                         (True, 374.95, 375.93))
        self.assertEqual((plan["improve"]["children"], round(plan["improve"]["seconds"] / 60, 2),
                          round(plan["producer_seconds"] / 60, 1)), (5, 203.35, 171.6))
        shares = {r["stage"]: round(r["improve_seconds"] / 60, 2) for r in plan["stages"] if r["improve_seconds"]}
        self.assertEqual(shares, {"spec": 44.49, "test-strategy": 61.06, "plan": 56.92, "step-plan": 26.7, "test-spec": 14.17})

    def test_the_luna_xhigh_tokens_include_the_compaction_requests_of_the_window(self):
        tokens = self.planning("luna-xhigh-1.21.0")["tokens"]
        # Leaving the 10 requests of the window out gives 1,116,758: their 37,141 output tokens carry no reasoning.
        self.assertEqual((tokens["output"], tokens["reasoning"], tokens["subagent_output"]), (1153899, 682569, 0))
        self.assertEqual(round(100 * tokens["reasoning"] / tokens["output"], 1), 59.2)

    def test_the_grok_none_extract_reproduces_20_5_engine_22_05_host_and_86986_tokens_at_43_percent_reasoning(self):
        plan = self.planning("grok-none-1.22.0")
        window = plan["window"]
        self.assertEqual((round(window["seconds"] / 60, 2), round(window["host_seconds"] / 60, 2), window["before_engine_seconds"]),
                         (20.5, 22.05, 92.8))
        self.assertEqual(plan["improve"], {"children": 0, "seconds": 0.0})
        self.assertEqual(plan["tokens"], {"output": 86986, "reasoning": 37770, "clock": "host", "source": "usage events"})
        self.assertEqual(round(100 * 37770 / 86986, 1), 43.4)

    def test_the_sonnet_extract_reproduces_6_47_minutes_and_2_57_in_five_improve_children_with_no_token_figure(self):
        plan = self.planning("sonnet-1.23.0")
        self.assertEqual((round(plan["window"]["seconds"] / 60, 2), plan["improve"]["children"],
                          round(plan["improve"]["seconds"] / 60, 2)), (6.47, 5, 2.57))
        self.assertIn("snapshot", plan["tokens"]["unmeasured"])


class SonnetCostDecompositionTest(unittest.TestCase):
    """The Sonnet cost rise of the batch-1007 live pair, rebuilt from the committed export (the folders are outside the repo).

    `inputs` of docs/experiments/batch-1007-live-20261007/cost-decomposition.json holds what cost_decomposition.py read
    from the two run folders; `recomputed` must equal `decompose(inputs)`, so the LEARNINGS entry that cites it can be
    checked by a script run instead of being taken from a model-judged account (journal rule)."""

    DIR = ROOT / "docs" / "experiments" / "batch-1007-live-20261007"

    def setUp(self):
        spec = importlib.util.spec_from_file_location("cost_decomposition", self.DIR / "cost_decomposition.py")
        self.script = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.script)
        self.data = json.loads((self.DIR / "cost-decomposition.json").read_text())

    def test_the_recomputed_figures_are_the_arithmetic_on_the_committed_inputs(self):
        self.assertEqual(self.script.decompose(self.data["inputs"]), self.data["recomputed"])

    def test_the_fitted_rates_reproduce_both_recorded_session_costs(self):
        for name, cost in (("old", 6.5405192), ("new", 9.6542784)):
            self.assertAlmostEqual(self.script.cost(self.data["inputs"][name]["usage"]), cost, places=7)
            self.assertLess(self.data["recomputed"][name]["fit_error_usd"], 1e-6)

    def test_the_rise_is_the_sum_of_its_components_and_most_of_it_is_cache_reads_of_the_extra_calls(self):
        r = self.data["recomputed"]
        self.assertAlmostEqual(sum(r["rise_by_component_usd"].values()), r["rise_usd"], places=3)
        self.assertEqual(r["rise_usd"], 3.1138)
        self.assertGreater(r["rise_by_component_usd"]["cache_read_input_tokens"], 0.8 * r["rise_usd"])
        q = r["quadratic"]
        self.assertEqual((q["first_calls_of_the_new_run"], q["extra_calls"]), (133, 34))
        self.assertEqual(q["cache_read_tokens_of_those_calls"] + q["cache_read_tokens_of_extra_calls"],
                         self.data["inputs"]["new"]["usage"]["cache_read_input_tokens"])
        self.assertGreater(q["share_of_the_increase_in_the_extra_calls"], 0.8)

    def test_the_two_runs_are_not_a_controlled_pair(self):
        old, new = self.data["inputs"]["old"], self.data["inputs"]["new"]
        self.assertNotEqual(old["claude_code_version"], new["claude_code_version"])
        self.assertEqual(old["versions"]["plugin_version"], new["versions"]["plugin_version"])
        self.assertNotEqual(old["versions"]["local_head"], new["versions"]["local_head"])

    def test_decompose_splits_the_cache_reads_of_a_longer_run_at_the_length_of_the_shorter(self):
        usage = lambda cr: {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": cr, "output_tokens": 0}  # noqa: E731
        old = {"cost_usd": 1.0, "usage": usage(30), "cache_read_per_call": [10, 20], "context_per_call": [10, 20]}
        new = {"cost_usd": 2.0, "usage": usage(70), "cache_read_per_call": [10, 20, 40], "context_per_call": [10, 20, 40]}
        q = self.script.decompose({"old": old, "new": new})["quadratic"]
        self.assertEqual((q["cache_read_tokens_of_those_calls"], q["cache_read_tokens_of_extra_calls"]), (30, 40))
        self.assertEqual((q["against_the_old_run"], q["share_of_the_increase_in_the_extra_calls"]), (0.0, 1.0))


class GitDiscoveryTests(unittest.TestCase):
    """A case's work folder never adopts a repository above the run (2026-10-10: a home folder that is itself a Git
    repository made the hello case's empty work folder resolve to it, and ShipLoop refused to start there)."""

    def test_git_in_the_work_folder_stops_at_the_run_output_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp) / "home"
            work = parent / "runs" / "out" / "work"
            work.mkdir(parents=True)
            git_env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
            subprocess.run(["git", "init", "-q", str(parent)], check=True, env=git_env)
            probe = ["git", "-C", str(work), "rev-parse", "--show-toplevel"]
            found = subprocess.run(probe, capture_output=True, text=True, env=git_env)
            self.assertEqual(found.returncode, 0, "the control: without the ceiling git finds the outer repository")
            env = run.isolate_git_discovery(git_env, work.parent)
            isolated = subprocess.run(probe, capture_output=True, text=True, env=env)
            self.assertNotEqual(isolated.returncode, 0, isolated.stdout)
            self.assertIn(str(work.parent.resolve()), env["GIT_CEILING_DIRECTORIES"].split(os.pathsep))

    def test_an_existing_ceiling_is_kept(self):
        env = run.isolate_git_discovery({"GIT_CEILING_DIRECTORIES": "/a"}, Path("/tmp/out"))
        self.assertIn("/a", env["GIT_CEILING_DIRECTORIES"].split(os.pathsep))


if __name__ == "__main__":
    unittest.main()
