#!/usr/bin/env python3
"""Relocation smoke coverage for ShipLoop's bundled managed Improve copy."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts" / "sync-improve-managed.py"


class ManagedPackageRelocationTests(unittest.TestCase):
    """The bridge must load its pinned local controller after relocation."""

    def copy_packages(self, parent: Path) -> Path:
        root = parent / "isolated skill-craft package with spaces"
        ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
        shutil.copytree(ROOT / "skills" / "improve", root / "skills" / "improve", ignore=ignore)
        shutil.copytree(ROOT / "skills" / "shiploop", root / "skills" / "shiploop", ignore=ignore)
        (root / "scripts").mkdir(parents=True)
        shutil.copy2(SYNC, root / "scripts" / SYNC.name)
        return root

    def run_command(self, root: Path, *args: str, code: str | None = None) -> subprocess.CompletedProcess[str]:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONNOUSERSITE"] = "1"
        environment["PYTHONPATH"] = str(root / "skills" / "shiploop" / "scripts")
        scratch = root / "scratch"
        scratch.mkdir(exist_ok=True)
        command = [sys.executable, "-B"]
        if code is not None:
            command.extend(["-c", code])
        else:
            command.extend(args)
        return subprocess.run(
            command,
            cwd=scratch,
            env=environment,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def executor_digest(self, root: Path) -> subprocess.CompletedProcess[str]:
        return self.run_command(
            root,
            code="""
import shiploop_improve_bridge as bridge
print(bridge._executor_digest())
""",
        )

    def test_relocated_packages_use_the_pinned_local_controller(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.copy_packages(Path(directory))
            source = root / "skills" / "improve" / "scripts" / "managed_controller.py"
            destination = root / "skills" / "shiploop" / "scripts" / "_improve_managed.py"
            pin_path = root / "skills" / "shiploop" / "references" / "improve-managed-controller-pin.json"
            contract_source = root / "skills" / "improve" / "references" / "managed-consumer.md"
            contract_destination = root / "skills" / "shiploop" / "references" / "improve-managed-consumer.md"

            self.assertEqual(source.read_bytes(), destination.read_bytes())
            self.assertEqual(contract_source.read_bytes(), contract_destination.read_bytes())
            pin = json.loads(pin_path.read_text(encoding="utf-8"))
            self.assertEqual(pin["source"], "skills/improve/scripts/managed_controller.py")
            self.assertEqual(pin["contract_source"], "skills/improve/references/managed-consumer.md")
            self.assertEqual(pin["contract_path"], "references/improve-managed-consumer.md")

            synced = self.run_command(root, str(root / "scripts" / "sync-improve-managed.py"))
            self.assertEqual(synced.returncode, 0, synced.stderr)

            probe = self.run_command(
                root,
                code="""
import json
from pathlib import Path
import shiploop_improve_bridge as bridge

controller = bridge._controller()
binding = controller.new_binding(
    parent_action="managed-improve",
    child_action_id="package-smoke",
    profile="product",
    input_identity={"candidate": "package smoke", "baseline": "a" * 64},
    policy_digest="b" * 64,
    executor_digest=bridge._executor_digest(),
    commit_policy="audit-every-iteration",
    independent_review={"required": False, "fallback_allowed": False},
)
child = controller.new_child(binding)
print(json.dumps({
    "controller": str(Path(controller.__file__).resolve()),
    "bridge": str(Path(bridge.__file__).resolve()),
    "binding_sha256": binding["binding_sha256"],
    "phase": child["current_phase"],
}, sort_keys=True))
""",
            )
            self.assertEqual(probe.returncode, 0, probe.stderr)
            result = json.loads(probe.stdout)
            self.assertEqual(Path(result["controller"]), destination.resolve())
            self.assertEqual(
                Path(result["bridge"]),
                (root / "skills" / "shiploop" / "scripts" / "shiploop_improve_bridge.py").resolve(),
            )
            self.assertEqual(result["phase"], "review")
            self.assertEqual(len(result["binding_sha256"]), 64)

            original_destination = destination.read_bytes()
            destination.write_bytes(original_destination + b"\n")
            stale_runtime_controller = self.executor_digest(root)
            self.assertNotEqual(stale_runtime_controller.returncode, 0)
            self.assertIn("managed Improve controller source differs from its pin", stale_runtime_controller.stderr)
            destination.write_bytes(original_destination)

            original_pin = pin_path.read_text(encoding="utf-8")
            pin["sha256"] = "0" * 64
            pin_path.write_text(json.dumps(pin, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            stale_pin = self.run_command(root, str(root / "scripts" / "sync-improve-managed.py"))
            self.assertNotEqual(stale_pin.returncode, 0)
            self.assertIn("Managed Improve controller pin differs", stale_pin.stderr)
            stale_runtime_pin = self.executor_digest(root)
            self.assertNotEqual(stale_runtime_pin.returncode, 0)
            self.assertIn("managed Improve controller source differs from its pin", stale_runtime_pin.stderr)

            pin_path.write_text(original_pin, encoding="utf-8")
            original_source = source.read_bytes()
            source.write_bytes(original_source + b"\n")
            stale_source = self.run_command(root, str(root / "scripts" / "sync-improve-managed.py"))
            self.assertNotEqual(stale_source.returncode, 0)
            self.assertIn("Managed Improve controller copy differs", stale_source.stderr)

            source.write_bytes(original_source)
            original_contract = contract_source.read_bytes()
            contract_source.write_bytes(original_contract + b"\n")
            stale_contract_pin = self.run_command(root, str(root / "scripts" / "sync-improve-managed.py"))
            self.assertNotEqual(stale_contract_pin.returncode, 0)
            self.assertIn("Managed Improve controller pin differs", stale_contract_pin.stderr)

            contract_source.write_bytes(original_contract)
            original_contract_destination = contract_destination.read_bytes()
            contract_destination.write_bytes(original_contract_destination + b"\n")
            stale_contract_copy = self.run_command(root, str(root / "scripts" / "sync-improve-managed.py"))
            self.assertNotEqual(stale_contract_copy.returncode, 0)
            self.assertIn("Managed Improve consumer contract copy differs", stale_contract_copy.stderr)
            stale_runtime_contract = self.executor_digest(root)
            self.assertNotEqual(stale_runtime_contract.returncode, 0)
            self.assertIn("managed Improve consumer contract differs from its pin", stale_runtime_contract.stderr)


if __name__ == "__main__":
    unittest.main()
