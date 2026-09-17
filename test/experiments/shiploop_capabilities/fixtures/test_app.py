#!/usr/bin/env python3
"""Thin ordinary checks for the synthetic Checkers fixture's public contract."""

from __future__ import annotations

import http.client
import json
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
APP_ROOT = HERE if (HERE / "app.py").is_file() else HERE.parent
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))
from app import Store, default_state, start_server, write_state  # noqa: E402


class SyntheticCheckersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="shiploop-capability-app-")
        self.workspace = Path(self.temp.name)
        write_state(self.workspace / "state.json", default_state())
        self.store = Store(self.workspace)

    def tearDown(self) -> None:
        self.store.close()
        self.temp.cleanup()

    def _move(self, actor: str, source: str, target: str, version: int, key: str):
        return self.store.move(
            actor=actor,
            from_square=source,
            to_square=target,
            expected_version=version,
            idempotency_key=key,
            authorization=f"Bearer {actor}-fixture-token",
        )

    def test_ordinary_two_turn_persisted_move(self) -> None:
        red = self._move("red", "b2", "c3", 1, "ordinary-red")
        self.assertEqual(200, red.status)
        self.assertEqual("black", red.body["turn"])
        self.assertEqual(2, red.body["version"])
        black = self._move("black", "g7", "f6", 2, "ordinary-black")
        self.assertEqual(200, black.status)
        self.assertEqual("red", black.body["turn"])
        self.assertEqual(3, Store(self.workspace).snapshot()["version"])

    def test_loopback_http_state_and_move(self) -> None:
        running = start_server(self.store)
        try:
            connection = http.client.HTTPConnection("127.0.0.1", running.server.server_port, timeout=2)
            connection.request("GET", "/api/state")
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            self.assertEqual(1, json.loads(response.read())["version"])
            body = json.dumps(
                {
                    "actor": "red",
                    "from": "b2",
                    "to": "c3",
                    "expectedVersion": 1,
                    "idempotencyKey": "http-red",
                }
            )
            connection.request(
                "POST",
                "/api/move",
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer red-fixture-token",
                },
            )
            self.assertEqual(200, connection.getresponse().status)
        finally:
            running.stop()


if __name__ == "__main__":
    unittest.main(verbosity=2)
