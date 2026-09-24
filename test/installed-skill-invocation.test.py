#!/usr/bin/env python3
"""Hermetic installed-package invocation checks for script-backed skill leaves.

Each case copies the generated plugin's shipped skill package beneath a path
containing spaces, makes that copy read-only, and invokes it from an unrelated
writable cwd. It does not install a host plugin or use a live host/model
session. Script-backed members of plugin bundles are copied from their bundle
view (plugins/<bundle>/skills/<member>).
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
LEAVES = (
    "review-coverage",
    "skill-interop",
    "evidence-gates",
    "shiploop",
    "shiploop-e2e-audit",
    "improve",
)
# (bundle plugin, member skill) pairs shipped inside a multi-skill plugin view.
BUNDLE_MEMBERS = (
    ("backchain", "plan-dispatcher"),
)


class InstalledSkillInvocationTest(unittest.TestCase):
    """Exercise bundled CLIs without a checkout-relative or ambient-skill path."""

    def test_review_campaign_dependency_is_not_silently_invented(self) -> None:
        body = (self.package("review-coverage") / "SKILL.md").read_text()
        self.assertIn("driver is an external skill, not bundled", body)
        self.assertIn("missing prerequisite", body)
        self.assertIn("status-only `update_goal` tool cannot", body)

    def test_audit_copied_package_binds_without_checkout_from_unrelated_cwd(self) -> None:
        package = self.package("shiploop-e2e-audit")
        cli = package / "scripts/resolve_harness.py"
        before = set(self.consumer.iterdir())
        result = self.invoke_python(cli)
        self.assert_ok(result, "audit copied-package binding without clone")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["binding_source"], "package")
        self.assertEqual(payload["harness"], str((package / "harness").resolve()))
        self.assertIsNone(payload["checkout"])
        self.assertTrue(payload["harness_sha256"])
        self.assertEqual(set(self.consumer.iterdir()), before)
        self.assert_no_bytecode()

    def test_audit_copied_package_accepts_explicit_source_checkout(self) -> None:
        package = self.package("shiploop-e2e-audit")
        before = set(self.consumer.iterdir())
        result = self.invoke_python(package / "scripts/resolve_harness.py", "--checkout", str(ROOT))
        self.assert_ok(result, "audit copied-package explicit binding")
        payload = json.loads(result.stdout)
        self.assertEqual(payload["binding_source"], "explicit")
        self.assertEqual(payload["checkout"], str(ROOT.resolve()))
        self.assertEqual(payload["resolved_skill_file"], str((package / "SKILL.md").resolve()))
        self.assertEqual(set(self.consumer.iterdir()), before)
        self.assert_no_bytecode()

    def test_audit_mock_runs_from_read_only_marketplace_copies_without_clone(self) -> None:
        audit = self.package("shiploop-e2e-audit")
        subject = self.package("shiploop")
        output = self.temp_root / "packaged mock results"
        before = set(self.consumer.iterdir())
        result = self.invoke_python(audit / "harness/check_suite.py", "--suite", "mock",
                                    "--skill-root", str(subject), "--output", str(output))
        self.assert_ok(result, "audit mock from read-only marketplace copies")
        payload = json.loads((output / "result.json").read_text())
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["model_calls"], 0)
        self.assertEqual(payload["failures"], 0)
        self.assertEqual(payload["errors"], 0)
        self.assertEqual(payload["skipped"], 0)
        self.assertGreater(payload["tests"], 0)
        self.assertEqual(payload["harness"]["root"], str((audit / "harness").resolve()))
        self.assertEqual(payload["selected_subject"]["root"], str(subject.resolve()))
        self.assertTrue(payload["selected_subject"]["package_sha256"])
        self.assertIsNone(payload["harness"]["source_checkout"])
        self.assertEqual(set(self.consumer.iterdir()), before)
        self.assert_no_bytecode()

    def test_audit_mock_uses_isolated_installed_subject_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="audit installed default ") as temporary:
            area = Path(temporary).resolve()
            home = area / "home"
            cwd = area / "empty folder"
            cwd.mkdir()
            copies = []
            try:
                for leaf in ("shiploop-e2e-audit", "shiploop"):
                    destination = home / ".grok/skills" / leaf
                    shutil.copytree(self.package(leaf), destination)
                    copies.append(destination)
                result = subprocess.run(
                    [sys.executable, "-B", str(copies[0] / "harness/check_suite.py"),
                     "--suite", "mock", "--output", str(area / "results")],
                    cwd=cwd, env=self.base_env({"HOME": str(home)}),
                    capture_output=True, text=True, timeout=60,
                )
                self.assert_ok(result, "audit mock using isolated installed subject default")
                payload = json.loads((area / "results/result.json").read_text())
                self.assertEqual(payload["status"], "passed")
                self.assertEqual(payload["model_calls"], 0)
                self.assertEqual(payload["selected_subject"]["root"], str(copies[1]))
                self.assertEqual(payload["selected_subject"]["default_selection"], "installed-skill-dir")
                self.assertIsNone(payload["harness"]["source_checkout"])
                self.assertEqual(list(cwd.iterdir()), [])
            finally:
                for package in copies:
                    self._make_writable(package)

    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory(prefix="skill-craft-installed-skill-")
        cls.temp_root = Path(cls.temp.name)
        cls.package_parent = cls.temp_root / "installed marketplace packages with spaces"
        cls.package_parent.mkdir()
        cls.consumer = cls.temp_root / "unrelated consumer project with spaces"
        cls.consumer.mkdir()
        cls.home = cls.temp_root / "isolated home"
        cls.home.mkdir()
        cls.packages: dict[str, Path] = {}
        # Bundle members keep their plugin layout (their own skills/ parent),
        # so they never become siblings that a leaf's dependency lookup finds.
        sources = [(leaf, ROOT / "plugins" / leaf / "skills" / leaf, cls.package_parent) for leaf in LEAVES]
        sources += [
            (member, ROOT / "plugins" / bundle / "skills" / member,
             cls.temp_root / "installed bundle plugins with spaces" / bundle / "skills")
            for bundle, member in BUNDLE_MEMBERS
        ]
        for leaf, source, parent in sources:
            parent.mkdir(parents=True, exist_ok=True)
            destination = parent / leaf
            shutil.copytree(
                source,
                destination,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
            )
            cls.packages[leaf] = destination
            cls._make_read_only(destination)

    @classmethod
    def tearDownClass(cls) -> None:
        # Restore permissions only inside this test's disposable directory so
        # TemporaryDirectory can remove it on every supported platform.
        for package in cls.packages.values():
            cls._make_writable(package)
        cls.temp.cleanup()

    @staticmethod
    def _make_read_only(root: Path) -> None:
        paths = sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True)
        for path in paths:
            if path.is_dir():
                path.chmod(0o555)
            elif path.is_file():
                executable = bool(path.stat().st_mode & stat.S_IXUSR)
                path.chmod(0o555 if executable else 0o444)
        root.chmod(0o555)

    @staticmethod
    def _make_writable(root: Path) -> None:
        paths = sorted(root.rglob("*"), key=lambda path: len(path.parts), reverse=True)
        for path in paths:
            if path.is_dir():
                path.chmod(0o755)
            elif path.is_file():
                executable = bool(path.stat().st_mode & stat.S_IXUSR)
                path.chmod(0o755 if executable else 0o644)
        root.chmod(0o755)

    def package(self, leaf: str) -> Path:
        package = self.packages[leaf]
        self.assertTrue((package / "SKILL.md").is_file(), package)
        self.assertFalse(
            bool(package.stat().st_mode & stat.S_IWUSR),
            f"package must be read-only: {package}",
        )
        return package

    def base_env(self, extra: Mapping[str, str] | None = None) -> dict[str, str]:
        env = dict(os.environ)
        env.pop("PYTHONPATH", None)
        env["HOME"] = str(self.home)
        env["PYTHONNOUSERSITE"] = "1"
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if extra:
            env.update(extra)
        return env

    def invoke(
        self,
        argv: Sequence[str | Path],
        *,
        extra_env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(item) for item in argv],
            cwd=self.consumer,
            capture_output=True,
            text=True,
            check=False,
            env=self.base_env(extra_env),
        )

    def invoke_python(
        self,
        script: Path,
        *args: str,
        extra_env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return self.invoke(
            (sys.executable, "-B", script, *args),
            extra_env=extra_env,
        )

    def assert_ok(self, result: subprocess.CompletedProcess[str], label: str) -> None:
        self.assertEqual(
            result.returncode,
            0,
            f"{label} failed ({result.returncode})\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def assert_no_bytecode(self) -> None:
        for package in self.packages.values():
            leftovers = [
                path.relative_to(package)
                for path in package.rglob("*")
                if path.name == "__pycache__" or path.suffix == ".pyc"
            ]
            self.assertEqual(leftovers, [], f"package was mutated: {package}: {leftovers}")

    def test_card_contracts_bind_selected_loaded_skill(self) -> None:
        expected = {
            "review-coverage": (
                "selected, loaded",
                'CLI="$SKILL_ROOT/scripts/review-coverage"',
                "Do not infer",
            ),
            "skill-interop": (
                "selected,\nloaded",
                'MARKETPLACE_RUN="$SKILL_ROOT/scripts/marketplace-run.sh"',
                "MARKETPLACE_INSTALL_SH",
            ),
            "evidence-gates": (
                "selected, loaded",
                'CLI="$SKILL_ROOT/scripts/evidence-gates"',
                "rather than invoking a same-named program from",
            ),
            "shiploop": (
                "selected, loaded",
                'CLI="$SKILL_ROOT/scripts/shiploop"',
                "dependency's own observed, selected `SKILL.md` path",
            ),
            "improve": (
                "selected, loaded",
                'RUNTIME_SCRIPT="$SKILL_ROOT/runtime/until-loop/scripts/until_loop_ephemeral.py"',
                "ambient Until Loop installation",
            ),
        }
        for leaf, phrases in expected.items():
            text = (ROOT / "skills" / leaf / "SKILL.md").read_text(encoding="utf-8")
            for phrase in phrases:
                self.assertIn(phrase, text, f"{leaf} missing invocation contract: {phrase}")

        interop_card = (ROOT / "skills/skill-interop/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("bash skills/skill-interop/scripts/", interop_card)
        graph = (ROOT / "skills/shiploop/references/graph-dry-run.md").read_text(encoding="utf-8")
        self.assertNotIn("python3 skills/shiploop/scripts/shiploop", graph)
        for doc in (
            ROOT / "skills/skill-interop/references/checklist.md",
            ROOT / "skills/skill-interop/references/host-paths.md",
        ):
            text = doc.read_text(encoding="utf-8")
            self.assertNotIn("../../../../docs/ARCHITECTURE.md", text)
            self.assertIn(
                "https://github.com/whichguy/skill-craft/blob/main/docs/ARCHITECTURE.md",
                text,
            )

    def test_review_coverage_cli_from_read_only_copy(self) -> None:
        package = self.package("review-coverage")
        cli = package / "scripts/review-coverage"

        template = self.invoke_python(cli, "template", "--short")
        self.assert_ok(template, "review-coverage template")
        self.assertIn("## Review Coverage", template.stdout)
        self.assertIn("residual", template.stdout.lower())

        plan = self.consumer / "filled plan.md"
        plan.write_text(
            """## Review Coverage

| Field | Value |
|-------|-------|
| Base ref | abcdef1234567890deadbeef |
| Repo | /tmp/consumer-repo |
| Target paths | src/example.py |
| Test command | python3 -m unittest |
| Materiality bar | material (P0/P1) |
| Driver | review-converge under /goal |

1. Forward audit of specs to code.
2. Reverse audit of code vs base.
two consecutive clean residual rounds with green suite
""",
            encoding="utf-8",
        )
        validate = self.invoke_python(cli, "validate", str(plan))
        self.assert_ok(validate, "review-coverage validate")
        self.assertEqual(validate.stdout.strip(), "ok")

        missing = self.invoke_python(cli, "validate", str(self.consumer / "missing plan.md"))
        self.assertEqual(missing.returncode, 2, missing.stderr)
        self.assertIn("cannot read", missing.stderr)
        self.assert_no_bytecode()

    def test_skill_interop_facade_routes_from_read_only_copy(self) -> None:
        package = self.package("skill-interop")
        cli = package / "scripts/marketplace-run.sh"
        bin_dir = self.temp_root / "facade host stubs"
        bin_dir.mkdir(exist_ok=True)
        overrides: dict[str, str] = {}
        for host, variable in (
            ("claude", "CLAUDE_BIN"),
            ("grok", "GROK_BIN"),
            ("codex", "CODEX_BIN"),
        ):
            stub = bin_dir / host
            stub.write_text("#!/usr/bin/env sh\nexit 97\n", encoding="utf-8")
            stub.chmod(0o755)
            overrides[variable] = str(stub)

        hosts = self.invoke(("/bin/bash", cli, "hosts", "--json"), extra_env=overrides)
        self.assert_ok(hosts, "marketplace-run hosts")
        payload = json.loads(hosts.stdout)
        self.assertEqual([row["host"] for row in payload["hosts"]], ["claude", "grok", "codex"])
        self.assertTrue(all(row["status"] == "available" for row in payload["hosts"]))

        routes = (
            ("claude", "fixture@market", "plugin install fixture@market"),
            ("grok", "owner/fixture", "plugin install owner/fixture"),
            ("codex", "fixture@market", "plugin add fixture@market"),
        )
        for host, identifier, expected_argv in routes:
            result = self.invoke(
                (
                    "/bin/bash",
                    cli,
                    "plugins",
                    "install",
                    identifier,
                    "--host",
                    host,
                    "--dry-run",
                ),
                extra_env=overrides,
            )
            self.assert_ok(result, f"marketplace-run {host} dry-run")
            self.assertIn(expected_argv, result.stdout)

        no_checkout = self.invoke(
            ("/bin/bash", cli, "install-local", "--dry-run"),
            extra_env=overrides,
        )
        self.assertEqual(no_checkout.returncode, 4, no_checkout.stderr)
        self.assertIn("MARKETPLACE_INSTALL_SH", no_checkout.stderr)

        installer = self.consumer / "chosen checkout installer.sh"
        installer.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        installer.chmod(0o755)
        explicit_checkout = self.invoke(
            ("/bin/bash", cli, "install-local", "--dry-run"),
            extra_env={**overrides, "MARKETPLACE_INSTALL_SH": str(installer)},
        )
        self.assert_ok(explicit_checkout, "marketplace-run explicit checkout installer")
        self.assertIn(str(installer), explicit_checkout.stdout)
        self.assert_no_bytecode()

    def test_evidence_gates_self_check_from_read_only_copy(self) -> None:
        package = self.package("evidence-gates")
        cli = package / "scripts/evidence-gates"
        self_check = self.invoke_python(cli, "self-check")
        self.assert_ok(self_check, "evidence-gates self-check")
        payload = json.loads(self_check.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["mode"], "native")
        self.assertEqual(payload["package_root"], str(package.resolve()))

        charter = self.consumer / "charter.json"
        charter.write_text('{"criteria": []}\n', encoding="utf-8")
        package_write = self.invoke_python(
            cli,
            "freeze",
            "--charter",
            str(charter),
            "--repo",
            str(package),
        )
        self.assertEqual(package_write.returncode, 2, package_write.stderr)
        self.assertIn("package_root_write", package_write.stderr)
        self.assert_no_bytecode()

    def test_shiploop_graph_and_recovery_from_read_only_copy(self) -> None:
        package = self.package("shiploop")
        cli = package / "scripts/shiploop"

        dry_run = self.invoke_python(
            cli,
            "graph-dry-run",
            "--scenario",
            "blocked-resume",
            "--format",
            "json",
        )
        self.assert_ok(dry_run, "shiploop graph dry-run")
        trace = json.loads(dry_run.stdout)
        self.assertIn("blocked-resume", json.dumps(trace))
        self.assertIn("simulation_only", json.dumps(trace))

        run_dir = self.consumer / ".shiploop"
        init = self.invoke_python(
            cli,
            "init",
            "--repo",
            str(self.consumer),
            "--run-dir",
            str(run_dir),
            "--prompt=verify installed package invocation",
        )
        self.assert_ok(init, "shiploop init")
        self.assertIn("ShipLoop navigator | intake", init.stdout)
        self.assertIn(str(cli.resolve()), init.stdout)
        self.assertTrue((run_dir / "state.md").is_file())

        resumed = self.invoke_python(cli, "next", "--run-dir", str(run_dir))
        self.assert_ok(resumed, "shiploop next")
        self.assertIn("ShipLoop navigator | intake", resumed.stdout)

        absent = self.invoke_python(
            cli,
            "next",
            "--run-dir",
            str(self.consumer / "missing run"),
        )
        self.assertNotEqual(absent.returncode, 0)
        self.assertIn("error:", absent.stderr)
        self.assert_no_bytecode()

    def test_improve_ephemeral_runtime_from_read_only_installed_copy(self) -> None:
        package = self.package("improve")
        runtime = package / "runtime/until-loop/scripts/until_loop_ephemeral.py"
        contract = {
            "workspace": str(self.consumer),
            "work": "Exercise one synthetic protocol review; do not change product files.",
            "exit_condition": "Two synthetic qualifying reviews complete.",
            "repeat_condition": "Continue while the review gate remains open.",
            "required_trivial_reviews": 2,
            "context": {"request": "Installed runtime protocol fixture", "scope": "Fixture only",
                        "authority": "No product edits or commits", "environment": sys.executable,
                        "resources": []},
        }

        def call(argv, payload=None):
            result = subprocess.run(argv, input=None if payload is None else json.dumps(payload),
                                    cwd=self.consumer, text=True, capture_output=True,
                                    env=self.base_env(), timeout=30)
            self.assert_ok(result, "installed ephemeral callback")
            return json.loads(result.stdout)

        packet = call([sys.executable, "-B", str(runtime), "start"], contract)
        state = Path(packet["state_file"])
        self.addCleanup(lambda: state.unlink(missing_ok=True))
        self.assertNotIn(package, state.parents)
        self.assertEqual(call(packet["next_argv"]), packet)
        report = {"classification": "trivial", "exit_assessment": "satisfied",
                  "continuation_assessment": "allowed", "evidence": "Synthetic review fixture",
                  "handoff": "Retain this protocol-only fixture; no semantic review claim."}
        first = call(packet["done_argv"], report)
        self.assertEqual(first["status"], "active")
        terminal = call(first["done_argv"], report)
        self.assertEqual(terminal["status"], "complete")
        self.assertEqual(terminal["context"], contract["context"])
        self.assertFalse(state.exists())
        self.assertFalse((self.consumer / ".until-loop").exists())
        self.assert_no_bytecode()

    def test_plan_dispatcher_capabilities_from_read_only_bundle_copy(self) -> None:
        package = self.package("plan-dispatcher")
        digest = {
            path.relative_to(package).as_posix(): path.read_bytes()
            for path in sorted(package.rglob("*")) if path.is_file()
        }
        before = set(self.consumer.iterdir())
        result = self.invoke(("node", package / "scripts/dispatch.js", "capabilities"))
        self.assert_ok(result, "plan-dispatcher capabilities from the bundle view")
        payload = json.loads(result.stdout)
        self.assertEqual("execution-graph/v1", payload["capabilities"]["graph_validation"])
        self.assertEqual(set(self.consumer.iterdir()), before)
        self.assertEqual(digest, {
            path.relative_to(package).as_posix(): path.read_bytes()
            for path in sorted(package.rglob("*")) if path.is_file()
        })

    def test_improve_bound_adapter_ignores_ambient_runtime(self) -> None:
        package = self.package("improve")
        runtime = package / "runtime/until-loop/scripts/until-loop"
        collector = package / "scripts/capture_evidence.py"
        contract = self.consumer / "preview contract.json"
        contract.write_text(
            json.dumps(
                {
                    "version": 1,
                    "policy": "decision-rubric/2",
                    "original_request": "Preview a bounded Improve review.",
                    "interpretation": (
                        "Execute: inspect the selected candidate. Continue while a "
                        "required criterion lacks current evidence. Success: every "
                        "criterion has current evidence. Early stop: a real blocker "
                        "prevents useful progress."
                    ),
                    "criteria": [
                        {
                            "id": "C1",
                            "text": "Review the selected candidate before proposing changes.",
                            "basis": {
                                "kind": "request",
                                "reference": "Preview a bounded Improve review.",
                            },
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        fake_bin = self.temp_root / "ambient until-loop bin"
        fake_bin.mkdir(exist_ok=True)
        sentinel = self.consumer / "ambient-runtime-was-used"
        fake_runtime = fake_bin / "until-loop"
        fake_runtime.write_text(
            "#!/usr/bin/env sh\n: > \"$AMBIENT_UNTIL_SENTINEL\"\nexit 97\n",
            encoding="utf-8",
        )
        fake_runtime.chmod(0o755)
        env = {
            "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            "AMBIENT_UNTIL_SENTINEL": str(sentinel),
        }
        preview = self.invoke_python(
            runtime,
            "v2",
            "preview",
            "--contract-file",
            str(contract),
            extra_env=env,
        )
        self.assert_ok(preview, "Improve bundled Until Loop preview")
        payload = json.loads(preview.stdout)
        self.assertEqual(payload["mode"], "preview")
        self.assertEqual(payload["status"], "not_initialized")
        self.assertFalse(sentinel.exists(), "bundled adapter invoked ambient until-loop")

        missing_repo = self.invoke_python(
            collector,
            "snapshot",
            "--repo",
            str(self.consumer / "missing workspace"),
            "--owner",
            "standalone-improve",
            "--history-window",
            "1",
            "--scope",
            "candidate.txt",
            extra_env=env,
        )
        self.assertEqual(missing_repo.returncode, 2, missing_repo.stderr)
        self.assertIn("repository directory does not exist", missing_repo.stderr)
        self.assert_no_bytecode()


if __name__ == "__main__":
    unittest.main(verbosity=2)
