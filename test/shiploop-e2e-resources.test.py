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




class SuiteTest(HarnessCase):
    def use_catalog(self, cases: dict, suites: dict) -> None:
        for attr, data in (("CASES", cases), ("SUITES", suites)):
            path = self.tmp / (attr.lower() + ".json")
            path.write_text(json.dumps(data))
            saved = getattr(run, attr)
            setattr(run, attr, path)
            self.addCleanup(setattr, run, attr, saved)

    def run_suite(self, name: str) -> tuple[int, dict]:
        os.environ["FAKE_MODE"] = "done"
        out = self.tmp / "suite-out"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--suite", name, "--host", "grok", "--grok-bin", str(self.fakes["grok"]),
                             "--output", str(out), "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        return code, json.loads((out / "suite-result.json").read_text())

    def test_follow_on_starts_from_its_predecessor_and_rows_record_the_suite(self):
        self.use_catalog(
            {"first": {"style": "s", "prompt": "p", "checks": ["test -f hello.py"]},
             "second": {"style": "s", "follows": "first", "prompt": "q", "checks": [], "retention": []}},
            {"focus": {"kind": "focused", "style": "s", "cases": ["first", "second"]}})
        code, result = self.run_suite("focus")
        self.assertEqual(code, 0, result)
        self.assertEqual([row["case"] for row in result["cases"]], ["first", "second"])
        second = json.loads((self.tmp / "suite-out" / "second" / "result.json").read_text())
        self.assertEqual(second["follow_on"]["prior"], str((self.tmp / "suite-out" / "first").resolve()))
        rows = [json.loads(line) for line in self.baselines.read_text().splitlines()]
        self.assertEqual([(r["case"], r["style"], r["suite"], r["pass"]) for r in rows],
                         [("first", "s", "focus", True), ("second", "s", "focus", True)])

    def test_follow_on_is_skipped_when_its_predecessor_failed(self):
        self.use_catalog(
            {"first": {"style": "s", "prompt": "p", "checks": ["false"]},
             "second": {"style": "s", "follows": "first", "prompt": "q", "checks": []}},
            {"focus": {"kind": "focused", "style": "s", "cases": ["first", "second"]}})
        code, result = self.run_suite("focus")
        self.assertEqual(code, 1)
        self.assertIn("failed", result["cases"][1]["skipped"])
        self.assertFalse((self.tmp / "suite-out" / "second").exists())

    def test_tmp_writes_and_names_shared_across_runs(self):
        """P13: a literal /tmp path is shared with every other run; the suite names any two that met."""
        self.assertEqual(metrics.tmp_writes("node --test > /tmp/w1.txt 2>&1"), ["/tmp/w1.txt"])
        self.assertEqual(metrics.tmp_writes("python3 x.py | tee /tmp/r.json"), ["/tmp/r.json"])
        self.assertEqual(metrics.tmp_writes('mv out.json "/tmp/improve-done-1.json"'), ["/tmp/improve-done-1.json"])
        self.assertEqual(metrics.tmp_writes("cat /tmp/a.txt"), [])  # a read
        self.assertEqual(metrics.tmp_writes("x > /x/run/scratch/a.txt"), [])  # the run's own scratch
        self.assertEqual(metrics.tmp_writes("python3 - <<'PY'\nopen('/tmp/x','w')\nPY"), [])  # a document
        outs = []
        for name, target in (("a", "/tmp/improve-done-1.json"), ("b", "/tmp/improve-done-1.json"),
                             ("c", "/tmp/other.json")):
            out = self.tmp / name
            out.mkdir()
            (out / "events.jsonl").write_text(json.dumps({"type": "tool_call", "toolCallId": "1", "toolName": "write",
                                                          "rawInput": {"file_path": target, "content": "{}"}}) + "\n")
            outs.append(out)
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/improve-done-1.json": ["a", "b"]})

    def test_independent_chains_run_concurrently_and_report_in_suite_order(self):
        cases = {"a": {"style": "s", "prompt": "p", "checks": []},
                 "b": {"style": "t", "prompt": "p", "checks": []},
                 "a2": {"style": "s", "follows": "a", "prompt": "q", "checks": []}}
        self.assertEqual(run.suite_chains(["a", "b", "a2"], cases), [["a", "a2"], ["b"]])
        self.use_catalog(cases, {"wide": {"kind": "breadth", "cases": ["a", "b", "a2"]}})
        started = []
        real_main = run.main

        def spy(argv=None):
            if argv and "--case" in argv:
                started.append(argv[argv.index("--case") + 1])
                self.assertIn("--quiet", argv)  # concurrent live views would interleave
            return real_main(argv)

        with mock.patch.object(run, "main", side_effect=spy):
            code, result = self.run_suite("wide")
        self.assertEqual(code, 0, result)
        self.assertEqual([row["case"] for row in result["cases"]], ["a", "b", "a2"])
        self.assertLess(started.index("a"), started.index("a2"))
        self.assertTrue(all((self.tmp / "suite-out" / name / "result.json").is_file() for name in ("a", "b", "a2")))

    def test_a_batch_gate_runs_first_and_a_failed_gate_stops_the_rest(self):
        cases = {"g": {"style": "s", "prompt": "p", "checks": ["false"]},
                 "a": {"style": "t", "prompt": "p", "checks": []}}
        self.use_catalog(cases, {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        code, result = self.run_suite("b")
        self.assertEqual(code, 1)
        self.assertEqual([(r["case"], r.get("skipped")) for r in result["cases"]], [("g", None), ("a", "the gate failed")])
        self.assertFalse((self.tmp / "suite-out" / "a").exists())
        cases["g"]["checks"] = []
        self.use_catalog(cases, {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        shutil.rmtree(self.tmp / "suite-out")
        code, result = self.run_suite("b")
        self.assertEqual(code, 0, result)
        self.assertEqual([r["case"] for r in result["cases"]], ["g", "a"])

    def test_committed_suites_name_known_cases_and_breadth_covers_every_focused_style(self):
        cases = json.loads(run.CASES.read_text())
        suites = {k: v for k, v in json.loads(run.SUITES.read_text()).items() if not k.startswith("_")}
        for name, suite in suites.items():
            for case in suite["cases"]:
                self.assertIn(case, cases, name)
                if suite["kind"] == "focused":
                    self.assertEqual(cases[case]["style"], suite["style"], (name, case))
        focused = {s["style"] for s in suites.values() if s["kind"] == "focused" and s["style"] != "smoke"}
        breadth = {cases[c]["style"] for c in suites["breadth"]["cases"]}
        self.assertEqual(breadth, focused)

    def test_each_named_suite_selects_exactly_the_styles_its_claim_names(self):
        """The 2026-10-16 E2E audit (item 5): SPEC called breadth "one case of every style", but it held three of the five
        styles. Every named suite now states the styles it covers, the breadth suite also names each style it leaves out
        and why, and SPEC and README name the same styles, so a claim and its selection cannot drift apart."""
        cases = json.loads(run.CASES.read_text())
        suites = {k: v for k, v in json.loads(run.SUITES.read_text()).items() if not k.startswith("_")}
        styles_in_catalog = {case["style"] for name, case in cases.items() if not name.startswith("_")}
        for name, suite in suites.items():
            with self.subTest(suite=name):
                selected = {cases[case]["style"] for case in suite.get("gate", []) + suite["cases"]}
                self.assertEqual(selected, set(suite["styles"]), "the suite's cases must cover exactly the styles it claims")
        breadth = suites["breadth"]
        self.assertEqual(len(breadth["cases"]), len(breadth["styles"]), "breadth runs one case per style it claims")
        self.assertEqual(set(breadth["styles"]) | set(breadth["not_covered"]), styles_in_catalog,
                         "every catalog style is either covered by breadth or named as left out")
        self.assertFalse(set(breadth["styles"]) & set(breadth["not_covered"]))
        self.assertTrue(all(reason.strip() for reason in breadth["not_covered"].values()))
        spec = (run.HERE / "SPEC.md").read_text()
        claim = spec[spec.index("- **Breadth suite**"):spec.index("- **Promotion**")]
        readme = (run.HERE / "README.md").read_text()
        for style in styles_in_catalog:
            self.assertIn(f"`{style}`", claim, f"SPEC's breadth claim names {style}")
            self.assertIn(f"`{style}`", readme, f"README names {style}")
        self.assertNotIn("one case of every style", claim)

    def test_case_checks_name_existing_helper_scripts_and_subcommands(self):
        cases = json.loads(run.CASES.read_text())
        for name, case in cases.items():
            for check in case["checks"] + case.get("retention", []):
                for script, sub in re.findall(r'"\$E2E_CHECKS/([\w.]+)" (\w+)', check):
                    with self.subTest(case=name, check=check):
                        path = run.HERE / "checks" / script
                        self.assertTrue(path.is_file())
                        self.assertIn('"' + sub + '":', path.read_text())

    def test_a_second_run_reports_the_change_against_the_previous_row(self):
        self.invoke("grok", "done")
        output = io.StringIO()
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(output):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "again"),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertIn("baseline  vs", output.getvalue())
        self.assertEqual(len(self.baselines.read_text().splitlines()), 2)


@unittest.skipUnless(shutil.which("node") and shutil.which("lsof"), "needs node and lsof")
class HttpCheckBindingTest(unittest.TestCase):
    """The 2026-10-16 E2E audit's port control (docs/experiments/shiploop-e2e-audit-20261016/port-probe/): with a sibling
    serving a Battleship page on the check's port, the Battleship page check passed for a candidate that could only answer
    "candidate". A check must accept only a response its own candidate served."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.page_check = json.loads(run.CASES.read_text())["battleship"]["checks"][1]

    def candidate(self, source: str) -> Path:
        work = self.tmp / f"candidate-{len(list(self.tmp.iterdir()))}"
        work.mkdir()
        (work / "server.js").write_text(source)
        return work

    def check_port(self) -> tuple[int, dict]:
        """The port the page check will use: a fixed one written in the check, else the one pinned through E2E_SERVE_PORT."""
        fixed = re.search(r"127\.0\.0\.1:(\d+)", self.page_check)
        if fixed and "serve.py" not in self.page_check:
            return int(fixed.group(1)), {}
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        return port, {"E2E_SERVE_PORT": str(port)}

    def sibling(self, port: int) -> subprocess.Popen:
        proc = subprocess.Popen(["node", str(PORT_PROBE / "sibling" / "server.js")], env=dict(os.environ, PORT=str(port)),
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.wait)
        self.addCleanup(proc.kill)
        for _ in range(100):
            with contextlib.suppress(OSError), socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return proc
            time.sleep(0.05)
        self.fail("the sibling never listened")

    def check(self, work: Path, env: dict | None = None) -> dict:
        with mock.patch.dict(os.environ, env or {}):
            return run.run_checks(work, [self.page_check], timeout=60)[0]

    def test_a_candidate_listener_does_not_hide_a_sibling_listener_on_the_same_port(self):
        spec = importlib.util.spec_from_file_location("shiploop_e2e_test_serve", run.HERE / "checks" / "serve.py")
        serve = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(serve)
        proc = mock.Mock()
        proc.pid = 101
        proc.returncode = None
        proc.poll.return_value = None
        stderr = self.tmp / "server.stderr"
        stderr.write_text("")
        clock = iter((0.0, 0.0))

        def stop(message):
            raise RuntimeError(message)

        with mock.patch.object(serve, "READY_SECONDS", 1), \
                mock.patch.object(serve.time, "monotonic", side_effect=lambda: next(clock)), \
                mock.patch.object(serve, "listening_pids", return_value={101, 202}), \
                mock.patch.object(serve, "in_group", side_effect=lambda pid, leader: pid == leader), \
                mock.patch.object(serve, "fail", side_effect=stop) as fail:
            with self.assertRaisesRegex(RuntimeError, "not by the candidate"):
                serve.wait_for_candidate(proc, 49123, stderr)

        fail.assert_called_once()
        self.assertIn("202", fail.call_args.args[0])

    def test_the_audit_candidate_beside_a_sibling_on_the_check_port_fails(self):
        port, env = self.check_port()
        sibling = self.sibling(port)
        result = self.check(self.candidate((PORT_PROBE / "candidate" / "server.js").read_text()), env)
        self.assertFalse(result["pass"], result)
        self.assertIsNone(sibling.poll(), "the check must not stop a process it did not start")

    def test_a_valid_candidate_passes_alone_and_is_refused_when_a_sibling_holds_its_port(self):
        work = self.candidate(VALID_PAGE)
        self.assertTrue(self.check(work)["pass"], "the valid candidate alone")
        port, env = self.check_port()
        sibling = self.sibling(port)
        result = self.check(work, env)
        self.assertFalse(result["pass"], result)
        # Either the candidate exits first or the ownership probe sees the sibling first.
        # Both refuse its response; the latter can happen before Node emits its bind error.
        self.assertRegex(result["output"], r"EADDRINUSE|not by the candidate")
        self.assertIsNone(sibling.poll(), "the check must not stop the foreign listener")

    def test_a_candidate_that_exits_before_listening_reports_its_startup_error(self):
        work = self.candidate("process.stderr.write('startup fixture refused\\n'); process.exit(23);\n")
        result = self.check(work)
        self.assertFalse(result["pass"], result)
        self.assertIn("the candidate exited (rc 23)", result["output"])
        self.assertIn("startup fixture refused", result["output"])

    def test_a_listener_that_is_not_the_candidate_is_refused_and_only_the_candidate_is_ended(self):
        port, env = self.check_port()
        sibling = self.sibling(port)
        work = self.candidate(ELSEWHERE)
        result = self.check(work, env)
        self.assertFalse(result["pass"], result)
        self.assertIn("not by the candidate", result["output"])
        self.assertIsNone(sibling.poll())
        # The ownership check can stop Node before its source runs. Use the PID
        # recorded at launch, not a file whose creation depends on startup order.
        candidate_pid = re.search(r"not by the candidate \(pid (\d+)\)", result["output"])
        self.assertIsNotNone(candidate_pid, result["output"])
        pid = int(candidate_pid.group(1))
        self.assertNotEqual(pid, sibling.pid)
        for _ in range(50):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            self.fail(f"the candidate {pid} the check started is still running")


class CheckHygieneTest(unittest.TestCase):
    def test_temperature_unit_check_requires_tests_and_success(self):
        check = json.loads(run.CASES.read_text())["temperature-report"]["checks"][0]
        for name, source, expected in (
            ("no tests", None, False),
            ("passing", "import unittest\nclass T(unittest.TestCase):\n    def test_ok(self): self.assertTrue(True)\n", True),
            ("failing", "import unittest\nclass T(unittest.TestCase):\n    def test_bad(self): self.fail('broken product')\n", False),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                if source is not None:
                    (work / "test_product.py").write_text(source)
                result = run.run_checks(work, [check])[0]
                self.assertEqual(result["pass"], expected, result["output"])

    def test_temperature_stats_check_rejects_missing_wrong_and_nonconforming_modules(self):
        check = json.loads(run.CASES.read_text())["temperature-report"]["checks"][2]
        correct = (
            "def mean(values):\n"
            "    if not values: raise ValueError('empty')\n"
            "    return sum(values) / len(values)\n"
            "def median(values):\n"
            "    if not values: raise ValueError('empty')\n"
            "    ordered = sorted(values); middle = len(ordered) // 2\n"
            "    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2\n"
        )
        variants = (
            ("missing", None, False),
            ("correct", correct, True),
            ("wrong mean", correct.replace("sum(values) / len(values)", "99"), False),
            ("wrong median", correct.replace("ordered = sorted(values)", "ordered = list(values)"), False),
            ("wrong exception", correct.replace("ValueError", "TypeError"), False),
            ("accepts empty", correct.replace("raise ValueError('empty')", "return 0"), False),
        )
        for name, source, expected in variants:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                if source is not None:
                    (work / "stats.py").write_text(source)
                result = run.run_checks(work, [check])[0]
                self.assertEqual(result["pass"], expected, result["output"])

    def test_checks_run_with_standard_input_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run.run_checks(Path(tmp), ["read line; test -z \"$line\""], timeout=10)[0]
        self.assertTrue(result["pass"], result)  # reading stdin returns at once instead of waiting

    def test_checks_leave_no_untracked_file_behind(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            subprocess.run(["git", "init", "-q", str(work)], check=True)
            (work / "mine.txt").write_text("the user's own file\n")
            results = run.run_checks(work, ["echo log > server.log", "echo page > page.html; false"])
            self.assertEqual([r["pass"] for r in results], [True, False])
            self.assertFalse((work / "server.log").exists())
            self.assertFalse((work / "page.html").exists())
            self.assertTrue((work / "mine.txt").exists(), "files present before the checks are kept")

    def test_scoring_spec_check_accepts_in_place_requirement_updates(self):
        check = json.loads(run.CASES.read_text())["battleship-scoring"]["retention"][3]
        with tempfile.TemporaryDirectory() as tmp:
            prior, work = Path(tmp) / "prior", Path(tmp) / "work"
            for root, extra in ((prior, ""), (work, "Every fire returns shots, hits and accuracy.\n")):
                (root / "docs" / "shiploop").mkdir(parents=True)
                (root / "docs" / "shiploop" / "spec.md").write_text("## R-1 Fire\n" + extra)
            ok = run.run_checks(work, [check], env={"PRIOR_WORK": str(prior)})[0]
            self.assertTrue(ok["pass"], ok["output"])
            (work / "docs" / "shiploop" / "spec.md").write_text("## R-2 Other\nshots and accuracy\n")
            dropped = run.run_checks(work, [check], env={"PRIOR_WORK": str(prior)})[0]
            self.assertFalse(dropped["pass"], "a dropped earlier id still fails")


@unittest.skipUnless(shutil.which("node"), "the retention check runs the real `node --test`")
class TestRetentionCheckTest(unittest.TestCase):
    """battleship-scoring's test retention check (SPEC S-11 row, amended 2026-10-26): no fewer tests pass than in the followed
    run, and the added test lines name the new shots and hits fields. A pass count that must grow failed the Grok gate's
    delivery, which asserted the fields inside its 11 existing test() declarations."""

    BASE = ("const test = require('node:test'); const assert = require('node:assert');\n"
            "test('a shot reports its result', () => { assert.equal(1, 1); });\n")

    @staticmethod
    def check() -> str:
        found = [c for c in json.loads(run.CASES.read_text())["battleship-scoring"]["retention"] if "count()" in c]
        assert len(found) == 1, "the test retention check moved: update this test"
        return found[0]

    def verdict(self, work_tests: dict, prior_tests: dict | None = None) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            prior, work = Path(tmp) / "prior", Path(tmp) / "work"
            for root, files in ((prior, prior_tests or {"rules.test.js": self.BASE}), (work, work_tests)):
                (root / "test").mkdir(parents=True)
                for name, text in files.items():
                    (root / "test" / name).write_text(text)
            return run.run_checks(work, [self.check()], timeout=120, env={"PRIOR_WORK": str(prior)})[0]

    def test_assertions_folded_into_existing_tests_pass_and_so_does_a_new_test_file(self):
        folded = self.BASE.replace("assert.equal(1, 1);", "assert.deepEqual({shots: 1, hits: 1}, {shots: 1, hits: 1});")
        result = self.verdict({"rules.test.js": folded})
        self.assertTrue(result["pass"], result["output"])
        self.assertIn("tests 1 -> 1", result["output"])
        new_file = "const test = require('node:test');\ntest('scoring', () => { const shots = 2, hits = 1; });\n"
        result = self.verdict({"rules.test.js": self.BASE, "score.test.js": new_file})
        self.assertTrue(result["pass"], result["output"])

    def test_unchanged_fewer_or_unnamed_tests_fail_with_the_reason(self):
        base_naming = {"rules.test.js": self.BASE.replace("a shot reports", "shots and hits report")}
        for name, work, prior, reason in (
                ("unchanged", {"rules.test.js": self.BASE}, None, "the test files are unchanged"),
                ("unchanged, though the followed run already names the fields", base_naming, base_naming,
                 "the test files are unchanged"),
                # node --test counts a file with no test() as one passing test, so "fewer" needs two tests before and one after.
                ("fewer", {"rules.test.js": self.BASE + "// shots hits\n"},
                 {"rules.test.js": self.BASE + "test('a miss is a miss', () => {});\n"}, "fewer tests pass"),
                ("only shots named", {"rules.test.js": self.BASE + "// shots\n"}, None, "no added test line names hits")):
            with self.subTest(name):
                result = self.verdict(work, prior)
                self.assertFalse(result["pass"], result["output"])
                self.assertIn(reason, result["output"])


class CheckScratchFileTest(unittest.TestCase):
    """A case check writes nothing into the product's folder (2026-10-24 runner review, E4): the release-gate Battleship run
    failed because check 2 fetched the page to work/page.html and removed it, and that product commits a page.html its
    server reads at start, so the check deleted it and every later check's server died. Scratch output goes to mktemp or a
    shell variable. docs/experiments/e2e-runner-review-20261024/e4-check-clobber.json."""

    # A redirect or a curl -o into a relative name with an extension or a leading dot; `=>` and `>=` are JavaScript.
    WRITES = re.compile(r"(?:(?<![=\-<>&0-9])\d?>\s*|-o\s+)(\.[\w-]+|[A-Za-z_][\w-]*\.[A-Za-z]+)\b")
    # The lines E4 found, kept as the scan's controls.
    OLD = ("node --test > node-test.log 2>&1; rc=$?; rm -f node-test.log",
           "python3 \"$E2E_CHECKS/serve.py\" -- sh -c 'curl -fsS \"$BASE/\" -o page.html && grep -qi battleship page.html; "
           "rc=$?; rm -f page.html; exit $rc'",
           "ids \"$PRIOR_WORK\" > .ids-before; ids . > .ids-after",
           "printf '' | python3 measure.py > out.txt 2> err.txt")
    SENTINELS = ("page.html", "node-test.log", "out.txt", "err.txt", ".ids-before", ".ids-after")

    def lines(self):
        for name, case in json.loads(run.CASES.read_text()).items():
            for kind in ("checks", "retention"):
                for index, line in enumerate(case.get(kind) or []):
                    yield name, kind, index, line, case

    def test_no_case_check_writes_a_relative_file_and_the_scan_flags_the_lines_e4_found(self):
        for old in self.OLD:
            self.assertTrue(self.WRITES.search(old), old)
        found = [(name, kind, index, self.WRITES.findall(line)) for name, kind, index, line, _ in self.lines()
                 if self.WRITES.search(line)]
        self.assertEqual(found, [], "write scratch output to mktemp or a variable, never into the product's folder")

    def product(self, root: Path) -> Path:
        work = root / "work"
        (work / "test").mkdir(parents=True)
        (work / "server.js").write_text(
            "const http=require('node:http'),fs=require('node:fs'),path=require('node:path');\n"
            "const PAGE=fs.readFileSync(path.join(__dirname,'page.html'));\n"
            "http.createServer((q,s)=>{if(q.url==='/'){s.writeHead(200,{'content-type':'text/html'});return s.end(PAGE);}"
            "s.writeHead(404);s.end();}).listen(Number(process.env.PORT||3000),'127.0.0.1');\n")
        (work / "test" / "ok.test.js").write_text("require('node:test')('ok', () => {});\n")
        for name in self.SENTINELS:
            (work / name).write_text("<title>Battleship</title> Checkers accuracy\n" if name == "page.html" else f"the product's {name}\n")
        subprocess.run(["git", "init", "-q", str(work)], check=True)
        subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
        # maintenance.auto=false: a detached auto-maintenance after the commit held objects/maintenance.lock while the test
        # copied the tree, and copytree failed on the vanished lock (release CI 40447967270, git 2.55).
        subprocess.run(["git", "-C", str(work), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                        "-c", "maintenance.auto=false", "commit", "-qm", "product"], check=True)
        return work

    def test_a_product_that_commits_page_html_and_the_scratch_names_keeps_them_through_every_case_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.product(Path(tmp))
            prior = Path(tmp) / "prior"
            shutil.copytree(work, prior)
            before = {name: (work / name).read_bytes() for name in self.SENTINELS}
            page_checks = {}
            for name, kind, index, line, case in self.lines():
                if case.get("platform"):
                    continue  # a hosted case's checks call a real org
                result = run.run_checks(work, [line], timeout=60, env={"PRIOR_WORK": str(prior)})[0]
                if "grep -qi" in line and "$BASE/" in line:
                    page_checks[(name, index)] = result
                with self.subTest(case=name, kind=kind, index=index):
                    status = subprocess.run(["git", "-C", str(work), "status", "--porcelain"], capture_output=True,
                                            text=True).stdout
                    self.assertEqual(status, "", f"{name} {kind}[{index}] changed the product's tracked files")
                    self.assertEqual({n: (work / n).read_bytes() for n in self.SENTINELS}, before)
            self.assertEqual(sorted(page_checks), [("battleship", 1), ("battleship-scoring", 2), ("checkers", 1)])
            for key, result in page_checks.items():
                self.assertTrue(result["pass"], (key, result["output"]))
            # The control: E4's line deletes the page, which is what this test exists to catch.
            run.run_checks(work, [self.OLD[1]], timeout=60)
            self.assertFalse((work / "page.html").exists())


class BattleshipGameCheckTest(unittest.TestCase):
    """checks/battleship_game.py, the Battleship case's game check (2026-10-24 runner review, E2; calibrated 2026-10-26, build
    step 5). It must reject the audit's server with no fleet, the three stubs of the 2026-10-04 review and each targeted
    defect of the prompt's sentences, and accept a game that plays and the independently written games of BATTLESHIP_ALT.
    The fifteen saved real deliveries it accepts are in docs/experiments/e2e-oracle-calibration-20261026/."""

    def verdict(self, mode: str, stub: str = BATTLESHIP_STUB) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "stub.py").write_text(stub)
            done = subprocess.run([sys.executable, str(run.HERE / "checks" / "serve.py"), "--start",
                                   f"{shlex.quote(sys.executable)} stub.py {mode}", "--",
                                   sys.executable, str(run.HERE / "checks" / "battleship_game.py")],
                                  cwd=tmp, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        return done.returncode, done.stdout + done.stderr

    def test_a_game_that_plays_passes_and_every_stub_that_only_answers_in_shape_fails(self):
        for mode, code in (("plays", 0), ("audit", 5), ("all-sunk", 5), ("no-fleet", 5), ("constant-id", 5),
                           ("never-ends", 4), ("bad-result", 3), ("restarts", 7)):
            with self.subTest(mode=mode):
                returncode, output = self.verdict(mode)
                self.assertEqual(returncode, code, output)
                if code:
                    self.assertIn("FAIL:", output)

    def test_each_targeted_defect_fails_and_each_independently_written_game_passes(self):
        # Build step 5 (Astra): correct and alternative implementations pass; each targeted broken variant fails.
        for mode, code, reason in (("sunk-first-hit", 5, "a hit: the game ends when the last ship sinks"),
                                   ("never-sunk", 5, "a hit: the game ends when the last ship sinks"),
                                   ("over-after-first-sink", 5, "after 1 sunk ship(s)"),
                                   # The gap the calibration found: the check only knew "more than one ship".
                                   ("over-after-two-sunk", 8, "a ship was still afloat when the game ended")):
            with self.subTest(defect=mode):
                returncode, output = self.verdict(mode)
                self.assertEqual(returncode, code, output)
                self.assertIn(reason, output)
        for mode in ("answers-after-end", "refuses-after-end"):
            with self.subTest(alternative=mode):
                returncode, output = self.verdict(mode, BATTLESHIP_ALT)
                self.assertEqual(returncode, 0, output)

    def test_the_case_runs_it_through_serve_py_in_place_of_the_sweep_that_passed_the_audit_server(self):
        cases = json.loads(run.CASES.read_text())
        line = 'python3 "$E2E_CHECKS/serve.py" -- python3 "$E2E_CHECKS/battleship_game.py"'
        self.assertEqual(cases["battleship"]["checks"][3], line)
        self.assertIn(line, cases["battleship-scoring"]["checks"], "the follow-on keeps the game playing")
        self.assertFalse([c for c in cases["battleship"]["checks"] if "for(let r=0;r<10" in c], "the old sweep is gone")


class SharedExpensesCheckTest(unittest.TestCase):
    """checks/expense_service.py, the shared-expenses case's product checks (style stateful-service; a Node service that leases
    no port, added 2026-11-01 as the representative case for the send-back replication R3). Calibrated as seat-reservations was
    (P6) before any live run: the reference service passes all six checks and writes nothing into the work folder, and each
    defect of one of the prompt's sentences fails the check that reads that sentence. The race-prone service, in which every
    request works on a snapshot taken before an await, is seen only by the concurrency check."""

    REFERENCE = run.HERE / "fixtures" / "shared-expenses-reference"
    CHECKS = ("unit", "contract", "split", "settle", "restart", "concurrency")
    RACE = ([("server.js", "req.on('end', () => {", "req.on('end', async () => {"),
             ("server.js", "const [status, payload] = route(",
              "const stale = JSON.stringify(groups);\n    await new Promise((resolve) => setTimeout(resolve, 3));\n"
              "    groups = JSON.parse(stale);\n    const [status, payload] = route(")], "concurrency")
    DEFECTS = {
        "the cents left over by an even split go to the members listed last":
            ([("expenses.js", "index < extra", "index >= members.length - extra")], "split"),
        "shares that do not add up to the amount are accepted":
            ([("expenses.js", "return total === cents ? owed : null;", "return owed;")], "contract"),
        "a negative share is accepted":
            ([("expenses.js", "Number.isSafeInteger(value) && value >= 0", "Number.isSafeInteger(value)")], "contract"),
        "a group of one member is accepted":
            ([("expenses.js", "members.length >= 2", "members.length >= 1")], "contract"),
        "a fractional amount is accepted":
            ([("server.js", "!Number.isSafeInteger(cents) || cents <= 0", "!(cents > 0)")], "contract"),
        "expense numbers start at 0":
            ([("server.js", "expense: group.expenses.length", "expense: group.expenses.length - 1")], "contract"),
        "a tie between members goes to the member listed last":
            ([("expenses.js", "net[name] < net[debtor]", "net[name] <= net[debtor]"),
              ("expenses.js", "net[name] > net[creditor]", "net[name] >= net[creditor]")], "settle"),
        "nothing is written to the data file": ([("server.js", "function save() {", "function save() {\n  return;")], "restart"),
        "every request works on a snapshot taken before an await (lost updates)": RACE,
    }

    @classmethod
    def setUpClass(cls):
        if shutil.which("node") is None:
            raise unittest.SkipTest("node is not installed")

    def service(self, tmp: str, edits=()) -> Path:
        work = Path(tmp) / "work"
        shutil.copytree(self.REFERENCE, work)
        for filename, find, replace in edits:
            source = (work / filename).read_text()
            self.assertEqual(source.count(find), 1, find)
            (work / filename).write_text(source.replace(find, replace))
        return work

    def verdict(self, work: Path, check: str) -> tuple[int, str]:
        done = subprocess.run([sys.executable, "-B", str(run.HERE / "checks" / "expense_service.py"), check], cwd=work,
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        return done.returncode, done.stdout + done.stderr

    def test_the_reference_service_passes_every_check_and_the_checks_write_nothing_into_the_work_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = self.service(tmp)
            before = sorted(item.relative_to(work).as_posix() for item in work.rglob("*"))
            for check in self.CHECKS:
                with self.subTest(check=check):
                    code, output = self.verdict(work, check)
                    self.assertEqual(code, 0, output)
            self.assertEqual(sorted(item.relative_to(work).as_posix() for item in work.rglob("*")), before)

    def test_each_defect_fails_the_check_that_reads_the_sentence_it_breaks(self):
        for what, (edits, check) in self.DEFECTS.items():
            with self.subTest(defect=what), tempfile.TemporaryDirectory() as tmp:
                code, output = self.verdict(self.service(tmp, edits), check)
                self.assertEqual(code, 1, output)
                self.assertIn("FAIL:", output)

    def test_the_race_prone_service_passes_every_check_but_the_concurrency_check(self):
        edits, _ = self.RACE
        with tempfile.TemporaryDirectory() as tmp:
            work = self.service(tmp, edits)
            for check in self.CHECKS:
                with self.subTest(check=check):
                    code, output = self.verdict(work, check)
                    self.assertEqual(code, 1 if check == "concurrency" else 0, output)

    def test_the_case_declares_its_six_checks_a_probe_term_and_no_port_lease(self):
        case = json.loads(run.CASES.read_text())["shared-expenses"]
        self.assertEqual(case["style"], "stateful-service")
        self.assertEqual([check.rsplit(" ", 1)[1] for check in case["checks"]], list(self.CHECKS))
        self.assertFalse(run.case_quality("shared-expenses").get("refuse_ports"), "a case with no fixed port leases none")
        self.assertIn("shared-expenses", json.loads((run.HERE / "probe_terms.json").read_text())["terms"])


class SessionStopTest(unittest.TestCase):
    """The stop reason is the host's own, and an error is never recorded as a success."""

    CLAUDE_API_ERROR = {"type": "result", "subtype": "success", "is_error": True, "terminal_reason": "api_error",
                        "api_error_status": None, "stop_reason": "stop_sequence", "num_turns": 143,
                        "result": "API Error: Unable to connect to API: SSL certificate has expired"}

    def test_a_claude_api_error_is_not_a_success(self):
        stop = metrics.session_stop(self.CLAUDE_API_ERROR)
        self.assertTrue(stop.startswith("error: api_error"), stop)
        self.assertIn("SSL certificate has expired", stop)
        limited = dict(self.CLAUDE_API_ERROR, api_error_status=429, result="You've hit your limit")
        self.assertEqual(metrics.session_stop(limited), "error: api_error 429: You've hit your limit")

    def test_a_normal_claude_stop_and_the_other_hosts_keep_their_own_reason(self):
        ok = {"type": "result", "subtype": "success", "is_error": False, "terminal_reason": "completed",
              "stop_reason": "end_turn"}
        self.assertEqual(metrics.session_stop(ok), "success")
        self.assertEqual(metrics.session_stop({"type": "end", "stopReason": "cancelled"}), "cancelled")
        self.assertEqual(metrics.session_stop({"type": "end", "stopReason": "end_turn"}), "end_turn")
        failed_turn = {"type": "end", "stopReason": "error", "error": "You've hit your usage limit.\nTry later"}
        self.assertEqual(metrics.session_stop(failed_turn), "error: You've hit your usage limit. Try later")

    def test_nothing_reported_stays_unknown_and_a_structured_reason_is_still_text(self):
        self.assertIsNone(metrics.session_stop({"type": "end"}))
        stop = metrics.session_stop({"type": "end", "stopReason": {"kind": "max_turns"}})
        self.assertEqual(stop, '{"kind": "max_turns"}')
        self.assertEqual(run.stopped_line(run.termination_facts(
            {"status": "failed", "returncode": 1, "sessions": [{"stop": stop}], "resumes": 0}, {}, None)).count("max_turns"), 1)

    def test_collect_records_the_error_stop_of_a_claude_session(self):
        m = collect_stream([self.CLAUDE_API_ERROR], [])
        self.assertTrue(m["sessions"][0]["stop"].startswith("error: api_error"), m["sessions"])
        self.assertIn("error: api_error", metrics.summary_lines(m)[0])


class TerminationThroughMainTest(PrintedCase):
    """Why a run stopped, as run.main records it in result.json, the baseline row and the printed report."""

    def test_a_finished_run_records_why_it_stopped_everywhere_it_is_reported(self):
        code, result, printed = self.invoke_printed("grok", "done")
        self.assertEqual(code, 0, result)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"], t["sessions"], t["resumes"]), ("exited", 0, 1, 0))
        self.assertEqual((t["session_stops"], t["resume_stop"], t["engine_status"]),
                         (["cancelled"], "ShipLoop run is done", "done"))
        # The row keeps why it stopped; the blocked detail stays in result.json (batch 1011 integration).
        self.assertEqual(self.last_row()["termination"], run.row_termination(t))
        self.assertEqual(self.stopped(printed), "  stopped   host exited rc=0; session stops cancelled; "
                                                "no further resume: ShipLoop run is done; engine done")

    def test_the_result_the_baseline_row_and_the_report_are_wired_to_the_same_records(self):
        code, result, printed = self.invoke_printed("grok", "done")
        row = self.last_row()
        self.assertEqual(result["metrics"]["stages"], [])  # the key is there: a comparison reads it
        self.assertEqual(row["stages"], run.baseline_stages(result["metrics"]["stages"]))
        self.assertEqual(row["unmeasured"], sorted(result["metrics"]["unmeasured"]))
        self.assertEqual(row["sessions"], len(result["process"]["sessions"]))
        self.assertIn("  baseline  nothing compared: no earlier row for hello", printed)

    def test_a_run_that_never_finishes_names_the_stage_and_the_spent_budget(self):
        code, result, printed = self.invoke_printed("grok", "stuck", "--max-resumes", "2")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["sessions"], t["resumes"], t["resume_stop"]), (3, 2, "resume budget spent (2)"))
        self.assertEqual((t["engine_status"], t["engine_unaccepted_stage"]), ("active", "test-refine"))
        self.assertFalse(self.baselines.exists(), "a run left active is not a baseline, so no row carries its termination")
        self.assertEqual(self.stopped(printed),
                         "  stopped   host exited rc=0; session stops cancelled, cancelled, cancelled; "
                         "no further resume: resume budget spent (2); engine active with test-refine never accepted")

    def test_the_last_permitted_resume_that_finishes_the_run_is_not_called_a_spent_budget(self):
        code, result, _ = self.invoke_printed("grok", "resume", "--max-resumes", "1")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["termination"]["sessions"], 2)
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")

    def test_a_run_finished_by_its_only_permitted_session_is_not_called_a_spent_budget(self):
        code, result, _ = self.invoke_printed("grok", "done", "--max-resumes", "0")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")

    def test_a_session_that_names_no_host_session_cannot_be_resumed(self):
        code, result, _ = self.invoke_printed("grok", "anon")
        self.assertEqual(code, 1)
        self.assertEqual(result["termination"]["resume_stop"], "no host session id to resume")
        self.assertEqual(result["termination"]["sessions"], 1)

    def test_a_killed_session_is_unknown_and_the_deadline_is_the_stop(self):
        code, result, printed = self.invoke_printed("grok", "hang", "--timeout", "3")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"]), ("timeout", -9))
        self.assertEqual((t["sessions"], t["session_stops"], t["resume_stop"]),
                         (1, ["unknown"], "run deadline spent"))
        self.assertIn("host timeout rc=-9; session stops unknown", self.stopped(printed))

    def test_session_stops_has_one_entry_per_session_and_unknown_for_a_crashed_one(self):
        code, result, _ = self.invoke_printed("grok", "crash-resumed", "--max-resumes", "2")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual(len(result["process"]["sessions"]), 3)
        self.assertEqual((t["sessions"], t["session_stops"]), (3, ["cancelled", "unknown", "unknown"]))
        self.assertEqual((t["process_status"], t["returncode"]), ("failed", 1))
        self.assertEqual(t["resume_stop"], "resume budget spent (2)")

    def test_with_no_resume_limit_a_host_that_keeps_failing_ends_the_loop_on_the_third_stalled_failure(self):
        """No resume limit is the default (owner 2026-10-24), so a resumed host that can never run (an expired auth, a
        broken binary) would be resumed forever. Three resumed sessions in a row that fail while ShipLoop's revision stands
        still end the loop as the host's failure. The --timeout only keeps a regression from hanging the suite."""
        code, result, _ = self.invoke_printed("grok", "crash-resumed", "--timeout", "300")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual(t["sessions"], 1 + run.RESUME_STALL)
        self.assertEqual(t["resume_stop"], "resumed host failed 3 times in a row with ShipLoop still at revision 25 "
                                           "(last exit code 1)")
        self.assertEqual(result["outcome_class"], "FAILED")

    def test_with_no_resume_limit_a_session_that_ends_without_moving_the_run_is_resumed_three_times_then_stopped(self):
        """The same evidence for a host that exits cleanly: a model that ends every turn with ShipLoop's revision where it
        was would otherwise spend forever. The harness ends that run (STOPPED), and the printed command continues it."""
        code, result, printed = self.invoke_printed("grok", "stuck", "--timeout", "300")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["sessions"], t["resume_stop"]),
                         (1 + run.RESUME_STALL, "resumed host made no ShipLoop progress 3 times in a row (revision 25)"))
        self.assertEqual(result["outcome_class"], "STOPPED")
        self.assertIn("--resume-run", printed)

    def test_claude_is_not_resumable_and_its_own_stop_is_recorded(self):
        code, result, _ = self.invoke_printed("claude", "done")
        self.assertEqual(code, 0, result)
        t = result["termination"]
        self.assertEqual((t["resume_stop"], t["session_stops"]), ("host is not resumable", ["success"]))

    def test_a_claude_api_error_is_recorded_as_an_error_not_a_success(self):
        code, result, printed = self.invoke_printed("claude", "api-error")
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["returncode"]), ("failed", 1))
        self.assertTrue(t["session_stops"][0].startswith("error: api_error"), t["session_stops"])
        self.assertIn("session stops error: api_error", self.stopped(printed))
        self.assertNotIn("session stops success", printed)


class SuiteTmpCheckHostTest(HarnessCase):
    """The suite's /tmp collision check reads the writes of every host's runs, Claude's included."""

    @staticmethod
    def claude_writer(out: Path, target: str) -> Path:
        out.mkdir()
        stream = [{"type": "assistant", "message": {"usage": {"input_tokens": 1}, "content": [
            {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": f"echo x > {target}"}}]}},
            {"type": "result", "subtype": "success", "num_turns": 1}]
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        return out

    @staticmethod
    def grok_writer(out: Path, target: str) -> Path:
        out.mkdir()
        stream = [{"type": "usage", "usage": {"input_tokens": 1}},
                  {"type": "tool_call", "toolCallId": "1", "rawInput": {"command": f"echo x > {target}"}}]
        (out / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in stream))
        return out

    def test_two_claude_runs_that_write_the_same_tmp_name_collide(self):
        outs = [self.claude_writer(self.tmp / name, "/tmp/shared-notes.txt") for name in ("a", "b")]
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/shared-notes.txt": ["a", "b"]})

    def test_a_collision_is_found_across_hosts(self):
        outs = [self.claude_writer(self.tmp / "a", "/tmp/shared-notes.txt"),
                self.grok_writer(self.tmp / "b", "/tmp/shared-notes.txt"),
                self.grok_writer(self.tmp / "c", "/tmp/shared-notes.txt"),
                self.claude_writer(self.tmp / "d", "/tmp/own-notes.txt")]
        self.assertEqual(run.shared_tmp_writes(outs), {"/tmp/shared-notes.txt": ["a", "b", "c"]})

    def test_a_claude_suite_names_a_tmp_collision_and_records_no_unchecked_run(self):
        cases = {"first": {"style": "s", "prompt": "p", "checks": []},
                 "second": {"style": "t", "prompt": "p", "checks": []}}
        for attr, data in (("CASES", cases), ("SUITES", {"wide": {"kind": "breadth", "cases": ["first", "second"]}})):
            path = self.tmp / (attr.lower() + ".json")
            path.write_text(json.dumps(data))
            saved = getattr(run, attr)
            setattr(run, attr, path)
            self.addCleanup(setattr, run, attr, saved)
        os.environ["FAKE_MODE"] = "done"
        os.environ["FAKE_COMMAND"] = "echo x > /tmp/shared-notes.txt"
        self.addCleanup(os.environ.pop, "FAKE_COMMAND", None)
        out, printed = self.tmp / "suite-out", io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--suite", "wide", "--host", "claude", "--backend", "anthropic", "--claude-bin", str(self.fakes["claude"]),
                             "--output", str(out), "--plugin-dir", str(self.plugin),
                             "--baseline", str(self.baselines)])
        self.assertEqual(code, 0, printed.getvalue())
        result = json.loads((out / "suite-result.json").read_text())
        self.assertEqual(result["shared_tmp_writes"], {"/tmp/shared-notes.txt": ["first", "second"]})
        self.assertNotIn("tmp_writes_unmeasured", result)
        self.assertIn("/tmp names written by more than one case", printed.getvalue())
        self.assertNotIn("not checked", printed.getvalue())


class SessionStopSubtypeTest(unittest.TestCase):
    """An error result keeps the subtype the host named, so a turn or budget limit is not a bare 'error' (review 2)."""

    def test_an_error_subtype_is_kept_with_its_first_listed_error(self):
        stop = metrics.session_stop({"type": "result", "subtype": "error_max_turns", "is_error": True,
                                     "errors": ["Reached maximum number of turns (3)"]})
        self.assertEqual(stop, "error: error_max_turns: Reached maximum number of turns (3)")
        self.assertEqual(metrics.session_stop({"type": "result", "subtype": "error_during_execution", "is_error": True}),
                         "error: error_during_execution")
        budget = {"type": "result", "subtype": "error_max_budget_usd", "is_error": True, "terminal_reason": "max_budget"}
        self.assertEqual(metrics.session_stop(budget), "error: error_max_budget_usd max_budget")

    def test_a_success_subtype_with_an_api_error_does_not_repeat_success(self):
        stop = metrics.session_stop({"type": "result", "subtype": "success", "is_error": True,
                                     "terminal_reason": "api_error", "result": "API Error: rate limit"})
        self.assertEqual(stop, "error: api_error: API Error: rate limit")


class StopFileTest(PrintedCase):
    """A requested stop (<output>/stop) ends the host with its records written, and is never a pass."""

    def setUp(self):
        super().setUp()
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)
        patched.start()
        self.addCleanup(patched.stop)

    def sessions(self) -> list[dict]:
        return [json.loads(line) for line in Path(str(self.log) + ".sessions").read_text().splitlines()]

    def stop_when_the_host_runs(self, out: Path, session: int = 1) -> None:
        """Create the stop file once the fake host has started its `session`th session (1 = the first)."""
        def ask():
            sessions = Path(str(self.log) + ".sessions")
            for _ in range(400):
                if sessions.exists() and len(sessions.read_text().splitlines()) >= session:
                    break
                time.sleep(0.05)
            (out / "stop").write_text("")
        threading.Thread(target=ask, daemon=True).start()

    def main(self, out: Path, *extra: str) -> tuple[int, dict, str]:
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.object(
                run, "review_export", return_value="review export: fake") as exporter:
            code = run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines),
                             "--timeout", "30", *extra])
        self.exporter = exporter
        return code, json.loads((out / "result.json").read_text()), printed.getvalue()

    def test_the_stop_file_ends_the_host_and_the_records_are_written_without_a_relaunch(self):
        os.environ["FAKE_MODE"] = "hang-active"
        out = self.tmp / "out-stop"
        self.stop_when_the_host_runs(out)
        code, result, printed = self.main(out)
        self.assertEqual(code, 1, "a requested stop is not a finished run: it must never exit 0")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        t = result["termination"]
        self.assertEqual((t["process_status"], t["sessions"], t["engine_status"]), ("stopped", 1, "active"))
        self.assertEqual(t["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertEqual(len(self.sessions()), 1, "a stopped host is not relaunched")
        self.assertFalse((out / "stop").exists(), "the request is consumed when it is acted on")
        self.assertTrue((out / "metrics.json").is_file())
        self.exporter.assert_called_once()
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")
        self.assertFalse((out / "mismatch.md").exists(), "a requested stop is not a mismatch to explain")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        self.assertIn("host stopped rc=-9", printed)

    def test_a_stop_requested_as_a_session_ends_stops_the_resume_loop_and_reads_as_stopped_everywhere(self):
        os.environ["FAKE_MODE"] = "stuck-stop"
        out = self.tmp / "out-stop-between"
        code, result, printed = self.main(out)
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sessions()), 1, "the loop would otherwise resume up to the cap")
        self.assertEqual(result["termination"]["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertFalse((out / "stop").exists())
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        # The host ended by itself (exit 0) as the request arrived, yet the run reads as stopped in every record, the
        # same as a killed host (SPEC: a requested stop has no process verdict); the session keeps its own status.
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(result["termination"]["process_status"], "stopped")
        # On a busy machine the harness can see the request in the instant before the host has left and then end it
        # itself: the session reads "stopped" and the host's code is -9, and every record above is the same. Either
        # ending is the one under test (the kill is also pinned, deterministically, by the stop-file test above).
        self.assertIn([s["status"] for s in result["process"]["sessions"]], (["exited"], ["stopped"]))
        self.assertRegex(printed, r"host stopped rc=(0|-9)")
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")

    def test_a_stop_during_a_resumed_session_reads_as_stopped_and_is_not_relaunched(self):
        os.environ["FAKE_MODE"] = "hang-resumed"
        out = self.tmp / "out-stop-resumed"
        self.stop_when_the_host_runs(out, session=2)
        code, result, printed = self.main(out, "--timeout", "120")  # a resume needs more than 60 s of the run deadline left
        self.assertEqual(code, 1)
        self.assertEqual(len(self.sessions()), 2, "one session, one resume, and no third launch")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual([s["status"] for s in result["process"]["sessions"]], ["exited", "stopped"])
        self.assertEqual(result["termination"]["resume_stop"], f"stopped by {out.resolve() / 'stop'}")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")
        self.assertFalse((out / "stop").exists())

    def test_a_stop_before_any_engine_state_exists_writes_no_baseline_row_and_no_resume_command(self):
        # The host was killed before ShipLoop wrote any state, so the engine status is unknown: still not a finished run.
        os.environ["FAKE_MODE"] = "hang"
        out = self.tmp / "out-stop-no-state"
        self.stop_when_the_host_runs(out)
        code, result, printed = self.main(out)
        self.assertEqual(code, 1)
        t = result["termination"]
        self.assertEqual((t["process_status"], t["engine_status"]), ("stopped", "unknown"))
        self.assertFalse(self.baselines.exists(), "the row would be offered as the last comparable row")
        self.assertIn("baseline  nothing compared: the run is not finished", printed)
        self.assertEqual(printed.count("--resume-run"), 1, "only the start line: a run with no engine state cannot be resumed")

    def test_a_stale_stop_file_does_not_stop_a_later_resume(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        (out / "stop").write_text("")  # left over from a stop nobody consumed
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "codex", "--allow-host-change", "--codex-bin", str(self.fakes["codex"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(result["termination"]["resume_stop"], "ShipLoop run is done")
        self.assertNotEqual(result["process"]["status"], "stopped")
        self.assertFalse((out / "stop").exists())

    def test_a_stop_never_answers_a_blocked_run(self):
        code, first, _ = self.invoke_printed("grok", "stuck", "--max-resumes", "0")
        out = Path(first["output"])
        shutil.rmtree(out / "work" / ".shiploop")
        (out / "work" / ".shiploop").mkdir()
        run.store.write_record(out / "work" / ".shiploop" / "state.md",
                               {"status": "blocked", "stage": "test-refine", "status_reason": "waiting for a person"})
        (out / "stop").write_text("")
        self.log.unlink(missing_ok=True)
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        result = json.loads((out / "result.json").read_text())
        self.assertFalse(self.log.exists(), "no host was started for a blocked run")
        self.assertEqual(result["shiploop"]["status"], "blocked")
        self.assertNotEqual(result["termination"].get("process_status"), "stopped")
        self.assertFalse((out / "stop").exists(), "the request was cleared at the start, not acted on")


@needs_listeners
class ListenerParseSelectionTest(unittest.TestCase):
    """Which processes the harness stops: read from lsof's field output, chosen by place, and never the harness itself.

    Pure checks over captured output, so they run on a runner with no lsof (the real-process classes skip there)."""

    def test_lsof_field_output_is_parsed_into_pid_ports_cwd_and_argv(self):
        self.assertEqual(listeners.listeners_of(LSOF_LISTENING, 501),
                         [{"pid": 969, "command": "rapportd", "ports": [58318]},
                          {"pid": 2059, "command": "Ollama", "ports": [11434]},
                          {"pid": 63973, "command": "node", "ports": [3457]}], "own user only; one port listed once")
        self.assertEqual(listeners.cwds_of(LSOF_CWD), {2059: "/", 63973: "/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work"})
        self.assertEqual(listeners.argvs_of(PS_COMMANDS)[63973],
                         "node /Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/.shiploop-runs/work-1/worktree/server.js")

        def fake_run(argv):
            return LSOF_LISTENING if "-iTCP" in argv else LSOF_CWD if "cwd" in argv else PS_COMMANDS
        with mock.patch.object(listeners, "_run", side_effect=fake_run), mock.patch.object(listeners.os, "getuid", return_value=501):
            seen = {item["pid"]: item for item in listeners.observe()}
        self.assertEqual(sorted(seen), [969, 2059, 63973])
        self.assertEqual((seen[63973]["ports"], seen[63973]["cwd"]),
                         ([3457], "/Users/dadleet/e2e-runs/20261008/r1-checkers-sonnet/work"))
        self.assertTrue(seen[63973]["argv"].endswith("/worktree/server.js"))
        self.assertEqual((seen[969]["cwd"], seen[969]["argv"]), (None, ""), "a process that vanished between the calls has neither")

    def test_a_name_that_is_not_host_and_port_is_not_a_port_and_never_raises(self):
        # lsof prints host:port for a TCP listener; a name without a colon (an all-digit one included) is no endpoint to list.
        odd = "p1\ncx\nu501\nn123\nnno-colon-here\nn*:80\nnhost:notaport\n"
        self.assertEqual(listeners.listeners_of(odd, 501), [{"pid": 1, "command": "x", "ports": [80]}])

    def test_only_a_listener_inside_the_case_folder_on_a_path_boundary_is_selected(self):
        folder = "/e2e/case-1"
        chosen = [listener(10, "/e2e/case-1/work"), listener(11, "/e2e/case-1"),
                  listener(12, "/", "node /e2e/case-1/.shiploop-runs/x/server.js"),
                  listener(13, "/", "node server.js --root=/e2e/case-1/site"), listener(14, "/e2e/case-1/work/deep/er")]
        left = [listener(20, "/e2e/case-10/work"),
                listener(21, "/", "node /e2e/case-10/server.js"), listener(22, "/", "tail -f /e2e/case-1-other/log"),
                listener(23, "/e2e/case-1/work"), listener(24, None, ""), listener(25, "/", "python3 -m http.server"),
                listener(1, "/e2e/case-1/work"), listener(26, "/e2e")]
        got = {item["pid"] for item in listeners.under(chosen + left, folder, protected={23})}
        self.assertEqual(got, {10, 11, 12, 13, 14}, "pid 23 is protected, pid 1 is never touched, siblings and parents are not inside")

    def test_a_folder_reached_through_a_symlink_is_matched_by_either_spelling(self):
        with tempfile.TemporaryDirectory() as temp:
            real = Path(temp).resolve() / "real"
            (real / "case").mkdir(parents=True)
            link = Path(temp) / "link"
            link.symlink_to(real)
            asked = str(link / "case")  # how the output folder was spelled; lsof reports a cwd as the real path
            by_cwd, by_argv = listener(30, str(real / "case" / "work")), listener(31, "/", f"node {asked}/server.js")
            self.assertEqual({i["pid"] for i in listeners.under([by_cwd, by_argv], asked)}, {30, 31})

    def test_the_harness_and_its_ancestors_are_protected(self):
        parents = {500: 400, 400: 300, 300: 1, 600: 1}
        self.assertEqual(listeners.ancestors(parents, 500), {500, 400, 300})
        self.assertEqual(listeners.ancestors(parents, 999), {999}, "a pid with no parent row is only itself")
        with mock.patch.object(listeners, "_run", return_value="  1 0\n 500 400\n 400 300\n 300 1\n"), \
                mock.patch.object(listeners.os, "getpid", return_value=500):
            self.assertEqual(listeners.protected_pids(), {500, 400, 300})
        with mock.patch.object(listeners, "_run", side_effect=listeners.Unobserved("ps not found")), \
                mock.patch.object(listeners.os, "getpid", return_value=500), mock.patch.object(listeners.os, "getppid", return_value=400):
            self.assertEqual(listeners.protected_pids(), {500, 400}, "no process table: at least this process and its parent")

    def test_a_tool_that_cannot_run_is_unobserved_with_its_reason(self):
        with mock.patch.object(listeners.subprocess, "run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(listeners.Unobserved, "lsof not found"):
                listeners.observe()
        with mock.patch.object(listeners.subprocess, "run",
                               side_effect=listeners.subprocess.TimeoutExpired(["lsof"], listeners.LSOF_TIMEOUT)):
            with self.assertRaisesRegex(listeners.Unobserved, "lsof timed out"):
                listeners.observe()
        failed = subprocess.CompletedProcess(["lsof"], 2, stdout="", stderr="lsof: permission denied\nmore\n")
        with mock.patch.object(listeners.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(listeners.Unobserved, r"lsof exited 2: lsof: permission denied"):
                listeners.observe()
        none_listening = subprocess.CompletedProcess(["lsof"], 1, stdout="", stderr="")
        with mock.patch.object(listeners.subprocess, "run", return_value=none_listening):
            self.assertEqual(listeners.observe(), [], "exit 1 with no output is a measured none")

    def pass_record(self, *reaped: int, survived: tuple = (), observed: bool = True, reason: str | None = None) -> dict:
        if not observed:
            return {"observed": False, "reason": reason}
        return {"observed": True, "reaped": [dict(listener(pid, "/x"), ended_by="SIGTERM") for pid in reaped],
                "survived": [listener(pid, "/x") for pid in survived]}

    def test_the_passes_of_a_run_merge_and_an_unseen_pass_never_reads_as_none(self):
        self.assertIsNone(listeners.merge_left_behind([]), "a regrade ran no pass")
        self.assertIsNone(listeners.merge_left_behind([None, None]))
        merged = listeners.merge_left_behind([self.pass_record(7), self.pass_record(8, survived=(9,)), self.pass_record(survived=(9,))])
        self.assertIsNotNone(merged)
        self.assertEqual(merged["observed"], True)
        self.assertEqual([i["pid"] for i in merged["reaped"]], [7, 8])
        self.assertEqual([i["pid"] for i in merged["survived"]], [9], "one process seen twice is listed once")
        later = listeners.merge_left_behind([self.pass_record(survived=(9,)), self.pass_record(9)])
        self.assertEqual(([i["pid"] for i in later["reaped"]], later["survived"]), ([9], []), "stopped by a later pass: not a survivor")
        nothing = listeners.merge_left_behind([self.pass_record(), self.pass_record()])
        self.assertEqual(nothing, {"observed": True, "reaped": [], "survived": []}, "two passes that looked and found none")
        blind = listeners.merge_left_behind([self.pass_record(observed=False, reason="lsof not found"),
                                             self.pass_record(observed=False, reason="lsof not found")])
        self.assertEqual(blind, {"observed": False, "reason": "lsof not found"}, "no pass looked: no reaped key to read as none")
        partial = listeners.merge_left_behind([self.pass_record(7), self.pass_record(observed=False, reason="lsof timed out after 30s")])
        self.assertIsNotNone(partial)
        self.assertEqual((partial["observed"], partial["reason"]), (False, "lsof timed out after 30s"))
        self.assertEqual([i["pid"] for i in partial["reaped"]], [7], "what the pass that looked found is kept beside the reason")
        again = listeners.merge_left_behind([partial, self.pass_record(8)])  # a resume merges the earlier record with its own
        self.assertIsNotNone(again)
        self.assertEqual(([i["pid"] for i in again["reaped"]], again["observed"]), ([7, 8], False))

    def test_the_printed_line_names_what_was_stopped_and_what_could_not_be_seen(self):
        self.assertIsNone(listeners.left_behind_line(None))
        self.assertIsNone(listeners.left_behind_line({"observed": True, "reaped": [], "survived": []}), "a clean run prints nothing")
        line = listeners.left_behind_line(listeners.merge_left_behind([self.pass_record(7), self.pass_record(survived=(9,))]))
        self.assertEqual(line, "  left      stopped pid 7 x (port 3457) by SIGTERM; could not stop pid 9 x (port 3457)")
        blind = listeners.left_behind_line({"observed": False, "reason": "lsof not found"})
        self.assertEqual(blind, "  left      not observed: lsof not found")


class CaseRunCase(PrintedCase):
    """A harness case that runs one named case into its own folder and returns what the run recorded."""

    def case_main(self, name: str, *extra: str, mode: str = "done", host: str = "claude", env: dict | None = None):
        out = self.tmp / name
        os.environ["FAKE_MODE"] = mode
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), mock.patch.dict(os.environ, env or {}):
            code = run.main(["--host", host, *ANTHROPIC_ROUTE.get(host, ()), f"--{host}-bin", str(self.fakes[host]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
        return code, json.loads((out / "result.json").read_text()), printed.getvalue(), out

    def reaped(self, result: dict) -> list[int]:
        return [i["pid"] for i in (result.get("left_behind") or {}).get("reaped", [])]


class RealListeners:
    """Mixin: tests that start real servers and let the harness stop them, in a world scoped to the test's own folder."""

    def scope_to_tmp(self) -> None:
        """What lsof shows is only what has its working directory under self.tmp, so no other session's server (or a leaked one
        on this machine) can change a result; the real lsof, ps and signals are still used. The scope is checked here, not by
        listeners.under, and a signal to any pid outside it is refused: a defect in the code under test (or a mutant of it) must
        never be able to stop a process of the machine's user that the test did not start."""
        root = os.path.realpath(self.tmp)

        def in_tmp() -> list[dict]:
            return [item for item in REAL_OBSERVE() if item.get("cwd") and (item["cwd"] == root or item["cwd"].startswith(root + os.sep))]

        real_signal = listeners._signal

        def guarded_signal(pid: int, number: int) -> None:
            if pid not in {item["pid"] for item in in_tmp()}:
                raise AssertionError(f"refusing to signal pid {pid}: it is not a listener under the test's own folder")
            real_signal(pid, number)

        for patcher in (mock.patch.object(listeners, "observe", side_effect=in_tmp),
                        mock.patch.object(listeners, "_signal", side_effect=guarded_signal)):
            patcher.start()
            self.addCleanup(patcher.stop)
        isolate_git(self)

    def serve(self, cwd: Path, *flags: str) -> tuple[subprocess.Popen, int]:
        """A listening server whose working directory is `cwd`, as a model leaves one; killed when the test ends."""
        cwd.mkdir(parents=True, exist_ok=True)
        portfile = self.tmp / f"port-{len(list(self.tmp.glob('port-*')))}"
        proc = subprocess.Popen([sys.executable, "-c", LISTENER_SOURCE, str(portfile), *flags], cwd=cwd, start_new_session=True,
                                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(end_quietly, proc)
        for _ in range(200):
            if portfile.exists():
                break
            time.sleep(0.05)
        else:
            raise AssertionError("the test's listener never started")
        proc.portfile = portfile
        return proc, int(portfile.read_text().split()[1])


@needs_lsof
@needs_listeners
class ReapTest(RealListeners, unittest.TestCase):
    """listeners.reap with the real lsof, ps and signals, on servers the test starts."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        self.scope_to_tmp()

    def test_a_folder_with_nothing_under_it_is_a_measured_none(self):
        self.assertEqual(listeners.reap(self.tmp / "empty"), {"observed": True, "reaped": [], "survived": []})

    def test_a_listener_under_the_folder_is_stopped_and_a_sibling_with_the_same_prefix_is_not(self):
        inside, port = self.serve(self.tmp / "case-1" / "work")
        beside, beside_port = self.serve(self.tmp / "case-10" / "work")
        record = listeners.reap(self.tmp / "case-1")
        self.assertEqual([(i["pid"], i["ports"], i["ended_by"]) for i in record.get("reaped", [])], [(inside.pid, [port], "SIGTERM")])
        self.assertEqual(record.get("survived"), [])
        self.assertTrue(refuses_soon(port))
        self.assertTrue(answers(beside_port), "case-10 is not inside case-1")

    def test_a_listener_that_ignores_sigterm_is_killed_after_the_grace(self):
        stubborn, port = self.serve(self.tmp / "case-1", "ignore-term")
        with mock.patch.object(listeners, "GRACE_SECONDS", 0.3):
            record = listeners.reap(self.tmp / "case-1")
        self.assertEqual([(i["pid"], i["ended_by"]) for i in record.get("reaped", [])], [(stubborn.pid, "SIGKILL")])
        self.assertTrue(refuses_soon(port))

    def test_a_listener_that_stays_is_reported_as_survived_and_never_as_reaped(self):
        stays, port = self.serve(self.tmp / "case-1")
        with mock.patch.object(listeners, "_signal"), mock.patch.object(listeners, "GRACE_SECONDS", 0.2), \
                mock.patch.object(listeners, "FORCE_SECONDS", 0.2):
            record = listeners.reap(self.tmp / "case-1")
        self.assertEqual(record.get("reaped"), [])
        self.assertEqual([(i["pid"], i["ports"]) for i in record.get("survived", [])], [(stays.pid, [port])])
        self.assertTrue(answers(port))

    def test_a_world_that_cannot_be_read_is_unobserved_even_for_a_folder_with_a_listener(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            self.assertEqual(listeners.reap(self.tmp / "case-1"), {"observed": False, "reason": "lsof not found"})


@needs_lsof
@needs_listeners
class LeftBehindThroughMainTest(RealListeners, CaseRunCase):
    """What a host or a check leaves listening is stopped, recorded in result.json and printed (SPEC: a run leaves nothing listening)."""

    def setUp(self):
        super().setUp()
        self.scope_to_tmp()

    def test_a_server_a_host_leaves_running_is_stopped_and_recorded(self):
        for host in ("claude", "grok"):
            with self.subTest(host=host):
                portfile = self.tmp / f"leak-{host}"
                self.addCleanup(kill_leaked, portfile)
                code, result, printed, out = self.case_main(f"case-{host}", host=host, env={"FAKE_LISTEN": str(portfile)})
                pid, port = map(int, portfile.read_text().split())
                self.assertEqual(code, 0, result)
                self.assertIn("left_behind", result)
                left = result.get("left_behind", {})
                self.assertEqual(left.get("observed"), True, left)
                self.assertEqual([(i["pid"], i["ports"], i["ended_by"]) for i in left.get("reaped", [])], [(pid, [port], "SIGTERM")])
                self.assertEqual([i["cwd"] for i in left.get("reaped", [])], [str((out / "work").resolve())])
                self.assertEqual(left.get("survived"), [])
                self.assertTrue(refuses_soon(port), "the server no longer answers")
                self.assertRegex(printed, rf"(?m)^  left      stopped pid {pid} .*\(port {port}\) by SIGTERM$")
                self.assertTrue(result["pass"], "a leftover is a record, not a verdict")

    def test_a_clean_run_records_a_measured_none_and_prints_no_left_line(self):
        code, result, printed, out = self.case_main("case-clean")
        self.assertEqual(result.get("left_behind"), {"observed": True, "reaped": [], "survived": []})
        self.assertNotRegex(printed, r"(?m)^  left ")

    def test_listeners_outside_the_case_folder_are_left_alone(self):
        portfile = self.tmp / "leak"
        self.addCleanup(kill_leaked, portfile)
        elsewhere, elsewhere_port = self.serve(self.tmp / "elsewhere")
        sibling, sibling_port = self.serve(self.tmp / "case-10" / "work")  # shares a name prefix with the case folder
        code, result, printed, out = self.case_main("case-1", env={"FAKE_LISTEN": str(portfile)})
        self.assertEqual(self.reaped(result), [int(portfile.read_text().split()[0])])
        self.assertTrue(answers(elsewhere_port) and answers(sibling_port))

    def test_a_listener_a_check_leaves_is_stopped_after_the_checks(self):
        portfile = self.tmp / "leak-check"
        self.addCleanup(kill_leaked, portfile)
        spawner = ("import os, subprocess, sys, time\n"
                   f"subprocess.Popen([sys.executable, '-c', {LISTENER_SOURCE!r}, {str(portfile)!r}], start_new_session=True,\n"
                   "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                   f"while not os.path.exists({str(portfile)!r}):\n    time.sleep(0.05)\n")
        check = f"{shlex.quote(sys.executable)} -c {shlex.quote(spawner)}"
        code, result, printed, out = self.case_main("case-check", "--prompt", "say hello", "--check", check)
        pid, port = map(int, portfile.read_text().split())
        self.assertEqual(self.reaped(result), [pid], "the session ended before the check started it")
        self.assertTrue(refuses_soon(port))
        self.assertTrue(all(c["pass"] for c in result["checks"]), result["checks"])

    def test_launch_reaps_when_its_session_ends_and_returns_the_record(self):
        portfile = self.tmp / "leak-launch"
        self.addCleanup(kill_leaked, portfile)
        out = self.tmp / "case-launch"
        (out / "work").mkdir(parents=True)
        spawner = ("import os, subprocess, sys, time\n"
                   f"subprocess.Popen([sys.executable, '-c', {LISTENER_SOURCE!r}, {str(portfile)!r}], start_new_session=True,\n"
                   "                 stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                   f"while not os.path.exists({str(portfile)!r}):\n    time.sleep(0.05)\n")
        session = run.launch([sys.executable, "-c", spawner], out / "work", out, dict(os.environ), 60, watch=False)
        pid, port = map(int, portfile.read_text().split())
        self.assertEqual(session["status"], "exited")
        self.assertEqual(self.reaped(session), [pid])
        self.assertTrue(refuses_soon(port))

    def test_a_regrade_and_grade_only_reap_nothing_and_keep_the_earlier_record(self):
        code, first, _, out = self.case_main("case-done")
        live = listeners.hold_case(out)  # a live host means a live harness: without the lock this folder would look like a leak to other launches
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        proc, port = self.serve(out / "work")  # something a live host could be serving: a regrade starts no host and must not touch it
        recorded = first.get("left_behind")
        self.assertIsNotNone(recorded, "the run being regraded recorded what it left behind")
        for extra in ((), ("--grade-only",)):
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
            self.assertTrue(answers(port), f"a regrade {extra} reaped")
            self.assertEqual(json.loads((out / "result.json").read_text()).get("left_behind"), recorded)
        old = json.loads((out / "result.json").read_text())
        old.pop("left_behind", None)  # a result written before the key existed
        (out / "result.json").write_text(json.dumps(old))
        with contextlib.redirect_stdout(io.StringIO()):
            run.main(["--resume-run", str(out), "--grade-only", "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertNotIn("left_behind", json.loads((out / "result.json").read_text()), "not recorded is not none")
        self.assertTrue(answers(port))

    def test_a_world_that_cannot_be_read_is_recorded_as_unobserved_and_the_run_is_not_failed(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            code, result, printed, out = self.case_main("case-blind")
        self.assertEqual(code, 0, result)
        self.assertEqual(result.get("left_behind"), {"observed": False, "reason": "lsof not found"})
        self.assertIn("  left      not observed: lsof not found", printed)

    def test_a_resume_stops_what_the_earlier_invocation_left_before_its_host_starts(self):
        code, first, _, out = self.case_main("case-resume", "--max-resumes", "0", mode="stuck", host="grok")
        self.assertEqual(first["shiploop"]["status"], "active")
        orphan, port = self.serve(out / "work")  # a model's server that outlived a killed harness
        self.log.unlink()
        Path(str(self.log) + ".probe").unlink(missing_ok=True)
        os.environ["FAKE_MODE"] = "done"
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": None,
                    "shiploop_version": None, "unreleased": [], "ci": "success"}  # a resume on its own install checks main's state
        with contextlib.redirect_stdout(io.StringIO()), mock.patch.dict(os.environ, {"FAKE_PROBE_PORT": str(orphan.portfile)}), \
                mock.patch.object(run, "released_versions", return_value=released):
            run.main(["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out),
                      "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        self.assertEqual(Path(str(self.log) + ".probe").read_text().split(), ["refused"], "gone before the new session began")
        result = json.loads((out / "result.json").read_text())
        self.assertEqual(self.reaped(result), [orphan.pid])


@needs_listeners
class CaseLockTest(unittest.TestCase):
    """A case's harness is alive exactly while it holds an exclusive lock on <output>/.harness-lock; the kernel drops it on any death."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name).resolve()

    def case(self, name: str) -> Path:
        folder = self.tmp / name
        (folder / "work").mkdir(parents=True)
        (folder / "invocation.json").write_text("{}")
        return folder

    def test_a_case_folder_is_the_nearest_ancestor_with_an_invocation_record_and_a_work_directory(self):
        folder = self.case("case-1")
        self.assertEqual(listeners.case_folder(folder / "work" / "deep" / "server.js"), folder)
        self.assertEqual(listeners.case_folder(folder), folder)
        self.assertIsNone(listeners.case_folder(self.tmp / "elsewhere" / "a"))
        (self.tmp / "half").mkdir()
        (self.tmp / "half" / "invocation.json").write_text("{}")  # a record without a work directory is not a case
        self.assertIsNone(listeners.case_folder(self.tmp / "half" / "x"))

    def test_the_lock_is_held_while_its_file_is_open_and_a_second_holder_gets_none(self):
        folder = self.case("case-1")
        self.assertFalse(listeners.case_alive(folder), "no lock file: no live harness")
        self.assertFalse((folder / ".harness-lock").exists(), "looking creates nothing in a folder the run does not own")
        held = listeners.hold_case(folder)
        self.assertIsNotNone(held)
        self.assertTrue(listeners.case_alive(folder), "a second open file description in this very process sees it held")
        self.assertIsNone(listeners.hold_case(folder), "one harness per case folder; the second gets None, not an exception (main refuses on it)")
        held.close()
        self.assertFalse(listeners.case_alive(folder))
        self.assertIsNone(listeners.hold_case(self.tmp / "no-such-folder"), "never raises")

    def test_the_kernel_drops_the_lock_when_its_holder_is_killed(self):
        folder = self.case("case-1")
        holder = subprocess.Popen([sys.executable, "-c", "import fcntl, sys, time\nf = open(sys.argv[1], 'a')\n"
                                   "fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)\nprint('held', flush=True)\ntime.sleep(60)\n",
                                   str(folder / ".harness-lock")], stdout=subprocess.PIPE, text=True)
        self.addCleanup(end_quietly, holder)
        self.assertEqual(holder.stdout.readline().strip(), "held")
        self.assertTrue(listeners.case_alive(folder))
        holder.kill()
        holder.wait()
        self.assertFalse(listeners.case_alive(folder), "a SIGKILLed harness leaves no lock behind")

    def test_stale_lists_the_listeners_of_ended_cases_other_than_its_own(self):
        alive, ended, own = self.case("alive"), self.case("ended"), self.case("own")
        held = listeners.hold_case(alive)
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        items = [listener(900001, str(ended / "work"), "node server.js"),
                 listener(900002, str(alive / "work"), "node server.js"),
                 listener(900003, str(own / "work"), "node server.js"),
                 listener(900004, "/", f"node {ended}/.shiploop-runs/x/server.js"),
                 listener(900005, "/", "node unrelated.js"),
                 listener(900006, str(ended / "work"), "node protected.js")]
        with mock.patch.object(listeners, "observe", return_value=items), \
                mock.patch.object(listeners, "protected_pids", return_value={900006}):
            found = listeners.stale(own)
            everything = listeners.stale(None)
        self.assertEqual({(i["pid"], i["case"]) for i in found}, {(900001, str(ended)), (900004, str(ended))},
                         "a live harness, the run's own folder, an unrelated process and a protected pid are not stale")
        self.assertEqual({i["pid"] for i in everything}, {900001, 900003, 900004}, "with no folder of its own, the own case is stale too")


@needs_listeners
class StalePreflightThroughMainTest(CaseRunCase):
    """A launch is refused, whole, while another case leaves a listener and its harness is not alive (SPEC: a run leaves nothing listening)."""

    def setUp(self):
        super().setUp()
        isolate_git(self)
        patched = mock.patch.object(run, "POLL_SECONDS", 0.2, create=True)
        patched.start()
        self.addCleanup(patched.stop)

    def ended_case(self, name: str = "case-old") -> Path:
        folder = self.tmp / name
        (folder / "work").mkdir(parents=True)
        (folder / "invocation.json").write_text("{}")
        return folder

    def leaking(self, folder: Path, pid: int = 900001) -> mock._patch:
        return mock.patch.object(listeners, "observe", return_value=[listener(pid, str(folder / "work"), "node server.js", (3457,))])

    def test_a_launch_is_refused_while_an_ended_case_leaves_a_listener_and_no_host_starts(self):
        ended = self.ended_case()
        with self.leaking(ended), self.assertRaises(SystemExit) as refused:
            self.case_main("case-new")
        for part in ("pid 900001", "port 3457", str(ended), "kill 900001"):
            self.assertIn(part, str(refused.exception))
        self.assertFalse(self.log.exists(), "no host started")
        self.assertFalse((self.tmp / "case-new").exists(), "a refused launch leaves no output folder behind")

    def test_preflight_only_refuses_the_same_way_and_a_clean_machine_passes(self):
        ended = self.ended_case()
        for leaks, want in ((True, 1), (False, 0)):
            printed = io.StringIO()
            with (self.leaking(ended) if leaks else mock.patch.object(listeners, "observe", return_value=[])), \
                    mock.patch.object(run, "marketplace_preflight", return_value=(self.plugin, None, {"gate": []})), \
                    contextlib.redirect_stdout(printed):
                code = run.main(["--preflight-only", "--host", "claude", "--backend", "anthropic", "--output", str(self.tmp / f"pf-{leaks}")])
            self.assertEqual(code, want, printed.getvalue())
            self.assertEqual("kill 900001" in printed.getvalue(), leaks)

    def test_a_case_whose_harness_is_alive_is_not_stale_even_in_the_same_process(self):
        ended = self.ended_case()
        held = listeners.hold_case(ended)  # what a sibling case of a parallel suite holds
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        with self.leaking(ended):
            code, result, printed, out = self.case_main("case-new")
        self.assertEqual(code, 0, result)

    def resume_argv(self, out: Path, *extra: str) -> list[str]:
        return ["--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--resume-run", str(out), "--plugin-dir", str(self.plugin),
                "--baseline", str(self.baselines), *extra]

    def test_a_second_harness_for_a_case_whose_harness_is_alive_is_refused_and_touches_nothing(self):
        code, first, _, out = self.case_main("case-live", "--max-resumes", "0", mode="stuck", host="grok")
        self.assertEqual(first["shiploop"]["status"], "active")
        live = listeners.hold_case(out)  # the harness that is running this case
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        (out / "stop").write_text("")  # its owner has asked it to end
        self.log.unlink()
        reaped: list = []
        released = {"origin_main": "a" * 40, "local_head": "a" * 40, "local_behind_main": False, "catalog_version": None,
                    "shiploop_version": None, "unreleased": [], "ci": "success"}
        with mock.patch.object(listeners, "reap", side_effect=lambda folder: reaped.append(folder)), \
                mock.patch.object(run, "released_versions", return_value=released), \
                contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            run.main(self.resume_argv(out))
        self.assertIn("another harness is running", str(refused.exception))
        self.assertIn(str(out), str(refused.exception))
        self.assertTrue((out / "stop").exists(), "the stop request belongs to the harness that is running")
        self.assertFalse(self.log.exists(), "no host started")
        self.assertEqual(reaped, [], "the live harness's servers are not this invocation's to stop")

    def test_a_regrade_of_a_case_whose_harness_is_alive_is_not_refused_and_leaves_its_stop_request(self):
        code, first, _, out = self.case_main("case-done")
        live = listeners.hold_case(out)
        self.assertIsNotNone(live)
        self.addCleanup(live.close)
        (out / "stop").write_text("")
        for extra in ((), ("--grade-only",)):
            with contextlib.redirect_stdout(io.StringIO()):
                run.main(self.resume_argv(out, *extra))
            self.assertTrue(json.loads((out / "result.json").read_text())["process"]["regraded"], extra)
            self.assertTrue((out / "stop").exists(), f"a regrade {extra} starts nothing, so it owns no stop request")

    def test_a_regrade_is_never_refused_because_it_starts_nothing(self):
        code, first, _, out = self.case_main("case-done")
        ended = self.ended_case()
        for extra in ((), ("--grade-only",)):
            with self.leaking(ended), contextlib.redirect_stdout(io.StringIO()):
                run.main(["--resume-run", str(out), "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines), *extra])
            self.assertTrue(json.loads((out / "result.json").read_text())["process"]["regraded"], extra)

    def test_a_listener_that_cannot_be_looked_for_is_noted_and_the_launch_goes_ahead(self):
        with mock.patch.object(listeners, "observe", side_effect=listeners.Unobserved("lsof not found")):
            code, result, printed, out = self.case_main("case-new")
        self.assertEqual(code, 0, result)
        self.assertIn("stale-listener check skipped: lsof not found", printed)

    def test_the_harness_holds_its_case_lock_while_it_runs_and_drops_it_when_it_ends(self):
        out = self.tmp / "case-lock"
        seen: list[bool] = []

        def watch():
            sessions = Path(str(self.log) + ".sessions")
            for _ in range(400):
                if sessions.exists():
                    break
                time.sleep(0.05)
            seen.append(listeners.case_alive(out))
            (out / "stop").write_text("")

        threading.Thread(target=watch, daemon=True).start()
        code, result, printed, _ = self.case_main("case-lock", "--timeout", "30", mode="hang-active", host="grok")
        self.assertEqual(seen, [True], "alive while the host runs")
        self.assertFalse(listeners.case_alive(out), "dropped when main returns")

    def test_a_suite_refuses_once_before_any_case_starts_and_its_cases_do_not_check_again(self):
        SuiteTest.use_catalog(self, {"a": {"style": "s", "prompt": "p", "checks": []}, "b": {"style": "t", "prompt": "p", "checks": []}},
                              {"wide": {"kind": "breadth", "cases": ["a", "b"]}})
        ended = self.ended_case()
        os.environ["FAKE_MODE"] = "done"
        argv = ["--suite", "wide", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(self.tmp / "suite-out"),
                "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)]
        with self.leaking(ended), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as refused:
            run.main(argv)
        self.assertIn("kill 900001", str(refused.exception))
        self.assertFalse((self.tmp / "suite-out").exists(), "refused before the suite's folder or any case existed")
        self.assertFalse(self.log.exists())
        # A case the suite starts has been checked by the suite, once: it must not raise inside a worker thread.
        with self.leaking(ended):
            code, result, printed, out = self.case_main("case-in-suite", "--case", "a", "--suite-name", "wide")
        self.assertEqual(code, 0, result)


@needs_lsof
@needs_listeners
class StaleListenerRealTest(RealListeners, CaseRunCase):
    """The same refusal against a real server and the real lsof."""

    def setUp(self):
        super().setUp()
        self.scope_to_tmp()

    def test_a_real_server_an_ended_case_left_refuses_the_launch_and_is_never_stopped_by_the_refusal(self):
        ended = self.tmp / "case-old"
        leaked, port = self.serve(ended / "work")
        # The one state this test is about is a case with no live harness, which another session's real launch would also refuse
        # on: so the case record is written last and the lock taken as soon as the refusal is seen, a window of one scan.
        (ended / "invocation.json").write_text("{}")
        with self.assertRaises(SystemExit) as refused:
            self.case_main("case-new")
        held = listeners.hold_case(ended)
        self.assertIsNotNone(held)
        self.addCleanup(held.close)
        for part in (f"pid {leaked.pid}", f"port {port}", str(ended), f"kill {leaked.pid}"):
            self.assertIn(part, str(refused.exception))
        self.assertTrue(answers(port), "a refusal names the process and leaves it to the owner")
        code, result, _, _ = self.case_main("case-new")
        self.assertEqual(code, 0, result)
        self.assertTrue(answers(port), "the other case's server is not this run's to stop")


class TerminationSignalTest(CaseRunCase):
    """The harness as a task runner meets it: a program that is sent a signal while its host works.

    The harness runs as a real subprocess (python3 run.py), so the signal wiring under __main__ is the one tested, and the test
    process's own handlers are never touched. A fake `lsof` first on PATH shows an empty process table, so no real listener of
    this machine can refuse or change a run."""

    def setUp(self):
        super().setUp()
        isolate_git(self)
        self.home = self.tmp / "home"
        (self.home / ".grok").mkdir(parents=True)
        (self.home / ".grok" / "auth.json").write_text("{}")
        tools = self.tmp / "tools"
        tools.mkdir()
        (tools / "lsof").write_text("#!/bin/sh\nexit 1\n")
        (tools / "lsof").chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home), PATH=f"{tools}{os.pathsep}{os.environ['PATH']}", FAKE_LOG=str(self.log),
                        FAKE_MODE="hang-active", SHIPLOOP_PROGRESS="off")

    # What the task runner's child starts with is not what this test process inherited: a job a shell started in the background
    # has SIGINT ignored (and one under nohup has SIGHUP ignored), and Python installs no Ctrl-C handler for an ignored SIGINT.
    # The harness is started through this, which sets the named signals to their defaults first and keeps the rest as inherited.
    DEFAULT_SIGNALS = ("import os, signal, sys\n[signal.signal(getattr(signal, n), signal.SIG_DFL) for n in sys.argv[1].split(',') if n]\n"
                       "os.execv(sys.executable, [sys.executable] + sys.argv[2:])\n")

    def start(self, name: str, *extra: str, launcher: tuple = (), reset: str = "SIGINT,SIGTERM,SIGHUP") -> tuple[subprocess.Popen, Path]:
        out = self.tmp / name
        proc = subprocess.Popen([*launcher, sys.executable, "-c", self.DEFAULT_SIGNALS, reset, str(run.HERE / "run.py"), "--host", "grok",
                                 "--grok-bin", str(self.fakes["grok"]), "--output", str(out), "--plugin-dir", str(self.plugin),
                                 "--baseline", str(self.baselines), "--timeout", "120", *extra],
                                env=self.env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Registered before the harness's own kill, so it runs after it: a harness that is still alive would start another host.
        self.addCleanup(self.kill_hosts)
        self.addCleanup(end_quietly, proc)
        return proc, out

    def kill_hosts(self) -> None:
        """Every host the harness ever started in this test (the fake logs one line per session), whole group, whatever the code
        under test did: a test that fails must not leave an orphan host (each also sleeps for at most 600 s)."""
        sessions = Path(str(self.log) + ".sessions")
        for line in sessions.read_text().splitlines() if sessions.exists() else []:
            with contextlib.suppress(ValueError, KeyError, ProcessLookupError, PermissionError):
                pid = json.loads(line)["pid"]
                if os.getpgid(pid) == pid:  # a host leads the session it was started in; a reused pid does not
                    os.killpg(pid, signal.SIGKILL)

    def host_pid(self) -> int:
        """The fake host's pid, once it is running."""
        sessions = Path(str(self.log) + ".sessions")
        for _ in range(600):
            if sessions.exists() and sessions.read_text().strip():
                break
            time.sleep(0.05)
        else:
            raise AssertionError("the host never started")
        return json.loads(sessions.read_text().splitlines()[0])["pid"]

    @staticmethod
    def kill_pid(pid: int) -> None:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, 9)

    @staticmethod
    def gone(pid: int, seconds: float = 5.0) -> bool:
        end = time.time() + seconds
        while time.time() < end:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.05)
        return False

    def test_sigterm_kills_the_host_writes_the_records_and_reads_as_stopped(self):
        proc, out = self.start("case-term")
        host = self.host_pid()
        proc.send_signal(signal.SIGTERM)
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue(self.gone(host), "the host does not outlive its harness")
        self.assertEqual(proc.returncode, 1, printed)
        self.assertTrue((out / "result.json").is_file(), printed)
        result = json.loads((out / "result.json").read_text())
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(result["termination"]["resume_stop"], "terminated by SIGTERM")
        self.assertTrue((out / "metrics.json").is_file())
        self.assertFalse(self.baselines.exists(), "a stopped run is not a baseline")
        self.assertEqual(len(Path(str(self.log) + ".sessions").read_text().splitlines()), 1, "a terminated host is not relaunched")
        self.assertRegex(printed, r"(?m)^STOPPED  shiploop e2e case=")

    def test_sighup_ends_the_run_the_same_way_unless_the_launch_ignored_it(self):
        proc, out = self.start("case-hup")
        host = self.host_pid()
        proc.send_signal(signal.SIGHUP)
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue(self.gone(host))
        self.assertEqual(proc.returncode, 1, printed)
        self.assertEqual(json.loads((out / "result.json").read_text())["termination"]["resume_stop"], "terminated by SIGHUP")

    @unittest.skipUnless(shutil.which("nohup"), "needs nohup")
    def test_a_nohup_launch_keeps_its_run_through_a_hangup(self):
        proc, out = self.start("case-nohup", launcher=("nohup",), reset="SIGINT,SIGTERM")  # nohup's own SIGHUP is ignored; keep it so
        host = self.host_pid()
        proc.send_signal(signal.SIGHUP)  # the terminal went away; nohup's whole purpose is that the run does not
        time.sleep(1.5)
        self.assertIsNone(proc.poll(), "the harness ended on a hangup that its launch ignored")
        self.assertFalse(self.gone(host, 0.1), "the host was killed by a hangup that its launch ignored")
        proc.send_signal(signal.SIGTERM)  # an explicit stop still works
        printed, _ = proc.communicate(timeout=60)
        self.assertTrue((out / "result.json").is_file(), printed)
        self.assertEqual(json.loads((out / "result.json").read_text())["termination"]["resume_stop"], "terminated by SIGTERM", printed)

    def test_a_second_signal_ends_the_harness_at_once_even_while_a_check_runs(self):
        marker, pidfile = self.tmp / "check-started", self.tmp / "check-pid"
        proc, out = self.start("case-twice", "--prompt", "say hello", "--check", f"echo $$ > {pidfile}; touch {marker}; exec sleep 20")
        self.host_pid()
        proc.send_signal(signal.SIGTERM)  # ends the host; the harness goes on to its checks
        for _ in range(600):
            if marker.exists():
                break
            time.sleep(0.05)
        self.addCleanup(lambda: pidfile.exists() and self.kill_pid(int(pidfile.read_text())))
        self.assertTrue(marker.exists(), "the harness reached its checks after the first signal")
        proc.send_signal(signal.SIGTERM)  # the person means it
        proc.communicate(timeout=30)
        self.assertEqual(proc.returncode, -signal.SIGTERM)

    def test_ctrl_c_on_a_suite_ends_its_hosts_at_once_and_writes_the_records(self):
        # A suite runs its cases in worker threads and a Ctrl-C reaches only the main thread, which then waits for them: without
        # its own handling the hosts ran on (the review saw them alive 40 s later) because the atexit kill comes after that wait.
        proc, out = self.start("suite-int", "--suite", "smoke")
        host = self.host_pid()
        proc.send_signal(signal.SIGINT)
        try:
            printed, _ = proc.communicate(timeout=45)
        except subprocess.TimeoutExpired:
            self.fail("the suite kept running after a Ctrl-C")
        self.assertTrue(self.gone(host), "the host does not outlive a Ctrl-C of its suite")
        self.assertEqual(proc.returncode, 1, printed)
        self.assertEqual([(r["case"], r["pass"]) for r in json.loads((out / "suite-result.json").read_text())["cases"]], [("hello", False)])
        result = json.loads((out / "hello" / "result.json").read_text())
        self.assertEqual((result["process"]["status"], result["termination"]["resume_stop"]), ("stopped", "terminated by SIGINT"))
        self.assertEqual(len(Path(str(self.log) + ".sessions").read_text().splitlines()), 1, "a terminated host is not relaunched")

    def test_ctrl_c_leaves_no_host_behind(self):
        proc, out = self.start("case-int")
        host = self.host_pid()
        proc.send_signal(signal.SIGINT)
        printed, _ = proc.communicate(timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertTrue(self.gone(host), "a Ctrl-C on the harness must not orphan its host")
        self.assertFalse((out / "result.json").exists(), "a Ctrl-C on a single case writes no records (the README says so)")


@needs_listeners
class LiveHostTest(unittest.TestCase):
    """The harness's bookkeeping of the hosts it started, driven without any real signal.

    The poll interval is long here, so a session can only end promptly because the harness killed its group, not because the
    poll loop noticed."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        for patcher in (mock.patch.object(listeners, "observe", return_value=[]), mock.patch.object(run, "POLL_SECONDS", 30, create=True)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        self.addCleanup(run.end_live_hosts)  # runs first: a failing test leaves no host (each also sleeps for at most 20 s)

    def session(self, name: str) -> tuple[threading.Thread, dict, Path]:
        out = self.tmp / name
        (out / "work").mkdir(parents=True)
        result: dict = {}
        thread = threading.Thread(target=lambda: result.update(run.launch(
            [sys.executable, "-c", "import time; time.sleep(20)"], out / "work", out, dict(os.environ), 60, watch=False)))
        thread.start()
        return thread, result, out

    @staticmethod
    def registered(count: int) -> bool:
        for _ in range(100):
            if len(run.LIVE_HOST_GROUPS) == count:
                return True
            time.sleep(0.05)
        return False

    def test_end_live_hosts_kills_every_registered_group_and_launch_discards_its_own(self):
        threads = [self.session(f"case-{n}") for n in range(2)]
        self.assertTrue(self.registered(2), "each running session is registered")
        groups = sorted(run.LIVE_HOST_GROUPS)
        run.end_live_hosts()
        for thread, result, _ in threads:
            thread.join(timeout=15)
            self.assertFalse(thread.is_alive(), "the session ended at once, not at the next poll")
            self.assertEqual(result["status"], "failed")  # no one asked for a stop: only the groups were killed
        self.assertEqual(run.LIVE_HOST_GROUPS, set(), "a session that ended is no longer registered, so a reused pgid is never signalled")
        for pid in groups:
            with self.assertRaises(ProcessLookupError):
                os.killpg(pid, 0)

    def test_a_termination_ends_a_running_session_at_once_as_stopped_and_starts_no_later_one(self):
        thread, result, out = self.session("case-running")
        self.assertTrue(self.registered(1))
        run.on_termination(signal.SIGTERM, None)
        thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "the handler killed the group; the 30 s poll did not have to notice")
        self.assertEqual(result.get("status"), "stopped", result)
        self.assertTrue(run.TERMINATION.is_set())
        self.assertEqual(run.TERMINATED_BY, ["SIGTERM"])

    def test_a_session_that_begins_after_the_harness_was_told_to_end_is_ended_at_its_first_poll(self):
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()  # say, during the install, before any host
        later = self.tmp / "case-later"
        (later / "work").mkdir(parents=True)
        started = time.time()
        after = run.launch([sys.executable, "-c", "import time; time.sleep(20)"], later / "work", later, dict(os.environ), 60, watch=False)
        self.assertEqual(after["status"], "stopped")
        self.assertLess(time.time() - started, 10, "it did not run to its end")
        self.assertEqual(run.LIVE_HOST_GROUPS, set())
        self.assertTrue((later / "events.jsonl").is_file(), "the session's files exist so the records can be written")

    def test_a_signal_that_arrives_before_the_host_is_registered_still_ends_it(self):
        real_popen = subprocess.Popen

        def popen_then_signal(*args, **kwargs):
            proc = real_popen(*args, **kwargs)
            run.on_termination(signal.SIGTERM, None)  # the handler runs now and cannot know this group yet
            return proc

        with mock.patch.object(run.subprocess, "Popen", side_effect=popen_then_signal):
            thread, result, out = self.session("case-race")
            thread.join(timeout=15)
        self.assertFalse(thread.is_alive(), "the poll loop must notice the termination and end the group")
        self.assertEqual(result.get("status"), "stopped")


class SignalledHarnessThroughMainTest(CaseRunCase):
    def test_a_suite_told_to_end_starts_no_further_case(self):
        SuiteTest.use_catalog(self, {"a": {"style": "s", "prompt": "p", "checks": []}, "b": {"style": "t", "prompt": "p", "checks": []}},
                              {"wide": {"kind": "breadth", "cases": ["a", "b"]}})
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()
        out = self.tmp / "suite-out"
        os.environ["FAKE_MODE"] = "done"
        with contextlib.redirect_stdout(io.StringIO()):
            code = run.main(["--suite", "wide", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        rows = json.loads((out / "suite-result.json").read_text())["cases"]
        self.assertEqual(code, 1)
        self.assertEqual([(r["case"], r.get("skipped")) for r in rows], [("a", "terminated by SIGTERM"), ("b", "terminated by SIGTERM")])
        self.assertFalse(self.log.exists(), "no host started")

    def test_a_batch_suite_told_to_end_skips_its_gate_and_the_cases_behind_it(self):
        SuiteTest.use_catalog(self, {"g": {"style": "s", "prompt": "p", "checks": []}, "a": {"style": "t", "prompt": "p", "checks": []}},
                              {"b": {"kind": "batch", "gate": ["g"], "cases": ["a"]}})
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        run.TERMINATED_BY.append("SIGTERM")
        run.TERMINATION.set()
        out = self.tmp / "suite-out"
        os.environ["FAKE_MODE"] = "done"
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = run.main(["--suite", "b", "--host", "grok", "--grok-bin", str(self.fakes["grok"]), "--output", str(out),
                             "--plugin-dir", str(self.plugin), "--baseline", str(self.baselines)])
        rows = json.loads((out / "suite-result.json").read_text())["cases"]
        self.assertEqual(code, 1)
        self.assertEqual(rows, [{"case": "g", "pass": False, "skipped": "terminated by SIGTERM", "gate": True},
                                {"case": "a", "skipped": "the gate failed"}])
        self.assertIn("gate failed (g)", printed.getvalue())
        self.assertFalse(self.log.exists(), "no host started, not even the gate's")

    def test_a_signal_as_a_session_ends_stops_the_resume_loop_without_a_phantom_session(self):
        self.addCleanup(run.TERMINATION.clear)
        self.addCleanup(run.TERMINATED_BY.clear)
        calls: list[int] = []

        def host_that_ends_as_the_signal_arrives(argv, work, out, *args, **kwargs):
            calls.append(1)
            for name in ("events.jsonl", "stderr.txt", "timeline.jsonl"):
                (out / name).write_text("")
            run.TERMINATED_BY.append("SIGHUP")
            run.TERMINATION.set()
            return {"status": "exited", "returncode": 0, "elapsed_seconds": 1.0, "stop": None, "left_behind": None}

        with mock.patch.object(run, "launch", side_effect=host_that_ends_as_the_signal_arrives):
            code, result, printed, out = self.case_main("case-between", host="grok")
        self.assertEqual(len(calls), 1, "no second session is started or recorded for a harness that was told to end")
        self.assertEqual(result["termination"]["resume_stop"], "terminated by SIGHUP")
        self.assertEqual((result["process"]["status"], result["process"]["pass"]), ("stopped", None))
        self.assertEqual(len(result["process"]["sessions"]), 1)
        self.assertEqual(code, 1)


class LeftBehindReadmeTest(unittest.TestCase):
    def test_the_readme_says_what_the_harness_does_with_a_leftover_listener(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("stops every TCP listener of your user whose working directory or command line lies under the case's output folder",
                       "`left_behind` in `result.json`", "never reads as none", "do not serve a case folder by hand while its run ends"):
            self.assertIn(phrase, readme)
        self.assertNotIn("nothing looks for what the host left behind", readme)

    def test_the_readme_says_when_a_launch_is_refused_and_how_liveness_is_known(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("A launch is refused while a listener sits under another case's output folder",
                       "`<output>/.harness-lock`", "no override", "stop it by pid with `kill <pid>`",
                       "A `--resume-run` of a case whose harness is running is refused too",
                       "A harness started before the lock existed holds none, so a launch refuses its listeners as stale while it is still running"):
            self.assertIn(phrase, readme)

    def test_the_operator_contract_in_the_module_docstring_names_signals_left_behind_and_the_refusals(self):
        doc = " ".join(run.__doc__.split())
        for phrase in ("A SIGTERM or SIGHUP to the harness", "`left_behind`", "A launch is refused while", "--resume-run of a case whose harness is running"):
            self.assertIn(phrase, doc)

    def test_the_readme_says_to_run_compared_runs_one_after_the_other_and_what_that_cannot_promise(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("Run the runs you compare one after the other", "`--serial` for a suite",
                       "The suite default of 3 parallel chains stays", "carries `overlapped_runs`", "a discipline and not a guarantee"):
            self.assertIn(phrase, readme)

    def test_the_spec_carries_the_rules_this_code_serves(self):
        spec = " ".join((ROOT / "test" / "shiploop_e2e" / "SPEC.md").read_text().split())
        for phrase in ("**A run leaves nothing listening**", "`<output>/.harness-lock`", "`left_behind`",
                       "A SIGTERM to the harness (a task runner's stop, `kill`) is a requested stop too",
                       "**Runs compared on wall time or per-call cost run one after the other**",
                       "a pair whose figures are compared is the exception stated in the bullet "
                       "\"Runs compared on wall time or per-call cost run one after the other\"",
                       "a Ctrl-C on a suite is handled as a SIGTERM",
                       "A `--resume-run` of a case whose harness is running (its lock is held) is refused too; a regrade is not"):
            self.assertIn(phrase, spec)
        self.assertNotIn("bullet after next", spec, "a position breaks when a bullet is added: the bullet is named")

    def test_the_readme_says_what_a_signal_to_the_harness_does(self):
        readme = " ".join((ROOT / "test" / "shiploop_e2e" / "README.md").read_text().split())
        for phrase in ("A SIGTERM or SIGHUP to the harness ends every live host at once", "`terminated by SIGTERM`",
                       "a detached `nohup` launch ignores the hangup", "Only a SIGKILL gives the harness no chance to run anything",
                       "not `iterate.py`", "A Ctrl-C on a suite is handled as a SIGTERM",
                       "a Ctrl-C on a single case ends the hosts as the harness exits and writes no records"):
            self.assertIn(phrase, readme)
        self.assertNotIn("no harness code runs", readme)
        self.assertNotIn("taking the harness and its host with it", readme)


if __name__ == "__main__":
    unittest.main()
