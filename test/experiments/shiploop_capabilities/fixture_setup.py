#!/usr/bin/env python3
"""Create isolated, synthetic Checkers fixtures for capability experiments.

This is coordinator tooling.  It writes only temporary worker workspaces passed
by the caller.  It does not launch agents, use a real account, install packages,
or call an external network endpoint.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.request import urlopen


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
sys.path.insert(0, str(FIXTURES))
from app import (  # noqa: E402
    AUTHORITATIVE_RECEIPTS_ENV,
    DEFAULT_ACTOR_TOKENS,
    DEFAULT_SERVICE_CONFIG,
    FIXTURE_REVISION,
    capture_trace_state,
    default_state,
    write_state,
)


CASES = ("ENV", "INNER", "OUTER", "OUTER_HOLDOUT", "TEST")
VARIANTS = (
    "baseline",
    "skill-procedure",
    "metadata-only",
    "acquisition-available",
    "acquisition-unavailable",
    "timing-initial-only",
    "timing-gap-triggered",
    "timing-unchanged",
    "timing-new-gap",
    "timing-stable",
)
MUTANTS = ("wrong_actor", "duplicate", "stale", "cache", "invalid_move")


@dataclass
class ServiceProcess:
    """A loopback child process plus its durable readiness and cleanup receipts."""

    process: subprocess.Popen[str]
    ready_file: Path
    stdout_file: Path
    stderr_file: Path
    _stdout: Any
    _stderr: Any

    @property
    def ready(self) -> dict[str, Any]:
        return json.loads(self.ready_file.read_text(encoding="utf-8"))

    @property
    def url(self) -> str:
        return str(self.ready["url"])

    def stop(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=4)
        self._stdout.close()
        self._stderr.close()
        receipt = self.ready_file.with_name("service-cleanup.json")
        receipt.write_text(
            json.dumps(
                {
                    "cleanupPID": self.process.pid,
                    "returncode": self.process.returncode,
                    "stopped": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )


@dataclass
class CaseLayout:
    """A worker-visible workspace and its process-start helper."""

    case: str
    workspace: Path
    variant: str
    served_revision: str
    served_config: dict[str, Any]
    prime_cache_on_start: bool = False

    @property
    def ready_file(self) -> Path:
        return self.workspace / "service-ready.json"

    @property
    def command(self) -> list[str]:
        return [
            sys.executable,
            str(self.workspace / "app.py"),
            "--workspace",
            str(self.workspace),
            "--config",
            str(self.workspace / "served-service-config.json"),
            "--revision",
            self.served_revision,
            "--port",
            "0",
            "--ready-file",
            str(self.ready_file),
        ]

    def start(
        self,
        timeout_seconds: float = 5.0,
        *,
        authoritative_receipt_path: Path | str | None = None,
    ) -> ServiceProcess:
        """Start the generated source with only explicitly configured receipts."""

        self.ready_file.unlink(missing_ok=True)
        stdout_file = self.workspace / "service.stdout.log"
        stderr_file = self.workspace / "service.stderr.log"
        stdout = stdout_file.open("w", encoding="utf-8")
        stderr = stderr_file.open("w", encoding="utf-8")
        environment = dict(os.environ)
        environment.pop(AUTHORITATIVE_RECEIPTS_ENV, None)
        if authoritative_receipt_path is not None:
            environment[AUTHORITATIVE_RECEIPTS_ENV] = str(authoritative_receipt_path)
        process = subprocess.Popen(
            self.command,
            cwd=self.workspace,
            env=environment,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
        )
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            if self.ready_file.is_file():
                running = ServiceProcess(process, self.ready_file, stdout_file, stderr_file, stdout, stderr)
                if self.prime_cache_on_start:
                    with urlopen(running.url + "/api/state", timeout=2) as response:  # noqa: S310 - loopback fixture
                        if response.status != 200:
                            running.stop()
                            raise RuntimeError(f"cache-prime state read failed: {response.status}")
                return running
            if process.poll() is not None:
                stdout.close()
                stderr.close()
                detail = stderr_file.read_text(encoding="utf-8") if stderr_file.exists() else ""
                raise RuntimeError(f"synthetic service exited before readiness ({process.returncode}): {detail}")
            time.sleep(0.02)
        process.terminate()
        process.wait(timeout=2)
        stdout.close()
        stderr.close()
        raise TimeoutError(f"synthetic service did not create {self.ready_file}")


def _replace_once(source: str, old: str, new: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"worker-source transformation expected one match, found {count}: {old[:72]!r}")
    return source.replace(old, new)


def _remove_between(source: str, start: str, end: str) -> str:
    beginning = source.find(start)
    finish = source.find(end, beginning)
    if beginning < 0 or finish < 0:
        raise RuntimeError(f"worker-source transformation could not locate {start!r}")
    return source[:beginning] + source[finish:]


def _baked_app_source(selected: Iterable[str] = ()) -> str:
    """Produce worker source with one behavior baked and no selector exposed."""

    selected_set = frozenset(selected)
    unknown = selected_set.difference(MUTANTS)
    if unknown:
        raise ValueError(f"unknown mutant names: {sorted(unknown)}")
    source = (FIXTURES / "app.py").read_text(encoding="utf-8")
    source = _replace_once(
        source,
        "from typing import Any, Iterable, Mapping",
        "from typing import Any, Mapping",
    )
    source = _replace_once(source, "        defects: Iterable[str] = (),\n", "")
    source = _replace_once(
        source,
        '''        self.defects = frozenset(defects)
        unknown = self.defects.difference(
            {"wrong_actor", "duplicate", "stale", "cache", "invalid_move"}
        )
        if unknown:
            raise ValueError(f"unknown fixture defects: {sorted(unknown)}")
''',
        "",
    )
    source = _replace_once(
        source,
        '            self._observe("store_started", revision=self.revision, defects=sorted(self.defects))',
        '            self._observe("store_started", revision=self.revision)',
    )
    duplicate_block = '''                if old_record:
                    if old_record["request"] != request:
                        return self._error(409, "idempotency_conflict")
                    if "duplicate" not in self.defects:
                        replay = copy.deepcopy(old_record["response"])
                        replay["idempotentReplay"] = True
                        self._observe("move_replayed", version=state["version"])
                        return Outcome(200, replay)
                    return self._apply_duplicate_mutant(state, request)
'''
    if "duplicate" in selected_set:
        duplicate_replacement = '''                if old_record:
                    if old_record["request"] != request:
                        return self._error(409, "idempotency_conflict")
                    return self._apply_repeated_request(state, request)
'''
        source = _replace_once(source, duplicate_block, duplicate_replacement)
        source = _replace_once(source, "_apply_duplicate_mutant", "_apply_repeated_request")
        source = _replace_once(source, '"duplicateMutation": True', '"repeatedRequest": True')
        source = _replace_once(source, '"duplicate_mutation_applied"', '"repeated_request_applied"')
    else:
        duplicate_replacement = '''                if old_record:
                    if old_record["request"] != request:
                        return self._error(409, "idempotency_conflict")
                    replay = copy.deepcopy(old_record["response"])
                    replay["idempotentReplay"] = True
                    self._observe("move_replayed", version=state["version"])
                    return Outcome(200, replay)
'''
        source = _replace_once(source, duplicate_block, duplicate_replacement)
        source = _remove_between(source, "    def _apply_duplicate_mutant", "    def _load_state")
    stale_block = '''                if request["expectedVersion"] != state["version"] and "stale" not in self.defects:
                    return self._error(409, "version_mismatch")
'''
    if "stale" in selected_set:
        source = _replace_once(source, stale_block, "")
    else:
        source = _replace_once(
            source,
                stale_block,
                '''                if request["expectedVersion"] != state["version"]:
                    return self._error(409, "version_mismatch")
''',
        )
    source = _replace_once(
        source,
        '''        if request["actor"] != authenticated["actor"] and "wrong_actor" not in self.defects:
            raise ValidationError(403, "actor_mismatch")
''',
        "" if "wrong_actor" in selected_set else '''        if request["actor"] != authenticated["actor"]:
            raise ValidationError(403, "actor_mismatch")
''',
    )
    invalid_block = '''        if "invalid_move" in self.defects:
            return capture
        if not capture and not self._is_quiet_move(source, target, piece):
            raise ValidationError(422, "illegal_move")
        if not capture and self._has_any_capture(state, request["actor"]):
            raise ValidationError(422, "capture_required")
        return capture
'''
    source = _replace_once(
        source,
        invalid_block,
        "        return capture\n" if "invalid_move" in selected_set else invalid_block.replace(
            '        if "invalid_move" in self.defects:\n            return capture\n', ""
        ),
    )
    cache_block = '''                if "cache" not in self.defects:
                    self._cache = None
                    self._cache_at = 0.0
'''
    cache_count = source.count(cache_block)
    if cache_count not in {1, 2}:
        raise RuntimeError(f"worker-source transformation expected one or two cache blocks, found {cache_count}")
    source = source.replace(
        cache_block,
        "" if "cache" in selected_set else "                self._cache = None\n                self._cache_at = 0.0\n",
    )
    repeated_cache_block = '''        if "cache" not in self.defects:
            self._cache = None
            self._cache_at = 0.0
'''
    repeated_cache_count = source.count(repeated_cache_block)
    if repeated_cache_count not in {0, 1}:
        raise RuntimeError(
            f"worker-source transformation expected zero or one repeated-request cache block, found {repeated_cache_count}"
        )
    source = source.replace(
        repeated_cache_block,
        "" if "cache" in selected_set else "        self._cache = None\n        self._cache_at = 0.0\n",
    )
    source = _replace_once(source, '    parser.add_argument("--defect", action="append", default=[])\n', "")
    source = _replace_once(source, '        defects=args.defect,\n', "")
    source = source.replace("    `defects` selects explicitly declared experiment mutants; it defaults to an\n    empty set for the correct implementation.\n", "")
    if "defects" in source:
        at = source.index("defects")
        raise RuntimeError(f"generated worker source still exposes a selector: {source[at - 60:at + 100]!r}")
    return source


def materialize_mutant(name: str, destination: Path | str) -> Path:
    """Coordinator-only: write one hidden implementation variant outside a worker root."""

    if name not in MUTANTS:
        raise ValueError(f"unknown mutant: {name}")
    target = Path(destination)
    if target.exists() and target.is_dir():
        target = target / "app.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(_baked_app_source((name,)), encoding="utf-8")
    return target


def _case_behavior(case: str) -> tuple[set[str], str, dict[str, Any], dict[str, Any]]:
    config = dict(DEFAULT_SERVICE_CONFIG)
    state = default_state()
    if case == "INNER":
        return {"duplicate", "stale"}, "inner-seeded-r1", config, state
    if case == "OUTER":
        config["cacheTtlSeconds"] = 60
        return {"cache"}, "served-r0", config, state
    if case == "OUTER_HOLDOUT":
        config["requiredScope"] = "checkers:admin"
        return set(), "served-permission-r0", config, state
    if case == "ENV":
        return set(), "environment-r1", config, capture_trace_state()
    if case == "TEST":
        return set(), "test-reference-r1", config, state
    raise ValueError(f"unsupported case: {case}")


def _catalog(variant: str) -> dict[str, Any]:
    procedure = "available" if variant in {"baseline", "skill-procedure", "timing-gap-triggered"} else "metadata-only"
    if variant in {"timing-new-gap", "timing-stable"}:
        procedure = "available"
    if variant == "acquisition-available":
        procedure = "eligibility-only-no-capability-supplied"
    if variant == "acquisition-unavailable":
        procedure = "not-eligible-no-unique-gap"
    return {
        "purpose": "small synthetic catalog; not a package installer",
        "variant": variant,
        "entries": [
            {
                "name": "http-state-testing",
                "status": procedure,
                "purpose": "inspect HTTP state, retries, version boundaries, and a browser/client trace",
                "requires": ["loopback endpoint or native state reader"],
            },
            {
                "name": "design-copywriting",
                "status": "available",
                "purpose": "unrelated presentation guidance",
                "requires": [],
            },
            {
                "name": "legacy-remote-debugger",
                "status": "incompatible",
                "purpose": "requires an unavailable remote browser service",
                "requires": ["remote browser service"],
            },
        ],
    }


def _write_case_note(case: str, workspace: Path) -> None:
    notes = {
        "ENV": """# Environment investigation fixture

Inspect the local source, runtime receipt, and authorized observation boundary.
A historical note claims that the browser calls a filesystem MCP directly; verify
or correct that claim from current evidence.  The application RPC is separate
from the optional inspection reader.  One resource is intentionally not supplied;
record that boundary rather than inventing access.
""",
        "INNER": """# Inner-loop fixture

The supplied trace shows a request retry and a client that submits an older
version after another write.  Diagnose and repair the existing transport/state
behavior, then use ordinary and HTTP checks appropriate to the workspace.
""",
        "OUTER": """# Outer-loop fixture

Local ordinary tests may pass while the running service has a distinct revision
and effective configuration.  Verify source, served metadata, and a state read
after a write before making a readiness decision.
""",
        "OUTER_HOLDOUT": """# Outer-loop holdout fixture

This is a separate service permission/configuration boundary.  Use the actual
served response and configuration evidence to determine readiness; do not infer
it from the revision/cache scenario.
""",
        "TEST": """# Test-expansion fixture

Keep application implementation fixed.  Expand executable tests around the
public HTTP/state contract and independent boundary examples.  Do not claim a
test family is covered solely because an ordinary happy-path test passes.
""",
    }
    (workspace / "CASE.md").write_text(notes[case], encoding="utf-8")


def _write_variant_artifacts(case: str, variant: str, workspace: Path) -> None:
    """Add public, fair evidence for the few preregistered variant traces."""

    procedure_variants = {"skill-procedure", "metadata-only"}
    if case == "INNER" and variant in procedure_variants:
        (workspace / "interaction-trace.json").write_text(
            json.dumps(
                {
                    "trace": [
                        {"step": 1, "operation": "POST /api/move", "request": "red b2->c3 v1 key retry-1"},
                        {"step": 2, "operation": "service restart", "fact": "state.json remains authoritative"},
                        {"step": 3, "operation": "POST /api/move", "request": "repeat step 1 exactly"},
                        {"step": 4, "operation": "POST /api/move", "request": "black g7->f6 with expectedVersion 1"},
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    if case == "TEST" and variant in procedure_variants:
        (workspace / "cache-prime-trace.json").write_text(
            json.dumps(
                {
                    "beforeWorker": ["GET /api/state"],
                    "purpose": "prime the served state cache before the first move",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (workspace / "tests" / "test_variant_black_turn.py").write_text(
            '''import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import Store, default_state, write_state


class OrdinaryBlackTurnTest(unittest.TestCase):
    def test_black_can_make_an_ordinary_opening_move(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-black-turn-") as raw:
            state = default_state()
            state["turn"] = "black"
            write_state(Path(raw) / "state.json", state)
            result = Store(raw).move(
                actor="black", from_square="g7", to_square="f6", expected_version=1,
                idempotency_key="ordinary-black", authorization="Bearer black-fixture-token",
            )
            self.assertEqual(200, result.status)


if __name__ == "__main__":
    unittest.main()
''',
            encoding="utf-8",
        )
    if case == "OUTER_HOLDOUT" and variant in {"timing-gap-triggered", "timing-new-gap"}:
        (workspace / "checkpoint-two.md").write_text(
            "At checkpoint two, a newly asked question is whether the actual service authorizes the configured client mutation scope. Reuse earlier revision findings, then inspect the served authorization boundary.\n",
            encoding="utf-8",
        )
    if case == "ENV" and variant in {"timing-unchanged", "timing-stable"}:
        (workspace / "checkpoint-two.md").write_text(
            "At checkpoint two, the question and supplied environment evidence are unchanged. Reuse the existing supported finding; a cheap confirming read is optional.\n",
            encoding="utf-8",
        )


def create_case(
    case: str,
    workspace: Path | str,
    *,
    variant: str = "baseline",
    mutant: str | None = None,
) -> CaseLayout:
    """Materialize one worker-visible synthetic case directly in `workspace`.

    `mutant` is reserved for coordinator-controlled diagnostic setup.  Normal
    TEST workers receive the correct app; use `materialize_mutant` after a run
    to assess expanded tests without disclosing source variants beforehand.
    """

    normalized_case = case.upper()
    if normalized_case not in CASES:
        raise ValueError(f"case must be one of {CASES}, got {case!r}")
    if variant not in VARIANTS:
        raise ValueError(f"variant must be one of {VARIANTS}, got {variant!r}")
    if mutant is not None and mutant not in MUTANTS:
        raise ValueError(f"unknown mutant: {mutant}")
    root = Path(workspace).resolve()
    if root.exists():
        if not root.is_dir():
            raise NotADirectoryError(f"case workspace is not a directory: {root}")
        if any(root.iterdir()):
            raise FileExistsError(f"refusing to overwrite nonempty case workspace: {root}")
    else:
        root.mkdir(parents=True)
    selected, revision, config, state = _case_behavior(normalized_case)
    if mutant:
        selected = {mutant}
    write_state(root / "state.json", state)
    scenario = {
        "initialStateFile": "state.json",
        "case": normalized_case,
        "trace": [],
    }
    if normalized_case == "ENV":
        scenario["trace"] = [
            "red b2 captures d4 over c3",
            "red must then capture f6 over e5 before black receives the turn",
        ]
    (root / "scenario.json").write_text(
        json.dumps(scenario, indent=2) + "\n", encoding="utf-8"
    )
    (root / "app.py").write_text(_baked_app_source(selected), encoding="utf-8")
    shutil.copy2(FIXTURES / "client.html", root / "client.html")
    shutil.copy2(FIXTURES / "SPEC.md", root / "SPEC.md")
    tests_dir = root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy2(FIXTURES / "test_app.py", tests_dir / "test_app.py")
    (root / "runtime-observations").mkdir(exist_ok=True)
    (root / "runtime-observations" / "README.md").write_text(
        "This is an inspection-only observation root for an already-configured filesystem reader.\n"
        "Its permission bits do not make it authoritative against the same local identity.\n",
        encoding="utf-8",
    )
    (root / "connection.json").write_text(
        json.dumps(
            {
                "baseUrl": "read service-ready.json after start",
                "authorization": "Authorization: Bearer <synthetic actor token>",
                "actors": {
                    "red": {"token": "red-fixture-token"},
                    "black": {"token": "black-fixture-token"},
                },
                "syntheticOnly": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    candidate_config = dict(DEFAULT_SERVICE_CONFIG)
    candidate_revision = "candidate-r1"
    if normalized_case == "OUTER":
        candidate_config["cacheTtlSeconds"] = 0
    if normalized_case == "OUTER_HOLDOUT":
        candidate_config["requiredScope"] = "checkers:write"
    (root / "candidate-revision.txt").write_text(candidate_revision + "\n", encoding="utf-8")
    (root / "candidate-service-config.json").write_text(
        json.dumps(candidate_config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "served-revision.txt").write_text(revision + "\n", encoding="utf-8")
    (root / "served-service-config.json").write_text(
        json.dumps(config, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "skill-catalog.json").write_text(
        json.dumps(_catalog(variant), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (root / "access-policy.json").write_text(
        json.dumps(
            {
                "applicationRpc": "HTTP",
                "filesystemObservationRoot": "runtime-observations",
                "filesystemReader": "existing only if configured by the host",
                "notSupplied": ["remote account", "external deployment target", "denied-resource contents"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_case_note(normalized_case, root)
    _write_variant_artifacts(normalized_case, variant, root)
    manifest = {
        "case": normalized_case,
        "variant": variant,
        "source": "synthetic-loopback-only",
        "stateFile": "state.json",
        "applicationRpc": "HTTP",
        "applicationRpcIsMcp": False,
        "readyFile": "service-ready.json",
        "observationRoot": "runtime-observations",
        "workspaceObservations": "inspection-only-untrusted",
        "fixtureContractRevision": FIXTURE_REVISION,
        "workerVisibleRoot": ".",
    }
    (root / "fixture-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    command = [
        "python3",
        "app.py",
        "--workspace",
        ".",
        "--config",
        "served-service-config.json",
        "--revision",
        revision,
        "--port",
        "0",
        "--ready-file",
        "service-ready.json",
    ]
    (root / "service-command.json").write_text(
        json.dumps({"argv": command, "cwd": ".", "cleanup": "terminate PID in service-ready.json"}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    return CaseLayout(
        normalized_case,
        root,
        variant,
        revision,
        config,
        normalized_case == "TEST" and variant in {"skill-procedure", "metadata-only"},
    )


def _smoke(case: str) -> None:
    with tempfile.TemporaryDirectory(prefix="shiploop-capability-smoke-") as raw:
        layout = create_case(case, raw)
        running = layout.start()
        try:
            with urlopen(running.url + "/api/meta", timeout=2) as response:  # noqa: S310 - loopback fixture
                meta = json.loads(response.read())
            if meta["rpcTransport"] != "http":
                raise RuntimeError(f"unexpected smoke metadata: {meta}")
        finally:
            running.stop()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", choices=CASES, help="write a case to --workspace")
    parser.add_argument("--workspace", help="destination for --create")
    parser.add_argument("--variant", choices=VARIANTS, default="baseline")
    parser.add_argument("--smoke", choices=CASES, help="create and loopback-smoke a temporary case")
    args = parser.parse_args()
    if args.smoke:
        _smoke(args.smoke)
        print(json.dumps({"smoke": args.smoke, "result": "passed"}))
        return
    if not args.create or not args.workspace:
        parser.error("supply --smoke CASE or both --create CASE and --workspace PATH")
    layout = create_case(args.create, args.workspace, variant=args.variant)
    print(json.dumps({"case": layout.case, "workspace": str(layout.workspace), "command": layout.command}))


if __name__ == "__main__":
    main()
