#!/usr/bin/env python3
"""Deterministic public-contract checks for the Battleship probe."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class CheckFailure(RuntimeError):
    pass


class RequestRejected(CheckFailure):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class CoordinateOriginRetry(CheckFailure):
    pass


class GridIncomplete(CheckFailure):
    pass


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class PageTitle(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.in_title = False
        self.title_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join(" ".join(self.title_parts).split())


def page_title(document: str) -> str:
    parser = PageTitle()
    parser.feed(document)
    return parser.title


class RunningServer:
    def __init__(self, work: Path, diagnostics: Path):
        self.work = work
        self.port = free_port()
        self.base = f"http://127.0.0.1:{self.port}"
        self.log_path = diagnostics / "server.log"
        self.log_file = self.log_path.open("wb")
        env = dict(os.environ, PORT=str(self.port))
        try:
            self.process = subprocess.Popen(
                ["node", "server.js"],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
            )
        except Exception:
            self.log_file.close()
            raise

    def __enter__(self) -> "RunningServer":
        deadline = time.monotonic() + 8
        try:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise CheckFailure(f"node server exited with status {self.process.returncode}")
                try:
                    self.get("/")
                    return self
                except (URLError, TimeoutError, OSError):
                    time.sleep(0.05)
            raise CheckFailure(f"server did not answer on its assigned port {self.port}")
        except Exception:
            self.stop()
            raise

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def stop(self) -> None:
        if self.process.poll() is None:
            try:
                self.process.terminate()
            except ProcessLookupError:
                pass
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    self.process.kill()
                except ProcessLookupError:
                    pass
                self.process.wait(timeout=3)
        if not self.log_file.closed:
            self.log_file.close()

    def get(self, path: str) -> bytes:
        with urlopen(f"{self.base}{path}", timeout=2) as response:
            if response.status < 200 or response.status >= 300:
                raise CheckFailure(f"GET {path} returned HTTP {response.status}")
            return response.read(2_000_000)

    def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            f"{self.base}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=3) as response:
                if response.status < 200 or response.status >= 300:
                    raise CheckFailure(f"POST {path} returned HTTP {response.status}")
                result = json.loads(response.read(1_000_000).decode("utf-8"))
        except HTTPError as error:
            raise RequestRejected(error.code, f"POST {path} returned HTTP {error.code}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CheckFailure(f"POST {path} did not return valid JSON") from error
        if not isinstance(result, dict):
            raise CheckFailure(f"POST {path} did not return a JSON object")
        return result


def find_game_id(payload: Any) -> Any:
    if isinstance(payload, dict):
        for key in ("game", "id", "gameId"):
            value = payload.get(key)
            if value is not None and value != "":
                return value
    raise CheckFailure("GET /api/new did not return a game id")


def check_page(server: RunningServer, *, scoring: bool) -> None:
    document = server.get("/").decode("utf-8", errors="replace")
    title = page_title(document)
    if title != "Battleship":
        raise CheckFailure(f"GET / page title was {title!r}, expected 'Battleship'")
    print("HTTP page title=Battleship.")
    if scoring:
        print("Rendered score panel, accuracy calculation, ship-name display, and browser interaction: UNVERIFIED.")
    else:
        print("Playable 10x10 UI behavior: UNVERIFIED (this check has no browser runtime).")


def coordinates(reverse: bool, origin: int) -> list[tuple[int, int]]:
    points = [(row, col) for row in range(origin, origin + 10) for col in range(origin, origin + 10)]
    return list(reversed(points)) if reverse else points


def valid_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def check_lifecycle_grid(
    server: RunningServer, *, scoring: bool, reverse: bool, origin: int
) -> tuple[int, int, int]:
    try:
        new_game = json.loads(server.get("/api/new").decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CheckFailure("GET /api/new did not return valid JSON") from error
    game = find_game_id(new_game)
    shots = 0
    hits = 0
    sunk_count = 0
    finished = False
    seen_non_miss = False

    for row, col in coordinates(reverse, origin):
        try:
            response = server.post_json("/api/fire", {"game": game, "row": row, "col": col})
        except RequestRejected as error:
            if origin == 0 and shots == 0 and error.status in (400, 422):
                raise CoordinateOriginRetry(str(error)) from error
            raise
        result = response.get("result")
        if result not in ("miss", "hit", "sunk"):
            raise CheckFailure(f"shot ({row}, {col}) returned invalid result {result!r}")
        shots += 1
        if result in ("hit", "sunk"):
            hits += 1
            seen_non_miss = True
        if result == "sunk":
            sunk_count += 1
            if scoring:
                ship = response.get("ship")
                if not isinstance(ship, str) or not ship.strip():
                    raise CheckFailure(f"sunk shot ({row}, {col}) did not name the ship")

        game_over = response.get("gameOver")
        if not isinstance(game_over, bool):
            raise CheckFailure(f"shot ({row}, {col}) did not return boolean gameOver")
        if scoring:
            response_shots = response.get("shots")
            response_hits = response.get("hits")
            if not valid_integer(response_shots) or response_shots != shots:
                raise CheckFailure(f"shot ({row}, {col}) reported shots={response_shots!r}; expected {shots}")
            if not valid_integer(response_hits) or response_hits != hits:
                raise CheckFailure(f"shot ({row}, {col}) reported hits={response_hits!r}; expected {hits}")

        if game_over:
            finished = True
            break

    if not finished:
        raise GridIncomplete(f"the game did not reach gameOver=true after scanning origin-{origin} coordinates")
    if not seen_non_miss:
        raise CheckFailure("no shot returned hit or sunk while completing the game")
    if sunk_count == 0:
        raise CheckFailure("the completed game never returned result='sunk'")
    return shots, hits, sunk_count


def check_lifecycle(server: RunningServer, *, scoring: bool, reverse: bool) -> tuple[int, int, int, int]:
    try:
        shots, hits, sunk_count = check_lifecycle_grid(
            server, scoring=scoring, reverse=reverse, origin=0
        )
        return shots, hits, sunk_count, 0
    except (CoordinateOriginRetry, GridIncomplete) as zero_based_error:
        try:
            shots, hits, sunk_count = check_lifecycle_grid(
                server, scoring=scoring, reverse=reverse, origin=1
            )
            return shots, hits, sunk_count, 1
        except CheckFailure as one_based_error:
            raise CheckFailure(
                f"coordinate scans failed (zero-based: {zero_based_error}; one-based: {one_based_error})"
            ) from one_based_error


def check_tests(work: Path, diagnostics: Path) -> int:
    try:
        result = subprocess.run(
            ["node", "--test"],
            cwd=work,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as error:
        raise CheckFailure("node executable was not found") from error
    except subprocess.TimeoutExpired as error:
        output = error.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        (diagnostics / "node-test.log").write_text(output + "\nTimed out after 120 seconds.\n")
        raise CheckFailure("node --test timed out after 120 seconds") from error
    output = result.stdout or ""
    (diagnostics / "node-test.log").write_text(output)
    if result.returncode != 0:
        raise CheckFailure(f"node --test exited {result.returncode}")

    test_counts = [int(value) for value in re.findall(r"(?m)^(?:ℹ|#)\s+tests\s+(\d+)\s*$", output)]
    pass_counts = [int(value) for value in re.findall(r"(?m)^(?:ℹ|#)\s+pass\s+(\d+)\s*$", output)]
    if not test_counts or max(test_counts) < 1 or not pass_counts or max(pass_counts) < 1:
        tap_plan = re.search(r"(?m)^1\.\.([1-9]\d*)\s*$", output)
        tap_pass = re.search(r"(?m)^ok\s+\d+\b", output)
        if not tap_plan or not tap_pass:
            raise CheckFailure("node --test completed without evidence of a passing test")
        count = int(tap_plan.group(1))
    else:
        count = max(test_counts)
    return count


def create_diagnostics() -> Path:
    configured = os.environ.get("SHIPLOOP_BATTLESHIP_DIAGNOSTICS")
    parent = Path(configured).expanduser() if configured else None
    if parent:
        parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="shiploop-battleship-", dir=parent))


def report_diagnostics(path: Path) -> None:
    print(f"Diagnostics retained at: {path}", file=sys.stderr)
    for filename in ("server.log", "node-test.log"):
        log_path = path / filename
        if log_path.is_file():
            log = log_path.read_text(errors="replace").strip()
            if log:
                print(f"{filename} tail:", file=sys.stderr)
                print(log[-4000:], file=sys.stderr)


def run(action: str, work: Path) -> None:
    diagnostics = create_diagnostics()
    if action == "tests":
        try:
            count = check_tests(work, diagnostics)
        except CheckFailure:
            report_diagnostics(diagnostics)
            raise
        shutil.rmtree(diagnostics, ignore_errors=True)
        print(f"node --test: passing tests observed ({count}).")
        return

    try:
        with RunningServer(work, diagnostics) as server:
            check_page(server, scoring=(action == "scoring"))
            shots, hits, sunk_count, origin = check_lifecycle(
                server,
                scoring=(action == "scoring"),
                reverse=(action == "transfer"),
            )
        shutil.rmtree(diagnostics, ignore_errors=True)
        label = "scoring" if action == "scoring" else "delivery lifecycle"
        order = "reverse" if action == "transfer" else "row-major"
        print(f"Battleship {label}: PASS; {shots} shots, {hits} hits, {sunk_count} sunk result(s), {order} coordinate order, origin {origin}.")
    except (CheckFailure, HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        report_diagnostics(diagnostics)
        if isinstance(error, CheckFailure):
            raise
        raise CheckFailure(f"HTTP/server check failed: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("tests", "delivery", "scoring", "transfer"))
    args = parser.parse_args()
    try:
        run(args.action, Path.cwd())
    except CheckFailure as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
