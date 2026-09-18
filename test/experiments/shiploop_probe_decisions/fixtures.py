#!/usr/bin/env python3
"""Local-only fixture corpus and calibration for probe-decision trials."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
from textwrap import dedent
from typing import Any


CASES: dict[str, dict[str, object]] = {
    "f1": {
        "task": "Plan a daily operations export that combines the required ledger and fulfillment service exports.",
        "required": (
            "separate a current scoped receipt from a receipt whose effective target or role drifted",
            "treat one changed read as sufficient for the drifted connection",
        ),
        "forbidden": ("claim real service authorization", "rerun an unchanged current receipt without a stated reason"),
    },
    "f2": {
        "task": "Expose the existing local exporter through a JSON CLI entrypoint. If the operation fails, preserve the prior output file.",
        "required": (
            "distinguish the launcher-selected parser from the manifest declaration",
            "distinguish preview acceptance from a committed replacement write",
        ),
        "forbidden": ("claim preview proves commit safety", "risk checked-in output while probing"),
    },
    "f3": {
        "task": "Add report output with Unicode-preserving NFC-normalized labels, ascending ID order, and deterministic JSON bytes. Do not install connectors.",
        "required": (
            "inspect the indexed native path and its representative operation",
            "separate the unrelated preview-only accelerator from the affected path",
        ),
        "forbidden": ("install or invoke a connector", "treat an unrelated preview as reuse evidence"),
    },
    "f4": {
        "task": "Plan a combined export across both required targets and an independent local formatting change.",
        "required": (
            "distinguish metadata or listing success from representative target reads",
            "preserve an unknown effect after the modeled timeout and keep independent formatting separate",
        ),
        "forbidden": ("claim real MCP connectivity or authorization", "substitute the unrelated connector for a required target"),
    },
}


SUPPORT = r'''
"""Shared local recorder; it never contacts a service."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def emit(payload):
    record = {"simulation": "local-read-only-fixture", **payload}
    scratch = ROOT / "scratch"
    scratch.mkdir(exist_ok=True)
    with (scratch / "probe-log.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
'''


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(dedent(body).lstrip().rstrip() + "\n", encoding="utf-8")


def _readme(title: str, commands: str) -> str:
    return f"""# {title}

This is a deterministic local fixture. Its commands read checked-in fixture data,
model only read-only external behavior, print one JSON object, and append that
same record under scratch/probe-log.jsonl. They do not read credentials or the
environment, contact a network, install anything, or change source files.

Supported observations:

    {commands}
"""


def _f1(mutant: bool) -> dict[str, str]:
    fulfillment = {"schema": "service-read-receipt/v1", "binding": {
        "target": "fulfillment-current" if mutant else "fulfillment-legacy",
        "role": "export.read" if mutant else "viewer",
    }, "scope": "current", "evidence_kind": "current_scoped_test_receipt", "status": "ok"}
    return {
        "README.md": _readme(
            "Two required export connections",
            "python3 capability.py --help\n    python3 capability.py read --target ledger-current\n    python3 capability.py read --target fulfillment-current\n\n    Receipt contract: contracts/service-receipt-v1.md",
        ),
        "connections.json": json.dumps({"receipt_contract": "contracts/service-receipt-v1.md", "connections": [
            {"name": "ledger", "required": True, "effective": {"target": "ledger-current", "role": "export.read"}, "prior_receipt": "evidence/ledger-current.json"},
            {"name": "fulfillment", "required": True, "effective": {"target": "fulfillment-current", "role": "export.read"}, "prior_receipt": "evidence/fulfillment-prior.json"},
        ]}, indent=2),
        "contracts/service-receipt-v1.md": """# Service export receipt validity

This contract applies to every required service export connection in this
fixture. A receipt is sufficient current planning evidence only when its schema
is `service-read-receipt/v1`, status is `ok`, scope is `current`, and its target
and role binding exactly match that connection's effective binding.

The fixture has no separate expiry rule. A receipt that satisfies this contract
is valid evidence for the matching connection; a receipt with a different
binding is evidence only for the binding it records.
""",
        "evidence/ledger-current.json": json.dumps({"schema": "service-read-receipt/v1", "binding": {"target": "ledger-current", "role": "export.read"}, "scope": "current", "evidence_kind": "current_scoped_test_receipt", "status": "ok"}, indent=2),
        "evidence/fulfillment-prior.json": json.dumps(fulfillment, indent=2),
        "capability.py": r'''
            import argparse
            import json
            from pathlib import Path
            from fixture_support import emit

            ROOT = Path(__file__).resolve().parent

            def main():
                parser = argparse.ArgumentParser(description="Local modeled read-only capability receipt")
                parser.add_argument("operation", choices=("read",))
                parser.add_argument("--target", required=True)
                args = parser.parse_args()
                connections = json.loads((ROOT / "connections.json").read_text(encoding="utf-8"))["connections"]
                selected = next((row for row in connections if row["effective"]["target"] == args.target), None)
                if selected is None:
                    parser.error("target is not configured by this fixture")
                emit({"operation": args.operation, "schema": "service-read-receipt/v1", "target": args.target, "role": selected["effective"]["role"], "binding": selected["effective"], "scope": "current", "status": "ok", "receipt_kind": "modeled_current_read"})

            if __name__ == "__main__":
                main()
        ''',
    }


def _f2(mutant: bool) -> dict[str, str]:
    row_id = 'row.get("id", f"generated-{position + 1}")' if mutant else 'row["id"]'
    writer = r'''
        import json
        from pathlib import Path

        def preview(rows):
            return json.dumps({"format": "json", "rows": rows}, ensure_ascii=False, sort_keys=True)

        def write_json(destination, rows):
            target = Path(destination)
            staged = target.with_name("." + target.name + ".next")
            try:
                with staged.open("w", encoding="utf-8") as stream:
                    stream.write("[")
                    for position, row in enumerate(rows):
                        if position:
                            stream.write(",")
                        item = {"id": ROW_ID, "amount": row["amount"]}
                        json.dump(item, stream, ensure_ascii=False, sort_keys=True)
                    stream.write("]")
                staged.replace(target)
            except Exception:
                staged.unlink(missing_ok=True)
                raise
            return {"target": str(target), "write_mode": "native_json_atomic_replace"}
    '''.replace("ROW_ID", row_id)
    return {
        "README.md": _readme(
            "Local exporter",
            "python3 probe.py --help\n    python3 probe.py version\n    python3 probe.py preview\n    python3 probe.py write-preservation\n    python3 -m unittest -q",
        ),
        "manifest.json": json.dumps({"parser": "3.1.0", "formats": ["text", "json"]}, indent=2),
        "bundled/__init__.py": "",
        "bundled/parser.py": f'VERSION = "{"3.1.0" if mutant else "2.6.4"}"\n',
        "bin/__init__.py": "",
        "bin/launcher.py": "from bundled.parser import VERSION\n\ndef active_parser_version():\n    return VERSION\n",
        "exporter.py": writer,
        "data/rows.json": '[{"id": "first", "amount": 4}, {"amount": 9}]\n',
        "probe.py": r'''
            import argparse
            import json
            from pathlib import Path
            import tempfile
            from bin.launcher import active_parser_version
            from exporter import preview, write_json
            from fixture_support import emit

            ROOT = Path(__file__).resolve().parent

            def rows():
                return json.loads((ROOT / "data" / "rows.json").read_text(encoding="utf-8"))

            def main():
                parser = argparse.ArgumentParser(description="Local exporter representative observations")
                parser.add_argument("operation", choices=("version", "preview", "write-preservation"))
                args = parser.parse_args()
                if args.operation == "version":
                    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
                    emit({"operation": "version", "manifest_parser": manifest["parser"], "active_parser": active_parser_version(), "launcher": "bin/launcher.py"})
                    return
                if args.operation == "preview":
                    emit({"operation": "preview", "status": "accepted", "rendered": json.loads(preview(rows()))})
                    return
                with tempfile.TemporaryDirectory(prefix="fixture-export-write-") as directory:
                    target = Path(directory) / "export.json"
                    previous = '{"previous":true}\n'
                    target.write_text(previous, encoding="utf-8")
                    try:
                        write_json(target, rows())
                    except KeyError as error:
                        staged = target.with_name("." + target.name + ".next")
                        emit({"operation": "write-preservation", "status": "error", "error": type(error).__name__, "previous_output_preserved": target.read_text(encoding="utf-8") == previous, "temporary_exists": staged.exists()})
                    else:
                        emit({"operation": "write-preservation", "status": "ok", "previous_output_replaced": target.read_text(encoding="utf-8") != previous})

            if __name__ == "__main__":
                main()
        ''',
        "test_exporter.py": r'''
            import json
            from pathlib import Path
            import tempfile
            import unittest
            from exporter import write_json

            class ExporterRepresentativeTest(unittest.TestCase):
                def test_valid_rows_use_native_json_replacement(self):
                    with tempfile.TemporaryDirectory() as directory:
                        target = Path(directory) / "export.json"
                        target.write_text("old\n", encoding="utf-8")
                        result = write_json(target, [{"id": "ok", "amount": 7}])
                        self.assertEqual(result["write_mode"], "native_json_atomic_replace")
                        self.assertEqual(json.loads(target.read_text(encoding="utf-8")), [{"amount": 7, "id": "ok"}])
        ''',
    }


def _f3(mutant: bool) -> dict[str, str]:
    label = 'unicodedata.normalize("NFC", value).encode("ascii", "ignore").decode("ascii")' if mutant else 'unicodedata.normalize("NFC", value)'
    native = r'''
        import json
        import unicodedata

        def normalize_rows(rows):
            normalized = []
            for row in rows:
                value = str(row["label"])
                normalized.append({"id": str(row["id"]), "label": LABEL})
            return json.dumps(sorted(normalized, key=lambda row: (row["id"], row["label"])), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    '''.replace("LABEL", label)
    return {
        "README.md": _readme(
            "Normalized export reuse fixture",
            "python3 probe.py --help\n    python3 probe.py representative\n    python3 -m unittest -q\n\n    Indexed local skills: skills/native-format/SKILL.md and skills/preview-accelerator/SKILL.md",
        ),
        "src/__init__.py": "",
        "src/native_format.py": native,
        "data/rows.json": '[{"id": "b", "label": "Cafe\\u0301"}, {"id": "a", "label": "São Paulo"}]\n',
        "skills/native-format/SKILL.md": "# Native normalized export\n\nThe supported implementation is src/native_format.py, function normalize_rows. Its local representative operation is python3 probe.py representative.\n",
        "skills/preview-accelerator/SKILL.md": "# Preview accelerator\n\nThis optional preview-only helper is for a separate dashboard sample. It is not imported by src/native_format.py and does not implement the normalized export operation.\n",
        "skills/preview-accelerator/preview_only.py": 'from fixture_support import emit\n\ndef preview():\n    emit({"operation": "unrelated-preview", "status": "sample"})\n',
        "probe.py": r'''
            import argparse
            import json
            from pathlib import Path
            from fixture_support import emit
            from src.native_format import normalize_rows

            ROOT = Path(__file__).resolve().parent

            def main():
                parser = argparse.ArgumentParser(description="Local native-format representative operation")
                parser.add_argument("operation", choices=("representative",))
                args = parser.parse_args()
                rows = json.loads((ROOT / "data" / "rows.json").read_text(encoding="utf-8"))
                emit({"operation": args.operation, "implementation": "src.native_format.normalize_rows", "output": json.loads(normalize_rows(rows))})

            if __name__ == "__main__":
                main()
        ''',
        "test_native_format.py": r'''
            import json
            import unittest
            from src.native_format import normalize_rows

            class NativeFormatRepresentativeTest(unittest.TestCase):
                def test_order_is_deterministic(self):
                    rendered = json.loads(normalize_rows([{"id": "b", "label": "B"}, {"id": "a", "label": "A"}]))
                    self.assertEqual([row["id"] for row in rendered], ["a", "b"])
        ''',
    }


def _f4(mutant: bool) -> dict[str, str]:
    states = {
        "ledger-target": {"status": "ok", "effect_status": "read_only_confirmed"},
        "catalog-target": {"status": "ok", "effect_status": "read_only_confirmed"},
    } if mutant else {
        "ledger-target": {"status": "scope_required", "effect_status": "not_started"},
        "catalog-target": {"status": "timeout", "effect_status": "unknown"},
    }
    return {
        "README.md": _readme(
            "MCP target fixture",
            "python3 mcp_sim.py --help\n    python3 mcp_sim.py metadata\n    python3 mcp_sim.py list\n    python3 mcp_sim.py read --target ledger-target\n    python3 mcp_sim.py read --target catalog-target\n    python3 -m unittest -q",
        ),
        "requirements.json": json.dumps({"required_targets": [
            {"target": "ledger-target", "role": "export.read"},
            {"target": "catalog-target", "role": "export.read"},
        ], "independent_local_path": "formatting/local_format.py"}, indent=2),
        "connectors/catalog.json": json.dumps([{"name": "calendar-preview", "target": "calendar-target", "purpose": "unrelated preview"}], indent=2),
        "formatting/__init__.py": "",
        "formatting/local_format.py": 'def local_format(value):\n    return " ".join(value.strip().split()).lower()\n',
        "mcp_sim.py": r'''
            import argparse
            import json
            from pathlib import Path
            from fixture_support import emit

            ROOT = Path(__file__).resolve().parent
            STATES = STATES_VALUE

            def main():
                parser = argparse.ArgumentParser(description="Local no-network MCP behavior model")
                parser.add_argument("operation", choices=("metadata", "list", "read"))
                parser.add_argument("--target")
                args = parser.parse_args()
                if args.operation == "metadata":
                    emit({"operation": "metadata", "status": "ok", "protocol": "fixture-mcp/1"})
                    return
                if args.operation == "list":
                    offered = json.loads((ROOT / "connectors" / "catalog.json").read_text(encoding="utf-8"))
                    emit({"operation": "list", "status": "ok", "tools": ["read_target"], "offered_connectors": offered})
                    return
                if args.target not in STATES:
                    parser.error("target is not configured by this fixture")
                emit({"operation": "read", "target": args.target, **STATES[args.target]})

            if __name__ == "__main__":
                main()
        '''.replace("STATES_VALUE", repr(states)),
        "test_formatting.py": r'''
            import unittest
            from formatting.local_format import local_format

            class LocalFormattingTest(unittest.TestCase):
                def test_local_format(self):
                    self.assertEqual(local_format("  Hello   World "), "hello world")
        ''',
    }


_BUILDERS = {"f1": _f1, "f2": _f2, "f3": _f3, "f4": _f4}


def materialize(family: str, root: str | Path, mutant: bool = False) -> dict[str, object]:
    """Write a worker-visible fixture to an empty root."""
    if family not in _BUILDERS:
        raise ValueError(f"unknown fixture family: {family!r}")
    destination = Path(root).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"fixture root must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    _write(destination, {"fixture_support.py": SUPPORT, **_BUILDERS[family](bool(mutant))})
    (destination / "scratch").mkdir(exist_ok=True)
    return {"family": family, "root": str(destination), "task": CASES[family]["task"], "mutant": bool(mutant)}


def _run(root: Path, *arguments: str) -> dict[str, Any]:
    completed = subprocess.run([sys.executable, "-B", *arguments], cwd=root, text=True, capture_output=True, timeout=10, check=False)
    if completed.returncode != 0:
        raise AssertionError(f"probe failed: {arguments!r}: {completed.stderr}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"probe emitted non-JSON stdout: {arguments!r}") from error
    if not isinstance(payload, dict):
        raise AssertionError(f"probe emitted a non-object: {arguments!r}")
    return payload


def _logs(root: Path) -> list[dict[str, Any]]:
    path = root / "scratch" / "probe-log.jsonl"
    if not path.is_file():
        raise AssertionError("probe log was not created under scratch")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _drift(root: Path) -> tuple[list[str], bool]:
    connections = json.loads((root / "connections.json").read_text(encoding="utf-8"))["connections"]
    contract = (root / "contracts" / "service-receipt-v1.md").read_text(encoding="utf-8")
    contract_ready = all(phrase in contract for phrase in ("service-read-receipt/v1", "exactly match", "sufficient current planning evidence"))
    drifted, current = [], False
    for connection in connections:
        receipt = json.loads((root / connection["prior_receipt"]).read_text(encoding="utf-8"))
        effective = connection["effective"]
        binding = receipt.get("binding", {})
        differs = binding.get("target") != effective["target"] or binding.get("role") != effective["role"]
        if differs:
            drifted.append(connection["name"])
        if connection["name"] == "ledger":
            current = contract_ready and receipt.get("schema") == "service-read-receipt/v1" and receipt.get("status") == "ok" and receipt.get("scope") == "current" and receipt.get("evidence_kind") == "current_scoped_test_receipt" and not differs
    return drifted, current


def _observe(family: str, root: Path) -> dict[str, Any]:
    if family == "f1":
        drifted, current = _drift(root)
        return {"changed_read": _run(root, "capability.py", "read", "--target", "fulfillment-current"), "receipt_drift": drifted, "current_receipt": current, "logs": _logs(root)}
    if family == "f2":
        return {"version": _run(root, "probe.py", "version"), "preview": _run(root, "probe.py", "preview"), "write": _run(root, "probe.py", "write-preservation"), "logs": _logs(root)}
    if family == "f3":
        return {"representative": _run(root, "probe.py", "representative"), "logs": _logs(root)}
    required = json.loads((root / "requirements.json").read_text(encoding="utf-8"))["required_targets"]
    reads = [_run(root, "mcp_sim.py", "read", "--target", row["target"]) for row in required]
    return {"metadata": _run(root, "mcp_sim.py", "metadata"), "list": _run(root, "mcp_sim.py", "list"), "reads": reads, "logs": _logs(root)}


def _checks(family: str, reference: dict[str, Any], mutant: dict[str, Any]) -> dict[str, bool]:
    if family == "f1":
        return {
            "reference_receipt_drift": reference["receipt_drift"] == ["fulfillment"] and reference["current_receipt"],
            "one_changed_read": reference["changed_read"].get("target") == "fulfillment-current" and len(reference["logs"]) == 1,
            "mutant_removes_drift": mutant["receipt_drift"] == [] and mutant["current_receipt"],
        }
    if family == "f2":
        return {
            "reference_version_differs": reference["version"].get("manifest_parser") == "3.1.0" and reference["version"].get("active_parser") == "2.6.4",
            "preview_and_write_differ": reference["preview"].get("status") == "accepted" and reference["write"].get("error") == "KeyError" and reference["write"].get("previous_output_preserved") is True,
            "mutant_resolves_both": mutant["version"].get("manifest_parser") == mutant["version"].get("active_parser") and mutant["write"].get("status") == "ok" and mutant["write"].get("previous_output_replaced") is True,
        }
    if family == "f3":
        reference_labels = [row.get("label") for row in reference["representative"].get("output", [])]
        mutant_labels = [row.get("label") for row in mutant["representative"].get("output", [])]
        return {
            "reference_native_unicode": reference["representative"].get("implementation") == "src.native_format.normalize_rows" and reference_labels == ["São Paulo", "Café"],
            "mutant_loses_unicode": mutant_labels != reference_labels and "Café" not in mutant_labels,
            "representative_logged": len(reference["logs"]) == len(mutant["logs"]) == 1,
        }
    statuses = [row.get("status") for row in reference["reads"]]
    mutant_statuses = [row.get("status") for row in mutant["reads"]]
    offered = reference["list"].get("offered_connectors", [])
    return {
        "metadata_and_list_succeed": reference["metadata"].get("status") == reference["list"].get("status") == "ok",
        "reference_reads_are_decisive": statuses == ["scope_required", "timeout"] and reference["reads"][1].get("effect_status") == "unknown",
        "unrelated_connector_remains_unmatched": isinstance(offered, list) and all(row.get("target") not in {"ledger-target", "catalog-target"} for row in offered),
        "mutant_target_reads_succeed": mutant_statuses == ["ok", "ok"],
    }


def calibrate(root: str | Path) -> dict[str, Any]:
    """Exercise each reference/mutant pair and return coordinator-only evidence."""
    parent = Path(root).resolve()
    parent.mkdir(parents=True, exist_ok=True)
    families: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="shiploop-probe-calibration-", dir=parent) as temporary:
        base = Path(temporary)
        for family in CASES:
            try:
                reference_root, mutant_root = base / f"{family}-reference", base / f"{family}-mutant"
                materialize(family, reference_root)
                materialize(family, mutant_root, mutant=True)
                reference, mutant = _observe(family, reference_root), _observe(family, mutant_root)
                checks = _checks(family, reference, mutant)
                if not all(checks.values()):
                    raise AssertionError(", ".join(name for name, passed in checks.items() if not passed))
                families[family] = {"reference": reference, "mutant": mutant, "checks": checks, "passed": True}
            except Exception as error:
                families[family] = {"error": f"{type(error).__name__}: {error}", "passed": False}
    return {
        "schema": "shiploop-probe-decisions-calibration/1",
        "passed": all(row["passed"] for row in families.values()),
        "families": families,
        "limits": "All observations are local simulations. They establish only modeled fixture behavior, never real service, MCP, identity, authorization, deployment, or network state.",
    }
