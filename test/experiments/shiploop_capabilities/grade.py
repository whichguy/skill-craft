#!/usr/bin/env python3
"""Independent behavioral grader for the ShipLoop capability fixture.

The grader deliberately writes its own default state from the frozen public
specification.  It never asks a candidate implementation for expected output.
It supports three bounded modes:

* ``calibration`` proves the correct reference passes and each declared defect
  fails a relevant frozen check;
* ``inner`` grades a final implementation against the held-out behavior; and
* ``test`` runs a worker's unchanged ``test*.py`` files against a fixed
  reference and grader-only mutant source files.

No network, package installation, credential, deployment, or agent action is
performed by this module.
"""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
import hashlib
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
import uuid
from typing import Any, Callable, Iterable, Mapping


DEFAULT_STATE: dict[str, Any] = {
    "schemaVersion": 1,
    "board": {
        "b2": {"actor": "red", "king": False},
        "g7": {"actor": "black", "king": False},
    },
    "turn": "red",
    "version": 1,
    "forcedFrom": None,
    "history": [],
    "idempotency": {},
}

ACTOR_TOKENS: dict[str, dict[str, Any]] = {
    "red-fixture-token": {"actor": "red", "scopes": ["checkers:write"]},
    "black-fixture-token": {"actor": "black", "scopes": ["checkers:write"]},
    "red-readonly-token": {"actor": "red", "scopes": ["checkers:read"]},
}
SERVICE_CONFIG = {"requiredScope": "checkers:write", "cacheTtlSeconds": 3_600}
AUTHORITATIVE_RECEIPTS_ENV = "SHIPLOOP_CAPABILITY_SERVICE_RECEIPTS"
_NO_HTTP_BODY = object()
ORACLE_REVISION = "capability-oracle-r2"


class CheckFailure(AssertionError):
    """A frozen observable expectation was not met."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CheckFailure(message)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_binding(path: Path | str, *, kind: str) -> dict[str, Any]:
    """Describe one receipt input without reading it after execution begins."""

    supplied = Path(path).expanduser()
    try:
        resolved = supplied.resolve()
        is_file = resolved.is_file()
    except OSError as error:
        return {
            "kind": kind,
            "supplied_path": str(supplied),
            "path": None,
            "sha256": None,
            "exists": False,
            "error": f"{type(error).__name__}: {error}",
        }
    if not is_file:
        return {
            "kind": kind,
            "supplied_path": str(supplied),
            "path": str(resolved),
            "sha256": None,
            "exists": False,
            "error": "not_a_file",
        }
    try:
        digest = _hash_file(resolved)
    except OSError as error:
        return {
            "kind": kind,
            "supplied_path": str(supplied),
            "path": str(resolved),
            "sha256": None,
            "exists": False,
            "error": f"{type(error).__name__}: {error}",
        }
    return {
        "kind": kind,
        "supplied_path": str(supplied),
        "path": str(resolved),
        "sha256": digest,
        "exists": True,
        "error": None,
    }


def _tree_binding(path: Path | str) -> dict[str, Any]:
    """Hash the worker input tree before any reference or mutant test run."""

    supplied = Path(path).expanduser()
    try:
        resolved = supplied.resolve()
        if not resolved.is_dir():
            raise NotADirectoryError(resolved)
        entries = sorted(resolved.rglob("*"), key=lambda entry: entry.relative_to(resolved).as_posix())
    except OSError as error:
        return {
            "kind": "worker_test_tree",
            "supplied_path": str(supplied),
            "path": None,
            "sha256": None,
            "file_count": 0,
            "exists": False,
            "error": f"{type(error).__name__}: {error}",
        }

    digest = hashlib.sha256()
    file_count = 0
    try:
        for entry in entries:
            relative = entry.relative_to(resolved).as_posix()
            if entry.is_symlink():
                digest.update(b"symlink\0" + relative.encode("utf-8") + b"\0" + os.readlink(entry).encode("utf-8"))
                file_count += 1
            elif entry.is_file():
                digest.update(b"file\0" + relative.encode("utf-8") + b"\0")
                digest.update(entry.read_bytes())
                file_count += 1
    except OSError as error:
        return {
            "kind": "worker_test_tree",
            "supplied_path": str(supplied),
            "path": str(resolved),
            "sha256": None,
            "file_count": file_count,
            "exists": False,
            "error": f"{type(error).__name__}: {error}",
        }
    return {
        "kind": "worker_test_tree",
        "supplied_path": str(supplied),
        "path": str(resolved),
        "sha256": digest.hexdigest(),
        "file_count": file_count,
        "exists": True,
        "error": None,
    }


def _service_environment(*, authoritative_receipt_path: Path | str | None = None) -> dict[str, str]:
    """Make receipt routing explicit for an isolated grader process."""

    environment = dict(os.environ)
    environment.pop(AUTHORITATIVE_RECEIPTS_ENV, None)
    if authoritative_receipt_path is not None:
        environment[AUTHORITATIVE_RECEIPTS_ENV] = str(authoritative_receipt_path)
    return environment


def _construct_store(
    constructor: Callable[[], Any], *, authoritative_receipt_path: Path | str | None = None
) -> Any:
    """Construct an in-process Store without inheriting a parent receipt path."""

    previous = os.environ.get(AUTHORITATIVE_RECEIPTS_ENV)
    had_previous = AUTHORITATIVE_RECEIPTS_ENV in os.environ
    os.environ.pop(AUTHORITATIVE_RECEIPTS_ENV, None)
    if authoritative_receipt_path is not None:
        os.environ[AUTHORITATIVE_RECEIPTS_ENV] = str(authoritative_receipt_path)
    try:
        return constructor()
    finally:
        if had_previous:
            os.environ[AUTHORITATIVE_RECEIPTS_ENV] = str(previous)
        else:
            os.environ.pop(AUTHORITATIVE_RECEIPTS_ENV, None)


def _receipt_bindings(
    *,
    reference: Path | None = None,
    candidate: Path | None = None,
    mutants: Mapping[str, Path] | None = None,
    tests_root: Path | None = None,
) -> dict[str, Any]:
    """Capture all score-relevant inputs before a mode starts executing."""

    source = Path(__file__).resolve()
    bindings: dict[str, Any] = {
        "spec": _file_binding(source.with_name("fixtures") / "SPEC.md", kind="public_spec"),
        "fixture_setup": _file_binding(source.with_name("fixture_setup.py"), kind="fixture_setup"),
    }
    if reference is not None:
        bindings["reference"] = _file_binding(reference, kind="fixed_reference")
    if candidate is not None:
        bindings["candidate"] = _file_binding(candidate, kind="candidate_app")
    if mutants is not None:
        bindings["mutants"] = {
            name: _file_binding(path, kind="provided_mutant_source")
            for name, path in mutants.items()
        }
    if tests_root is not None:
        bindings["worker_test_tree"] = _tree_binding(tests_root)
    return bindings


def _validate_mutant_sources(
    *, reference: Path, mutants: Mapping[str, Path]
) -> dict[str, Any]:
    """Require one distinct non-reference file for every declared family."""

    expected = tuple(MUTANT_PROBES)
    selected = tuple(mutants)
    missing = sorted(set(expected).difference(selected))
    unexpected = sorted(set(selected).difference(expected))
    reference_binding = _file_binding(reference, kind="fixed_reference")
    mutant_bindings = {
        name: _file_binding(path, kind="provided_mutant_source") for name, path in mutants.items()
    }
    errors: list[str] = []
    if not reference_binding["exists"]:
        errors.append("reference source is unavailable")
    for name, binding in mutant_bindings.items():
        if not binding["exists"]:
            errors.append(f"{name}: source is unavailable")

    paths: dict[str, str] = {}
    hashes: dict[str, str] = {}
    reference_hash = reference_binding.get("sha256")
    for name, binding in mutant_bindings.items():
        path = binding.get("path")
        source_hash = binding.get("sha256")
        if isinstance(path, str):
            original = paths.setdefault(path, name)
            if original != name:
                errors.append(f"{name}: source path aliases {original}")
        if isinstance(source_hash, str):
            original = hashes.setdefault(source_hash, name)
            if original != name:
                errors.append(f"{name}: source hash duplicates {original}")
            if source_hash == reference_hash:
                errors.append(f"{name}: source hash equals the reference")

    exact_families = not missing and not unexpected
    return {
        "expected_families": list(expected),
        "selected_families": list(selected),
        "missing_families": missing,
        "unexpected_families": unexpected,
        "exact_declared_families": exact_families,
        "valid": exact_families and not errors,
        "errors": errors,
        "reference": reference_binding,
        "mutants": mutant_bindings,
    }


def _load_app(path: Path) -> Any:
    """Load a candidate app from a unique module name without sharing state."""

    resolved = path.resolve()
    module_name = "shiploop_capability_app_" + hashlib.sha256(
        str(resolved).encode("utf-8")
    ).hexdigest()[:16] + "_" + uuid.uuid4().hex[:8]
    spec = importlib.util.spec_from_file_location(module_name, resolved)
    if not spec or not spec.loader:
        raise CheckFailure(f"could not import candidate app: {resolved}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def _write_default_state(workspace: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    state_path = workspace / "state.json"
    temporary = state_path.with_name(state_path.name + ".oracle-tmp")
    temporary.write_text(
        json.dumps(copy.deepcopy(DEFAULT_STATE), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(state_path)


def _token(name: str) -> str:
    return f"Bearer {name}"


def _outcome(result: Any) -> tuple[int, Mapping[str, Any]]:
    status = getattr(result, "status", None)
    body = getattr(result, "body", None)
    require(isinstance(status, int), "move result must expose integer .status")
    require(isinstance(body, Mapping), "move result must expose mapping .body")
    return status, body


def _expect_outcome(
    result: Any,
    status: int,
    *,
    error: str | None = None,
    replay: bool | None = None,
) -> Mapping[str, Any]:
    actual_status, body = _outcome(result)
    require(actual_status == status, f"expected HTTP {status}, received {actual_status}: {dict(body)}")
    if error is not None:
        require(body.get("error") == error, f"expected error {error!r}, received {dict(body)}")
    if replay is not None:
        require(
            body.get("idempotentReplay") is replay,
            f"expected idempotentReplay={replay}, received {dict(body)}",
        )
    return body


def _assert_default_move_state(state: Mapping[str, Any], *, turn: str, version: int) -> None:
    board = state.get("board")
    require(isinstance(board, Mapping), f"snapshot.board must be a mapping: {state}")
    require(state.get("turn") == turn, f"expected turn {turn}, received {state}")
    require(state.get("version") == version, f"expected version {version}, received {state}")


def _red_b2_to_c3(store: Any, *, key: str = "oracle-red-1", expected_version: int = 1) -> Any:
    return store.move(
        actor="red",
        from_square="b2",
        to_square="c3",
        expected_version=expected_version,
        idempotency_key=key,
        authorization=_token("red-fixture-token"),
    )


def _black_g7_to_f6(store: Any, *, key: str = "oracle-black-1", expected_version: int = 2) -> Any:
    return store.move(
        actor="black",
        from_square="g7",
        to_square="f6",
        expected_version=expected_version,
        idempotency_key=key,
        authorization=_token("black-fixture-token"),
    )


class DirectCompatibilityHarness:
    """Unscored compatibility adapter for the fixture's direct Store API.

    Scored oracle decisions use :class:`HttpHarness` below.  This adapter stays
    available for local implementation diagnostics, where a Store constructor is
    a deliberate compatibility surface rather than a substitute for its HTTP
    contract.
    """

    def __init__(
        self,
        app_path: Path,
        base: Path,
        defects: Iterable[str] = (),
        *,
        authoritative_receipt_path: Path | str | None = None,
    ) -> None:
        self.app_path = app_path.resolve()
        self.module = _load_app(self.app_path)
        self.base = base.resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.defects = tuple(defects)
        self.authoritative_receipt_path = authoritative_receipt_path
        self._counter = 0

    def new_store(self, label: str) -> tuple[Any, Path]:
        self._counter += 1
        workspace = Path(
            tempfile.mkdtemp(prefix=f"{label}-{self._counter}-", dir=str(self.base))
        ).resolve()
        _write_default_state(workspace)
        try:
            store = self.store_for(workspace)
        except TypeError as error:
            raise CheckFailure(
                "candidate does not support the frozen Store API "
                "(workspace, service_config=, actor_tokens=; calibration may add defects=): "
                + str(error)
            ) from error
        return store, workspace

    def store_for(self, workspace: Path) -> Any:
        """Keep baked worker sources selector-free outside calibration."""

        kwargs: dict[str, Any] = {
            "service_config": SERVICE_CONFIG,
            "actor_tokens": ACTOR_TOKENS,
        }
        if self.defects:
            kwargs["defects"] = self.defects
        return _construct_store(
            lambda: self.module.Store(workspace, **kwargs),
            authoritative_receipt_path=self.authoritative_receipt_path,
        )

    @staticmethod
    def close(store: Any) -> None:
        close = getattr(store, "close", None)
        if callable(close):
            close()


@dataclass(frozen=True)
class HttpOutcome:
    """A parsed loopback HTTP response exposed in the Oracle's Outcome shape."""

    status: int
    body: Mapping[str, Any]


class HttpStoreAdapter:
    """Only exposes public loopback HTTP calls to behavioral checks."""

    def __init__(self, running: Any) -> None:
        self.running = running
        self._closed = False

    def _request(
        self,
        method: str,
        route: str,
        *,
        body: Any = _NO_HTTP_BODY,
        authorization: str | None = None,
    ) -> HttpOutcome:
        connection = http.client.HTTPConnection(
            "127.0.0.1", self.running.server.server_port, timeout=3
        )
        headers: dict[str, str] = {}
        encoded: str | None = None
        if body is not _NO_HTTP_BODY:
            encoded = json.dumps(body, separators=(",", ":"))
            headers["Content-Type"] = "application/json"
        if authorization is not None:
            headers["Authorization"] = authorization
        try:
            connection.request(method, route, body=encoded, headers=headers)
            response = connection.getresponse()
            raw = response.read()
        finally:
            connection.close()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as error:
            raise CheckFailure(f"HTTP {method} {route} returned non-JSON content") from error
        require(isinstance(parsed, Mapping), f"HTTP {method} {route} returned non-object JSON: {parsed!r}")
        return HttpOutcome(response.status, parsed)

    def snapshot(self) -> dict[str, Any]:
        outcome = self._request("GET", "/api/state")
        _expect_outcome(outcome, 200)
        return dict(outcome.body)

    def move(
        self,
        *,
        actor: Any,
        from_square: Any,
        to_square: Any,
        expected_version: Any,
        idempotency_key: Any,
        authorization: str | None,
    ) -> HttpOutcome:
        return self._request(
            "POST",
            "/api/move",
            body={
                "actor": actor,
                "from": from_square,
                "to": to_square,
                "expectedVersion": expected_version,
                "idempotencyKey": idempotency_key,
            },
            authorization=authorization,
        )

    def post_json(self, body: Any, *, authorization: str | None) -> HttpOutcome:
        return self._request("POST", "/api/move", body=body, authorization=authorization)

    def close(self) -> None:
        if not self._closed:
            self.running.stop()
            self._closed = True


class HttpHarness:
    """Creates isolated servers while keeping behavioral assertions on HTTP."""

    def __init__(
        self,
        app_path: Path,
        base: Path,
        defects: Iterable[str] = (),
        *,
        authoritative_receipt_path: Path | str | None = None,
    ) -> None:
        self.app_path = app_path.resolve()
        self.module = _load_app(self.app_path)
        self.base = base.resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.defects = tuple(defects)
        self.authoritative_receipt_path = authoritative_receipt_path
        self._counter = 0

    def new_store(self, label: str) -> tuple[HttpStoreAdapter, Path]:
        self._counter += 1
        workspace = Path(
            tempfile.mkdtemp(prefix=f"{label}-{self._counter}-", dir=str(self.base))
        ).resolve()
        _write_default_state(workspace)
        return self.store_for(workspace), workspace

    def store_for(self, workspace: Path) -> HttpStoreAdapter:
        kwargs: dict[str, Any] = {
            "service_config": SERVICE_CONFIG,
            "actor_tokens": ACTOR_TOKENS,
        }
        if self.defects:
            kwargs["defects"] = self.defects
        try:
            store = _construct_store(
                lambda: self.module.Store(workspace, **kwargs),
                authoritative_receipt_path=self.authoritative_receipt_path,
            )
            running = self.module.start_server(store)
        except TypeError as error:
            raise CheckFailure(
                "candidate does not support the fixture Store bootstrap API "
                "(workspace, service_config=, actor_tokens=; calibration may add defects=): "
                + str(error)
            ) from error
        return HttpStoreAdapter(running)

    @staticmethod
    def close(store: HttpStoreAdapter) -> None:
        store.close()


Check = Callable[[Any], str]


def _using_store(harness: Any, label: str, fn: Callable[[Any, Path], str]) -> str:
    store, workspace = harness.new_store(label)
    try:
        return fn(store, workspace)
    finally:
        harness.close(store)


def _fresh_observed_state(harness: Any, workspace: Path) -> Mapping[str, Any]:
    """Read persistence through a newly started adapter, not a primed cache."""

    fresh = harness.store_for(workspace)
    try:
        return fresh.snapshot()
    finally:
        harness.close(fresh)


def _require_persisted_unchanged(harness: Any, workspace: Path, before: Mapping[str, Any], label: str) -> None:
    after = _fresh_observed_state(harness, workspace)
    require(after == before, f"{label} changed persistent/public state")


def check_retry_idempotency(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        first = _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        _assert_default_move_state(first, turn="black", version=2)
        board = first.get("board", {})
        require("b2" not in board, f"source must be empty after first move: {first}")
        require(board.get("c3", {}).get("actor") == "red", f"red must occupy c3: {first}")
        after_first = _fresh_observed_state(harness, workspace)
        replay = _expect_outcome(_red_b2_to_c3(store), 200, replay=True)
        _assert_default_move_state(replay, turn="black", version=2)
        _require_persisted_unchanged(harness, workspace, after_first, "idempotent retry")
        return "first write and exact retry preserved version 2"

    return _using_store(harness, "retry", run)


def check_black_followup(harness: Any) -> str:
    def run(store: Any, _workspace: Path) -> str:
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        response = _expect_outcome(_black_g7_to_f6(store), 200, replay=False)
        _assert_default_move_state(response, turn="red", version=3)
        board = response.get("board", {})
        require(board.get("f6", {}).get("actor") == "black", f"black must occupy f6: {response}")
        return "alternating legal move reached red turn at version 3"

    return _using_store(harness, "followup", run)


def check_actor_mismatch(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="black",
            from_square="g7",
            to_square="f6",
            expected_version=2,
            idempotency_key="oracle-actor-mismatch",
            authorization=_token("red-fixture-token"),
        )
        _expect_outcome(outcome, 403, error="actor_mismatch")
        _require_persisted_unchanged(harness, workspace, before, "actor impersonation")
        return "authenticated actor cannot impersonate black"

    return _using_store(harness, "actor", run)


def check_scope_required(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="b2",
            to_square="c3",
            expected_version=1,
            idempotency_key="oracle-readonly-scope",
            authorization=_token("red-readonly-token"),
        )
        _expect_outcome(outcome, 403, error="scope_required")
        _require_persisted_unchanged(harness, workspace, before, "scope failure")
        return "read-only token cannot mutate"

    return _using_store(harness, "scope", run)


def check_stale_version(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        before = _fresh_observed_state(harness, workspace)
        _expect_outcome(
            _black_g7_to_f6(store, key="oracle-stale", expected_version=1),
            409,
            error="version_mismatch",
        )
        _require_persisted_unchanged(harness, workspace, before, "stale write")
        return "stale write rejected without changing persisted state"

    return _using_store(harness, "stale", run)


def check_idempotency_conflict(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="c3",
            to_square="d4",
            expected_version=2,
            idempotency_key="oracle-red-1",
            authorization=_token("red-fixture-token"),
        )
        _expect_outcome(outcome, 409, error="idempotency_conflict")
        _require_persisted_unchanged(harness, workspace, before, "conflicting idempotency key")
        return "same key with different normalized request rejected"

    return _using_store(harness, "idempotency-conflict", run)


def check_invalid_coordinate(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="z9",
            to_square="a1",
            expected_version=1,
            idempotency_key="oracle-invalid-coordinate",
            authorization=_token("red-fixture-token"),
        )
        _expect_outcome(outcome, 400, error="invalid_coordinate")
        _require_persisted_unchanged(harness, workspace, before, "malformed coordinate")
        return "malformed coordinate rejected before mutation"

    return _using_store(harness, "coordinate", run)


def check_normalization_before_auth(harness: Any) -> str:
    """The public HTTP contract normalizes coordinates before authorization."""

    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="z9",
            to_square="a1",
            expected_version=1,
            idempotency_key="oracle-coordinate-before-auth",
            authorization=None,
        )
        _expect_outcome(outcome, 400, error="invalid_coordinate")
        _require_persisted_unchanged(harness, workspace, before, "coordinate normalization before auth")
        return "malformed coordinate returned 400 before a missing token was considered"

    return _using_store(harness, "coordinate-before-auth", run)


def check_unplayable_square(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="b2",
            to_square="b3",
            expected_version=1,
            idempotency_key="oracle-unplayable",
            authorization=_token("red-fixture-token"),
        )
        _expect_outcome(outcome, 422, error="unplayable_square")
        _require_persisted_unchanged(harness, workspace, before, "unplayable square")
        return "unplayable coordinate rejected without mutation"

    return _using_store(harness, "unplayable", run)


def check_illegal_geometry(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        outcome = store.move(
            actor="red",
            from_square="b2",
            to_square="d2",
            expected_version=1,
            idempotency_key="oracle-illegal-geometry",
            authorization=_token("red-fixture-token"),
        )
        _expect_outcome(outcome, 422, error="illegal_move")
        _require_persisted_unchanged(harness, workspace, before, "illegal geometry")
        return "valid coordinates with illegal geometry rejected"

    return _using_store(harness, "geometry", run)


def check_cache_after_write(harness: Any) -> str:
    def run(store: Any, _workspace: Path) -> str:
        primed = store.snapshot()
        _assert_default_move_state(primed, turn="red", version=1)
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        refreshed = store.snapshot()
        _assert_default_move_state(refreshed, turn="black", version=2)
        require(
            refreshed.get("board", {}).get("c3", {}).get("actor") == "red",
            f"state read after successful write returned stale board: {refreshed}",
        )
        return "cached state was invalidated before follow-up read"

    return _using_store(harness, "cache", run)


def check_restart_persistence(harness: Any) -> str:
    def run(store: Any, workspace: Path) -> str:
        _expect_outcome(_red_b2_to_c3(store), 200, replay=False)
        harness.close(store)
        restarted = harness.store_for(workspace)
        try:
            state = restarted.snapshot()
            _assert_default_move_state(state, turn="black", version=2)
            require(
                state.get("board", {}).get("c3", {}).get("actor") == "red",
                f"restart did not retain move: {state}",
            )
            return "fresh Store observed persistent version-2 state"
        finally:
            harness.close(restarted)

    return _using_store(harness, "restart", run)


def check_json_type_boundaries(harness: Any) -> str:
    """Keep type-boundary scoring on the real JSON/HTTP adapter."""

    def run(store: Any, workspace: Path) -> str:
        before = _fresh_observed_state(harness, workspace)
        malformed_actors = ([], {}, None, True, 7, "green")
        for index, actor in enumerate(malformed_actors, start=1):
            outcome = store.move(
                actor=actor,
                from_square="b2",
                to_square="c3",
                expected_version=1,
                idempotency_key=f"oracle-invalid-actor-{index}",
                authorization=_token("red-fixture-token"),
            )
            _expect_outcome(outcome, 400, error="invalid_actor")
            _require_persisted_unchanged(harness, workspace, before, "invalid actor JSON value")
        for payload in ([], "not-an-object", None):
            outcome = store.post_json(payload, authorization=_token("red-fixture-token"))
            _expect_outcome(outcome, 400, error="invalid_json")
            _require_persisted_unchanged(harness, workspace, before, "non-object JSON request")
        return "public JSON type boundaries returned 400 without changing persistence"

    return _using_store(harness, "json-boundaries", run)


HTTP_CHECKS: dict[str, Check] = {
    "retry_idempotency": check_retry_idempotency,
    "black_followup": check_black_followup,
    "actor_mismatch": check_actor_mismatch,
    "scope_required": check_scope_required,
    "stale_version": check_stale_version,
    "idempotency_conflict": check_idempotency_conflict,
    "invalid_coordinate": check_invalid_coordinate,
    "normalization_before_auth": check_normalization_before_auth,
    "unplayable_square": check_unplayable_square,
    "illegal_geometry": check_illegal_geometry,
    "cache_after_write": check_cache_after_write,
    "restart_persistence": check_restart_persistence,
    "json_type_boundaries": check_json_type_boundaries,
}

# This is intentionally smaller than HTTP_CHECKS: a direct constructor has no
# JSON transport boundary and is therefore useful only for compatibility work.
DIRECT_COMPATIBILITY_CHECKS: dict[str, Check] = {
    name: check
    for name, check in HTTP_CHECKS.items()
    if name not in {"json_type_boundaries", "normalization_before_auth"}
}

MUTANT_PROBES: dict[str, tuple[str, ...]] = {
    "duplicate": ("retry_idempotency",),
    "stale": ("stale_version",),
    "cache": ("cache_after_write",),
    "wrong_actor": ("actor_mismatch",),
    "invalid_move": ("illegal_geometry",),
}


def _run_checks(
    app_path: Path,
    base: Path,
    *,
    harness_type: type[Any],
    checks: Mapping[str, Check],
    transport: str,
    scored: bool,
    defects: Iterable[str] = (),
    selected: Iterable[str] | None = None,
    authoritative_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    names = tuple(selected or checks.keys())
    unknown = [name for name in names if name not in checks]
    if unknown:
        raise ValueError(f"unknown oracle checks: {unknown}")
    source_binding = _file_binding(app_path, kind="checked_app")
    harness = harness_type(
        app_path,
        base,
        defects,
        authoritative_receipt_path=authoritative_receipt_path,
    )
    completed: list[Any] = []

    class ObservableCase(unittest.TestCase):
        def __init__(self, name: str, check: Check) -> None:
            super().__init__("runTest")
            self.case_name = name
            self.check = check
            self.passed = False
            self.detail = "not run"

        def runTest(self) -> None:  # noqa: N802 - unittest API spelling
            try:
                self.detail = self.check(harness)
                self.passed = True
            except Exception as error:
                self.detail = f"{type(error).__name__}: {error}"
                raise

    suite = unittest.TestSuite()
    for name in names:
        test = ObservableCase(name, checks[name])
        completed.append(test)
        suite.addTest(test)
    stream = io.StringIO()
    outcome = unittest.TextTestRunner(stream=stream, verbosity=0).run(suite)
    cases = [
        {"name": test.case_name, "passed": test.passed, "detail": test.detail}
        for test in completed
    ]
    return {
        "app": str(app_path.resolve()),
        "defects": list(defects),
        "source": source_binding,
        "transport": transport,
        "scored": scored,
        "selected_checks": list(names),
        "passed": outcome.wasSuccessful(),
        "cases": cases,
        "unittest_output": stream.getvalue().strip(),
    }


def run_checks(
    app_path: Path,
    base: Path,
    *,
    defects: Iterable[str] = (),
    selected: Iterable[str] | None = None,
    authoritative_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run scored public-contract checks through a fresh loopback HTTP server."""

    return _run_checks(
        app_path,
        base,
        harness_type=HttpHarness,
        checks=HTTP_CHECKS,
        transport="loopback_http",
        scored=True,
        defects=defects,
        selected=selected,
        authoritative_receipt_path=authoritative_receipt_path,
    )


def run_direct_compatibility_checks(
    app_path: Path,
    base: Path,
    *,
    defects: Iterable[str] = (),
    selected: Iterable[str] | None = None,
    authoritative_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run unscored direct-Store diagnostics separate from public grading."""

    return _run_checks(
        app_path,
        base,
        harness_type=DirectCompatibilityHarness,
        checks=DIRECT_COMPATIBILITY_CHECKS,
        transport="direct_store_compatibility",
        scored=False,
        defects=defects,
        selected=selected,
        authoritative_receipt_path=authoritative_receipt_path,
    )


def _parse_mutants(values: Iterable[str]) -> dict[str, Path]:
    parsed: dict[str, Path] = {}
    for value in values:
        name, separator, raw_path = value.partition("=")
        if not separator or not name or not raw_path:
            raise ValueError(f"--mutant must be NAME=PATH, received {value!r}")
        if name in parsed:
            raise ValueError(f"duplicate mutant name: {name}")
        candidate = Path(raw_path).resolve()
        if not candidate.is_file():
            raise ValueError(f"mutant source does not exist: {candidate}")
        parsed[name] = candidate
    return parsed


def _safe_relative(root: Path, relative: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ValueError(f"worker app path escapes test root: {relative!r}") from error
    return candidate


def _is_infrastructure_failure(output: str) -> bool:
    lowered = output.lower()
    markers = (
        "importerror",
        "modulenotfounderror",
        "syntaxerror",
        "filenotfounderror",
        "no tests ran",
        "ran 0 tests",
    )
    if any(marker in lowered for marker in markers):
        return True
    # ``AssertionError: ...`` is a valid test detection.  Match the unittest
    # error heading only when it begins a rendered output line.
    return any(line.strip().startswith("error:") for line in lowered.splitlines())


def run_worker_tests(
    *,
    tests_root: Path,
    app_path: Path,
    app_relative: str,
    command_template: str | None,
    authoritative_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    """Run worker tests unchanged against a copied source tree and selected app."""

    source_root = tests_root.resolve()
    if not source_root.is_dir():
        raise ValueError(f"worker test root does not exist: {source_root}")
    with tempfile.TemporaryDirectory(prefix="shiploop-capability-test-suite-") as temporary:
        cloned = Path(temporary) / "worker"
        shutil.copytree(
            source_root,
            cloned,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".git"),
        )
        destination = _safe_relative(cloned, app_relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(app_path, destination)
        environment = _service_environment(
            authoritative_receipt_path=authoritative_receipt_path
        )
        python_path = [str(destination.parent), str(cloned)]
        if environment.get("PYTHONPATH"):
            python_path.append(environment["PYTHONPATH"])
        environment["PYTHONPATH"] = os.pathsep.join(python_path)

        if command_template:
            command = shlex.split(
                command_template.format(worker_root=str(cloned), app=str(destination))
            )
            commands = [(command, "custom")]
        else:
            test_files = sorted(
                path for path in cloned.rglob("test*.py") if path.is_file() and "__pycache__" not in path.parts
            )
            if not test_files:
                return {
                    "passed": False,
                    "valid_detection": False,
                    "reason": "no worker test*.py files found",
                    "runs": [],
                }
            commands = [
                ([sys.executable, str(path.relative_to(cloned))], str(path.relative_to(cloned)))
                for path in test_files
            ]

        runs: list[dict[str, Any]] = []
        all_passed = True
        infrastructure_failure = False
        for command, label in commands:
            completed = subprocess.run(
                command,
                cwd=cloned,
                env=environment,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=90,
            )
            output = completed.stdout[-6_000:]
            runs.append(
                {
                    "label": label,
                    "command": command,
                    "exit_code": completed.returncode,
                    "output_tail": output,
                }
            )
            all_passed = all_passed and completed.returncode == 0
            infrastructure_failure = infrastructure_failure or _is_infrastructure_failure(output)
        if all_passed:
            reason = "worker suite passed"
        elif infrastructure_failure:
            reason = "suite failure includes setup/import/runtime error; not a valid defect detection"
        else:
            reason = "worker suite produced an assertion-style failure"
        return {
            "passed": all_passed,
            "valid_detection": (not all_passed) and not infrastructure_failure,
            "reason": reason,
            "runs": runs,
        }


def _provenance() -> dict[str, str]:
    source = Path(__file__).resolve()
    review = source.with_name("oracle-review.md")
    return {
        "oracle_revision": ORACLE_REVISION,
        "score_basis": "loopback_http",
        "grade_path": str(source),
        "grade_sha256": _hash_file(source),
        "oracle_review_path": str(review),
        "oracle_review_sha256": _hash_file(review),
    }


def grade_calibration(
    reference: Path,
    base: Path,
    mutant_sources: Mapping[str, Path] | None = None,
) -> dict[str, Any]:
    """Calibrate only distinct supplied sources as evidence-grade mutants.

    Passing ``None`` retains the old in-process selector exercise as a useful
    diagnostic, but it can never be reported as evidence-grade calibration.
    """

    expected_families = list(MUTANT_PROBES)
    if mutant_sources is None:
        bindings = _receipt_bindings(reference=reference)
        reference_binding = bindings["reference"]
        selector_sources = {
            name: {
                **reference_binding,
                "kind": "reference_runtime_defect_selector",
                "selected_defect": name,
            }
            for name in MUTANT_PROBES
        }
        bindings["mutants"] = selector_sources
        source_validation = {
            "expected_families": expected_families,
            "selected_families": expected_families,
            "missing_families": [],
            "unexpected_families": [],
            "exact_declared_families": True,
            "valid": False,
            "errors": [
                "selector fallback reuses the reference source and is diagnostic only"
            ],
            "reference": reference_binding,
            "mutants": selector_sources,
        }
        baseline = run_checks(reference, base / "reference", defects=())
        mutants: dict[str, Any] = {}
        for mutant, probes in MUTANT_PROBES.items():
            result = run_checks(
                reference,
                base / f"selector-diagnostic-{mutant}",
                defects=(mutant,),
                selected=probes,
            )
            mutants[mutant] = {
                "probes": list(probes),
                "expected_to_fail": True,
                "detected": not result["passed"],
                "source": str(reference_binding["path"]),
                "source_kind": "reference_runtime_defect_selector",
                "source_sha256": reference_binding["sha256"],
                "result": result,
            }
        reference_valid = baseline["passed"]
        diagnostic_passed = reference_valid and all(value["detected"] for value in mutants.values())
        return {
            "mode": "calibration",
            "passed": False,
            "evidence_grade": False,
            "verdict": "diagnostic_selector_calibration" if diagnostic_passed else "diagnostic_selector_failure",
            "diagnostic_passed": diagnostic_passed,
            "reference_valid": reference_valid,
            "invalid_reference": not reference_valid,
            "expected_families": expected_families,
            "source_validation": source_validation,
            "input_bindings": bindings,
            "baseline": baseline,
            "mutants": mutants,
        }

    bindings = _receipt_bindings(reference=reference, mutants=mutant_sources)
    source_validation = _validate_mutant_sources(reference=reference, mutants=mutant_sources)
    if not source_validation["valid"]:
        return {
            "mode": "calibration",
            "passed": False,
            "evidence_grade": False,
            "verdict": "invalid_mutant_sources",
            "diagnostic_passed": False,
            "reference_valid": None,
            "invalid_reference": False,
            "expected_families": expected_families,
            "source_validation": source_validation,
            "input_bindings": bindings,
            "baseline": None,
            "mutants": {},
        }

    baseline = run_checks(reference, base / "reference", defects=())
    mutants: dict[str, Any] = {}
    for mutant, probes in MUTANT_PROBES.items():
        source = mutant_sources[mutant]
        source_binding = source_validation["mutants"][mutant]
        result = run_checks(source, base / f"mutant-{mutant}", defects=(), selected=probes)
        mutants[mutant] = {
            "probes": list(probes),
            "expected_to_fail": True,
            "detected": not result["passed"],
            "source": source_binding["path"],
            "source_kind": source_binding["kind"],
            "source_sha256": source_binding["sha256"],
            "result": result,
        }
    reference_valid = baseline["passed"]
    passed = reference_valid and all(value["detected"] for value in mutants.values())
    return {
        "mode": "calibration",
        "passed": passed,
        "evidence_grade": True,
        "verdict": "evidence_grade_passed" if passed else "evidence_grade_failed",
        "diagnostic_passed": None,
        "reference_valid": reference_valid,
        "invalid_reference": not reference_valid,
        "expected_families": expected_families,
        "source_validation": source_validation,
        "input_bindings": bindings,
        "baseline": baseline,
        "mutants": mutants,
    }


def grade_inner(app: Path, base: Path) -> dict[str, Any]:
    bindings = _receipt_bindings(candidate=app)
    result = run_checks(app, base / "inner", defects=())
    return {
        "mode": "inner",
        "passed": result["passed"],
        "score_basis": "loopback_http",
        "input_bindings": bindings,
        "held_out": result,
    }


def grade_test(
    *,
    reference: Path,
    mutants: Mapping[str, Path],
    tests_root: Path,
    app_relative: str,
    command_template: str | None,
    authoritative_receipt_path: Path | str | None = None,
) -> dict[str, Any]:
    bindings = _receipt_bindings(
        reference=reference,
        mutants=mutants,
        tests_root=tests_root,
    )
    source_validation = _validate_mutant_sources(reference=reference, mutants=mutants)
    fixed = run_worker_tests(
        tests_root=tests_root,
        app_path=reference,
        app_relative=app_relative,
        command_template=command_template,
        authoritative_receipt_path=authoritative_receipt_path,
    )
    if not fixed["passed"]:
        return {
            "mode": "test",
            "passed": False,
            "score_valid": False,
            "verdict": "invalid_reference",
            "expected_families": source_validation["expected_families"],
            "selected_families": source_validation["selected_families"],
            "source_validation": source_validation,
            "input_bindings": bindings,
            "fixed_reference": fixed,
            "mutants": {},
            "distinct_detected_families": [],
            "distinct_family_count": 0,
        }
    if not source_validation["valid"]:
        incomplete_only = bool(source_validation["missing_families"]) and not (
            source_validation["unexpected_families"] or source_validation["errors"]
        )
        return {
            "mode": "test",
            "passed": False,
            "score_valid": False,
            "verdict": "incomplete_mutant_set" if incomplete_only else "invalid_mutant_set",
            "expected_families": source_validation["expected_families"],
            "selected_families": source_validation["selected_families"],
            "source_validation": source_validation,
            "input_bindings": bindings,
            "fixed_reference": fixed,
            "mutants": {},
            "distinct_detected_families": [],
            "distinct_family_count": 0,
        }
    variants: dict[str, Any] = {}
    for name in MUTANT_PROBES:
        mutant_path = mutants[name]
        source_binding = source_validation["mutants"][name]
        result = run_worker_tests(
            tests_root=tests_root,
            app_path=mutant_path,
            app_relative=app_relative,
            command_template=command_template,
            authoritative_receipt_path=authoritative_receipt_path,
        )
        variants[name] = {
            "source": source_binding["path"],
            "source_kind": source_binding["kind"],
            "source_sha256": source_binding["sha256"],
            "detected": result["valid_detection"],
            "result": result,
        }
    detected = [name for name, value in variants.items() if value["detected"]]
    passed = bool(variants) and len(detected) == len(variants)
    return {
        "mode": "test",
        "passed": passed,
        "score_valid": True,
        "verdict": "passed" if passed else "incomplete_mutation_detection",
        "expected_families": source_validation["expected_families"],
        "selected_families": source_validation["selected_families"],
        "source_validation": source_validation,
        "input_bindings": bindings,
        "fixed_reference": fixed,
        "mutants": variants,
        "distinct_detected_families": detected,
        "distinct_family_count": len(detected),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("calibration", "inner", "test", "direct-compatibility"),
        required=True,
    )
    parser.add_argument("--app", type=Path, help="final candidate app for --mode inner")
    parser.add_argument("--reference-app", type=Path, help="independent fixed reference app")
    parser.add_argument("--workspace", type=Path, help="optional retained directory for direct-oracle fixtures")
    parser.add_argument("--tests-root", type=Path, help="worker root containing unchanged test*.py files")
    parser.add_argument("--worker-app-relative", default="app.py", help="candidate app path within a copied worker root")
    parser.add_argument(
        "--mutant",
        action="append",
        default=[],
        metavar="NAME=PATH",
        help="grader-only distinct mutant source for --mode calibration or --mode test; may repeat",
    )
    parser.add_argument(
        "--test-command",
        help="optional literal command; {worker_root} and {app} may be substituted without a shell",
    )
    parser.add_argument("--output", type=Path, help="optional JSON receipt path")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    workspace: Path | None = None
    retained_workspace = bool(args.workspace)
    try:
        reference = (args.reference_app or Path(__file__).with_name("fixtures") / "app.py").resolve()
        if not reference.is_file():
            raise ValueError(f"reference app does not exist: {reference}")
        app = args.app.resolve() if args.app else None
        if app and not app.is_file():
            raise ValueError(f"candidate app does not exist: {app}")
        mutants = _parse_mutants(args.mutant)
        if args.mode == "test" and not args.tests_root:
            raise ValueError("--mode test requires --tests-root")
        if args.mode == "inner" and not app:
            raise ValueError("--mode inner requires --app")

        if args.workspace:
            workspace = args.workspace.resolve()
            workspace.mkdir(parents=True, exist_ok=True)
            cleanup: Callable[[], None] = lambda: None
        else:
            temporary = tempfile.TemporaryDirectory(prefix="shiploop-capability-oracle-")
            workspace = Path(temporary.name)
            cleanup = temporary.cleanup
        try:
            if args.mode == "calibration":
                report = grade_calibration(reference, workspace, mutants if args.mutant else None)
            elif args.mode == "inner":
                report = grade_inner(app, workspace)
            elif args.mode == "direct-compatibility":
                compatibility = run_direct_compatibility_checks(reference, workspace)
                report = {
                    "mode": "direct-compatibility",
                    "passed": compatibility["passed"],
                    "scored": False,
                    "compatibility": compatibility,
                }
            else:
                report = grade_test(
                    reference=reference,
                    mutants=mutants,
                    tests_root=args.tests_root.resolve(),
                    app_relative=args.worker_app_relative,
                    command_template=args.test_command,
                )
            report["provenance"] = _provenance()
        finally:
            cleanup()
        report["workspace"] = str(workspace)
        report["workspace_retention"] = {
            "retained_after_run": retained_workspace and workspace.exists(),
            "disposition": "caller_retained" if retained_workspace else "temporary_cleaned",
        }
    except (CheckFailure, ValueError, OSError, subprocess.TimeoutExpired) as error:
        report = {"passed": False, "error": f"{type(error).__name__}: {error}", "provenance": _provenance()}
        if workspace is not None:
            report["workspace"] = str(workspace)
            report["workspace_retention"] = {
                "retained_after_run": retained_workspace and workspace.exists(),
                "disposition": "caller_retained" if retained_workspace else "temporary_cleaned",
            }

    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
