"""POSIX command pipes and best-effort publication of retained abort prefixes."""
from __future__ import annotations

import json
import os
import selectors
import stat
import subprocess
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from typing import Callable, Iterable, NamedTuple, Optional, Tuple


class Recovery(NamedTuple):
    run_dir: Path
    action: str
    operation: str


class PipeCapture:
    """The sole output reader, including across a normal timeout."""

    def __init__(self, process: "subprocess.Popen[bytes]"):
        self.process = process
        self.chunks: dict[str, list[bytes]] = {"stdout": [], "stderr": []}
        self.eof = dict.fromkeys(self.chunks, False)
        self.selector: Optional[selectors.BaseSelector] = None

    def capture(self, *, timeout: Optional[float] = None) -> Tuple[bytes, bytes]:
        deadline = None if timeout is None else time.monotonic() + timeout

        def remaining() -> Optional[float]:
            if deadline is None:
                return None
            left = deadline - time.monotonic()
            if left < 0:
                raise subprocess.TimeoutExpired(self.process.args, timeout)
            return left

        try:
            self._capture_pipes(remaining)
        except KeyboardInterrupt:
            # Preserve CPython communicate's first-interrupt teardown grace
            # within the existing deadline. This is not a workload timeout.
            try:
                grace = 0.25 if deadline is None else max(0.0, min(0.25, deadline - time.monotonic()))
                self.process.wait(timeout=grace)
            except BaseException:
                pass  # A failed grace wait must not replace the pipe interrupt.
            raise

        # Pipe EOF and leader exit are separate. Do not reap a leader while a
        # descendant still holds a pipe, except for the interrupt grace above.
        # Popen.wait already handles its own first KeyboardInterrupt.
        self.process.wait(timeout=None if deadline is None else deadline - time.monotonic())
        self.selector.close()
        return b"".join(self.chunks["stdout"]), b"".join(self.chunks["stderr"])

    def _capture_pipes(self, remaining: Callable[[], Optional[float]]) -> None:
        if self.selector is None:
            # Only an explicit empty payload has a stdin pipe on this route.
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.selector = selectors.DefaultSelector()
            for name in self.chunks:
                pipe = getattr(self.process, name)
                os.set_blocking(pipe.fileno(), False)
                self.selector.register(pipe, selectors.EVENT_READ, name)
        selector = self.selector
        while selector.get_map():
            events = selector.select(remaining())
            remaining()
            for key, _ in events:
                try:
                    data = os.read(key.fd, 32768)
                except BlockingIOError:
                    continue  # readiness can be stale
                if data:
                    self.chunks[key.data].append(data)
                    continue
                self.eof[key.data] = True
                selector.unregister(key.fileobj)
                key.fileobj.close()


def close_aborted(process: "subprocess.Popen[bytes]", capture: Optional[PipeCapture]) -> None:
    # Popen uses unbuffered parent pipes and never sends a payload on this path.
    selector = None if capture is None else capture.selector
    for resource in (selector, process.stdin, process.stdout, process.stderr):
        if resource is not None:
            try:
                resource.close()
            except BaseException:
                pass  # try the other descriptors and preserve the capture exception


def _write_exclusive(directory: int, name: str, chunks: Iterable[bytes]) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(name, flags, 0o600, dir_fd=directory)
    try:
        for chunk in chunks:
            rest = memoryview(chunk)
            while rest:
                count = os.write(fd, rest)
                if count <= 0:
                    raise OSError("no progress writing command recovery")
                rest = rest[count:]
    finally:
        os.close(fd)


def publish(recovery: Recovery, capture: PipeCapture) -> None:
    """Publish a completion record last, or leave a visibly partial attempt."""
    path = recovery.run_dir.absolute()
    if ".." in path.parts:
        raise ValueError("command recovery needs a run path without parent traversal")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    with ExitStack() as directories:
        def open_directory(name: str, parent: Optional[int] = None) -> int:
            fd = os.open(name, flags, dir_fd=parent)
            directories.callback(os.close, fd)
            return fd

        run = open_directory(path.anchor)
        for part in path.parts[1:]:
            run = open_directory(part, run)
        try:
            os.mkdir("command-recovery", 0o700, dir_fd=run)
        except FileExistsError:
            pass
        root = open_directory("command-recovery", run)
        info = os.fstat(root)
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise PermissionError("command recovery directory must be private")
        attempt = uuid.uuid4().hex
        os.mkdir(attempt, 0o700, dir_fd=root)
        directory = open_directory(attempt, root)
        for name, chunks in capture.chunks.items():
            _write_exclusive(directory, name, chunks)
        metadata = {
            "action": recovery.action,
            "operation": recovery.operation,
            "streams": {name: {"bytes": sum(map(len, chunks)), "eof": capture.eof[name]}
                        for name, chunks in capture.chunks.items()},
            "incomplete_capture": not all(capture.eof.values()),
            "publication": "complete",
        }
        _write_exclusive(directory, ".metadata.tmp", [(json.dumps(metadata) + "\n").encode("ascii")])
        # Publish atomically and exclusively: a partial metadata write cannot
        # look complete, and an unrelated pre-existing name isn't replaced.
        os.link(".metadata.tmp", "metadata.json", src_dir_fd=directory, dst_dir_fd=directory, follow_symlinks=False)
        os.unlink(".metadata.tmp", dir_fd=directory)
