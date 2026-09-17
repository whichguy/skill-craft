#!/usr/bin/env python3
"""Synthetic loopback Checkers state service used only by capability experiments.

This module deliberately uses the Python standard library.  Its HTTP endpoints
are application RPC, not MCP.  See SPEC.md for the public experiment contract.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Mapping


FIXTURE_REVISION = "fixture-r2"
DEFAULT_SERVICE_CONFIG = {
    "service": "synthetic-checkers",
    "requiredScope": "checkers:write",
    "cacheTtlSeconds": 60,
}
DEFAULT_ACTOR_TOKENS = {
    "red-fixture-token": {"actor": "red", "scopes": ["checkers:write"]},
    "black-fixture-token": {"actor": "black", "scopes": ["checkers:write"]},
}
COORDINATE = re.compile(r"^[a-h][1-8]$")
AUTHORITATIVE_RECEIPTS_ENV = "SHIPLOOP_CAPABILITY_SERVICE_RECEIPTS"

# These values deliberately form a small, fixed receipt vocabulary.  A receipt
# is evidence of an explicit HTTP response; it is not a classifier for arbitrary
# process failures or request content.
HTTP_RECEIPT_METHODS = frozenset({"GET", "POST"})
HTTP_RECEIPT_ROUTES = frozenset({"/", "/api/state", "/api/meta", "/api/move", "other"})
HTTP_RECEIPT_ACTOR_CLASSES = frozenset({"red", "black", "invalid"})
HTTP_RECEIPT_STATUSES = frozenset({200, 400, 403, 404, 405, 409, 422, 500})
HTTP_RECEIPT_ERRORS = frozenset(
    {
        "invalid_json",
        "invalid_actor",
        "invalid_expected_version",
        "invalid_idempotency_key",
        "invalid_coordinate",
        "unplayable_square",
        "mutation_token_required",
        "invalid_token",
        "scope_required",
        "actor_mismatch",
        "not_your_turn",
        "source_not_owned",
        "target_occupied",
        "illegal_move",
        "capture_required",
        "forced_capture_origin",
        "idempotency_conflict",
        "version_mismatch",
        "not_found",
        "method_not_allowed",
        "internal_error",
    }
)


@dataclass(frozen=True)
class Outcome:
    """The public non-throwing result of a Store operation."""

    status: int
    body: dict[str, Any]

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300


class ValidationError(Exception):
    def __init__(self, status: int, error: str, **details: Any) -> None:
        self.status = status
        self.error = error
        self.details = details
        super().__init__(error)


def default_state() -> dict[str, Any]:
    """The public default board documented in SPEC.md."""

    return {
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


def capture_trace_state() -> dict[str, Any]:
    """A small public scenario: red b2 captures d4, then must capture f6."""

    return {
        "schemaVersion": 1,
        "board": {
            "b2": {"actor": "red", "king": False},
            "c3": {"actor": "black", "king": False},
            "e5": {"actor": "black", "king": False},
            "h8": {"actor": "black", "king": False},
        },
        "turn": "red",
        "version": 1,
        "forcedFrom": None,
        "history": [],
        "idempotency": {},
    }


def write_state(path: Path, state: Mapping[str, Any]) -> None:
    """Atomically materialize a synthetic state file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _as_path(state_path: Path | str) -> Path:
    raw = Path(state_path)
    return raw / "state.json" if raw.exists() and raw.is_dir() else raw


class Store:
    """Authoritative, file-persisted synthetic Checkers state.

    `state_path` may name a `state.json` file or a workspace containing one.
    `defects` selects explicitly declared experiment mutants; it defaults to an
    empty set for the correct implementation.
    """

    def __init__(
        self,
        state_path: Path | str,
        *,
        defects: Iterable[str] = (),
        revision: str = FIXTURE_REVISION,
        service_config: Mapping[str, Any] | None = None,
        actor_tokens: Mapping[str, Mapping[str, Any]] | None = None,
        observation_dir: Path | str | None = None,
    ) -> None:
        self.state_path = _as_path(state_path).resolve()
        if not self.state_path.is_file():
            raise FileNotFoundError(f"missing state file: {self.state_path}")
        self.defects = frozenset(defects)
        unknown = self.defects.difference(
            {"wrong_actor", "duplicate", "stale", "cache", "invalid_move"}
        )
        if unknown:
            raise ValueError(f"unknown fixture defects: {sorted(unknown)}")
        self.revision = revision
        self.service_config = dict(DEFAULT_SERVICE_CONFIG)
        if service_config:
            self.service_config.update(service_config)
        self.actor_tokens = {
            token: {"actor": value["actor"], "scopes": list(value.get("scopes", []))}
            for token, value in (actor_tokens or DEFAULT_ACTOR_TOKENS).items()
        }
        self._lock = threading.RLock()
        self._cache: dict[str, Any] | None = None
        self._cache_at = 0.0
        self._observation_dir = Path(observation_dir).resolve() if observation_dir else None
        self._event_file: Any | None = None
        self._authoritative_receipt_status = {
            "configured": bool(os.environ.get(AUTHORITATIVE_RECEIPTS_ENV)),
            "available": False,
            "error": None,
        }
        self._authoritative_receipt_file: Any | None = self._open_authoritative_receipt_file()
        self._receipt_sequence = 0
        if self._observation_dir:
            self._observation_dir.mkdir(parents=True, exist_ok=True)
            event_path = self._observation_dir / "events.jsonl"
            self._event_file = event_path.open("a", encoding="utf-8")
            self._observe("store_started", revision=self.revision, defects=sorted(self.defects))

    def close(self) -> None:
        if self._event_file:
            self._event_file.close()
            self._event_file = None
        if self._authoritative_receipt_file:
            self._authoritative_receipt_file.close()
            self._authoritative_receipt_file = None

    def _open_authoritative_receipt_file(self) -> Any | None:
        """Open only a coordinator-provided receipt path outside this workspace.

        The worker-visible observation directory is intentionally not treated as
        an integrity boundary.  A coordinator may opt in to a separate receipt
        file through an absolute path whose parent already exists.
        """

        raw_path = os.environ.get(AUTHORITATIVE_RECEIPTS_ENV)
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if not candidate.is_absolute() or not candidate.parent.is_dir():
            self._authoritative_receipt_status["error"] = "receipt_path_unavailable"
            return None
        try:
            candidate.parent.resolve().relative_to(self.state_path.parent.resolve())
        except ValueError:
            pass
        else:
            self._authoritative_receipt_status["error"] = "receipt_path_inside_state_workspace"
            return None
        if candidate.exists() and (candidate.is_symlink() or not candidate.is_file()):
            self._authoritative_receipt_status["error"] = "receipt_target_unsafe"
            return None
        try:
            receipt_file = candidate.open("a", encoding="utf-8")
        except OSError:
            self._authoritative_receipt_status["error"] = "receipt_open_failed"
            return None
        self._authoritative_receipt_status["available"] = True
        return receipt_file

    def seal_observations(self) -> None:
        """Mark the observation root read-only after retaining an append FD.

        The open event descriptor remains usable by this process on POSIX.  This
        is a fixture boundary for a filesystem-MCP reader, not an access-control
        claim about a process that can change local file permissions.
        """

        if not self._observation_dir:
            return
        event_path = self._observation_dir / "events.jsonl"
        try:
            os.chmod(event_path, 0o444)
            os.chmod(self._observation_dir, 0o555)
        except OSError:
            # The experiment is still safe to run on filesystems without POSIX
            # modes; setup records this boundary in its manifest.
            pass

    def unseal_observations(self) -> None:
        if not self._observation_dir:
            return
        try:
            os.chmod(self._observation_dir, 0o755)
            event_path = self._observation_dir / "events.jsonl"
            if event_path.exists():
                os.chmod(event_path, 0o644)
        except OSError:
            pass

    def snapshot(self) -> dict[str, Any]:
        """Return a cacheable, public state snapshot without the idempotency ledger."""

        with self._lock:
            ttl = float(self.service_config.get("cacheTtlSeconds", 0))
            now = time.monotonic()
            if self._cache is None or ttl <= 0 or now - self._cache_at >= ttl:
                self._cache = self._load_state()
                self._cache_at = now
                self._observe("state_read", cache="miss", version=self._cache["version"])
            else:
                self._observe("state_read", cache="hit", version=self._cache["version"])
            return self._public_state(self._cache)

    def receipt_version(self) -> int | None:
        """Read the persisted version for an HTTP receipt without using cache."""

        with self._lock:
            try:
                version = self._load_state().get("version")
            except (OSError, json.JSONDecodeError):
                return None
            return version if isinstance(version, int) and not isinstance(version, bool) else None

    def raw_state(self) -> dict[str, Any]:
        """Return an internal copied state for fixture setup and ordinary tests."""

        with self._lock:
            return copy.deepcopy(self._load_state())

    def meta(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "serviceConfig": copy.deepcopy(self.service_config),
            "rpcTransport": "http",
            "applicationRpcIsMcp": False,
            "observationRoot": "runtime-observations",
            "authoritativeHttpReceipt": copy.deepcopy(self._authoritative_receipt_status),
        }

    def move(
        self,
        *,
        actor: Any,
        from_square: Any,
        to_square: Any,
        expected_version: Any,
        idempotency_key: Any,
        authorization: str | None,
    ) -> Outcome:
        """Apply one mutation and always return an Outcome rather than a 4xx exception."""

        try:
            request = self._normalize_request(
                actor=actor,
                from_square=from_square,
                to_square=to_square,
                expected_version=expected_version,
                idempotency_key=idempotency_key,
            )
            authenticated = self._authorize(authorization)
            with self._lock:
                state = self._load_state()
                old_record = state["idempotency"].get(request["idempotencyKey"])
                if old_record:
                    if old_record["request"] != request:
                        return self._error(409, "idempotency_conflict")
                    if "duplicate" not in self.defects:
                        replay = copy.deepcopy(old_record["response"])
                        replay["idempotentReplay"] = True
                        self._observe("move_replayed", version=state["version"])
                        return Outcome(200, replay)
                    return self._apply_duplicate_mutant(state, request)
                if request["expectedVersion"] != state["version"] and "stale" not in self.defects:
                    return self._error(409, "version_mismatch")
                self._validate_authorized_actor(request, authenticated, state)
                capture = self._validate_move(state, request)
                self._apply_move(state, request, capture)
                response = self._public_state(state)
                response["idempotentReplay"] = False
                state["idempotency"][request["idempotencyKey"]] = {
                    "request": request,
                    "response": copy.deepcopy(response),
                }
                self._persist(state)
                if "cache" not in self.defects:
                    self._cache = None
                    self._cache_at = 0.0
                self._observe(
                    "move_applied",
                    actor=request["actor"],
                    fromSquare=request["from"],
                    toSquare=request["to"],
                    version=state["version"],
                    staleAccepted=request["expectedVersion"] != state["version"] - 1,
                )
                return Outcome(200, response)
        except ValidationError as error:
            self._observe("move_rejected", error=error.error)
            return self._error(error.status, error.error, **error.details)

    def _normalize_request(self, **raw: Any) -> dict[str, Any]:
        if not isinstance(raw["actor"], str) or raw["actor"] not in {"red", "black"}:
            raise ValidationError(400, "invalid_actor")
        if not isinstance(raw["expected_version"], int) or isinstance(raw["expected_version"], bool):
            raise ValidationError(400, "invalid_expected_version")
        if not isinstance(raw["idempotency_key"], str) or not raw["idempotency_key"].strip():
            raise ValidationError(400, "invalid_idempotency_key")
        return {
            "actor": raw["actor"],
            "from": self._coordinate(raw["from_square"]),
            "to": self._coordinate(raw["to_square"]),
            "expectedVersion": raw["expected_version"],
            "idempotencyKey": raw["idempotency_key"],
        }

    def _coordinate(self, value: Any) -> str:
        if not isinstance(value, str) or not COORDINATE.fullmatch(value):
            raise ValidationError(400, "invalid_coordinate")
        if not self._playable(value):
            raise ValidationError(422, "unplayable_square")
        return value

    @staticmethod
    def _playable(square: str) -> bool:
        return ((ord(square[0]) - ord("a")) + int(square[1])) % 2 == 1

    def _authorize(self, authorization: str | None) -> dict[str, Any]:
        if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
            raise ValidationError(403, "mutation_token_required")
        token = authorization.removeprefix("Bearer ")
        identity = self.actor_tokens.get(token)
        if not identity:
            raise ValidationError(403, "invalid_token")
        scope = self.service_config.get("requiredScope")
        if scope and scope not in identity["scopes"]:
            raise ValidationError(403, "scope_required", requiredScope=scope)
        return identity

    def _validate_authorized_actor(
        self, request: Mapping[str, Any], authenticated: Mapping[str, Any], state: Mapping[str, Any]
    ) -> None:
        if request["actor"] != authenticated["actor"] and "wrong_actor" not in self.defects:
            raise ValidationError(403, "actor_mismatch")
        if request["actor"] != state["turn"]:
            raise ValidationError(422, "not_your_turn", turn=state["turn"])

    def _validate_move(self, state: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
        board = state["board"]
        source = request["from"]
        target = request["to"]
        piece = board.get(source)
        if not piece or piece["actor"] != request["actor"]:
            raise ValidationError(422, "source_not_owned")
        if target in board:
            raise ValidationError(422, "target_occupied")
        if source == target:
            raise ValidationError(422, "illegal_move")
        capture = self._is_capture(state, source, target, piece)
        if state.get("forcedFrom"):
            if source != state["forcedFrom"]:
                raise ValidationError(422, "forced_capture_origin", fromSquare=state["forcedFrom"])
            if not capture:
                raise ValidationError(422, "capture_required")
        if "invalid_move" in self.defects:
            return capture
        if not capture and not self._is_quiet_move(source, target, piece):
            raise ValidationError(422, "illegal_move")
        if not capture and self._has_any_capture(state, request["actor"]):
            raise ValidationError(422, "capture_required")
        return capture

    def _is_quiet_move(self, source: str, target: str, piece: Mapping[str, Any]) -> bool:
        file_delta, rank_delta = self._delta(source, target)
        if abs(file_delta) != 1:
            return False
        return rank_delta in self._allowed_rank_deltas(piece)

    def _is_capture(
        self, state: Mapping[str, Any], source: str, target: str, piece: Mapping[str, Any]
    ) -> bool:
        file_delta, rank_delta = self._delta(source, target)
        if abs(file_delta) != 2 or rank_delta not in {value * 2 for value in self._allowed_rank_deltas(piece)}:
            return False
        middle = chr((ord(source[0]) + ord(target[0])) // 2) + str((int(source[1]) + int(target[1])) // 2)
        jumped = state["board"].get(middle)
        return bool(jumped and jumped["actor"] != piece["actor"])

    @staticmethod
    def _delta(source: str, target: str) -> tuple[int, int]:
        return ord(target[0]) - ord(source[0]), int(target[1]) - int(source[1])

    @staticmethod
    def _allowed_rank_deltas(piece: Mapping[str, Any]) -> set[int]:
        if piece.get("king"):
            return {-1, 1}
        return {1} if piece["actor"] == "red" else {-1}

    def _has_any_capture(self, state: Mapping[str, Any], actor: str, source_only: str | None = None) -> bool:
        board = state["board"]
        for source, piece in board.items():
            if piece["actor"] != actor or (source_only and source != source_only):
                continue
            for file_step in (-2, 2):
                for rank_step in self._allowed_rank_deltas(piece):
                    target_file = ord(source[0]) + file_step
                    target_rank = int(source[1]) + rank_step * 2
                    if ord("a") <= target_file <= ord("h") and 1 <= target_rank <= 8:
                        target = chr(target_file) + str(target_rank)
                        if target not in board and self._is_capture(state, source, target, piece):
                            return True
        return False

    def _apply_move(self, state: dict[str, Any], request: Mapping[str, Any], capture: bool) -> None:
        board = state["board"]
        piece = copy.deepcopy(board.pop(request["from"]))
        if capture:
            middle = chr((ord(request["from"][0]) + ord(request["to"][0])) // 2) + str(
                (int(request["from"][1]) + int(request["to"][1])) // 2
            )
            board.pop(middle)
        if not piece["king"] and ((piece["actor"] == "red" and request["to"][1] == "8") or (piece["actor"] == "black" and request["to"][1] == "1")):
            piece["king"] = True
        board[request["to"]] = piece
        state["version"] += 1
        state["history"].append(
            {
                "actor": request["actor"],
                "from": request["from"],
                "to": request["to"],
                "capture": capture,
                "version": state["version"],
            }
        )
        if capture and self._has_any_capture(state, request["actor"], request["to"]):
            state["forcedFrom"] = request["to"]
        else:
            state["forcedFrom"] = None
            state["turn"] = "black" if request["actor"] == "red" else "red"

    def _apply_duplicate_mutant(self, state: dict[str, Any], request: Mapping[str, Any]) -> Outcome:
        state["version"] += 1
        state["history"].append(
            {
                "actor": request["actor"],
                "from": request["from"],
                "to": request["to"],
                "capture": False,
                "duplicateMutation": True,
                "version": state["version"],
            }
        )
        response = self._public_state(state)
        response["idempotentReplay"] = False
        self._persist(state)
        if "cache" not in self.defects:
            self._cache = None
            self._cache_at = 0.0
        self._observe("duplicate_mutation_applied", version=state["version"])
        return Outcome(200, response)

    def _load_state(self) -> dict[str, Any]:
        value = json.loads(self.state_path.read_text(encoding="utf-8"))
        value.setdefault("idempotency", {})
        value.setdefault("history", [])
        value.setdefault("forcedFrom", None)
        return value

    def _persist(self, state: Mapping[str, Any]) -> None:
        write_state(self.state_path, state)

    @staticmethod
    def _public_state(state: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "board": copy.deepcopy(state["board"]),
            "turn": state["turn"],
            "version": state["version"],
            "forcedFrom": state.get("forcedFrom"),
            "history": copy.deepcopy(state.get("history", [])),
        }

    @staticmethod
    def _error(status: int, error: str, **details: Any) -> Outcome:
        return Outcome(status, {"error": error, **details})

    def _observe(self, event: str, **details: Any) -> None:
        if not self._event_file:
            return
        record = {"event": event, "atMonotonic": round(time.monotonic(), 6), **details}
        try:
            self._event_file.write(json.dumps(record, sort_keys=True) + "\n")
            self._event_file.flush()
        except OSError:
            # Observation failures are visible to a caller through absence of
            # records; they must not make an otherwise valid state mutation lie.
            pass

    def observe_http(
        self,
        *,
        method: str,
        route: str,
        actor_class: str,
        status: int,
        error: Any,
        version_before: int | None,
        version_after: int | None,
    ) -> None:
        """Append a redacted, allowlisted receipt for one explicit HTTP response."""

        if method not in HTTP_RECEIPT_METHODS or route not in HTTP_RECEIPT_ROUTES:
            return
        if actor_class not in HTTP_RECEIPT_ACTOR_CLASSES or status not in HTTP_RECEIPT_STATUSES:
            return
        safe_error = error if isinstance(error, str) and error in HTTP_RECEIPT_ERRORS else None
        if not isinstance(version_before, int) or isinstance(version_before, bool):
            version_before = None
        if not isinstance(version_after, int) or isinstance(version_after, bool):
            version_after = None
        with self._lock:
            self._receipt_sequence += 1
            receipt = {
                "event": "http_request",
                "receipt_id": f"http-{self._receipt_sequence:06d}",
                "method": method,
                "route": route,
                "actor_class": actor_class,
                "status": status,
                "error": safe_error,
                "version_before": version_before,
                "version_after": version_after,
            }
            # This worker-visible copy helps an optional inspection reader.  It
            # is not an integrity-protected source of completion evidence.
            self._observe("http_request", **{key: value for key, value in receipt.items() if key != "event"})
            if self._authoritative_receipt_file:
                try:
                    self._authoritative_receipt_file.write(json.dumps(receipt, sort_keys=True) + "\n")
                    self._authoritative_receipt_file.flush()
                except OSError:
                    self._authoritative_receipt_status["available"] = False
                    self._authoritative_receipt_status["error"] = "receipt_write_failed"
                    self._authoritative_receipt_file.close()
                    self._authoritative_receipt_file = None


def make_handler(store: Store, client_path: Path) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "SyntheticCheckers/1"

        def _send_json(self, status: int, value: Mapping[str, Any]) -> None:
            raw = json.dumps(value, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        @staticmethod
        def _receipt_route(path: str) -> str:
            return path if path in HTTP_RECEIPT_ROUTES else "other"

        @staticmethod
        def _actor_class(body: Mapping[str, Any] | None) -> str:
            actor = body.get("actor") if body is not None else None
            return actor if isinstance(actor, str) and actor in {"red", "black"} else "invalid"

        def _send_observed_json(
            self,
            *,
            method: str,
            route: str,
            actor_class: str,
            version_before: int | None,
            status: int,
            value: Mapping[str, Any],
        ) -> None:
            self._send_json(status, value)
            store.observe_http(
                method=method,
                route=route,
                actor_class=actor_class,
                status=status,
                error=value.get("error"),
                version_before=version_before,
                version_after=store.receipt_version(),
            )

        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            version_before = store.receipt_version()
            if self.path == "/api/state":
                self._send_observed_json(
                    method="GET",
                    route="/api/state",
                    actor_class="invalid",
                    version_before=version_before,
                    status=200,
                    value=store.snapshot(),
                )
                return
            if self.path == "/api/meta":
                self._send_observed_json(
                    method="GET",
                    route="/api/meta",
                    actor_class="invalid",
                    version_before=version_before,
                    status=200,
                    value=store.meta(),
                )
                return
            if self.path == "/":
                raw = client_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
                store.observe_http(
                    method="GET",
                    route="/",
                    actor_class="invalid",
                    status=200,
                    error=None,
                    version_before=version_before,
                    version_after=store.receipt_version(),
                )
                return
            self._send_observed_json(
                method="GET",
                route=self._receipt_route(self.path),
                actor_class="invalid",
                version_before=version_before,
                status=404,
                value={"error": "not_found"},
            )

        def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
            version_before = store.receipt_version()
            route = self._receipt_route(self.path)
            if self.path != "/api/move":
                self._send_observed_json(
                    method="POST",
                    route=route,
                    actor_class="invalid",
                    version_before=version_before,
                    status=404,
                    value={"error": "not_found"},
                )
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length < 1 or length > 65_536:
                    raise ValueError
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError
            except (ValueError, json.JSONDecodeError):
                self._send_observed_json(
                    method="POST",
                    route="/api/move",
                    actor_class="invalid",
                    version_before=version_before,
                    status=400,
                    value={"error": "invalid_json"},
                )
                return
            outcome = store.move(
                actor=body.get("actor"),
                from_square=body.get("from"),
                to_square=body.get("to"),
                expected_version=body.get("expectedVersion"),
                idempotency_key=body.get("idempotencyKey"),
                authorization=self.headers.get("Authorization"),
            )
            self._send_observed_json(
                method="POST",
                route="/api/move",
                actor_class=self._actor_class(body),
                version_before=version_before,
                status=outcome.status,
                value=outcome.body,
            )

        def log_message(self, *_: Any) -> None:
            pass

    return Handler


@dataclass
class RunningFixture:
    server: ThreadingHTTPServer
    thread: threading.Thread
    store: Store

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}"

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.store.unseal_observations()
        self.store.close()


def start_server(
    store: Store, *, client_path: Path | str | None = None, port: int = 0
) -> RunningFixture:
    """Start an in-process, loopback-only HTTP wrapper around a Store."""

    page = Path(client_path or Path(__file__).with_name("client.html")).resolve()
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, page))
    thread = threading.Thread(target=server.serve_forever, name="synthetic-checkers", daemon=True)
    thread.start()
    store.seal_observations()
    return RunningFixture(server=server, thread=thread, store=store)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="workspace containing state.json")
    parser.add_argument("--revision", default=FIXTURE_REVISION)
    parser.add_argument("--config", help="JSON service configuration file")
    parser.add_argument("--defect", action="append", default=[])
    parser.add_argument("--port", type=int, default=0, help="loopback port; 0 asks the OS")
    parser.add_argument(
        "--ready-file",
        "--startup-file",
        dest="ready_file",
        default="service-ready.json",
        help="workspace-relative JSON readiness receipt",
    )
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else None
    observations = workspace / "runtime-observations"
    store = Store(
        workspace / "state.json",
        defects=args.defect,
        revision=args.revision,
        service_config=config,
        observation_dir=observations,
    )
    running = start_server(store, client_path=workspace / "client.html", port=args.port)
    ready = workspace / args.ready_file
    ready.write_text(
        json.dumps(
            {
                "url": running.url,
                "pid": os.getpid(),
                "revision": args.revision,
                "observationRoot": "runtime-observations",
                "authoritativeHttpReceipt": store.meta()["authoritativeHttpReceipt"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"url": running.url, "readyFile": str(ready)}), flush=True)
    try:
        running.thread.join()
    except KeyboardInterrupt:
        pass
    finally:
        running.stop()


if __name__ == "__main__":
    main()
