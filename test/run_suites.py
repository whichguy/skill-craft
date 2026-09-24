#!/usr/bin/env python3
"""Execute fixed hermetic suites selected from :mod:`suite_catalog`.

This runner intentionally owns process lifecycle, output receipts and catalog
coverage checks.  The public Bash entrypoints only preserve familiar command
spelling and forward here, so they cannot drift into separate inventories.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time
from typing import Iterable, Sequence

import suite_catalog


ROOT = Path(__file__).resolve().parents[1]
TOP_LEVEL_TEST_ALLOWLIST = frozenset({
    # Explicit host-dependent checks are invoked through test/run-integration.sh.
    "test/advisors.test.sh",
    "test/cursor-imported-skills.test.sh",
    "test/devloop-gas-weather-native.test.sh",
    "test/review-plan.test.sh",
    # Public entrypoints/wrappers are exercised by their catalog owners.
    "test/shiploop.test.sh",
})
_TEST_SUFFIXES = (".test.py", ".test.sh", ".test.js", ".test.cjs")


class UsageParser(argparse.ArgumentParser):
    """Keep the established CLI's usage failures at EX_USAGE (64)."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(64, f"{self.prog}: error: {message}\n")


@dataclass
class ProcessOutcome:
    status: str
    returncode: int | None
    duration_seconds: float
    stdout: str
    stderr: str
    error: str | None = None


def _parser(*, shiploop_entrypoint: bool = False) -> UsageParser:
    description = (
        "Run ShipLoop's full, smoke, or deterministic sharded hermetic suites."
        if shiploop_entrypoint else
        "Run a deduplicated union of fixed hermetic test groups."
    )
    epilog = (
        "Legacy ShipLoop flags: --smoke, --shard 1/3|2/3|3/3.\n"
        "Use --output with a new directory outside the checkout to retain a "
        "selected/completed receipt and per-suite logs."
        if shiploop_entrypoint else
        "Groups: " + ", ".join(suite_catalog.GROUPS) + "\n"
        "Use --output with a new directory outside the checkout to retain a "
        "selected/completed receipt and per-suite logs."
    )
    parser = UsageParser(
        prog="bash test/shiploop.test.sh" if shiploop_entrypoint else "bash test/run-all.sh",
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog,
    )
    parser.add_argument("--group", action="append", metavar="GROUP",
                        help=(argparse.SUPPRESS if shiploop_entrypoint else
                              "repeatable group; unions are deduplicated in catalog order"))
    parser.add_argument("--list", action="store_true", help="list selected catalog entries without executing")
    parser.add_argument("--output", type=Path, help="new external receipt directory")
    # This is set only by test/shiploop.test.sh.  Keeping it hidden prevents a
    # second user-facing dialect while preserving the wrapper's legacy flags.
    parser.add_argument("--shiploop-entrypoint", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--smoke", action="store_true",
                        help="run/list only the ShipLoop smoke subset" if shiploop_entrypoint else argparse.SUPPRESS)
    parser.add_argument("--shard", metavar="N/3",
                        help="run/list deterministic ShipLoop shard 1/3, 2/3, or 3/3" if shiploop_entrypoint else argparse.SUPPRESS)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> tuple[argparse.Namespace, tuple[str, ...], bool]:
    """Parse either the root or legacy ShipLoop wrapper dialect without work."""

    raw_argv = tuple(sys.argv[1:] if argv is None else argv)
    parser = _parser(shiploop_entrypoint="--shiploop-entrypoint" in raw_argv)
    args = parser.parse_args(raw_argv)
    if args.list and args.output is not None:
        parser.error("--output cannot be used with --list")

    if args.shiploop_entrypoint:
        for option in ("--list", "--smoke", "--shard"):
            if sum(value.split("=", 1)[0] == option for value in raw_argv) > 1:
                parser.error(f"{option} may be specified only once")
        if args.group:
            parser.error("--group is not accepted by test/shiploop.test.sh")
        if args.smoke and args.shard:
            parser.error("--smoke and --shard cannot be combined")
        if args.shard and args.shard not in {"1/3", "2/3", "3/3"}:
            parser.error("--shard must be 1/3, 2/3, or 3/3")
        if args.smoke:
            groups = ("smoke",)
        elif args.shard:
            groups = (f"shiploop-{args.shard[0]}",)
        else:
            groups = ("shiploop",)
        return args, groups, True

    if args.smoke or args.shard:
        parser.error("--smoke and --shard are only accepted by test/shiploop.test.sh")
    groups = tuple(args.group or ("all",))
    unknown = set(groups) - set(suite_catalog.GROUPS)
    if unknown:
        parser.error("unknown group: " + ", ".join(sorted(unknown)))
    return args, groups, False


def _inside(path: Path, possible_parent: Path) -> bool:
    try:
        path.relative_to(possible_parent)
    except ValueError:
        return False
    return True


def prepare_output(path: Path, root: Path) -> Path:
    """Create only a new external receipt directory."""

    output = path.expanduser().resolve()
    checkout = root.resolve()
    if output.exists():
        raise ValueError("--output must name a new directory")
    if _inside(output, checkout):
        raise ValueError("--output must be outside the checkout")
    output.mkdir(parents=True)
    (output / "logs").mkdir()
    return output


def _fixed_top_level_tests(root: Path) -> set[str]:
    test_root = root / "test"
    if not test_root.is_dir():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in test_root.iterdir()
        if path.is_file() and path.name.endswith(_TEST_SUFFIXES)
    }


def catalog_omissions(root: Path, suites: Iterable[suite_catalog.Suite] = suite_catalog.SUITES) -> tuple[str, ...]:
    """Report missing fixed targets and unclassified top-level test files."""

    entries = tuple(suites)
    missing = [suite.path for suite in entries if not (root / suite.path).is_file()]
    cataloged_top_level = {
        suite.path for suite in entries
        if suite.path.startswith("test/") and "/" not in suite.path.removeprefix("test/")
    }
    unclassified = sorted(
        _fixed_top_level_tests(root) - cataloged_top_level - TOP_LEVEL_TEST_ALLOWLIST
    )
    return tuple([*(f"missing catalog target: {path}" for path in missing),
                  *(f"unclassified top-level test: {path}" for path in unclassified)])


def _read_command(argv: Sequence[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    except OSError as exc:
        return f"unavailable: {exc}"
    if result.returncode:
        return f"unavailable (exit {result.returncode}): {result.stderr.strip()}"
    return (result.stdout or result.stderr).strip()


def source_identity(root: Path) -> dict[str, object]:
    """Collect checkout evidence without mutating the checkout."""

    def git(*args: str) -> str | None:
        value = _read_command(("git", *args), root)
        return value if value and not value.startswith("unavailable") else None

    status = git("status", "--porcelain=v1")
    try:
        dirty = subprocess.run(
            ("git", "diff", "--binary", "HEAD"), cwd=root,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False,
        )
    except OSError:
        dirty_digest = None
    else:
        dirty_digest = hashlib.sha256(dirty.stdout).hexdigest() if dirty.returncode == 0 else None
    return {
        "head": git("rev-parse", "HEAD"),
        "tree": git("rev-parse", "HEAD^{tree}"),
        "status": status.splitlines() if status else [],
        "dirty_diff_sha256": dirty_digest,
    }


def runtime_versions(root: Path) -> dict[str, str | None]:
    """Record resolved local runtimes, never an arbitrary environment dump."""

    return {
        "python3": _read_command(("python3", "--version"), root),
        "node": _read_command(("node", "--version"), root),
        "bash": _read_command(("bash", "--version"), root),
    }


def _terminate_process_group(process: subprocess.Popen[str]) -> str | None:
    """Terminate a timed-out process and its descendants on supported hosts."""

    warnings = []
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            warnings.append(f"TERM: {exc}")
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        # The leader can exit before a descendant that inherited its pipes.
        # Kill the process group even after that leader has exited; otherwise a
        # TERM-ignoring descendant can make communicate() wait indefinitely.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            # Darwin can return EPERM once an orphaned group has disappeared.
            # Retain the diagnostic; the timeout still fails and draining stays bounded.
            warnings.append(f"KILL: {exc}")
    else:
        if process.poll() is None:
            process.kill()
    return "; ".join(warnings) or None


def run_process(argv: Sequence[str], *, cwd: Path, timeout_seconds: float) -> ProcessOutcome:
    """Run a fixed argv with a bounded lifetime and collected output."""

    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(argv), cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, errors="replace", start_new_session=True,
        )
    except OSError as exc:
        return ProcessOutcome(
            status="failed", returncode=None, duration_seconds=time.monotonic() - started,
            stdout="", stderr="", error=str(exc),
        )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        cleanup_warning = _terminate_process_group(process)
        cleanup_detail = f"; cleanup: {cleanup_warning}" if cleanup_warning else ""
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired as drain:
            # Do not turn a timeout into an unbounded wait if an escaped child
            # kept a captured descriptor open.  The leader's result is enough
            # to report the bounded failure, and the pipe handles are closed.
            stdout = drain.output or ""
            stderr = drain.stderr or ""
            if isinstance(stdout, bytes):
                stdout = stdout.decode("utf-8", errors="replace")
            if isinstance(stderr, bytes):
                stderr = stderr.decode("utf-8", errors="replace")
            for stream in (process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
            return ProcessOutcome(
                status="timed_out", returncode=process.returncode,
                duration_seconds=time.monotonic() - started, stdout=stdout, stderr=stderr,
                error=f"timed out after {timeout_seconds:g} seconds; output drain timed out{cleanup_detail}",
            )
        return ProcessOutcome(
            status="timed_out", returncode=process.returncode,
            duration_seconds=time.monotonic() - started, stdout=stdout, stderr=stderr,
            error=f"timed out after {timeout_seconds:g} seconds{cleanup_detail}",
        )
    return ProcessOutcome(
        status="passed" if process.returncode == 0 else "failed",
        returncode=process.returncode, duration_seconds=time.monotonic() - started,
        stdout=stdout, stderr=stderr,
    )


def _write_log(output: Path | None, index: int, identifier: str, stream: str, value: str) -> str | None:
    if output is None:
        return None
    relative = Path("logs") / f"{index:03d}-{identifier}.{stream}.log"
    (output / relative).write_text(value, encoding="utf-8")
    return relative.as_posix()


def _emit(outcome: ProcessOutcome) -> None:
    if outcome.stdout:
        print(outcome.stdout, end="" if outcome.stdout.endswith("\n") else "\n")
    if outcome.stderr:
        print(outcome.stderr, end="" if outcome.stderr.endswith("\n") else "\n", file=sys.stderr)
    if outcome.error:
        print(outcome.error, file=sys.stderr)


def _command_record(suite: suite_catalog.Suite) -> dict[str, object]:
    return {
        "id": suite.id,
        "family": suite.family,
        "path": suite.path,
        "command": shlex.join(suite.argv),
        "timeout_seconds": suite.timeout_seconds,
        "hermetic": suite.hermetic,
    }


def _outcome_record(
    suite: suite_catalog.Suite,
    outcome: ProcessOutcome,
    output: Path | None,
    index: int,
) -> dict[str, object]:
    result = _command_record(suite)
    result.update({
        "status": outcome.status,
        "returncode": outcome.returncode,
        "duration_seconds": round(outcome.duration_seconds, 3),
        "stdout_log": _write_log(output, index, suite.id, "stdout", outcome.stdout),
        "stderr_log": _write_log(output, index, suite.id, "stderr", outcome.stderr),
    })
    if outcome.error:
        result["error"] = outcome.error
    return result


def _write_receipt(output: Path, receipt: dict[str, object]) -> None:
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _print_list(selected: Iterable[suite_catalog.Suite], *, shiploop_entrypoint: bool) -> None:
    for suite in selected:
        if shiploop_entrypoint:
            # Legacy ShipLoop --list consumers expect one bare test path per row.
            print(suite.path)
        else:
            print(f"{suite.family}\t{suite.id}\t{shlex.join(suite.argv)}")


def main(argv: Sequence[str] | None = None) -> int:
    args, groups, shiploop_entrypoint = parse_args(argv)
    selected = suite_catalog.select(groups)
    if shiploop_entrypoint:
        # Root --group smoke includes core by design.  The legacy ShipLoop
        # facade is intentionally narrower and lists/runs its ShipLoop paths only.
        selected = tuple(suite for suite in selected if suite.family == "shiploop")
    if args.list:
        _print_list(selected, shiploop_entrypoint=shiploop_entrypoint)
        return 0

    problems = catalog_omissions(ROOT)
    if problems:
        for problem in problems:
            print(f"run-suites: {problem}", file=sys.stderr)
        return 1

    try:
        output = prepare_output(args.output, ROOT) if args.output else None
    except ValueError as exc:
        _parser(shiploop_entrypoint=shiploop_entrypoint).error(str(exc))
        raise AssertionError("unreachable")

    receipt: dict[str, object] = {
        "schema": "skill-craft-hermetic-receipt/1",
        "entrypoint": "shiploop" if shiploop_entrypoint else "run-all",
        "groups": list(groups),
        "source": source_identity(ROOT),
        "runtimes": runtime_versions(ROOT),
        "selected": [_command_record(suite) for suite in selected],
        "completed": [],
        "status": "running",
    }
    if output is not None:
        _write_receipt(output, receipt)
    failures = False
    completed: list[dict[str, object]] = []
    for index, suite in enumerate(selected, start=1):
        print(f"==> [{suite.family}] {suite.id}")
        outcome = run_process(suite.argv, cwd=ROOT, timeout_seconds=suite.timeout_seconds)
        _emit(outcome)
        record = _outcome_record(suite, outcome, output, index)
        completed.append(record)
        receipt["completed"] = completed
        if output is not None:
            _write_receipt(output, receipt)
        if outcome.status != "passed":
            failures = True
            print(f"FAIL {suite.id}", file=sys.stderr)
        else:
            print(f"OK   {suite.id}")
    receipt["status"] = "failed" if failures else "passed"
    if output is not None:
        _write_receipt(output, receipt)
        print(f"receipt: {output / 'receipt.json'}")

    label = "shiploop.test.sh" if shiploop_entrypoint else "run-all.sh"
    if failures:
        print(f"{label}: FAILED", file=sys.stderr)
        return 1
    print(f"{label}: PASS ({', '.join(groups)} hermetic group selection)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
