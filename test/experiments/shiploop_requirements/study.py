#!/usr/bin/env python3
"""Prepare and audit bounded, no-model ShipLoop requirements-study fixtures."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from typing import Any, Iterator


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SKILL = ROOT / "skills" / "shiploop"
INPUTS = {
    "plan": HERE / "README.md",
    "oracle": HERE / "oracle.md",
    "judge_instructions": HERE / "judge-instructions.md",
    "helper": HERE / "study.py",
}
IGNORE = {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}
STUDY = "shiploop-requirements-study-v1"

CASES = {
    "preserve": "Add a category filter to the offline inventory catalog.",
    "override": "Change catalog filtering p99 from 420 ms to 275 ms at the existing workload, and add a category filter.",
    "ambiguity": "Make catalog filtering faster and add a category filter.",
    "proportional": "Add sorting to the existing local command-line text tool.",
}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _tree(root: Path) -> dict[str, Any]:
    """Return a stable regular-file inventory; snapshots reject links and caches."""
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"not a regular directory: {root}")
    files: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in IGNORE or part.endswith(".pyc") for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError(f"snapshot rejects symlink: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"snapshot rejects non-file: {path}")
        files[relative.as_posix()] = _sha(path.read_bytes())
    digest = hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    return {"digest": digest, "files": files}


def _source_snapshot() -> dict[str, Any]:
    return {"skill": _tree(SKILL), **{name: _sha(path.read_bytes()) for name, path in INPUTS.items()}}


def _head() -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True, capture_output=True,
        timeout=15,
    )
    if completed.returncode or len(completed.stdout.strip()) != 40:
        raise RuntimeError("cannot record exact Git HEAD: " + completed.stderr.strip())
    return completed.stdout.strip()


def _ignore(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORE or name.endswith(".pyc")}


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"expected regular file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _new_output(output: Path) -> Path:
    output = output.expanduser().resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("study output must be outside the product repository")
    if output.exists():
        if output.is_symlink() or not output.is_dir():
            raise ValueError(f"output is not a regular directory: {output}")
        if any(output.iterdir()):
            raise FileExistsError(f"output must be new or empty: {output}")
    else:
        output.mkdir(parents=True)
    return output


def initialize(output: Path) -> dict[str, Any]:
    """Freeze the selected source only when it stays unchanged across the copy."""
    output = _new_output(output)
    before = _source_snapshot()
    head = _head()
    staging = Path(tempfile.mkdtemp(prefix=".shiploop-requirements-", dir=output.parent))
    try:
        shutil.copytree(SKILL, staging / "frozen-skill", ignore=_ignore)
        frozen_inputs = staging / "frozen-inputs"
        frozen_inputs.mkdir()
        for name, path in INPUTS.items():
            shutil.copy2(path, frozen_inputs / ("study-plan.md" if name == "plan" else path.name))
        after = _source_snapshot()
        if after != before:
            raise RuntimeError("live source changed during snapshot; output remains empty")
        frozen_skill = _tree(staging / "frozen-skill")
        if frozen_skill != before["skill"]:
            raise RuntimeError("frozen skill does not match verified source snapshot")
        manifest = {
            "study": STUDY,
            "outcome": "UNKNOWN",
            "git_head": head,
            "source_before": before,
            "source_after": after,
            "frozen_skill": frozen_skill,
            "frozen_inputs": {name: _sha((frozen_inputs / ("study-plan.md" if name == "plan" else path.name)).read_bytes()) for name, path in INPUTS.items()},
            "note": "Frozen before participant launch; no participant, callback, or Improve run has occurred.",
        }
        _write_json(staging / "manifest.json", manifest)
        for item in staging.iterdir():
            os.replace(item, output / item.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    return {"outcome": "UNKNOWN", "summary": "initialized frozen study inputs; no trials launched", "output": str(output)}


def _manifest(output: Path) -> dict[str, Any]:
    manifest = _read_json(output / "manifest.json")
    if manifest.get("study") != STUDY:
        raise ValueError("unexpected study manifest")
    if _tree(output / "frozen-skill") != manifest.get("frozen_skill"):
        raise ValueError("frozen skill snapshot changed")
    for name, path in INPUTS.items():
        frozen = output / "frozen-inputs" / ("study-plan.md" if name == "plan" else path.name)
        if _sha(frozen.read_bytes()) != manifest["frozen_inputs"][name]:
            raise ValueError("frozen study input changed: " + name)
    return manifest


@contextmanager
def _navigator(frozen_skill: Path) -> Iterator[Any]:
    """Import the frozen package without leaving bytecode or module cache changes."""
    names = [name for name in sys.modules if name == "shiploop_navigator" or name.startswith("shiploop_")]
    saved = {name: sys.modules.pop(name) for name in names}
    old_path, old_bytecode = list(sys.path), sys.dont_write_bytecode
    sys.path.insert(0, str(frozen_skill / "scripts"))
    sys.dont_write_bytecode = True
    try:
        yield importlib.import_module("shiploop_navigator")
    finally:
        for name in list(sys.modules):
            if name == "shiploop_navigator" or name.startswith("shiploop_"):
                del sys.modules[name]
        sys.modules.update(saved)
        sys.path[:] = old_path
        sys.dont_write_bytecode = old_bytecode


def _synthetic_state(navigator: Any, repo: Path, request: str, target: str) -> dict[str, Any]:
    """Use only pure v3 APIs to select a trial cursor; no runtime work is implied."""
    state = navigator.new_state(str(repo), request, protocol_version=3, improve_skill="")
    while navigator.current_stage(state) != target:
        stage, action = navigator.current_stage(state), navigator.current_action(state)["id"]
        seed = {"outcome": "done", "summary": f"FIXTURE SETUP ONLY: synthetic {stage} producer.", "evidence_refs": [f"fixture://{stage}"]}
        waiting = navigator.apply(state, action, seed)
        receipt = {
            "summary": f"FIXTURE SETUP ONLY: no Improve ran for {stage}.",
            "review_refs": [f"fixture://review/{stage}"],
            "check_refs": [f"fixture://check/{stage}"],
            "lessons": "Fixture setup only; not an observed review or product evidence.",
        }
        state = navigator.finish_improve(waiting, action, receipt)
    return state


def _fixture_setup(stage: str) -> str:
    return f"""# Synthetic fixture setup\n\nThis run is a controlled no-model study fixture. Pure navigator APIs selected `{stage}`\nusing synthetic producer results and synthetic Improve receipts. Those records are fixture\nsetup only: no callback, Improve child, product operation, test, or acceptance occurred.\n\nThe current packet is the only assigned producer action. Do not use this setup as evidence.\n"""


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _catalog_files(case: str) -> dict[str, str]:
    links = """- [Accepted catalog requirements](docs/catalog-requirements.md)\n- [Accepted diagnostics policy](docs/diagnostics-policy.md)\n- [Accepted accessibility requirements](docs/accessibility.md)\n- [TSV export contract](docs/export.md)\n"""
    if case == "ambiguity":
        links += "- [Accepted support retention policy](docs/support-policy.md)\n"
    if case == "override":
        links += "- [Later design draft](docs/later-design-draft.md)\n"
    files = {
        "README.md": "# Offline inventory catalog\n\nThis README indexes the maintained product requirements.\n\n" + links,
        "docs/catalog-requirements.md": """# Catalog requirements\n\nStatus: accepted product requirement.\n\nCatalog filtering must complete at p99 in 420 ms or less for 7,500 locally stored\nitems with descriptions up to 3 KiB each on the documented [kiosk profile](kiosk-profile.md). The keyboard\ncategory picker supports keyboard navigation and always exposes visible focus. No catalog\ndata or diagnostic data is sent over a network. Cancelling a category-filter interaction\nleaves the selected category and result list unchanged.\n""",
        "docs/diagnostics-policy.md": """# Diagnostics policy\n\nStatus: accepted product policy.\n\nDiagnostics must not retain raw filter text or item descriptions. Local diagnostic records\nare retained for 72 hours. A manually exported diagnostic file is controlled by the user,\nincluding its deletion.\n""",
        "docs/accessibility.md": """# Accessibility requirements\n\nStatus: accepted product requirement.\n\nThe category picker remains keyboard navigable with visible focus. See the\n[keyboard appendix](keyboard-appendix.md) for additional interaction detail.\n""",
        "docs/export.md": """# TSV export\n\nStatus: accepted product contract.\n\nTSV export writes UTF-8 tab-separated rows without changing inventory records.\n""",
        "LICENSE.md": """Inventory Catalog License\n\nThis exact license paragraph permits internal offline inventory use and no other grant.\n""",
        "src/diagnostics.py": """def record_diagnostic(filter_text, item):\n    # Retain filter details to help support diagnose catalog behavior.\n    return {\"filter_text\": filter_text, \"item_description\": item.description}\n""",
        "tests/test_diagnostics.py": """def test_legacy_diagnostics_capture_raw_filter_and_description():\n    assert record_diagnostic(\"red tools\", item) == {\n        \"filter_text\": \"red tools\", \"item_description\": item.description\n    }\n""",
    }
    files["docs/kiosk-profile.md"] = "# Kiosk profile\n\nStatus: accepted measurement environment. Profile K-2 uses two logical CPU cores,\n4 GiB RAM, the deployed kiosk browser, a warmed local catalog, and no network.\nLatency is measured from filter confirmation to the completed result-list update.\nNo current benchmark measurements are available in this repository.\n"
    if case != "ambiguity":
        files["docs/keyboard-appendix.md"] = "# Keyboard appendix\n\nStatus: accepted detail. Arrow keys move category focus.\n"
    else:
        files["docs/support-policy.md"] = """# Support retention policy\n\nStatus: accepted product policy.\n\nLocal diagnostic records are retained for fourteen days. This policy does not identify\na superseded retention policy.\n"""
    if case == "override":
        files["docs/later-design-draft.md"] = """# Later catalog design draft\n\nStatus: draft proposal only; not accepted product intent.\n\nA future simplification could remove keyboard category-picker navigation.\n"""
    return files


def _proportional_files() -> dict[str, str]:
    return {
        "README.md": """# line-sort\n\nStatus: accepted product contract. This local command-line tool reads UTF-8 input on\nstdin and writes output on stdout. Sorting preserves stable order for equal keys. It uses\nno network, never overwrites input files, and reports a streaming output failure with a\nnonzero exit. In-memory sorting is allowed.\n""",
        "src/line_sort.py": "def sort_lines(lines):\n    return sorted(lines, key=lambda row: row.key)\n",
        "tests/test_line_sort.py": """# Expected checks: empty input, Unicode, stable equal keys, and output failure.\n""",
        "notes/future-timing.md": "# Proposal\n\nA future timing target may be useful. It is not accepted.\n",
    }


def _build_repo(repo: Path, case: str) -> dict[str, list[str]]:
    if case == "proportional":
        _write_files(repo, _proportional_files())
        return {"required": ["README.md", "tests/test_line_sort.py"], "optional": ["notes/future-timing.md"], "missing": []}
    _write_files(repo, _catalog_files(case))
    required = ["README.md", "docs/catalog-requirements.md", "docs/kiosk-profile.md", "docs/diagnostics-policy.md", "docs/accessibility.md", "docs/export.md", "LICENSE.md"]
    optional = ["src/diagnostics.py", "tests/test_diagnostics.py"]
    missing: list[str] = []
    if case == "ambiguity":
        required.append("docs/support-policy.md")
        missing.append("docs/keyboard-appendix.md")
    else:
        required.append("docs/keyboard-appendix.md")
    if case == "override":
        optional.append("docs/later-design-draft.md")
    return {"required": required, "optional": optional, "missing": missing}


def _bootstrap(trial: Path, stage: str, frozen_skill: Path) -> str:
    cold = "" if stage == "discovery" else """Read `previous-discovery-notes/` only as read-only locator/context. It is not accepted\nproduct authority and does not replace inspecting the maintained product sources yourself.\n"""
    return f"""# Participant bootstrap: {stage}\n\nPerform only the current `{stage}` producer in `run/packet.md`. This is a bounded study\nfixture, not a runnable ShipLoop session. Read only this bootstrap, the assigned product\nrepository `{trial / 'repo'}`, the shared read-only frozen skill `{frozen_skill}`, and\nthis trial's run/notes material. Do not modify the frozen skill, product files, navigator\nstate, packets, results, or inbox.\n\n{cold}Write only `notes/sources.md`, `notes/artifact.md`, `notes/status.md`, and\n`notes/result.json`. `sources.md` must list actual product files personally inspected in\nthis session and their status. Put findings, planned checks, unresolved questions, and any\nneeded user questions in `artifact.md`; do not contact a real user or another task.\n`status.md` must contain `current_stage_status: drafted for review` (or `blocked`) and\n`feature_acceptance_status: unproven`. `result.json` must be exactly an object with\n`outcome`, `summary`, and `evidence_refs`; use actual absolute file paths in evidence refs.\n\nDo not call the printed callback or recovery command, invoke Improve, use network, read\nmemory, spawn agents, run a model/harness alternative, edit product code, or claim a test\nor whole feature passed. Stop after writing the current producer outputs.\n"""


def _make_trial(output: Path, stage: str, case: str, repo: Path, prior_notes: Path | None = None) -> Path:
    trial = output / "trials" / stage / case
    if trial.exists():
        raise FileExistsError(f"trial already exists: {trial}")
    trial.mkdir(parents=True)
    trial_repo = trial / "repo"
    if repo == trial_repo:
        pass
    else:
        shutil.copytree(repo, trial_repo, ignore=_ignore)
    if prior_notes is not None:
        shutil.copytree(prior_notes, trial / "previous-discovery-notes", ignore=_ignore)
        (trial / "cold-context.md").write_text(
            "# Cold spec boundary\n\nThis is separately seeded fixture setup, not a live discovery-to-spec transition. "
            "Previous notes are read-only locator/context and do not become approved product authority.\n",
            encoding="utf-8",
        )
    run, notes = trial / "run", trial / "notes"
    run.mkdir()
    notes.mkdir()
    frozen = output / "frozen-skill"
    before = _tree(frozen)["digest"]
    with _navigator(frozen) as navigator:
        state = _synthetic_state(navigator, trial_repo, CASES[case], stage)
        navigator.save(run, state, {"fixture-setup.md": _fixture_setup(stage)})
        packet = navigator.render(SimpleNamespace(PACKAGE_ROOT=frozen), run, state)
    if _tree(frozen)["digest"] != before:
        raise RuntimeError("frozen skill changed while rendering packet")
    packet_path = run / "packet.md"
    packet_path.write_text(packet, encoding="utf-8")
    metadata: dict[str, Any] = {
        "id": f"{stage}/{case}", "stage": stage, "case": case,
        "input_tree": _tree(trial_repo), "packet": "run/packet.md",
        "packet_sha256": _sha(packet.encode()), "frozen_skill_digest": before,
        "semantic_correctness": "NOT_GRADED",
    }
    if prior_notes is not None:
        metadata["previous_notes_tree"] = _tree(trial / "previous-discovery-notes")
    _write_json(trial / "input.json", metadata)
    (trial / "bootstrap.md").write_text(_bootstrap(trial, stage, frozen), encoding="utf-8")
    return trial


def prepare(output: Path) -> dict[str, Any]:
    """Create fixture repositories and real frozen-v3 discovery packets only."""
    output = output.expanduser().resolve()
    _manifest(output)
    if (output / "trials").exists():
        raise FileExistsError("trials already prepared")
    source_map: dict[str, Any] = {}
    for case in CASES:
        source = output / ".fixture-source" / case
        source.mkdir(parents=True)
        source_map[case] = _build_repo(source, case)
        _make_trial(output, "discovery", case, source)
    shutil.rmtree(output / ".fixture-source")
    _write_json(output / "judges" / "source-map.json", {"study": STUDY, "cases": source_map, "note": "Fixture file map only; consult frozen oracle separately."})
    return {"outcome": "UNKNOWN", "summary": "prepared four discovery fixtures and packets; no models or callbacks launched", "output": str(output)}


def _note_files(trial: Path) -> dict[str, Path]:
    return {name: trial / "notes" / name for name in ("sources.md", "artifact.md", "status.md", "result.json")}


def _path_from_ref(reference: str, trial: Path, frozen: Path) -> bool:
    target = reference.split("#", 1)[0]
    if ":" in target and target.rsplit(":", 1)[1].isdigit():
        target = target.rsplit(":", 1)[0]
    path = Path(target)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        return False
    resolved = path.resolve()
    return any(_within(resolved, root.resolve()) for root in (trial, frozen))


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _validate_notes(output: Path, trial: Path) -> dict[str, Any]:
    files = _note_files(trial)
    for name, path in files.items():
        if path.is_symlink() or not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise ValueError(f"missing or empty required note: {name}")
    sources = files["sources.md"].read_text(encoding="utf-8").lower()
    if "status" not in sources or ".md" not in sources:
        raise ValueError("sources.md must record inspected product paths and status")
    status = files["status.md"].read_text(encoding="utf-8").lower()
    if "current_stage_status: drafted for review" not in status and "current_stage_status: blocked" not in status:
        raise ValueError("status.md lacks current-stage status")
    if "feature_acceptance_status: unproven" not in status:
        raise ValueError("status.md must retain unproven feature acceptance")
    result = _read_json(files["result.json"])
    if set(result) != {"outcome", "summary", "evidence_refs"}:
        raise ValueError("result.json must contain only outcome, summary, and evidence_refs")
    if not isinstance(result["summary"], str) or not result["summary"].strip():
        raise ValueError("result summary must be nonempty text")
    if not isinstance(result["evidence_refs"], list) or not result["evidence_refs"]:
        raise ValueError("result evidence_refs must be a nonempty list")
    if any(not isinstance(ref, str) or not _path_from_ref(ref, trial, output / "frozen-skill") for ref in result["evidence_refs"]):
        raise ValueError("result evidence_refs must point to actual trial or frozen files")
    return result


def next_trial(output: Path, case: str) -> dict[str, Any]:
    """Prepare an independently seeded cold spec trial after discovery artifacts exist."""
    if case not in CASES:
        raise ValueError(f"unknown case: {case}")
    output = output.expanduser().resolve()
    _manifest(output)
    discovery = output / "trials" / "discovery" / case
    meta = _read_json(discovery / "input.json")
    if _tree(discovery / "repo") != meta.get("input_tree"):
        raise ValueError("discovery product input changed; cold copy refused")
    _validate_notes(output, discovery)
    trial = _make_trial(output, "spec", case, discovery / "repo", discovery / "notes")
    return {"outcome": "UNKNOWN", "summary": "prepared separately seeded cold spec trial; no callback or Improve ran", "trial": str(trial)}


def _note_status(output: Path, trial: Path) -> dict[str, str]:
    try:
        _validate_notes(output, trial)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "INCOMPLETE_OR_INVALID", "detail": str(exc)}
    return {"status": "STRUCTURALLY_CONSISTENT", "detail": "No semantic correctness or acceptance judgment."}


def audit(output: Path) -> dict[str, Any]:
    """Report immutable-input and output-artifact observations without grading semantics."""
    output = output.expanduser().resolve()
    manifest = _manifest(output)
    rows = []
    for stage in ("discovery", "spec"):
        root = output / "trials" / stage
        if not root.is_dir():
            continue
        for trial in sorted(path for path in root.iterdir() if path.is_dir()):
            meta = _read_json(trial / "input.json")
            packet = trial / meta["packet"]
            packet_status = "MISSING"
            if packet.is_file() and not packet.is_symlink():
                packet_status = "INTACT" if _sha(packet.read_bytes()) == meta.get("packet_sha256") else "CHANGED"
            input_status = "UNCHANGED" if _tree(trial / "repo") == meta.get("input_tree") else "CHANGED"
            rows.append({"id": meta.get("id"), "packet": packet_status, "input_tree": input_status,
                         "notes": _note_status(output, trial), "semantic_correctness": "NOT_GRADED"})
    return {"study": STUDY, "outcome": "UNKNOWN", "summary": "Structural audit only; no blanket pass or semantic verdict.",
            "git_head": manifest["git_head"], "trials": rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("initialize", "prepare", "next", "audit"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=tuple(CASES))
    args = parser.parse_args()
    if args.command == "initialize":
        result = initialize(args.output)
    elif args.command == "prepare":
        result = prepare(args.output)
    elif args.command == "next":
        if args.case is None:
            parser.error("next requires --case")
        result = next_trial(args.output, args.case)
    else:
        result = audit(args.output)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
