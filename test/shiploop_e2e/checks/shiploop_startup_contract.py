"""Probe documented startup shell forms against the selected package observer.

This is a synthetic harness capability check, not evidence of natural model
behavior or a ShipLoop application or cost improvement.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

import shiploop_hook_contract as contract


class ContractFailure(RuntimeError):
    pass


ILLUSTRATIVE_CLI_ROOTS = ("/absolute/", "/selected/")
ILLUSTRATIVE_CLI_SUFFIX = "/scripts/shiploop"


def _is_illustrative_cli_head(value: str) -> bool:
    return any(value.startswith(root) and value.endswith(ILLUSTRATIVE_CLI_SUFFIX)
               and len(value) > len(root) + len(ILLUSTRATIVE_CLI_SUFFIX)
               for root in ILLUSTRATIVE_CLI_ROOTS)


def fail(message: str) -> None:
    raise ContractFailure(message)


def shell_single(value: str) -> str:
    """Return a POSIX single-quoted shell word, escaping embedded apostrophes."""
    return "'" + value.replace("'", "'\\''") + "'"


def shell_double(value: str) -> str:
    """Return a POSIX double-quoted shell word with shell expansions disabled."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace(chr(96), "\\" + chr(96))
    return '"' + escaped + '"'


def _quoted_head(command: str):
    """Return the simply quoted python3 head, its shell-decoded token and quote style."""
    match = re.match(r"""^python3\s+(?P<word>"(?:\\.|[^"\\])*"|'[^']*')(?=\s)""", command)
    if not match:
        return None
    try:
        words = shlex.split(match.group("word"), posix=True)
    except ValueError:
        return None
    if len(words) != 1:
        return None
    return match, words[0], match.group("word")[0]


def _startup_kind(command: str, selected_cli: str) -> str | None:
    head = _quoted_head(command)
    if head is None:
        return None
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return None
    if len(words) < 3 or words[0] != "python3" or words[1] != head[1]:
        return None
    if words[2:4] == ["workspace", "start"]:
        kind = "workspace_start"
    elif words[2] == "init":
        kind = "init"
    else:
        return None
    if head[1] in ("$CLI", selected_cli) or _is_illustrative_cli_head(head[1]):
        return kind
    if Path(head[1]).is_absolute():
        fail(f"unsupported absolute ShipLoop CLI head: {head[1]!r}")
    return None


def startup_commands_from_text(text: str, selected_cli: str) -> list[tuple[str, str]]:
    """Extract simple fenced sh/bash python3 startup commands without rewriting their heads."""
    commands: list[tuple[str, str]] = []
    fences = re.finditer(r"^\x60\x60\x60(?:sh|bash)\s*\n(.*?)^\x60\x60\x60\s*$",
                         text, flags=re.MULTILINE | re.DOTALL)
    for fence in fences:
        pending: str | None = None
        for raw in fence.group(1).splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if pending is None:
                if _quoted_head(line) is None:
                    continue
                pending = line
            else:
                pending += " " + line
            if line.endswith("\\"):
                pending = pending[:-1].rstrip()
                continue
            kind = _startup_kind(pending, selected_cli)
            if kind:
                commands.append((kind, pending))
            pending = None
    return commands


def documented_examples(skill: Path, selected_cli: str) -> dict[str, str]:
    """Read the selected card's first documented workspace-start and init commands."""
    try:
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        fail(f"selected ShipLoop SKILL.md is unreadable: {exc}")
    examples: dict[str, str] = {}
    for kind, command in startup_commands_from_text(text, selected_cli):
        examples.setdefault(kind, command)
    missing = {"workspace_start", "init"} - examples.keys()
    if missing:
        fail("selected SKILL.md lacks supported fenced python3 startup examples: " + ", ".join(sorted(missing)))
    return examples


def _render_path(command: str, name: str, value: str) -> str:
    pattern = re.compile(r'(?P<quote>["\'])\$' + re.escape(name) + r'(?P=quote)')
    match = pattern.search(command)
    if not match:
        return command
    quoted = shell_single(value) if match.group("quote") == "'" else shell_double(value)
    return command[:match.start()] + quoted + command[match.end():]


def render_example(command: str, *, selected_cli: str, repo: str, run_dir: str, request: str) -> str:
    """Render registered illustrative CLI heads and values; leave $CLI and exact heads alone."""
    head = _quoted_head(command)
    if head is None:
        fail("startup example has no simply quoted python3 CLI head")
    match, head_value, quote = head
    if _is_illustrative_cli_head(head_value):
        replacement = shell_single(selected_cli) if quote == "'" else shell_double(selected_cli)
        command = command[:match.start("word")] + replacement + command[match.end("word"):]
    elif head_value == selected_cli or head_value == "$CLI":
        pass
    elif Path(head_value).is_absolute():
        fail(f"unsupported absolute ShipLoop CLI head: {head_value!r}")
    else:
        fail(f"unsupported ShipLoop CLI head: {head_value!r}")
    rendered = _render_path(command, "REPO", repo)
    rendered = _render_path(rendered, "RUN_DIR", run_dir)
    prompt = "--prompt='<user request>'"
    if prompt not in rendered:
        fail("startup example no longer has the supported --prompt='<user request>' slot")
    return rendered.replace(prompt, "--prompt=" + shell_single(request), 1)


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
           before: tuple[dict[str, tuple[str, int]], str], *,
           source_command: str | None = None) -> bool:
    after = contract.tree_signature(package)
    package_unchanged = before == after
    passed = package_unchanged and all(observed.get(key) == value for key, value in expected.items())
    row = {"id": probe_id, "command": command, "expected": expected, "observed": observed,
           "package": {"before_sha256": before[1], "after_sha256": after[1],
                       "unchanged": package_unchanged},
           "status": "pass" if passed else "fail"}
    if source_command is not None:
        row["source_command"] = source_command
    report["probes"].append(row)
    contract.write_receipt(receipt, report)
    if not package_unchanged:
        fail(f"selected package content or executable modes changed during {probe_id}")
    return passed


def observer_probe(report: dict[str, Any], receipt: Path, package: Path, keepalive: Any,
                   host: str, probe_id: str, command: str, marker: str,
                   expected: dict[str, Any], *, source_command: str | None = None) -> dict[str, Any]:
    session = "startup-" + probe_id
    before = contract.tree_signature(package)
    observed = observe(keepalive, host, session, command, marker)
    record(report, receipt, probe_id, command, expected, observed, package, before,
           source_command=source_command)
    keepalive.session_end(host, {"session_id": session})
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


def _argv_stub_command(command: str, selected_cli: str, stub_cli: str) -> str:
    """Point a head at the stub for argv execution only, never to construct observer text."""
    head = _quoted_head(command)
    if head is None:
        fail("argv example has no simply quoted python3 command head")
    match, value, quote = head
    if value == "$CLI":
        return command
    if value != selected_cli:
        fail("argv example names a CLI other than the exact selected package path")
    replacement = shell_single(stub_cli) if quote == "'" else shell_double(stub_cli)
    return command[:match.start("word")] + replacement + command[match.end("word"):]


def _expected_arguments(kind: str, repo: str, run_dir: str, request: str) -> list[str]:
    args = ["workspace", "start"] if kind == "workspace_start" else ["init"]
    args.extend(["--repo", repo])
    if kind == "init":
        args.extend(["--run-dir", run_dir])
    args.append("--prompt=" + request)
    return args


def argv_probe(report: dict[str, Any], receipt: Path, package: Path, probe_id: str,
               observer_command: str, source_command: str, kind: str, selected_cli: str,
               stub_cli: str, env: dict[str, str], repo: str, run_dir: str,
               request: str) -> None:
    stub_command = _argv_stub_command(observer_command, selected_cli, stub_cli)
    observed = _argv_stub(stub_command, env, [stub_cli, *_expected_arguments(kind, repo, run_dir, request)])
    observed["argv_stub_command"] = stub_command
    before = contract.tree_signature(package)
    record(report, receipt, probe_id, observer_command, {"argv_match": True}, observed,
           package, before, source_command=source_command)


def _argv_examples(examples: dict[str, str], literal_examples: list[tuple[str, str]],
                   selected_cli: str, scratch: Path, report: dict[str, Any],
                   receipt: Path, package: Path) -> None:
    special = " path ' $ " + chr(96) + " Ω\ninside\n"
    stub_cli_path = scratch / ("cli" + special)
    repo = scratch / ("repo" + special)
    run_dir = scratch / ("run" + special)
    repo.mkdir()
    run_dir.mkdir()
    stub_cli_path.write_text(
        "import base64, json, os, sys\n"
        "print(json.dumps([base64.b64encode(os.fsencode(value)).decode('ascii') for value in sys.argv]))\n",
        encoding="utf-8")
    stub_cli = str(stub_cli_path)
    env = os.environ.copy()
    env.update({"CLI": stub_cli, "REPO": str(repo), "RUN_DIR": str(run_dir)})
    request = ("--option-like=value apostrophe's dollar$ grave" + chr(96) +
               " Unicode Ω\ninternal line\n")
    report["argv_fixture"] = {"stub_cli_path": stub_cli, "repo_path": str(repo),
                              "run_dir_path": str(run_dir), "request": request,
                              "request_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
                              "paths_are_synthetic": True}
    for kind, probe_id in (("workspace_start", "argv_documented_workspace_start"),
                           ("init", "argv_documented_init")):
        command = render_example(examples[kind], selected_cli=selected_cli, repo=str(repo),
                                 run_dir=str(run_dir), request=request)
        argv_probe(report, receipt, package, probe_id, command, examples[kind], kind, selected_cli,
                   stub_cli, env, str(repo), str(run_dir), request)
    literal_probe_ids = ("argv_literal_absolute_single", "argv_literal_selected_double",
                         "argv_literal_exact_double")
    for probe_id, (kind, source_command) in zip(literal_probe_ids, literal_examples):
        command = render_example(source_command, selected_cli=selected_cli, repo=str(repo),
                                 run_dir=str(run_dir), request=request)
        argv_probe(report, receipt, package, probe_id, command, source_command, kind, selected_cli,
                   stub_cli, env, str(repo), str(run_dir), request)


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
        selected_record = invocation.get("plugin")
        if invocation.get("host") in ("codex", "grok") and isinstance(selected_record, dict):
            selected_root = selected_record.get("path")
        else:
            selected_root = invocation.get("plugin_dir")
        if not isinstance(selected_root, str) or not selected_root:
            fail("selected package identity has no logical package path for its CLI")
        selected_cli = str(Path(selected_root).expanduser() / "skills" / "shiploop" /
                           "scripts" / "shiploop")
        if not Path(selected_cli).is_file():
            fail("selected package's exact ShipLoop CLI path is unavailable")
        source_path = skill / "SKILL.md"
        source_text = source_path.read_text(encoding="utf-8")
        examples = documented_examples(skill, selected_cli)
        repo = str(driver.repo)
        simple_request = "startup observer calibration"
        rendered = {kind: render_example(command, selected_cli=selected_cli, repo=repo,
                                         run_dir=run_dir, request=simple_request)
                    for kind, command in examples.items()}
        report["selected_documentation"] = {
            "path": str(source_path), "sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(),
            "commands": examples, "selected_cli_path": selected_cli,
            "observer_head_policy": (
                "preserve $CLI and exact selected literal; substitute only absolute heads under "
                "/absolute/ or /selected/ ending /scripts/shiploop"),
        }
        report["documented_probe_ids"] = ["documented_workspace_start", "documented_init"]
        for probe_id, kind in (("documented_workspace_start", "workspace_start"),
                               ("documented_init", "init")):
            observer_probe(report, receipt, package, keepalive, host, probe_id, rendered[kind], marker,
                           {"bound": True, "bound_run_id_matches": True},
                           source_command=examples[kind])

        synthetic_source = Path(scratch.name) / "external-synthetic-card.md"
        literal_absolute_single = (
            "python3 '/absolute/directory-containing-the-loaded-SKILL.md/scripts/shiploop' "
            "workspace start --repo \"$REPO\" "
            "--prompt='<user request>'")
        literal_selected_double = (
            'python3 "/selected/synthetic-installed-skill-root/scripts/shiploop" '
            'workspace start --repo "$REPO" '
            "--prompt='<user request>'")
        literal_exact_double = (
            f'python3 "{selected_cli}" workspace start --repo "$REPO" '
            "--prompt='<user request>'")
        synthetic_text = (
            "\x60\x60\x60sh\n" + literal_absolute_single + "\n\x60\x60\x60\n"
            "\x60\x60\x60bash\n" + literal_selected_double + "\n\x60\x60\x60\n"
            "\x60\x60\x60sh\n" + literal_exact_double + "\n\x60\x60\x60\n")
        synthetic_source.write_text(synthetic_text, encoding="utf-8")
        literal_examples = startup_commands_from_text(synthetic_source.read_text(encoding="utf-8"), selected_cli)
        expected_literal_examples = [
            ("workspace_start", literal_absolute_single),
            ("workspace_start", literal_selected_double),
            ("workspace_start", literal_exact_double),
        ]
        if literal_examples != expected_literal_examples:
            fail("external synthetic card did not preserve all registered and exact literal heads")
        report["synthetic_card"] = {
            "source": "temporary external synthetic card text", "path": str(synthetic_source),
            "sha256": hashlib.sha256(synthetic_source.read_bytes()).hexdigest(),
            "commands": [command for _, command in literal_examples], "text": synthetic_text,
        }
        literal_commands: list[tuple[str, str]] = []
        literal_probe_ids = ("literal_absolute_placeholder_single",
                             "literal_selected_placeholder_double",
                             "literal_exact_selected_double")
        for probe_id, (kind, source_command) in zip(literal_probe_ids, literal_examples):
            command = render_example(source_command, selected_cli=selected_cli, repo=repo, run_dir=run_dir,
                                     request=simple_request)
            observer_probe(report, receipt, package, keepalive, host, probe_id, command, marker,
                           {"bound": True, "bound_run_id_matches": True},
                           source_command=source_command)
            literal_commands.append((kind, source_command))

        foreign_source = Path(scratch.name) / "external-foreign-head-card.md"
        foreign_command = (
            "python3 '/foreign/unknown/scripts/shiploop' workspace start --repo \"$REPO\" "
            "--prompt='<user request>'")
        foreign_text = "\x60\x60\x60sh\n" + foreign_command + "\n\x60\x60\x60\n"
        foreign_source.write_text(foreign_text, encoding="utf-8")
        try:
            foreign_examples = startup_commands_from_text(
                foreign_source.read_text(encoding="utf-8"), selected_cli)
        except ContractFailure as exc:
            foreign_observed = {
                "rejected": str(exc).startswith("unsupported absolute ShipLoop CLI head:"),
                "observer_called": False, "rendered_command": None, "reason": str(exc),
            }
        else:
            foreign_observed = {
                "rejected": False, "observer_called": False, "rendered_command": None,
                "reason": "extraction returned " + repr(foreign_examples) + " without an unsupported-head report",
            }
        report["foreign_literal_card"] = {
            "source": "temporary external unsupported-head card text", "path": str(foreign_source),
            "sha256": hashlib.sha256(foreign_source.read_bytes()).hexdigest(),
            "command": foreign_command, "text": foreign_text,
        }
        foreign_probe_before = contract.tree_signature(package)
        record(report, receipt, "unsupported_foreign_literal", foreign_command,
               {"rejected": True, "observer_called": False, "rendered_command": None},
               foreign_observed, package, foreign_probe_before, source_command=foreign_command)

        variable_source = (
            'python3 "$CLI" workspace start --repo "$REPO" --prompt=\'<user request>\'')
        variable_command = render_example(
            variable_source, selected_cli=selected_cli, repo=repo, run_dir=run_dir,
            request=simple_request)
        observer_probe(report, receipt, package, keepalive, host, "variable_head",
                       variable_command, marker, {"bound": False},
                       source_command=variable_source)

        packet = shell_single(str(Path(run_dir) / "packets" / "next.md"))
        observer_probe(report, receipt, package, keepalive, host, "read_packet",
                       "cat " + packet, marker, {"bound": False})
        read_status = "python3 " + shell_double(selected_cli) + " hook-status --run-dir " + shell_single(run_dir)
        observer_probe(report, receipt, package, keepalive, host, "read_status",
                       read_status, marker, {"bound": False})

        missing_dir = str(Path(scratch.name) / "missing-run")
        missing_command = render_example(literal_absolute_single, selected_cli=selected_cli,
                                         repo=repo, run_dir=missing_dir,
                                         request=simple_request)
        missing_marker = _marker("missing-run-id", live.get("revision"), missing_dir)
        observer_probe(report, receipt, package, keepalive, host, "missing_state",
                       missing_command, missing_marker, {"bound": False},
                       source_command=literal_absolute_single)

        corrupt_dir = Path(scratch.name) / "corrupt-run"
        corrupt_dir.mkdir()
        (corrupt_dir / "state.md").write_text("not a ShipLoop state record\n", encoding="utf-8")
        corrupt_command = render_example(literal_absolute_single, selected_cli=selected_cli, repo=repo,
                                         run_dir=str(corrupt_dir),
                                         request=simple_request)
        corrupt_marker = _marker("corrupt-run-id", live.get("revision"), str(corrupt_dir))
        observer_probe(report, receipt, package, keepalive, host, "corrupt_state",
                       corrupt_command, corrupt_marker, {"bound": False},
                       source_command=literal_absolute_single)

        owner_session = "startup-owner"
        foreign_session = "startup-foreign-owner"
        owner_probe_before = contract.tree_signature(package)
        if not keepalive.claim_owner(run_dir, host, owner_session):
            fail("temporary owner fixture could not claim its own run")
        foreign_owner_command = render_example(literal_absolute_single, selected_cli=selected_cli,
                                               repo=repo, run_dir=run_dir, request=simple_request)
        foreign_binding = keepalive.observe(
            host, {"session_id": foreign_session, "tool_input": {"command": foreign_owner_command},
                   "tool_response": marker})
        if not isinstance(foreign_binding, dict) or foreign_binding.get("run_id") != live["run_id"]:
            fail("foreign session did not receive the live marker binding needed for ownership calibration")
        decision = keepalive._decide(host, foreign_session, foreign_binding)
        owner_after = keepalive._load_owner(run_dir).get("owner")
        observed = {"decision": decision.get("decision"), "why": decision.get("why"),
                    "owner_preserved": owner_after == keepalive._owner_id(host, owner_session)}
        record(report, receipt, "foreign_owner", foreign_owner_command,
               {"decision": "allow", "owner_preserved": True}, observed, package, owner_probe_before,
               source_command=literal_absolute_single)
        keepalive.session_end(host, {"session_id": foreign_session})
        keepalive.release_owner(run_dir, host, owner_session)

        _argv_examples(examples, literal_commands, selected_cli, Path(scratch.name),
                       report, receipt, package)
        report["fixture"] = {"run_id_sha256": hashlib.sha256(str(live["run_id"]).encode()).hexdigest(),
                             "state": "synthetic active run in a temporary Git fixture",
                             "keepalive_home": "temporary isolated directory",
                             "no_callbacks": True}
        controls = {
            "literal_absolute_placeholder_single", "literal_selected_placeholder_double",
            "literal_exact_selected_double", "unsupported_foreign_literal", "variable_head",
            "read_packet", "read_status", "missing_state", "corrupt_state", "foreign_owner",
            "argv_documented_workspace_start", "argv_documented_init",
            "argv_literal_absolute_single", "argv_literal_selected_double",
            "argv_literal_exact_double",
        }
        rows = {row["id"]: row for row in report["probes"]}
        report["calibration_verdict"] = (
            "pass" if controls.issubset(rows) and all(rows[item]["status"] == "pass" for item in controls)
            else "fail")
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
        "schema": "shiploop-startup-contract/v2",
        "verdict": "unknown",
        "calibration_verdict": "unknown",
        "work_cwd": str(work),
        "scope": "selected-package documented startup capability; raw or registered-placeholder-rendered heads reach the selected observer; "
                 "temporary observer state and argv-only shell stub; not natural model behavior or product/cost qualification",
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
        failed = [row["id"] for row in report["probes"] if row["status"] != "pass"]
        if failed:
            documented_failures = [probe_id for probe_id in report.get("documented_probe_ids", [])
                                   if probe_id in failed]
            if documented_failures:
                report["failure_or_unknown"] = (
                    "selected package documented startup commands did not bind through the observer: "
                    + ", ".join(documented_failures)
                )
            else:
                report["failure_or_unknown"] = "one or more startup contract probes failed: " + ", ".join(failed)
            report["verdict"] = "fail"
            print("FAIL: " + report["failure_or_unknown"] +
                  f"; independent calibration {report['calibration_verdict']}")
            return 1
        report["verdict"] = "pass"
        print("PASS: selected package documented startup forms preserve argv and bind")
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
