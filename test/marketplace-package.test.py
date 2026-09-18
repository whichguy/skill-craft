#!/usr/bin/env python3
"""Package acceptance must fail closed before a host tries to load a skill."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_check", ROOT / "scripts/check-marketplace-packages.py")
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class PackageTests(unittest.TestCase):
    def test_generated_agent_routers_bind_the_selected_installed_card(self):
        for name in ("shiploop", "skill-interop"):
            text = (ROOT / "plugins" / name / "agents" / f"{name}.md").read_text()
            self.assertIn("selected by the host", text)
            self.assertIn("absolute", text)
            self.assertNotIn("`skills/", text)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="marketplace package ")
        self.addCleanup(self.temp.cleanup)
        self.package = Path(self.temp.name) / "sample"
        self.skill = self.package / "skills/sample"
        self.skill.mkdir(parents=True)
        self.skill.joinpath("SKILL.md").write_text(
            "---\nname: sample\nversion: 1.2.3\nlicense: MIT\n"
            "metadata:\n  skill_craft:\n    kind: prompt-only\n---\n\n# Sample\n"
        )
        self.package.joinpath("LICENSE").write_text("MIT License\nfixture terms\n")
        self.package.joinpath("README.md").write_text("# Sample\nInstall and use this skill.\n")
        self.manifest = {"name": "sample", "version": "1.2.3", "description": "A sample skill", "license": "MIT"}
        self.write_manifest(".claude-plugin", self.manifest)
        self.codex = dict(
            self.manifest,
            skills="./skills/",
            interface={
                "displayName": "Sample",
                "shortDescription": "Sample package",
                "longDescription": "A complete sample package for offline validation.",
                "developerName": "Skill Craft",
                "category": "Productivity",
                "capabilities": ["Read"],
                "defaultPrompt": ["Use $sample for this task."],
            },
        )
        self.write_manifest(".codex-plugin", self.codex)

    def write_manifest(self, directory, value):
        target = self.package / directory / "plugin.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(value))

    def check(self):
        return CHECK.validate_package(self.package)

    def assert_bad(self, text):
        self.assertTrue(any(text in error for error in self.check()), self.check())

    def test_complete_package(self):
        self.assertEqual([], self.check())

    def test_missing_license(self):
        self.package.joinpath("LICENSE").unlink()
        self.assert_bad("LICENSE")

    def test_empty_readme(self):
        self.package.joinpath("README.md").write_text("")
        self.assert_bad("README.md")

    def test_missing_codex_adapter(self):
        shutil.rmtree(self.package / ".codex-plugin")
        self.assert_bad(".codex-plugin/plugin.json")

    def test_manifest_identity_drift(self):
        self.write_manifest(".codex-plugin", dict(self.codex, version="1.2.4"))
        self.assert_bad("version")

    def test_codex_interface_requires_complete_metadata(self):
        codex = dict(self.codex, interface=dict(self.codex["interface"]))
        codex["interface"].pop("category")
        self.write_manifest(".codex-plugin", codex)
        self.assert_bad("Codex interface category")

    def test_manifest_name_not_folder(self):
        self.write_manifest(".claude-plugin", dict(self.manifest, name="wrong"))
        self.assert_bad("name")

    def test_skill_version_drift(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("1.2.3", "1.2.4"))
        self.assert_bad("SKILL.md version")

    def test_missing_skill(self):
        self.skill.joinpath("SKILL.md").unlink()
        self.assert_bad("SKILL.md")

    def test_nested_public_skill(self):
        nested = self.skill / "runtime/nested/SKILL.md"
        nested.parent.mkdir(parents=True)
        nested.write_text("---\nname: nested\n---\n")
        self.assert_bad("additional public SKILL.md")

    def test_missing_declared_component(self):
        self.write_manifest(".codex-plugin", dict(self.codex, apps="./missing.json"))
        self.assert_bad("missing.json")

    def test_escaping_component(self):
        self.write_manifest(".codex-plugin", dict(self.codex, skills="../elsewhere"))
        self.assert_bad("confined")

    def test_symlink_payload_rejected(self):
        self.skill.joinpath("outside").symlink_to(Path(self.temp.name))
        self.assert_bad("symlink")

    def test_symlink_is_rejected_before_package_content_is_read(self):
        target = Path(self.temp.name) / "linked-readme"
        target.write_text("linked content\n")
        self.package.joinpath("README.md").unlink()
        self.package.joinpath("README.md").symlink_to(target)
        self.package.joinpath(".codex-plugin/plugin.json").write_text("{")
        errors = self.check()
        self.assertTrue(any("residual symlink" in error for error in errors), errors)
        self.assertFalse(any("invalid JSON" in error for error in errors), errors)

    def test_script_kind_requires_payload(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        self.assert_bad("script-backed")

    def test_script_kind_rejects_placeholder_files(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        scripts = self.skill / "scripts"
        scripts.mkdir()
        scripts.joinpath("README.md").write_text("not an entrypoint\n")
        scripts.joinpath(".DS_Store").write_bytes(b"not an entrypoint")
        self.assert_bad("runnable bundled script")

    def test_unknown_extensionless_shebang_requires_executable_mode(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        scripts = self.skill / "scripts"
        scripts.mkdir()
        entrypoint = scripts / "run"
        entrypoint.write_text("#!/usr/bin/env python3\nprint('fixture')\n")
        entrypoint.chmod(0o644)
        self.assert_bad("not executable")

    def test_absolute_interpreter_shebangs_are_recognized(self):
        self.assertEqual("python3", CHECK.script_interpreter(Path("run"), "#!/usr/bin/python3\n"))
        self.assertEqual("bash", CHECK.script_interpreter(Path("run"), "#!/bin/bash\n"))

    def test_declared_entrypoint_must_exist_and_match_its_interpreter(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        scripts = self.skill / "scripts"
        scripts.mkdir()
        scripts.joinpath("README.md").write_text("not an entrypoint\n")
        inventory = {"sample": {"scripts/run": "python3"}}
        with mock.patch.object(CHECK, "NATIVE_SCRIPT_ENTRYPOINTS", inventory, create=True):
            self.assert_bad("declared entrypoint")

    def test_extensionless_python_entrypoint_can_be_interpreter_invoked(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        scripts = self.skill / "scripts"
        scripts.mkdir()
        entrypoint = scripts / "run"
        entrypoint.write_text("#!/usr/bin/env python3\nprint('fixture')\n")
        entrypoint.chmod(0o644)
        inventory = {"sample": {"scripts/run": "python3"}}
        with mock.patch.object(CHECK, "NATIVE_SCRIPT_ENTRYPOINTS", inventory, create=True):
            self.assertEqual([], self.check())

    def test_declared_shell_entrypoint_rejects_wrong_interpreter(self):
        card = self.skill / "SKILL.md"
        card.write_text(card.read_text().replace("prompt-only", "script-backed"))
        scripts = self.skill / "scripts"
        scripts.mkdir()
        scripts.joinpath("run").write_text("#!/usr/bin/env python3\nprint('fixture')\n")
        inventory = {"sample": {"scripts/run": "bash"}}
        with mock.patch.object(CHECK, "NATIVE_SCRIPT_ENTRYPOINTS", inventory, create=True):
            self.assert_bad("expected bash")

    def test_improve_native_inventory_requires_ephemeral_runtime(self):
        source = ROOT / "plugins" / "improve"
        with tempfile.TemporaryDirectory(prefix="marketplace improve ") as temporary:
            package = Path(temporary) / "improve"
            shutil.copytree(source, package)
            runtime = package / "skills/improve/runtime/until-loop/scripts/until_loop_ephemeral.py"
            self.assertTrue(runtime.is_file())
            runtime.unlink()
            errors = CHECK.validate_package(package)
        self.assertTrue(
            any(
                "declared entrypoint "
                "runtime/until-loop/scripts/until_loop_ephemeral.py is missing" in error
                for error in errors
            ),
            errors,
        )

    def test_python_helper_syntax_checked_without_execution(self):
        scripts = self.skill / "scripts"
        scripts.mkdir()
        scripts.joinpath("helper.py").write_text("def broken(:\n")
        self.assert_bad("invalid Python")

    def test_undeclared_python_side_effect_not_executed(self):
        scripts = self.skill / "scripts"
        scripts.mkdir()
        scripts.joinpath("helper.py").write_text("raise RuntimeError('never execute during validation')\n")
        self.assertEqual([], self.check())

    def test_invalid_json_is_diagnostic(self):
        self.package.joinpath(".codex-plugin/plugin.json").write_text("{")
        self.assert_bad("invalid JSON")

    def test_every_generated_source_package_passes(self):
        leaves = sorted(path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(leaves)
        for name in leaves:
            with self.subTest(package=name):
                self.assertEqual([], CHECK.validate_package(ROOT / "plugins" / name))


if __name__ == "__main__":
    unittest.main()
