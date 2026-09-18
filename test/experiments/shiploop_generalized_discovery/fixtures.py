#!/usr/bin/env python3
"""Small public fixtures for generalized ShipLoop discovery trials.

Each workspace is self-contained and contains only local source plus a read-only
probe.  ``mutant=True`` changes one observable behavior while retaining the
same layout and probe interface, so a coordinator can calibrate an oracle.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


TASKS = {
    "f1": "Plan adding JSON output to this existing exporter. Do not edit files.",
    "f2": "Plan adding a receipt field through this existing event flow. Do not edit files.",
    "f3": "Plan adding an export operation to the referenced managed system. Do not edit files or seek additional access.",
    "f4": "Plan adding a refresh indicator to this existing application. Do not edit files.",
}


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, body in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(dedent(body).lstrip(), encoding="utf-8")


def _readme(title: str, task: str, probes: str, note: str = "") -> str:
    return f"""# {title}

This is a small local discovery fixture. {note}

Task: {task}

Inspect the checked-in sources first. The only supported runtime observation is
the local read-only probe below; it neither contacts a network service nor needs
an account, installation, credential, or permission change.

```sh
{probes}
```

Use observations as evidence, distinguish facts from inferences, and leave a
consequential unknown open when the supplied route cannot establish it.
"""


def _f1(mutant: bool) -> dict[str, str]:
    active_version = "3.1.0" if mutant else "2.6.4"
    return {
        "README.md": _readme(
            "Ledger batch export",
            TASKS["f1"],
            "python3 probe.py dependency\npython3 probe.py permissions\npython3 probe.py export",
        ),
        "pyproject.toml": """
            [project]
            name = "ledger-export"
            requires-python = ">=3.11"
            dependencies = ["record-parser==3.1.0"]
        """,
        "bin/run_export.py": """
            import json
            import sys
            from pathlib import Path

            ROOT = Path(__file__).resolve().parents[1]
            if str(ROOT) not in sys.path:
                sys.path.insert(0, str(ROOT))

            from app.export_writer import write_export
            from runtime.parser import VERSION, parse_rows

            ACTIVE_PARSER_VERSION = VERSION

            def preview(destination):
                return write_export(destination, parse_rows("id,total\\n1,42\\n"), dry_run=True)

            if __name__ == "__main__":
                destination = ROOT / "workspace" / "exports" / "preview.txt"
                print(json.dumps(preview(destination), sort_keys=True))
        """,
        "bin/__init__.py": "",
        "runtime/__init__.py": "",
        "runtime/parser.py": f"""
            # This bundled parser is selected by bin/run_export.py.
            VERSION = "{active_version}"

            def parse_rows(csv_text):
                lines = [line.split(",") for line in csv_text.strip().splitlines()]
                return [dict(zip(lines[0], row)) for row in lines[1:]]
        """,
        "app/__init__.py": "",
        "app/export_writer.py": """
            from pathlib import Path

            def write_export(destination, rows, *, dry_run):
                # Existing callers use this wrapper so finished files are replaced atomically.
                target = Path(destination)
                result = {"target": str(target), "rows": len(rows), "write_mode": "atomic_wrapper", "committed": not dry_run}
                if not dry_run:
                    temporary = target.with_suffix(".tmp")
                    temporary.write_text("\\n".join(row["id"] for row in rows) + "\\n", encoding="utf-8")
                    temporary.replace(target)
                return result
        """,
        "config/export-policy.json": """
            {"outputDirectory": "workspace/exports", "owner": "local-batch-user", "retentionDays": 14}
        """,
        "probe.py": """
            import argparse
            import json
            import os
            import stat
            from pathlib import Path

            from bin.run_export import ACTIVE_PARSER_VERSION, preview

            ROOT = Path(__file__).resolve().parent
            OUTPUT = ROOT / "workspace" / "exports" / "preview.txt"

            def observe(command):
                if command == "dependency":
                    return {"operation": command, "launcher": "bin/run_export.py", "active_parser_version": ACTIVE_PARSER_VERSION}
                if command == "permissions":
                    directory = OUTPUT.parent
                    return {"operation": command, "effective_uid": os.geteuid(), "directory_mode": oct(stat.S_IMODE(directory.stat().st_mode)), "writable": os.access(directory, os.W_OK)}
                return {"operation": command, **preview(OUTPUT)}

            parser = argparse.ArgumentParser(description="Read-only local fixture observations")
            parser.add_argument("command", choices=("dependency", "permissions", "export"))
            args = parser.parse_args()
            print(json.dumps(observe(args.command), sort_keys=True))
        """,
    }


def _f2(mutant: bool) -> dict[str, str]:
    deduplicate = "False" if mutant else "True"
    return {
        "README.md": _readme(
            "Receipt event worker",
            TASKS["f2"],
            "python3 probe.py runtime\npython3 probe.py retry",
            "The retry probe models local in-memory record handling. It can distinguish producer acceptance from modeled consumer handling, but cannot establish process-surviving durability.",
        ),
        "producer/manifest.json": """
            {"producerRuntime": "nodejs-20", "payloadSchema": 2, "topic": "receipt.created"}
        """,
        "host/selection.json": """
            {"consumerRuntime": "python3.11", "component": "normalize-receipt-v2", "topic": "receipt.created"}
        """,
        "components/__init__.py": "",
        "components/normalize_receipt_v2.py": """
            COMPONENT = "normalize-receipt-v2"
            SUPPORTED_SCHEMA = 2

            def normalize(event):
                if event["schema"] != SUPPORTED_SCHEMA:
                    raise ValueError("unsupported schema")
                return {"receipt_id": event["id"], "amount": event["amount"]}
        """,
        "worker.py": f"""
            from components.normalize_receipt_v2 import COMPONENT, SUPPORTED_SCHEMA, normalize

            DEDUPLICATE = {deduplicate}

            def process_retrying(event):
                effects = []
                seen = set()
                for attempt in (1, 2):
                    record = normalize(event)
                    if not DEDUPLICATE or record["receipt_id"] not in seen:
                        effects.append(record)
                        seen.add(record["receipt_id"])
                    # Attempt one loses its consumer acknowledgement after the durable effect.
                return {{
                    "producer_ack": "accepted",
                    "consumer_attempts": 2,
                    "recorded_effects": len(effects),
                    "consumer_completion": "recorded_locally",
                }}
        """,
        "probe.py": """
            import argparse
            import json
            from pathlib import Path

            from components.normalize_receipt_v2 import COMPONENT, SUPPORTED_SCHEMA
            from worker import process_retrying

            ROOT = Path(__file__).resolve().parent

            def observe(command):
                if command == "runtime":
                    selected = json.loads((ROOT / "host" / "selection.json").read_text(encoding="utf-8"))
                    return {"operation": command, "consumer_runtime": selected["consumerRuntime"], "selected_component": COMPONENT, "supported_schema": SUPPORTED_SCHEMA}
                event = {"id": "receipt-7", "schema": 2, "amount": 42}
                return {"operation": command, **process_retrying(event)}

            parser = argparse.ArgumentParser(description="Read-only local fixture observations")
            parser.add_argument("command", choices=("runtime", "retry"))
            args = parser.parse_args()
            print(json.dumps(observe(args.command), sort_keys=True))
        """,
    }


def _f3(mutant: bool) -> dict[str, str]:
    allow_data = "True" if mutant else "False"
    return {
        "README.md": _readme(
            "Managed-target reader",
            TASKS["f3"],
            "python3 probe.py metadata\npython3 probe.py task-data\npython3 probe.py connectors",
            "It simulates a managed target entirely in local source; it is not a vendor, account, or network connection.",
        ),
        "target_simulator.py": f"""
            # Local simulation only. No network client, credential, or account exists here.
            ALLOW_TASK_DATA = {allow_data}

            def metadata():
                return {{"operation": "metadata", "status": "ok", "target": "managed-synthetic-target", "reason": None, "record_count": None}}

            def task_data():
                if not ALLOW_TASK_DATA:
                    return {{"operation": "task_data", "status": "denied", "target": "managed-synthetic-target", "reason": "scope_required", "record_count": None}}
                return {{"operation": "task_data", "status": "ok", "target": "managed-synthetic-target", "reason": None, "record_count": 1}}
        """,
        "connectors/catalog.json": """
            [{"name": "sample-export", "target": "unrelated-local-sample", "purpose": "read a separate demonstration dataset", "installed": false}]
        """,
        "probe.py": """
            import argparse
            import json
            from pathlib import Path

            import target_simulator

            ROOT = Path(__file__).resolve().parent

            def observe(command):
                if command == "metadata":
                    return target_simulator.metadata()
                if command == "task-data":
                    return target_simulator.task_data()
                catalog = json.loads((ROOT / "connectors" / "catalog.json").read_text(encoding="utf-8"))
                return {"operation": "connectors", "connectors": catalog}

            parser = argparse.ArgumentParser(description="Read-only local fixture observations")
            parser.add_argument("command", choices=("metadata", "task-data", "connectors"))
            args = parser.parse_args()
            print(json.dumps(observe(args.command), sort_keys=True))
        """,
    }


def _f4(mutant: bool) -> dict[str, str]:
    python_guard = "False" if mutant else "True"
    javascript_guard = "false" if mutant else "true"
    return {
        "README.md": _readme(
            "Board refresh control",
            TASKS["f4"],
            "python3 probe.py completion-order\npython3 probe.py storage\npython3 probe.py component",
            "The probe is a local model of selected behavior. It does not prove browser rendering, network delivery, deployed service behavior, process-surviving storage, or cache expiry.",
        ),
        "web/client.js": f"""
            export function createBoardRefresh(fetchBoard, render) {{
              let latestRequest = 0;
              const useSequenceGuard = {javascript_guard};
              return async function refresh() {{
                const request = ++latestRequest;
                const state = await fetchBoard();
                if (useSequenceGuard && request !== latestRequest) return {{ applied: false, request }};
                render(state);
                return {{ applied: true, request }};
              }};
            }}
        """,
        "web/components/board_panel.js": """
            export function BoardPanel(state) {
              return { component: "BoardPanel", className: "board-panel", version: state.version };
            }
        """,
        "web/styles/board-panel.css": """
            .board-panel { border: 1px solid #2b4b63; padding: 1rem; }
        """,
        "web/package.json": """
            {"private": true, "type": "module"}
        """,
        "client_model.py": f"""
            USE_SEQUENCE_GUARD = {python_guard}

            class RefreshController:
                def __init__(self):
                    self.latest_request = 0
                    self.rendered_version = None

                def start(self):
                    self.latest_request += 1
                    return self.latest_request

                def complete(self, request, state):
                    applied = not USE_SEQUENCE_GUARD or request == self.latest_request
                    if applied:
                        self.rendered_version = state["version"]
                    return {{"request": request, "applied": applied, "rendered_version": self.rendered_version}}
        """,
        "service/__init__.py": "",
        "service/store.py": """
            # This local model has no process-surviving storage implementation.
            class DurableStore:
                def read_board(self):
                    return {"id": "main", "version": 7, "pieces": 24}
        """,
        "service/cache.py": """
            TTL_SECONDS = 30

            class BoardCache:
                def __init__(self):
                    self.values = {}

                def get_or_load(self, key, loader):
                    if key in self.values:
                        return self.values[key], True
                    self.values[key] = loader()
                    return self.values[key], False
        """,
        "probe.py": """
            import argparse
            import json

            from client_model import RefreshController
            from service.cache import BoardCache, TTL_SECONDS
            from service.store import DurableStore

            def observe(command):
                if command == "completion-order":
                    controller = RefreshController()
                    first, second = controller.start(), controller.start()
                    newer = controller.complete(second, {"version": 2})
                    older = controller.complete(first, {"version": 1})
                    return {"operation": command, "completion_order": [newer, older], "rendered_version": controller.rendered_version}
                if command == "storage":
                    cache, store = BoardCache(), DurableStore()
                    first, first_hit = cache.get_or_load("board:main", store.read_board)
                    second, second_hit = cache.get_or_load("board:main", store.read_board)
                    return {"operation": command, "durable_version": first["version"], "first_read_cache_hit": first_hit, "second_read_cache_hit": second_hit, "cache_ttl_seconds": TTL_SECONDS}
                return {"operation": command, "component": "BoardPanel", "stylesheet": "web/styles/board-panel.css"}

            parser = argparse.ArgumentParser(description="Read-only local fixture observations")
            parser.add_argument("command", choices=("completion-order", "storage", "component"))
            args = parser.parse_args()
            print(json.dumps(observe(args.command), sort_keys=True))
        """,
    }


_BUILDERS = {"f1": _f1, "f2": _f2, "f3": _f3, "f4": _f4}


def materialize(family: str, root: str | Path, *, mutant: bool = False) -> dict[str, object]:
    """Create one empty-root fixture and return its public task and safe probes.

    The caller owns the root. Refusing a nonempty root prevents accidental mixing
    of variants or trial evidence.
    """

    if family not in _BUILDERS:
        raise ValueError(f"unknown fixture family: {family!r}")
    destination = Path(root).resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"fixture root must be empty: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    _write(destination, _BUILDERS[family](bool(mutant)))
    if family == "f1":
        exports = destination / "workspace" / "exports"
        exports.mkdir(parents=True, exist_ok=True)
        exports.chmod(0o750)
    if family == "f3":
        # Intentionally empty: the target exists only through the local reader.
        (destination / "product").mkdir(exist_ok=True)
    return {
        "family": family,
        "root": str(destination),
        "task": TASKS[family],
        "probes": {
            "f1": ("dependency", "permissions", "export"),
            "f2": ("runtime", "retry"),
            "f3": ("metadata", "task-data", "connectors"),
            "f4": ("completion-order", "storage", "component"),
        }[family],
    }
