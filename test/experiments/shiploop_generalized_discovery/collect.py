#!/usr/bin/env python3
"""Create blinded evidence bundles without dropping successful tool receipts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import random
from typing import Any

from study_inputs import validate_study_inputs


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(study: Path, family: str, repetition: int = 0) -> Path:
    """Use the validated collector for both library and default CLI callers."""
    return collect_compact(study, family, repetition)


def _object(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{description} is unavailable or invalid") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{description} must be an object")
    return value


def _compact_mapping(study: Path, state: dict[str, Any], arms: list[tuple[str, dict[str, Any]]],
                     family: str, repetition: int) -> dict[str, str]:
    path = study / "private" / f"{family}-r{repetition}-mapping.json"
    names = {name for name, _ in arms}
    if path.is_file():
        mapping = _object(path, "existing blind mapping")
        if set(mapping) != {"Left", "Right"} or set(mapping.values()) != names:
            raise ValueError("existing blind mapping does not match prepared arms")
        return {label: str(name) for label, name in mapping.items()}
    ordered = list(arms)
    random.Random(f"{state['blind_order_seed']}:{family}:{repetition}").shuffle(ordered)
    mapping = dict(zip(("Left", "Right"), (name for name, _ in ordered)))
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(mapping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return mapping


def _expected_inputs(arm: Path) -> dict[str, str]:
    expected = _object(arm / "input-hashes.json", f"input hashes for {arm.name}")
    if not expected or any(not isinstance(path, str) or not isinstance(digest, str) for path, digest in expected.items()):
        raise ValueError(f"input hashes for {arm.name} are unsupported")
    workspace = arm / "workspace"
    changed: list[str] = []
    for relative, digest in expected.items():
        candidate = workspace / relative
        if Path(relative).is_absolute() or ".." in Path(relative).parts or not candidate.is_file() or candidate.is_symlink() or sha(candidate) != digest:
            changed.append(relative)
    if changed:
        raise ValueError(f"input integrity failure for {arm.name}: {', '.join(sorted(changed))}")
    return {str(path): str(digest) for path, digest in expected.items()}


def _sources(labels: dict[str, str], inputs: dict[str, dict[str, str]], study: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, str], str]]:
    records: list[dict[str, Any]] = []
    references: dict[tuple[str, str], str] = {}
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for label, name in labels.items():
        workspace = study / "arms" / name / "workspace"
        for path, digest in sorted(inputs[label].items()):
            if path.startswith("guidance/"):
                continue
            file = workspace / path
            try:
                text = file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise ValueError(f"unsupported source evidence {name}/{path}") from exc
            key = (path, digest)
            if key not in index:
                record = {"id": f"SRC-{len(records) + 1:03d}", "path": path, "sha256": digest,
                          "bytes": len(text.encode("utf-8")), "labels": [label], "text": text}
                records.append(record)
                index[key] = record
            elif label not in index[key]["labels"]:
                index[key]["labels"].append(label)
            references[(label, path)] = index[key]["id"]
    return records, references


def _runner_observation(arm: Path, *, require: bool) -> dict[str, Any]:
    path = arm / "run" / "metadata.json"
    if not path.is_file():
        if require:
            raise ValueError(f"missing runner metadata for {arm.name}")
        return {"status": "unknown", "reason": "synthetic fixture lacks runner metadata"}
    metadata = _object(path, f"runner metadata for {arm.name}")
    contexts = metadata.get("contexts")
    observed = metadata.get("observed_actions")
    ledger = metadata.get("gateway_ledger")
    if not isinstance(contexts, list) or not contexts or not isinstance(observed, dict) or not isinstance(ledger, dict):
        raise ValueError(f"runner metadata for {arm.name} is unsupported")
    completion = metadata.get("completion", {})
    if (not isinstance(completion, dict) or completion.get("status") != "completed"
            or metadata.get("fixture_edits_flagged") or metadata.get("fixture_edits")):
        raise ValueError(f"arm {arm.name} is not a completed unmodified run; comparison is inconclusive")
    compact_contexts: list[dict[str, Any]] = []
    for context in contexts:
        if not isinstance(context, dict) or not {"exit_code", "termination_reason", "elapsed_seconds"}.issubset(context):
            raise ValueError(f"runner context metadata is incomplete for {arm.name}")
        if context["exit_code"] != 0 or context["termination_reason"] is not None:
            raise ValueError(f"arm {arm.name} has a failed context; comparison is inconclusive")
        compact_contexts.append({key: context[key] for key in ("context", "exit_code", "termination_reason", "elapsed_seconds") if key in context})
    count = observed.get("observed_unique")
    records = ledger.get("records")
    if not isinstance(count, int) or not isinstance(records, list):
        raise ValueError(f"runner action metadata is incomplete for {arm.name}")
    phases: dict[str, int] = {}
    for record in records:
        phase = record.get("phase") if isinstance(record, dict) else None
        if not isinstance(phase, str):
            raise ValueError(f"runner ledger phase metadata is incomplete for {arm.name}")
        phases[phase] = phases.get(phase, 0) + 1
    return {"status": "observed", "contexts": compact_contexts, "observed_action_count": count, "ledger_phase_counts": phases}


def _guide_exec(argv: Any) -> bool:
    return isinstance(argv, list) and any(isinstance(item, str) and ("guidance/" in item or "guidance\\" in item) for item in argv)


def _probe(argv: Any) -> bool:
    """Return true only for a direct Python execution of probe.py.

    A Python ``-c`` program can mention probe.py while reading arbitrary fixture
    files.  Treating that text as a probe would incorrectly retain guide content.
    """
    if not isinstance(argv, list) or not argv or not isinstance(argv[0], str):
        return False
    executable = Path(argv[0]).name.lower()
    if not (executable == "python" or executable.startswith("python3")):
        return False
    for argument in argv[1:]:
        if not isinstance(argument, str):
            return False
        if argument in {"-c", "-m"}:
            return False
        if argument.startswith("-"):
            continue
        return Path(argument).name == "probe.py"
    return False


def _short_result(result: Any, *, note: str, source: str | None = None) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("receipt result is unsupported")
    kept = {key: value for key, value in result.items() if key not in {"text", "stdout", "stderr", "argv"}}
    kept["note"] = note
    if source is not None:
        kept["included_source"] = source
    return kept


def _receipt_for_bundle(receipt: dict[str, Any], *, label: str, arm: str, workspace: Path,
                        sources: dict[tuple[str, str], str], withheld: list[dict[str, Any]]) -> dict[str, Any]:
    value = json.loads(json.dumps(receipt))
    value.pop("arm", None)
    value.pop("at", None)
    request = value.get("request")
    arguments = request.get("arguments") if isinstance(request, dict) else None
    if not isinstance(arguments, dict):
        raise ValueError("receipt lacks supported workspace arguments")
    operation, path, argv = arguments.get("operation"), arguments.get("path"), arguments.get("argv")
    result = value.get("result")
    error = bool(value.get("is_error")) or isinstance(result, dict) and bool(result.get("error"))
    call = result.get("call") if isinstance(result, dict) else None
    guide_read = operation == "read" and isinstance(path, str) and path.startswith("guidance/")
    guide_execution = operation == "exec" and _guide_exec(argv) and not _probe(argv)
    if guide_read or guide_execution:
        withheld.append({"label": label, "call": call, "operation": operation,
                          "path": path, "kind": "guidance_execution" if guide_execution else "guidance_read"})
        if guide_execution:
            arguments["argv"] = ["<guidance-reading argv withheld>"]
        value["result"] = _short_result(result, note="guide variant content withheld")
    elif operation == "read" and not error and isinstance(path, str) and (label, path) in sources:
        value["result"] = _short_result(result, note="content appears in common source snapshot", source=sources[(label, path)])
    elif operation == "write" and path == "REPORT.md":
        arguments["content"] = "report content shown above"
    encoded = json.dumps(value, ensure_ascii=False)
    return json.loads(encoded.replace(str(workspace), "WORKSPACE").replace(arm, "TRIAL"))


def collect_compact(study: Path, family: str, repetition: int = 0) -> Path:
    validate_study_inputs(study)
    state = _object(study / "study.json", "study state")
    prepared = state.get("arms")
    if not isinstance(prepared, dict) or not isinstance(state.get("blind_order_seed"), (str, int)):
        raise ValueError("study state lacks prepared arms or blind seed")
    arms = [(name, data) for name, data in prepared.items() if isinstance(data, dict) and data.get("family") == family and data.get("repetition") == repetition]
    if len(arms) != 2:
        raise ValueError("need exactly two prepared arms")
    mapping = _compact_mapping(study, state, arms, family, repetition)
    target = study / "blind" / f"{family}-r{repetition}"
    target.mkdir(parents=True, exist_ok=True)
    bundle, manifest = target / "bundle-compact.md", target / "bundle-compact-manifest.json"
    if bundle.exists() or manifest.exists():
        raise FileExistsError("compact bundle already exists; original evidence is preserved")
    inputs = {label: _expected_inputs(study / "arms" / name) for label, name in mapping.items()}
    require_runner_metadata = state.get("schema") == "generalized-discovery-study/1"
    runner_observations = {label: _runner_observation(study / "arms" / name, require=require_runner_metadata) for label, name in mapping.items()}
    source_records, source_refs = _sources(mapping, inputs, study)
    receipt_path = study / "receipts.jsonl"
    if not receipt_path.is_file():
        raise ValueError("raw coordinator receipts are missing")
    raw: dict[str, list[dict[str, Any]]] = {label: [] for label in mapping}
    reverse = {name: label for label, name in mapping.items()}
    for line in receipt_path.read_text(encoding="utf-8").splitlines():
        try:
            receipt = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError("raw coordinator receipts are invalid") from exc
        if not isinstance(receipt, dict):
            raise ValueError("raw coordinator receipt is unsupported")
        label = reverse.get(receipt.get("arm"))
        if label is not None:
            raw[label].append(receipt)
    if any(not records for records in raw.values()):
        raise ValueError("missing coordinator evidence for a blinded arm")
    sections = ["# Blinded discovery comparison (compact)", "", "Reports are intact. Common fixture sources appear once below.",
                "Full raw coordinator receipts remain outside this judge bundle; the manifest records their hash.",
                "Guide-variant content is withheld from guide reads and guide-reading commands only.", ""]
    withheld: list[dict[str, Any]] = []
    for label, name in mapping.items():
        workspace, report = study / "arms" / name / "workspace", study / "arms" / name / "workspace" / "REPORT.md"
        if not report.is_file() or report.is_symlink():
            raise ValueError(f"missing report for {name}")
        sections += [f"## {label}", "", "### Report", "", report.read_text(encoding="utf-8"), "",
                     "### Input integrity", "", json.dumps({"status": "verified", "initial_input_count": len(inputs[label])}), "",
                     "### Runner observations", "", "```json", json.dumps(runner_observations[label], sort_keys=True), "```", "", "### Tool receipts", ""]
        for receipt in raw[label]:
            compact = _receipt_for_bundle(receipt, label=label, arm=name, workspace=workspace, sources=source_refs, withheld=withheld)
            sections += ["```json", json.dumps(compact, ensure_ascii=False, sort_keys=True), "```"]
        sections.append("")
    sections += ["## Common source snapshot", ""]
    for source in source_records:
        labels = ", ".join(source["labels"])
        sections += [f"### {source['id']}: {source['path']} ({labels})", "", "```text", source["text"], "```", ""]
    sections += ["## Withheld variant evidence", ""]
    if withheld:
        for item in withheld:
            sections.append(f"- {item['label']} call {item['call']}: {item['kind']} content withheld; metadata retained.")
    else:
        sections.append("- None.")
    bundle.write_text("\n".join(sections), encoding="utf-8")
    provenance = {"schema": "generalized-discovery-compact-bundle/1", "family": family, "repetition": repetition,
                  "mapping_sha256": sha(study / "private" / f"{family}-r{repetition}-mapping.json"),
                  "raw_receipts": {"path": "receipts.jsonl", "sha256": sha(receipt_path), "lines": len(receipt_path.read_text(encoding="utf-8").splitlines())},
                  "reports": {label: {"path": "REPORT.md", "sha256": sha(study / "arms" / name / "workspace" / "REPORT.md")} for label, name in mapping.items()},
                  "runner_observations": runner_observations,
                  "common_sources": [{key: value for key, value in source.items() if key != "text"} for source in source_records],
                  "withheld": withheld,
                  "receipt_counts": {label: len(items) for label, items in raw.items()},
                  "bundle_sha256": sha(bundle),
                  "omission_policy": "Only repeated successful common-source reads, REPORT write content, and guide-variant content are compacted; exec/probe/error results remain unless guide content itself is withheld."}
    manifest.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", type=Path, required=True)
    parser.add_argument("--family", required=True)
    parser.add_argument("--repetition", type=int, default=0)
    parser.add_argument("--compact", action="store_true", help="write a separate compact blind bundle")
    args = parser.parse_args()
    method = collect_compact if args.compact else collect
    print(method(args.study.resolve(), args.family, args.repetition))
