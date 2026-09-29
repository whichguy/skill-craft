#!/usr/bin/env python3
"""Replay the retained reviewer controls with an explicitly selected model."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PurePosixPath
import secrets
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import evidence  # noqa: E402
import hosts  # noqa: E402
import review  # noqa: E402

CONTROL_DIR = HERE / "calibration" / "controls"
CONTROL_SCHEMA = "shiploop-e2e-control/1"
TARGETS = {"clean", "material_defect", "incomplete"}
CONTROL_ATTEMPT_IDS = {"alternative": "control-01", "blocked": "control-02", "correct": "control-03",
                      "defect": "control-04", "incomplete": "control-05"}


def load_controls() -> list[dict]:
    controls = []
    for path in sorted(CONTROL_DIR.glob("*.json")):
        control = evidence.read_json(path)
        if control.get("schema") != CONTROL_SCHEMA or control.get("expected_class") not in TARGETS:
            raise ValueError(f"unsupported control fixture: {path}")
        if not control.get("id") or not control.get("rationale"):
            raise ValueError(f"control needs an id and rationale: {path}")
        criteria = control.get("criteria")
        run = control.get("run")
        if not isinstance(criteria, dict) or not isinstance(run, dict):
            raise ValueError(f"control needs criteria and run evidence: {path}")
        if not review._criteria_ids(criteria, "requirements") or not review._criteria_ids(criteria, "workflow"):
            raise ValueError(f"control needs requirement and workflow criteria: {path}")
        evidence_rows = run.get("primary_evidence")
        if not isinstance(evidence_rows, list) or not evidence_rows:
            raise ValueError(f"control needs primary evidence: {path}")
        for item in evidence_rows:
            locator = item.get("locator") if isinstance(item, dict) else None
            parts = PurePosixPath(locator.split("#", 1)[0]).parts if isinstance(locator, str) else ()
            if not parts or PurePosixPath(locator.split("#", 1)[0]).is_absolute() or ".." in parts:
                raise ValueError(f"unsafe or missing evidence locator in {path}")
        controls.append(control)
    if {row["id"] for row in controls} != {"correct", "alternative", "defect", "incomplete", "blocked"}:
        raise ValueError("the retained control set must include correct, alternative, defect, incomplete and blocked")
    return controls


def control_digest() -> str:
    return evidence.tree_digest(CONTROL_DIR)


def classify_response(response: dict | None, control: dict) -> tuple[str, list[str]]:
    """Classify only this control; this is a calibration result, not a live run verdict."""
    criteria = control["criteria"]
    errors = review.validate_response(response, criteria)
    if errors:
        return "unknown", errors
    run = control["run"]
    requirements = response["requirements"]
    workflow = response["workflow"]
    if run.get("evidence_status") != "valid":
        if all(row.get("status") == "unverified" for row in requirements):
            return "incomplete", []
        return "unknown", ["incomplete evidence was not consistently classified as unverified"]
    clean = not review._content_reasons(response, criteria)
    if clean:
        return "clean", []
    material = any(f.get("severity") == "material" and f.get("disposition") in {"open", "deferred", "disputed"}
                   for f in response.get("findings", []))
    failed = any(row.get("status") in {"failed", "blocked"} for row in requirements)
    failed |= any(row.get("status") == "fail" for row in workflow)
    if material or failed:
        return "material_defect", []
    return "unknown", ["control outcome was neither a clean pass nor a supported material defect"]


def compare_control(control: dict, observed: str, reasons: list[str], process_ok: bool) -> dict:
    expected = control["expected_class"]
    if reasons or not process_ok or observed == "unknown":
        result = "unknown"
    elif expected == "material_defect" and observed == "clean":
        result = "miss"
    elif expected in {"clean", "incomplete"} and observed == "clean" and expected == "incomplete":
        result = "false_alarm"
    elif expected == "clean" and observed != "clean":
        result = "false_alarm"
    elif expected == "incomplete" and observed != "incomplete":
        result = "unknown"
    elif expected == "material_defect" and observed != "material_defect":
        result = "unknown"
    else:
        result = "matched"
    return {"id": control["id"], "expected": expected, "observed": observed,
            "result": result, "reasons": reasons}


def _write_control_files(stage: Path, control: dict, spec_path: Path, identity: dict,
                         attempt_id: str) -> tuple[dict, dict]:
    run = control["run"]
    evaluation = stage / "evaluation"
    subject = evaluation / "subject" / "skills" / "shiploop"
    subject.mkdir(parents=True)
    evaluation.mkdir(exist_ok=True)
    (evaluation / "SPEC.md").write_bytes(spec_path.read_bytes())
    (subject / "SKILL.md").write_text(
        "---\nname: shiploop\ndescription: Calibration fixture skill.\n---\n\n"
        "This control uses no product-specific behavior outside its stated request.\n", encoding="utf-8")
    evidence_lines = []
    checks_by_index = {}
    for index, item in enumerate(run["primary_evidence"], 1):
        locator = item["locator"].split("#", 1)[0]
        pointer = item["locator"].partition("#")[2]
        if locator == "result.json" and pointer.startswith("/checks/"):
            check_index = pointer.removeprefix("/checks/").split("/", 1)[0]
            if check_index.isdigit():
                text = str(item.get("text") or "")
                checks_by_index[int(check_index)] = {
                    "command": text.partition(":")[2].strip() or text,
                    "pass": text.lower().startswith("pass:"),
                    "returncode": 0 if text.lower().startswith("pass:") else 1,
                    "status": "exited",
                    "synthetic_control": True,
                    **run.get("check_execution", {}),
                }
        elif locator != "result.json":
            path = stage.joinpath(*PurePosixPath(locator).parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(str(item.get("text") or ""), encoding="utf-8")
        evidence_lines += [f"- {item['locator']}: {item.get('text', '')}"]
    (stage / "prompt.txt").write_text(run["request"] + "\n", encoding="utf-8")
    mechanical = run["mechanical"]
    check_rows = [checks_by_index[index] for index in range(max(checks_by_index, default=-1) + 1)
                  if index in checks_by_index]
    if control.get("verify_report"):
        # Execute the control's assertions and retain a script-owned record in
        # the synthetic trace. Labels do not manufacture a passing receipt.
        script = subject / "scripts" / "verify-report.py"
        script.parent.mkdir(parents=True)
        shutil.copyfile(CONTROL_DIR / "verify-report.py", script)
        check_timeout = 10
        completed = subprocess.run([sys.executable, str(script)], cwd=stage / "work",
                                   stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=check_timeout)
        check_rows = json.loads(completed.stdout)["checks"]
        for row in check_rows:
            row.update({"stdin": "closed", "timeout_seconds": check_timeout})
        record = {"synthetic_control": True, "invocation_id": attempt_id,
                  "passed": completed.returncode == 0, "tests": len(check_rows),
                  "commands": [{"command": f"{sys.executable} {script}", "cwd": "work", "stdin": "closed",
                                "timeout_seconds": check_timeout,
                                "returncode": completed.returncode, "stdout": completed.stdout,
                                "stderr": completed.stderr}]}
        receipt = stage / "run" / "tests" / "report-verify1.md"
        receipt.parent.mkdir(parents=True)
        receipt.write_text("# Synthetic ShipLoop verification trace\n\n```json\n" + json.dumps(record, indent=2) + "\n```\n")
        evidence_lines.append("- run/tests/report-verify1.md: retained script verification receipt with exact command and output")
        evidence.atomic_json(stage / "metrics.json", {"script_verifications": {
            "records": 1, "passed": int(completed.returncode == 0), "commands": 1,
            "locators": ["run/tests/report-verify1.md"]}})
        event = {"type": "tool_call", "toolName": "run_terminal_command",
                 "rawInput": {"command": record["commands"][0]["command"]}}
        update = {"type": "tool_call_update", "output": completed.stdout, "returncode": completed.returncode,
                  "synthetic_control": True, "record": "run/tests/report-verify1.md"}
        (stage / "events.jsonl").write_text(json.dumps(event) + "\n" + json.dumps(update) + "\n")
    # A boundary case can pass its predeclared awaiting terminal without a
    # delivery commit or a successful `done` state. Preserve the runner's
    # kind-specific gate while the controller retains the hidden class label.
    kind = control["criteria"].get("kind")
    state_pass = (run["terminal"] == control["criteria"].get("expected_terminal", "done")
                  if control["criteria"].get("expected_terminal", "done") != "done"
                  else mechanical["shiploop"])
    committed_pass = True if kind == "boundary" else mechanical["committed"]
    checks_pass = bool(check_rows) and all(row["pass"] for row in check_rows)
    evidence_pass = run["evidence_status"] == "valid"
    raw_pass = (evidence_pass and mechanical["invoked"] and mechanical["plugin"] and mechanical["process"]
                and state_pass and committed_pass and checks_pass)
    result = {
        "identity": identity,
        "case": attempt_id,
        "pass": raw_pass,
        "evidence": {"status": run["evidence_status"],
                     "reasons": [] if run["evidence_status"] == "valid" else ["control deliberately has incomplete evidence"]},
        "versions": {"source": "checkout"},
        "invoked": {"pass": mechanical["invoked"]},
        "plugin": {"pass": mechanical["plugin"]},
        "process": {"pass": mechanical["process"], "status": "exited" if mechanical["process"] else "failed",
                    "returncode": 0 if mechanical["process"] else 1, **run.get("execution", {})},
        "shiploop": {"pass": mechanical["shiploop"], "status": run["terminal"]},
        "committed": {"pass": mechanical["committed"]},
        "checks": check_rows,
        "output": str(stage),
    }
    recipe = {"case": {"prompt": run["request"]}, "checks": [row["command"] for row in check_rows],
              "criteria": control["criteria"]}
    manifest = {"schema": evidence.SCHEMA, "identity": identity, "criteria": control["criteria"],
                "frozen_subject": "evaluation/subject", "frozen_digest": "fixture"}
    evidence.atomic_json(stage / "evaluation.json", manifest)
    evidence.atomic_json(stage / "result.json", result)
    transcript = stage / "transcript.md"
    retained_text = transcript.read_text() + "\n\n" if transcript.exists() else ""
    transcript.write_text("# Synthetic control transcript\n\n" + retained_text + "\n".join(evidence_lines) + "\n")
    if not (stage / "events.jsonl").exists():
        (stage / "events.jsonl").write_text("{\"type\":\"fixture\"}\n")
    if not (stage / "metrics.json").exists():
        (stage / "metrics.json").write_text("{}\n")
    return result, manifest


def run_calibration(*, host_name: str, model: str | None, effort: str | None, receipt_path: Path,
                    timeout: int = 1200, grok_bin: str = "grok", claude_bin: str = "claude",
                    codex_bin: str = "codex") -> dict:
    controls = load_controls()
    selected_model = model or hosts.HOST_DEFAULTS[host_name]["model"]
    selected_effort = effort or hosts.HOST_DEFAULTS[host_name]["effort"]
    identity = review.calibration_identity(host=host_name, model=selected_model, effort=selected_effort,
                                           spec_path=HERE / "SPEC.md", control_digest=control_digest())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = receipt_path.parent / f"{receipt_path.stem}.evidence-{stamp}-{secrets.token_hex(3)}"
    output_dir.mkdir(parents=True, exist_ok=False)
    agent = hosts.host(host_name, {"grok": grok_bin, "claude": claude_bin, "codex": codex_bin}[host_name])
    rows = []
    for control in controls:
        attempt_id = CONTROL_ATTEMPT_IDS[control["id"]]
        stage = output_dir / attempt_id
        stage.mkdir()
        result, evaluation = _write_control_files(stage, control, HERE / "SPEC.md", identity, attempt_id)
        prompt = review.reviewer_prompt(stage, frozen_spec_path=stage / "evaluation" / "SPEC.md")
        (stage / "review-prompt.txt").write_text(prompt, encoding="utf-8")
        before = review.retained_calibration_inputs(stage)
        process = {"status": "failed", "returncode": -1}
        response = None
        error = None
        try:
            env = agent.env(stage / "home")
            argv = agent.argv(prompt=prompt, prompt_file=stage / "review-prompt.txt", cwd=stage,
                              model=selected_model, effort=selected_effort,
                              permission_mode="read-only" if host_name == "codex" else "auto",
                              max_turns=60, read_only=(host_name == "codex"))
            process = hosts.run_agent(argv, stage, env, stage / "review-events.jsonl",
                                      stage / "review-stderr.txt", timeout, translate=agent.translator())
            response = hosts.last_json_object(hosts.final_text(stage / "review-events.jsonl"))
        except (OSError, ValueError, KeyError, RuntimeError, SystemExit) as exc:
            error = f"{type(exc).__name__}: {exc}"
        except KeyboardInterrupt:
            error = "operator interrupted reviewer calibration"
            process = {"status": "interrupted", "returncode": 130}
        after = review.retained_calibration_inputs(stage)
        reasons = review.validate_response(response, control["criteria"])
        if before != after:
            reasons.append("retained calibration inputs changed during review")
        observed, classification_reasons = classify_response(response, control)
        reasons.extend(classification_reasons)
        process_ok = (process.get("status") == "exited" and process.get("returncode") == 0
                      and not process.get("capture_errors") and not process.get("stream_errors")
                      and not process.get("cleanup_error"))
        if not process_ok:
            reasons.append("reviewer process did not exit successfully")
        row = compare_control(control, observed, list(dict.fromkeys(reasons)), process_ok)
        row.update(attempt_id=attempt_id, evidence_path=attempt_id, input_digests=after,
                   input_digest=evidence.object_digest(after), process=process,
                   prompt_digest=__import__("hashlib").sha256(prompt.encode()).hexdigest(),
                   error=error, expected_rationale=control["rationale"])
        evidence.atomic_json(stage / "calibration-result.json", {"response": response, "result": row})
        row["output_digests"] = review.retained_calibration_outputs(stage)
        rows.append(row)
        if process.get("status") == "interrupted":
            break

    summary = {name: sum(row["result"] == name for row in rows)
               for name in ("matched", "false_alarm", "miss", "unknown")}
    passed = (len(rows) == 5 and summary["matched"] == 5
              and summary["false_alarm"] == summary["miss"] == summary["unknown"] == 0)
    receipt = {"schema": review.CALIBRATION_SCHEMA, "status": "passed" if passed else "failed",
               "identity": identity, "summary": {"controls": len(rows), "false_alarms": summary["false_alarm"],
                                                   "misses": summary["miss"], "unknown": summary["unknown"],
                                                   "matched": summary["matched"]},
               "attempts": rows, "evidence_dir": str(output_dir.resolve()),
               "note": "This replay calibrates only this reviewer prompt/model on these synthetic retained controls; it is not a measure of general judge accuracy."}
    evidence.atomic_json(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=sorted(hosts.HOSTS), required=True)
    parser.add_argument("--model", help="defaults to the host's current default")
    parser.add_argument("--effort")
    parser.add_argument("--receipt", type=Path, required=True,
                        help="new path for the model-labeled calibration receipt")
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--grok-bin", default="grok")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--codex-bin", default="codex")
    args = parser.parse_args(argv)
    receipt_path = args.receipt.expanduser().resolve()
    if receipt_path.exists():
        raise SystemExit(f"refusing to overwrite calibration receipt: {receipt_path}")
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    result = run_calibration(host_name=args.host, model=args.model, effort=args.effort,
                             receipt_path=receipt_path, timeout=args.timeout,
                             grok_bin=args.grok_bin, claude_bin=args.claude_bin, codex_bin=args.codex_bin)
    print(json.dumps({"status": result["status"], "summary": result["summary"],
                      "receipt": str(receipt_path), "evidence_dir": result["evidence_dir"]}, indent=2))
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
