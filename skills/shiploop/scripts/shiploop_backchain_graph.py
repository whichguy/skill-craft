#!/usr/bin/env python3
"""ShipLoop's record-only ``backchain-check`` verb over Backchain's structural check.

The check is Backchain's own (``skills/backchain/scripts/backchain_graph.py``, the port of the Backchain
checkout's ``harness/lib.js``), found beside this skill in the plugin install.  ``shiploop backchain-check
--candidate PATH`` records only: it prints a receipt, writes a snapshot of the bytes checked and the receipt under
``<run>/backchain/<action>/``, and never changes run state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Backchain sits beside ShipLoop in the plugin install: the location rule of shiploop_prompts.backchain_skills_root.
BACKCHAIN_SCRIPTS = Path(__file__).resolve().parents[2] / "backchain" / "scripts"
if str(BACKCHAIN_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BACKCHAIN_SCRIPTS))
import backchain_graph as graph  # noqa: E402

SCHEMA = "shiploop-backchain-check/v1"
EXIT_CLEAN = 0
EXIT_FINDINGS = 1
EXIT_UNAVAILABLE = 3
_ACTION_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,159}")


# ---------------------------------------------------------------- receipt and CLI

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def receipt(data: bytes, candidate: str) -> Dict[str, Any]:
    """Check candidate bytes; raises CheckUnavailable when they are not JSON."""
    packaged = graph.package(graph.loads(data))
    structure = graph.validate_structure(packaged)
    return {
        "schema": SCHEMA,
        "candidate": candidate,
        "candidate_sha256": _sha256(data),
        "packaged_sha256": _sha256(graph.js_stringify(packaged).encode("utf-8")),
        "ok": structure["ok"],
        "failures": structure["failures"],
        "completion": graph.completion_status(packaged, structure)["status"],
        "parallel_groups": graph.compute_parallel_groups(packaged),
        "counts": graph.counts(packaged),
        "unconfirmed_produces": graph.unconfirmed_produces(packaged),
    }


def check(path: Any) -> Dict[str, Any]:
    """Read and check one candidate file and return its receipt."""
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise graph.CheckUnavailable(f"cannot read {path}: {exc.strerror or exc}") from exc
    return receipt(data, os.fspath(path))


def receipt_text(record: Dict[str, Any]) -> str:
    """The receipt record as indented JSON with a trailing newline."""
    return json.dumps(record, indent=2) + "\n"


def _current_action(core: Any, run_dir: Optional[str]) -> Tuple[Optional[Path], Optional[str], str]:
    """(run root, current action id, reason) from saved state; reads only."""
    import shiploop_navigator as navigator
    import shiploop_store as store

    root = Path(core.run_dir_from_arg(run_dir, walk=True)).resolve()
    if not (root / "state.md").is_file():
        return None, None, f"no ShipLoop run at {root}"
    try:
        loader = getattr(core, "load_state", None)
        if callable(loader):
            state = loader(root)
        else:
            state = store.read_record(root / "state.md")
            navigator.validate(state)
            import shiploop_current_spec as current_spec

            current_spec.assert_binding(root, state)
        action = navigator.current_action(state)["id"]
    except SystemExit as exc:
        return None, None, f"run state at {root} cannot be loaded: {exc}"
    except Exception as exc:  # noqa: BLE001 - any unreadable state only skips the files
        return None, None, f"run state at {root} cannot be read: {type(exc).__name__}: {exc}"
    if not isinstance(action, str) or not _ACTION_RE.fullmatch(action):
        return None, None, "the run has no current action"
    return root, action, ""


def _record_dir(root: Path, action: str) -> Path:
    directory = root / "backchain" / action
    for part in (root / "backchain", directory):
        if part.is_symlink():
            raise OSError(f"refusing symlink {part}")
    return directory


def record(root: Path, action: str, data: bytes, record_: Dict[str, Any]) -> Path:
    """Write ``candidate-<sha12>.json`` once and ``check-<sha12>.json`` when it changed; returns the receipt path."""
    import shiploop_store as store
    import shiploop_navigator as navigator
    import shiploop_current_spec as current_spec

    state = store.read_record(root / "state.md")
    navigator.validate(state)
    current_spec.assert_binding(root, state)

    directory = _record_dir(root, action)
    digest = record_["candidate_sha256"][:12]
    snapshot = directory / f"candidate-{digest}.json"
    if snapshot.is_symlink():
        raise OSError(f"refusing symlink {snapshot}")
    if snapshot.exists():
        if snapshot.read_bytes() != data:
            raise OSError(f"{snapshot} holds other bytes")
    else:
        store.atomic_write_text(snapshot, data.decode("utf-8"))
    path = directory / f"check-{digest}.json"
    text = receipt_text(record_)
    if path.is_symlink():
        raise OSError(f"refusing symlink {path}")
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        store.atomic_write_text(path, text)
    return path


def summary(record_: Dict[str, Any]) -> str:
    """One-line verdict for a check record: valid or invalid with its failed invariants, plus step and parallel-
    group counts.
    """
    counts = record_["counts"]
    if record_["ok"]:
        verdict = f"valid, {record_['completion']}"
    else:
        invariants = sorted({failure["invariant"] for failure in record_["failures"]})
        verdict = (f"invalid, {len(record_['failures'])} failure(s) on invariant(s) "
                   + ", ".join(map(str, invariants)))
    return (f"ShipLoop backchain-check: {verdict}; {counts['steps']} steps, "
            f"{len(record_['parallel_groups'])} parallel groups")


def main(core: Any, argv: Optional[List[str]] = None) -> int:
    """``shiploop backchain-check``: exit 0 valid, 1 invalid structure, 3 could not run."""
    parser = argparse.ArgumentParser(
        prog="shiploop backchain-check",
        description="Record-only check of a Backchain candidate plan against Backchain's structural "
                    "invariants (packaged first). Exit 0 valid, 1 invalid structure, 3 could not run.")
    parser.add_argument("--candidate", required=True, help="the candidate plan JSON file")
    parser.add_argument("--run-dir", help="the ShipLoop run; found from the working directory when omitted")
    args = parser.parse_args(list(argv or ()))
    try:
        data = Path(args.candidate).read_bytes()
        record_ = receipt(data, os.fspath(Path(args.candidate).absolute()))
    except OSError as exc:
        print(f"ShipLoop backchain-check could not run: cannot read {args.candidate}: {exc.strerror or exc}; "
              "this is not a finding", file=sys.stderr)
        return EXIT_UNAVAILABLE
    except graph.CheckUnavailable as exc:
        hint = ""
        if str(exc).startswith("not JSON"):
            # Both round-1 runs passed the Markdown plan note; say what the candidate is and where its shape is defined.
            from shiploop_prompts import backchain_skills_root
            hint = ("; the candidate is the Backchain plan graph as a JSON file, not a Markdown plan note and not a prose plan (its shape: "
                    "Backchain SKILL.md, \"Plan document shape\"; schema in "
                    f"{backchain_skills_root() / 'backchain' / 'prompts' / 'generator.v1.md'})")
        print(f"ShipLoop backchain-check could not run: {exc}{hint}; this is not a finding", file=sys.stderr)
        return EXIT_UNAVAILABLE
    sys.stdout.write(receipt_text(record_))
    root, action, reason = _current_action(core, args.run_dir)
    note = f"not recorded: {reason}"
    if root is not None and action is not None:
        try:
            note = f"receipt {record(root, action, data, record_)}"
        except Exception as exc:  # noqa: BLE001 - recording is best effort; the receipt is printed
            note = f"not recorded: {type(exc).__name__}: {exc}"
    print(f"{summary(record_)}; {note}", file=sys.stderr)
    return EXIT_CLEAN if record_["ok"] else EXIT_FINDINGS
