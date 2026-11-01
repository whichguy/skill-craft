"""Probe documented startup shell forms against the selected package observer.

The E2E runner calls this from work/ with E2E_CHECKS set. It is a synthetic
capability check, not evidence that a model naturally renders the commands or
that a ShipLoop application or cost measure improved.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import shiploop_hook_contract as contract


class ContractFailure(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ContractFailure(message)


def shell_single(value: str) -> str:
    """Return a POSIX single-quoted shell word, escaping embedded apostrophes."""
    return "'" + value.replace("'", "'\\''") + "'"


def shell_double(value: str) -> str:
    """Return a POSIX double-quoted shell word with expansions disabled."""
    escaped = "".join("\\" + char if char in '\\\"$' + chr(96) else char for char in value)
    return '"' + escaped + '"'


def _commands(block: str):
    """Read only simple python3 CLI commands and their backslash continuations."""
    pending = None
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if pending is None:
            if not re.match(r'^python3\s+["\']\$CLI["\']\s+', line):
                continue
            pending = line
        else:
            pending += " " + line
        if pending is not None and line.endswith("\\"):
            pending = pending[:-1].rstrip()
        elif pending is not None:
            yield pending
            pending = None


def documented_examples(skill: Path) -> dict[str, str]:
    """Extract the documented startup commands from fenced POSIX shell examples."""
    try:
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"selected ShipLoop SKILL.md is unreadable: {exc}")
    examples: dict[str, str] = {}
    for match in re.finditer(r"^\x60\x60\x60(?:sh|bash)\s*\n(.*?)^\x60\x60\x60\s*$",
                             text, flags=re.MULTILINE | re.DOTALL):
        for command in _commands(match.group(1)):
            kind = "workspace_start" if re.search(r"\bworkspace\s+start\b", command) else (
                "init" if re.search(r"\binit\b", command) else None)
            if kind and kind not in examples:
                examples[kind] = command
    missing = {"workspace_start", "init"} - examples.keys()
    if missing:
        fail("selected SKILL.md lacks supported fenced python3 startup examples: " + ", ".join(sorted(missing)))
    return examples


def _cli_token(command: str, path: str, style: str | None) -> str:
    pattern = re.compile(r'(?P<quote>["\'])\$CLI(?P=quote)')
    match = pattern.search(command)
    if not match:
        fail("startup example does not contain a simply quoted $CLI token")
    original_style = match.group("quote")
    chosen = style or ("single" if original_style == "'" else "double")
    value = shell_single(path) if chosen == "single" else shell_double(path)
    return command[:match.start()] + value + command[match.end():]


def _render_path(command: str, name: str, value: str) -> str:
    pattern = re.compile(r'(?P<quote>["\'])\$' + re.escape(name) + r'(?P=quote)')
    match = pattern.search(command)
    if not match:
        return command
    style = match.group("quote")
    quoted = shell_single(value) if style == "'" else shell_double(value)
    return command[:match.start()] + quoted + command[match.end():]


def render_example(command: str, *, cli: str, repo: str, run_dir: str,
                   request: str, cli_style: str | None = None) -> str:
    """Substitute only the documented startup placeholders; fail closed on drift."""
    rendered = _cli_token(command, cli, cli_style)
    rendered = _render_path(rendered, "REPO", repo)
    rendered = _render_path(rendered, "RUN_DIR", run_dir)
    prompt = "--prompt='<user request>'"
    if prompt not in rendered:
        fail("startup example no longer has the supported --prompt='<user request>' slot")
    return rendered.replace(prompt, "--prompt='" + request.replace("'", "'\\''") + "'", 1)


def _marker(run_id: str, revision: Any, run_dir: str) -> str:
    if not isinstance(revision, int) or revision < 0:
        fail("temporary live run has no numeric revision for its marker")
    return f"SHIPLOOP-RUN run={run_id} rev={revision} dir={run_dir}"


def observe(keepalive: Any, host: str, session: str, command: str, marker: str) -> dict[str, Any]:
    payload = {"session_id": session, "tool_input": {"command": command}, "tool_response": marker}
    returned = keepalive.observe(host, payload)
    binding = keepalive.load_binding(host, session)
    marker_run_id = marker.split(" run=", 1)[1].split(" ", 1)[0]
    return {"bound": binding is not None,
            "returned_binding": returned is not None,
            "bound_run_id_matches": binding is not None and binding.get("run_id") == marker_run_id}


def record(report: dict[str, Any], receipt: Path, probe_id: str, command: str,
           expected: dict[str, Any], observed: dict[str, Any], package: Path,
           before: tuple[dict[str, tuple[str, int]], str]) -> None:
    after = contract.tree_signature(package)
    package_unchanged = before == after
    passed = package_unchanged and all(observed.get(key) == value for key, value in expected.items())
    row = {"id": probe_id, "command": command, "expected": expected, "observed": observed,
           "package": {"before_sha256": before[1], "after_sha256": after[1],
                       "unchanged": package_unchanged},
           "status": "pass" if passed else "fail"}
    report["probes"].append(row)
    contract.write_receipt(receipt, report)
    if not package_unchanged:
        fail(f"selected package content or executable modes changed during {probe_id}")
    if not passed:
        fail(f"{probe_id} observed {observed!r}, expected {expected!r}")


def observer_probe(report: dict[str, Any], receipt: Path, package: Path, keepalive: Any,
                   host: str, session: str, command: str, marker: str,
                   expected: dict[str, Any]) -> dict[str, Any]:
    before = contract.tree_signature(package)
    observed = observe(keepalive, host, session, command, marker)
    record(report, receipt, session.removeprefix("startup-").replace("-", "_"), command,
           expected, observed, package, before)
    return observed


def _argv_stub(command: str, env: dict[str, str], expected: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(command, shell=True, env=env, capture_output=True, text=True,
                                   timeout=10, check=False)
    except subprocess.TimeoutExpired:
        fail("argv-only startup stub timed out")
    if completed.returncode != 0:
        fail("argv-only startup stub returned nonzero: " + completed.stderr[-500:])
    try:
        encoded = json.loads(completed.stdout)
        actual = [base64.b64decode(item, validate=True) for item in encoded]
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        fail(f"argv-only startup stub returned invalid output: {exc}")
    wanted = [os.fsencode(item) for item in expected]
    return {"argv_match": actual == wanted,
            "argv_bytes_base64": [base64.b64encode(item).decode("ascii") for item in actual],
            "expected_bytes_base64": [base64.b64encode(item).decode("ascii") for item in wanted]}


def _argv_examples(examples: dict[str, str], scratch: Path, request: str,
                   report: dict[str, Any], receipt: Path, package: Path) -> None:
    special = " path ' $ " + chr(96) + " Ω\ninside\n"
    cli = scratch / ("cli" + special)
    repo = scratch / ("repo" + special)
    run_dir = scratch / ("run" + special)
    repo.mkdir()
    run_dir.mkdir()
    cli.write_text(
        "import base64, json, os, sys\n"
        "print(json.dumps([base64.b64encode(os.fsencode(value)).decode('ascii') for value in sys.argv]))\n",
        encoding="utf-8")
    env = os.environ.copy()
    env.update({"CLI": str(cli), "REPO": str(repo), "RUN_DIR": str(run_dir)})
    for kind, probe_id in (("workspace_start", "argv_workspace_start"), ("init", "argv_init")):
        command = examples[kind]
        prompt = "--prompt='<user request>'"
        if prompt not in command:
            fail(f"documented {kind} has no supported prompt slot for argv calibration")
        command = command.replace(prompt, "--prompt='" + request.replace("'", "'\\''") + "'", 1)
        expected = ["workspace", "start"] if kind == "workspace_start" else ["init"]
        expected.extend(["--repo", str(repo)])
        if kind == "init":
            expected.extend(["--run-dir", str(run_dir)])
        expected.append("--prompt=" + request)
        forms = {
            "documented_variable": command,
            "literal_single": _cli_token(command, str(cli), "single"),
            "literal_double": _cli_token(command, str(cli), "double"),
        }
        before = contract.tree_signature(package)
        form_results = {name: _argv_stub(form, env, [str(cli), *expected])
                        for name, form in forms.items()}
        observed = {"argv_match": all(result["argv_match"] for result in form_results.values()),
                    "forms": form_results}
        record(report, receipt, probe_id, command, {"argv_match": True}, observed, package, before)


def run_probe(invocation: dict[str, Any], package: Path, skill: Path, modules: dict[str, Any],
              report: dict[str, Any], receipt: Path) -> None:
    check_dir = Path(os.environ.get("E2E_CHECKS", "")).resolve()
    test_dir = check_dir.parent.parent
    fixture_path = test_dir / "shiploop_inner_fixture.py"
    if not fixture_path.is_file():
        fail("temporary observer fixture is unavailable")
    sys.path.insert(0, str(test_dir))
    import shiploop_inner_fixture as fixture

    fixture.CORE = types.SimpleNamespace(PACKAGE_ROOT=skill, REF_DIR=skill / "references")
    host = invocation.get("host")
    if host not in modules["shiploop_keepalive"].HOSTS:
        fail(f"selected host is unknown: {host!r}")
    keepalive = modules["shiploop_keepalive"]
    original_home = keepalive.home
    scratch = tempfile.TemporaryDirectory(prefix="shiploop-startup-contract-")
    driver = fixture.RunDriver()
    try:
        driver.setUp()
        keepalive.home = lambda: Path(scratch.name) / "keepalive"
        improve = skill.parent / "improve" / "SKILL.md"
        if not improve.is_file():
            fail("selected package's Improve card is unavailable for the synthetic run")
        driver.start(str(improve.resolve()))
        run_dir = str(driver.run_dir.resolve())
        live = keepalive.run_status(run_dir)
        if live.get("error") or live.get("status") != "active" or not live.get("run_id"):
            fail("temporary fixture run is not readable and active through selected hook-status")
        marker = _marker(live["run_id"], live.get("revision"), live["run_dir"])
        cli = str((skill / "scripts" / "shiploop").resolve(strict=True))
        examples = documented_examples(skill)
        simple_request = "startup observer calibration"
        rendered = {
            kind: render_example(command, cli=cli, repo=str(driver.repo.resolve()), run_dir=run_dir,
                                 request=simple_request)
            for kind, command in examples.items()
        }
        for probe_id, kind in (("documented_workspace_start", "workspace_start"),
                               ("documented_init", "init")):
            session = "startup-" + probe_id
            observer_probe(report, receipt, package, keepalive, host, session, rendered[kind], marker,
                           {"bound": True, "bound_run_id_matches": True})
            keepalive.session_end(host, {"session_id": session})

        for probe_id, style in (("literal_quote_single", "single"), ("literal_quote_double", "double")):
            session = "startup-" + probe_id
            command = render_example(examples["workspace_start"], cli=cli, repo=str(driver.repo.resolve()),
                                     run_dir=run_dir, request=simple_request, cli_style=style)
            observer_probe(report, receipt, package, keepalive, host, session, command, marker,
                           {"bound": True, "bound_run_id_matches": True})
            keepalive.session_end(host, {"session_id": session})

        # Restore the source's variable head for this negative control.
        raw_variable = examples["workspace_start"].replace("--prompt='<user request>'",
                                                            "--prompt='" + simple_request + "'", 1)
        observer_probe(report, receipt, package, keepalive, host, "startup-variable-head",
                       raw_variable, marker, {"bound": False})

        packet = shell_single(str(Path(run_dir) / "packets" / "next.md"))
        read_packet = "cat " + packet
        observer_probe(report, receipt, package, keepalive, host, "startup-read-packet",
                       read_packet, marker, {"bound": False})
        read_status = "python3 " + shell_double(cli) + " hook-status --run-dir " + shell_single(run_dir)
        observer_probe(report, receipt, package, keepalive, host, "startup-read-status",
                       read_status, marker, {"bound": False})

        missing_dir = str(Path(scratch.name) / "missing-run")
        missing_command = render_example(examples["init"], cli=cli, repo=str(driver.repo.resolve()),
                                         run_dir=missing_dir, request=simple_request)
        missing_marker = _marker("missing-run-id", live.get("revision"), missing_dir)
        observer_probe(report, receipt, package, keepalive, host, "startup-missing-state",
                       missing_command, missing_marker, {"bound": False})

        corrupt_dir = Path(scratch.name) / "corrupt-run"
        corrupt_dir.mkdir()
        (corrupt_dir / "state.md").write_text("not a ShipLoop state record\n", encoding="utf-8")
        corrupt_command = render_example(examples["init"], cli=cli, repo=str(driver.repo.resolve()),
                                         run_dir=str(corrupt_dir), request=simple_request)
        corrupt_marker = _marker("corrupt-run-id", live.get("revision"), str(corrupt_dir))
        observer_probe(report, receipt, package, keepalive, host, "startup-corrupt-state",
                       corrupt_command, corrupt_marker, {"bound": False})

        owner_session, foreign_session = "startup-owner", "startup-foreign-owner"
        owner_probe_before = contract.tree_signature(package)
        if not keepalive.claim_owner(run_dir, host, owner_session):
            fail("temporary owner fixture could not claim its own run")
        foreign_command = rendered["workspace_start"]
        foreign_binding = keepalive.observe(
            host, {"session_id": foreign_session, "tool_input": {"command": foreign_command},
                   "tool_response": marker})
        if not isinstance(foreign_binding, dict) or foreign_binding.get("run_id") != live["run_id"]:
            fail("foreign session did not receive the live marker binding needed for ownership calibration")
        decision = keepalive._decide(host, foreign_session, foreign_binding)
        owner_after = keepalive._load_owner(run_dir).get("owner")
        observed = {"decision": decision.get("decision"), "why": decision.get("why"),
                    "owner_preserved": owner_after == keepalive._owner_id(host, owner_session)}
        record(report, receipt, "foreign_owner", foreign_command,
               {"decision": "allow", "owner_preserved": True}, observed, package, owner_probe_before)
        keepalive.session_end(host, {"session_id": foreign_session})
        keepalive.release_owner(run_dir, host, owner_session)

        request = ("--option-like=value apostrophe's dollar$ grave" + chr(96) +
                   " Unicode Ω\ninternal line\n")
        _argv_examples(examples, Path(scratch.name), request, report, receipt, package)

        report["fixture"] = {"run_id_sha256": hashlib.sha256(str(live["run_id"]).encode()).hexdigest(),
                             "state": "synthetic active run in a temporary Git fixture",
                             "keepalive_home": "temporary isolated directory",
                             "no_callbacks": True}
    finally:
        keepalive.home = original_home
        try:
            driver.doCleanups()
        finally:
            scratch.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation-file", help="test-only offline calibration input; final E2E case uses ancestor lookup")
    args = parser.parse_args()
    work = Path.cwd().resolve()
    report: dict[str, Any] = {
        "schema": "shiploop-startup-contract/v1",
        "verdict": "unknown",
        "work_cwd": str(work),
        "scope": "selected-package documented startup capability; synthetic observer run and argv-only shell stub; "
                 "not natural model behavior or product/cost qualification",
        "probes": [],
        "failure_or_unknown": None,
    }
    receipt: Path | None = None
    package: Path | None = None
    before_entries: Any = None
    before_signature: str | None = None
    try:
        invocation_path, invocation = contract.locate_invocation(work, args.invocation_file)
        receipt = invocation_path.parent / "shiploop-startup-contract-receipt.json"
        report["invocation"] = {"path": str(invocation_path), "case": invocation.get("case"),
                                "host": invocation.get("host"), "cwd": invocation.get("cwd")}
        wanted, package, identity = contract.package_identity(invocation)
        report["package"] = identity
        before_entries, before_signature = contract.tree_signature(package)
        skill, modules = contract.load_selected_modules(package)
        report["selected_skill"] = str(skill)
        report["selected_modules"] = {name: str(Path(module.__file__).resolve())
                                      for name, module in modules.items()}
        run_probe(invocation, package, skill, modules, report, receipt)
        after_entries, after_signature = contract.tree_signature(package)
        if before_entries != after_entries or before_signature != after_signature:
            fail("selected package content or executable modes changed during the startup probe")
        report["package_signature_before_sha256"] = before_signature
        report["package_signature_after_sha256"] = after_signature
        if contract.runner_tree_digest(wanted) != identity["plugin_sha256"]:
            fail("selected package digest changed during the startup probe")
        report["verdict"] = "pass"
        print("PASS: documented startup forms preserve argv and bind through the selected observer")
        return 0
    except ContractFailure as exc:
        report["failure_or_unknown"] = str(exc)
        report["verdict"] = "fail"
        print("FAIL: " + str(exc))
        return 1
    except Exception as exc:  # noqa: BLE001 - unknown identity or fixture mismatch must never pass
        report["failure_or_unknown"] = f"{type(exc).__name__}: {str(exc)[:500]}"
        report["verdict"] = "fail"
        print("FAIL: startup capability could not be established: " + report["failure_or_unknown"])
        return 1
    finally:
        if receipt is not None:
            if package is not None and before_entries is not None:
                try:
                    after_entries, after_signature = contract.tree_signature(package)
                    report["package_signature_before_sha256"] = before_signature
                    report["package_signature_after_sha256"] = after_signature
                    report["package_unchanged"] = before_entries == after_entries
                except Exception as exc:  # noqa: BLE001 - preserve the primary diagnostic in the receipt
                    report["package_after_signature_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            contract.write_receipt(receipt, report)


if __name__ == "__main__":
    raise SystemExit(main())
